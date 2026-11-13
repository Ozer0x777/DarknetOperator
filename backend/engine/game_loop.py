"""
Boucle de jeu d'une mission.

Les actions du joueur sont D'ABORD mises en file (GameLoop.submit), puis
traitées à chaque GameLoop.tick(), dans l'ordre : actions du joueur ->
défense automatique -> bruit de fond -> SIEM -> conditions de fin.
C'est cette classe que l'API (backend/api/) pilote à intervalle régulier.
"""
from __future__ import annotations

from dataclasses import dataclass, asdict, field
from pathlib import Path

from . import ability_engine, blue_ai, contracts, noise, siem, trace, win_conditions
from .ability_engine import Ability
from .models import ActionContext, ActionResult, Alert, GameState, HistoryEntry

ABILITIES_ROOT = Path(__file__).parent.parent / "abilities"


def load_all_abilities() -> dict[str, Ability]:
    return ability_engine.load_abilities(ABILITIES_ROOT / "red")


@dataclass
class QueuedAction:
    team: str                        # toujours "red" : le joueur ; la défense agit dans blue_ai
    ability_id: str
    target_id: str
    credential_username: str | None = None
    credential_type: str | None = None
    console_id: str = "main"
    ready_tick: int = 0
    params: dict = field(default_factory=dict)


