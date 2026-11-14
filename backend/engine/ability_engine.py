"""
Interprète les fichiers JSON d'abilities (backend/abilities/red/*.json)
contre l'état courant du jeu. Le moteur ne connaît QUE les registres de
predicates.py / effects.py - il n'a aucune logique spécifique à "psexec" ou
"DCSync". Voir docs/02-ability-system-design.md pour le pourquoi.
"""
from __future__ import annotations

import json
from pathlib import Path

from . import effects as effects_mod
from . import predicates as predicates_mod
from .models import ActionContext, ActionResult, GameState, LogEvent


class Ability:
    def __init__(self, data: dict):
        self.id = data["id"]
        self.team = data["team"]
        self.name = data["name"]
        self.requires = data.get("requires", [])
        self.noise = data.get("noise", 0)
        self.critical = data.get("critical", False)
        self.effects = data.get("effects", [])
        self.artifacts = data.get("artifacts", [])
        # Métadonnée de catalogue. Les arguments sont analysés par les parsers
        # spécialisés ; ce texte ne constitue pas une grammaire exécutable.
        self.command = data.get("command")
        self.help = data.get("help", "")
        self.tier = data.get("tier", 0)

    @staticmethod
    def load(path: Path) -> "Ability":
        return Ability(json.loads(path.read_text(encoding='utf-8')))


def load_abilities(directory: Path) -> dict[str, Ability]:
    abilities = {}
    for path in sorted(directory.glob("*.json")):
        ability = Ability.load(path)
        abilities[ability.id] = ability
    return abilities


def resolve(ability: Ability, state: GameState, ctx: ActionContext) -> ActionResult:
    # 1. Prérequis : tout échec est déterministe et explicite, pas de hasard
    #    caché sur le succès logique.
    for req in ability.requires:
        req = dict(req)
        pred_type = req.pop("type")
        predicate = predicates_mod.REGISTRY.get(pred_type)
        if predicate is None:
            raise KeyError(f"Prédicat inconnu: {pred_type} (ability {ability.id})")
        if not predicate(state, ctx, **req):
            return ActionResult(
                success=False,
                message=f"{ability.name} a échoué sur {ctx.target.hostname}",
                reason=f"prerequisite failed: {pred_type}",
            )

    # 2. Protection de l'hôte : la politique déclarée par le scénario décide (engine/security.py).
    #    Même action, même protection ; pas de loterie.
    from .security import inspect_action
    protected = inspect_action(state, ability, ctx)
    if protected is not None:
        return protected

    # 3. Effets - mutent l'état.
    for eff in ability.effects:
        eff = dict(eff)
        eff_type = eff.pop("type")
        effect_fn = effects_mod.REGISTRY.get(eff_type)
        if effect_fn is None:
            raise KeyError(f"Effet inconnu: {eff_type} (ability {ability.id})")
        effect_fn(state, ctx, **eff)

    # 4. Logs générés depuis les artifacts déclarés - alimentent le SIEM (siem.py).
    for artifact in ability.artifacts:
        artifact = {**artifact, "data": dict(artifact.get("data", {}))}
        if artifact["event_id"] == "4624":
            if ctx.params.get("kerberos_ticket"):
                artifact["data"].update(LogonProcessName="Kerberos", AuthenticationPackageName="Kerberos", KeyLength=0)
            else:
                # NTLM avec l'empreinte seule (pass-the-hash) : pas de clé de session, KeyLength 0 ;
                # avec le mot de passe, une connexion NTLM ordinaire (128).
                by_hash = ctx.credential is not None and ctx.credential.type == "NTLM_HASH"
                artifact["data"].update(LogonProcessName="NtLmSsp", AuthenticationPackageName="NTLM", KeyLength=0 if by_hash else 128)
        state.logs.append(
            LogEvent(
                event_id=artifact["event_id"],
                host_id=ctx.target.id,
                tick=ctx.tick,
                data=artifact.get("data", {}),
            )
        )

    if ctx.params.get("kerberos_ticket"):
        state.logs.append(LogEvent("4769", ctx.target.id, ctx.tick, {"ServiceName": "cifs/" + ctx.target.hostname, "user": ctx.params.get("ticket_user")}))

    return ActionResult(
        success=True,
        message=f"{ability.name} a réussi sur {ctx.target.hostname}",
        noise=ability.noise,
    )