class GameLoop:
    def __init__(self, state: GameState, abilities: dict[str, Ability] | None = None):
        self.state = state
        self.abilities = abilities or load_all_abilities()
        self._queue: list[QueuedAction] = [QueuedAction(**a) for a in state.pending_actions]

    def submit(self, action: QueuedAction) -> None:
        if self.state.status != "RUNNING":
            raise RuntimeError("La partie est terminée, aucune action n'est acceptée.")
        if len(self._queue) >= 20:
            raise RuntimeError("Trop d'actions en attente.")
        delay = 1
        if any(n["id"] == "tor" for n in self.state.trace.get("nodes", [])):
            delay += 1
        if action.ability_id == "red.recon_scan":
            delay += {0:5,1:4,2:2,3:0,4:0,5:0}.get(action.params.get("scan_timing",3),0)
        if action.ability_id == "red.crack_hash":
            gpu = max([int(i[-1]) for i in self.state.inventory if i.startswith("gpu")] or [0])
            delay += {0: 8, 1: 4, 2: 2, 3: 1}.get(gpu, 1)
            if "wordlist" in self.state.inventory and action.params.get("wordlist") == "/home/operator/wordlist.txt":
                delay = max(1, delay - 2)
        if action.params.get("gophish_campaign_id"):
            host = self.state.hosts[action.target_id]
            delay += max(0, host.phishing.get("delay_ticks", 1) - 1)
            model = host.phishing.get('human_model')
            if model: delay += self.state.rng.randint(model.get('delay_min',1), model.get('delay_max',5))
            from .world_time import wait_until_available
            wait = wait_until_available(self.state.environment.get('world_minute', self.state.tick // 3), host.phishing.get('availability'))
            delay += wait * 3
            action.params["availability_wait_minutes"] = wait
            action.params["created_tick"] = self.state.tick
        action.ready_tick = self.state.tick + delay
        self._queue.append(action)
        self.state.pending_actions = [asdict(a) for a in self._queue]

    def cancel_console(self, console_id: str) -> None:
        self._queue = [a for a in self._queue if a.console_id != console_id or (a.params.get("gophish_campaign_id") and self.state.tool_services.get("gophish", {}).get("running") and self.state.tool_services["gophish"].get("owner") != console_id)]
        self.state.pending_actions = [asdict(a) for a in self._queue]

    def tick(self) -> list[ActionResult]:
        """Traite un tick complet. Renvoie les ActionResult du tick (narration)."""
        state = self.state
        if state.status != "RUNNING":
            return []

        state.tick += 1
        results: list[ActionResult] = []

        from .shell_tools import advance_campaigns
        advance_campaigns(state)

        # 1 & 2. Actions Red puis Blue — §5.2 : phase RED d'abord, phase BLUE
        #        ensuite, dans l'ordre où elles ont été soumises.
        pending = [a for a in self._queue if a.ready_tick <= state.tick]
        self._queue = [a for a in self._queue if a.ready_tick > state.tick]
        state.pending_actions = [asdict(a) for a in self._queue]
        for action in pending:
            if state.status != "RUNNING":
                break
            results.append(self._resolve_queued(action))

        blue_ai.advance(state)

        # 3. Bruit de fond — §5.5 : logs légitimes qui ne matchent aucune règle.
        noise.generate(state)

        # 4. SIEM — évalue tous les logs produits CE tick (actions + bruit).
        new_logs = [log for log in state.logs if log.tick == state.tick]
        siem.evaluate(state, new_logs)
        trace.advance(state)

        # 5. Conditions de victoire — §11.4. 6. Messages du client selon la progression du joueur.
        if not self.finish_if_won(): contracts.advance(state)

        return results

    def has_pending(self) -> bool:
        """Vrai si une action attend encore sa résolution."""
        return bool(self._queue)

    def pending(self) -> list:
        """Copie des actions en attente, dans l'ordre de résolution (lecture seule pour l'appelant)."""
        return list(self._queue)

    def finish_if_won(self) -> bool:
        """Termine la mission si une condition de fin est atteinte et fait conclure le client.
        Seul endroit où une mission se termine d'elle-même : le tick et les lectures hors tick l'appellent."""
        state = self.state
        if state.status != "RUNNING": return False
        winner = win_conditions.check(state)
        if not winner: return False
        state.status, state.winner = "ENDED", winner
        if state.end_reason is None:
            state.end_reason = "objectives" if winner == "RED" else "timeout"
        contracts.advance(state)
        return True

    def abandon(self) -> bool:
        """Le joueur quitte la mission : elle se termine comme un échec « disconnected »."""
        state = self.state
        if state.status != "RUNNING": return False
        state.status, state.winner, state.end_reason = "ENDED", "BLUE", "disconnected"
        contracts.advance(state)
        return True

    def _resolve_queued(self, action: QueuedAction) -> ActionResult:
        state = self.state

        ability = self.abilities.get(action.ability_id)
        if ability is None:
            result = ActionResult(False, f"Ability inconnue: {action.ability_id}", reason="unknown_ability")
            state.history.append(HistoryEntry(state.tick, action.team, result.message, False, result.reason, action.console_id))
            _log_console(state, action, result.message)
            return result

        target = state.hosts.get(action.target_id)
        if target is None:
            result = ActionResult(False, f"Cible inconnue: {action.target_id}", reason="unknown_target")
            state.history.append(HistoryEntry(state.tick, action.team, result.message, False, result.reason, action.console_id))
            _log_console(state, action, result.message)
            return result

        credential = (
            state.find_credential(action.credential_username, action.credential_type)
            if action.credential_username else None
        )
        if action.params.get('credential_value') is not None:
            credential = next((c for c in reversed(state.loot) if c.username==action.credential_username and c.valid and (action.credential_type is None or c.type==action.credential_type) and c.value==action.params['credential_value']), None)
        params = dict(action.params)

        ctx = ActionContext(
            actor=action.team, target=target, tick=state.tick,
            credential=credential, params=params,
        )

        from .console_sessions import using
        from .terminal_native import output
        # Une console fermée entre-temps n'est pas recréée : le résultat arrive dans la console principale.
        if action.console_id != "main" and action.console_id not in state.terminals: action.console_id = "main"
        ctx.params["console_id"] = action.console_id
        with using(state, action.console_id):
            if ctx.params.get("gophish_campaign_id") and not state.tool_services.get("gophish", {}).get("running"):
                result = ActionResult(False, "GoPhish est arrêté : la campagne ne peut pas envoyer le message.", reason="service_stopped")
            elif ctx.params.get("gophish_campaign_id") and not ctx.params.get('smtp_available', True):
                result = ActionResult(False, "SMTP : impossible de joindre le serveur du profil d’envoi. Vérifie le profil smtp de la campagne.", reason='smtp_unavailable')
            elif ctx.params.get("gophish_campaign_id") and ctx.params.get('mail_filtered'):
                result = ActionResult(False, "Le message a été retenu par le filtre de messagerie du laboratoire.", reason='mail_filtered')
            elif ctx.params.get("gophish_campaign_id") and not ctx.params.get('capture_passwords', True):
                result = ActionResult(False, "Le destinataire a ouvert la page, mais la capture des mots de passe n’est pas activée.", reason='capture_disabled')
            else:
                from .human_behavior import decide
                response = decide(state,target,ctx.params) if ctx.params.get('gophish_campaign_id') else None
                if response in {'ignored','reported'}:
                    message = 'Le destinataire a signalé le message comme inhabituel.' if response == 'reported' else 'Le destinataire n’a pas soumis d’identifiants pendant ce créneau.'
                    result = ActionResult(False,message,reason='recipient_'+response)
                    if response == 'reported':
                        previous_reports = sum(a.rule_id == "USER-REPORT" and a.host_id == target.id for a in state.alerts)
                        state.alerts.append(Alert(state.next_alert_id(), "Messages répétés signalés" if previous_reports else "Message signalé par un utilisateur", "HIGH" if previous_reports else "MEDIUM", "USER-REPORT", target.id, state.tick, state.tick))
                else:
                    result = ability_engine.resolve(ability,state,ctx)
            from .shell_tools import finish_campaign
            finish_campaign(state, ctx, result)
            if result.success:
                detail = output(ability.id, state, ctx)
                if detail:
                    result.message = detail if ability.id == 'red.crack_hash' else result.message + "\n" + detail
                if ability.id == 'red.crack_hash' and ctx.params.get('hashes') and not all(value in ctx.params.get('crack_matches', {}) for value in ctx.params['hashes']):
                    # Les correspondances partielles restent dans le potfile ; la commande, elle, a échoué.
                    result.success, result.reason = False, 'wordlist_exhausted'
            if not ctx.params.get('gophish_campaign_id'):
                state.terminal_last_exit = state.terminal_last_native_exit = 0 if result.success else 1
        state.history.append(HistoryEntry(state.tick, action.team, result.message, result.success, result.reason, action.console_id, 0 if result.success else 1))
        _log_console(state, action, result.message)

        # Un prérequis manquant est un échec de l'action, jamais une défaite
        # instantanée : le joueur peut attendre le rétablissement et réessayer.

        # Détection heuristique liée au bruit : une action très bruyante peut
        # être repérée même sans règle SIEM dédiée : c'est ce qui donne un
        # effet au champ `noise` des outils.
        if result.success and result.noise >= 70 and state.rng.random() < result.noise / 200:
            alert = Alert(
                id=state.next_alert_id(),
                title="Activité suspecte (bruit élevé)",
                severity="MEDIUM",
                rule_id="HEURISTIC-NOISE",
                host_id=target.id,
                attack_tick=state.tick,
                detected_tick=state.tick,
            )
            state.alerts.append(alert)

        return result


def _log_console(state, action, message) -> None:
    """Les résultats différés apparaissent aussi dans l'historique sauvegardé de la console."""
    if action.team == "red" and action.console_id:
        from .console_sessions import record
        record(state, action.console_id, [f"[{state.tick}] {message}"])
