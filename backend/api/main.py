"""
API FastAPI + WebSocket par-dessus engine/game_loop.py.

Comble le gap "pas d'API, aucun terminal interactif" : un vrai joueur (ou la
GUI servie par ce même process) soumet des actions via HTTP, une tâche async
par partie fait tourner GameLoop.tick() à intervalle régulier et diffuse
l'état à jour sur WebSocket — exactement le flux décrit §2.2/§13.3 du
blueprint, réduit au MVP (pas d'auth, pas de rooms par rôle).
"""
from __future__ import annotations

import asyncio
import logging
import random
import uuid
from collections import defaultdict
from dataclasses import dataclass
from pathlib import Path
from typing import Literal
from datetime import datetime

from fastapi import FastAPI, HTTPException, WebSocket, WebSocketDisconnect
from pydantic import BaseModel, Field

from engine import contracts, terminal, social
from engine import console_sessions, shell_tools, terminal_native, completion, mission_data
from engine.models import GameState
from engine.persistence import state_to_dict
from engine.career import Career, CATALOG
from engine.persistence import state_from_dict
from engine.contracts import ContractValidationError
from engine.handles import generate_choices, is_valid_handle
from engine.game_loop import GameLoop, QueuedAction, load_all_abilities
from engine.scenario_loader import ScenarioValidationError, load_scenario

from .serializers import serialize_state

ROOT = Path(__file__).parent.parent
SCENARIOS_DIR = ROOT / "scenarios"
CONTRACTS_DIR = ROOT / "contracts"

ABILITIES = load_all_abilities()
_CAREER: Career | None = None
_WORKSPACE: GameState | None = None
_WORKSPACE_REVISION: int | None = None

def career() -> Career:
    global _CAREER
    if _CAREER is None:
        _CAREER = Career()
    return _CAREER


app = FastAPI(title="RedTeamSimulator — Solo")



@dataclass
class GameSession:
    id: str
    loop: GameLoop
    tick_interval: float = 2.0
    paused: bool = False
    task: asyncio.Task | None = None
    saved_signature: tuple = ()
    saved_at: float = 0.0

    @property
    def state(self):
        return self.loop.state


GAMES: dict[str, GameSession] = {}
CONNECTIONS: dict[str, list[WebSocket]] = defaultdict(list)


async def _broadcast(game_id: str) -> None:
    session = GAMES.get(game_id)
    if session is None:
        return
    payload = serialize_state(session.state)
    dead = []
    for ws in CONNECTIONS.get(game_id, []):
        try:
            await ws.send_json(payload)
        except Exception:
            dead.append(ws)
    for ws in dead:
        CONNECTIONS[game_id].remove(ws)


async def _tick_loop(game_id: str) -> None:
    """La vraie boucle de jeu (§5.2 du blueprint) : tourne en continu tant que
    la partie est RUNNING, indépendamment des requêtes HTTP qui ne font que
    remplir la file (GameLoop.submit)."""
    while True:
        session = GAMES.get(game_id)
        if session is None or session.state.status != "RUNNING":
            break
        await asyncio.sleep(session.tick_interval)
        session = GAMES.get(game_id)  # peut avoir été supprimée pendant le sleep
        if session is None or session.state.status != "RUNNING":
            break
        if session.paused:
            continue
        if session.state.contract:
            career().data['play_seconds'] = career().data.get('play_seconds', 0) + session.tick_interval
        # Le tutoriel laisse le temps de lire les messages : le monde avance
        # uniquement lorsqu'une action est en attente.
        if session.state.contract and (session.state.contract["tier"] == 0 or session.state.contract.get("relaxed_clock")) and not session.loop.has_pending() and not any(t > session.state.tick for t in session.state.cooldowns.values()):
            continue
        try:
            if session.state.contract: session.state.environment["world_minute"] = social.prepare(career())["minute"]
            session.loop.tick()
            _persist(session, throttled=True)
        except Exception:
            # Une erreur ponctuelle (écriture impossible, règle défaillante) ne doit pas arrêter la partie :
            # sans cette boucle, plus aucun tick, plus aucune commande résolue, plus aucune diffusion.
            logging.getLogger(__name__).exception("Tick en échec pour la partie %s ; la boucle continue.", game_id)
        await _broadcast(game_id)
    await _broadcast(game_id)  # diffuse l'état final (ENDED)


def _persist(session: "GameSession", *, throttled: bool = False) -> None:
    """Écrit une mission de contrat : règlement si elle est terminée, sinon point de sauvegarde.
    Une partie sans contrat n'écrit jamais dans la carrière."""
    state = session.state
    if not state.contract: return
    if state.status == "ENDED": career().settle(session.id, state)
    elif throttled: _checkpoint_if_changed(session)
    else: career().checkpoint(state)


CHECKPOINT_IDLE_SECONDS = 20.0


def _checkpoint_if_changed(session: GameSession) -> None:
    """Un tick sans événement ne réécrit pas la sauvegarde : écriture si l'état
    visible change, sinon au plus toutes les CHECKPOINT_IDLE_SECONDS."""
    import time
    state = session.state
    signature = (len(state.history), len(state.messages), len(state.alerts), len(state.loot), len(state.pending_actions),
                 state.status, state.guide_index, state.trace.get("progress"))
    now = time.monotonic()
    if signature == session.saved_signature and now - session.saved_at < CHECKPOINT_IDLE_SECONDS:
        return
    career().checkpoint(state)
    session.saved_signature, session.saved_at = signature, now


def _get_session(game_id: str) -> GameSession:
    session = GAMES.get(game_id)
    if session is None:
        raise HTTPException(404, f"Partie inconnue: {game_id}")
    return session


# ---------------------------------------------------------------------------
# Schémas de requête
# ---------------------------------------------------------------------------

class CreateGameRequest(BaseModel):
    scenario: str = Field(default="mvp_demo", pattern=r"^[a-zA-Z0-9_-]+$")
    # Si un contrat est donné, il fixe le scénario (le champ scenario est ignoré).
    contract: str | None = None
    handle: str | None = None
    tick_interval: float = Field(default=2.0, ge=0.1, le=30)
    rng_seed: int | None = None


class TerminalRequest(BaseModel):
    line: str = Field(default="", max_length=16384)
    console_id: str = Field(default="main", pattern=r"^[A-Za-z0-9_-]{1,64}$")
    interrupt: bool = False


class ActionRequest(BaseModel):
    team: str                              # "red" | "blue"
    ability_id: str
    target_id: str
    credential_username: str | None = None
    credential_type: str | None = None
    user_username: str | None = None
    alert_id: int | None = None


# ---------------------------------------------------------------------------
# Scénarios
# ---------------------------------------------------------------------------

@app.get("/api/health")
async def health():
    return {"status": "ok", "application": "RedTeamSimulator", "version": "0.5.3-dev"}


@app.get("/api/abilities")
async def list_abilities():
    """Évite de dupliquer noms/cooldowns/points des abilities dans le JS —
    la GUI construit ses boutons à partir de cette liste, pas de valeurs
    codées en dur côté frontend."""
    return [
        {"id": a.id, "team": a.team, "name": a.name, "cooldown": a.cooldown,
         "points": a.points, "noise": a.noise, "critical": a.critical,
         "cli": terminal_native.HELP.get(a.id, ("", "", ""))[1]}
        for a in ABILITIES.values() if a.team == "red"
    ]


@app.get("/api/scenarios")
async def list_scenarios():
    scenarios = []
    for path in sorted(SCENARIOS_DIR.glob("*.json")):
        try:
            state = load_scenario(path, known_ability_ids=set(ABILITIES))
        except ScenarioValidationError as exc:
            scenarios.append({"id": path.stem, "error": str(exc)})
            continue
        scenarios.append({"id": path.stem, "name": state.scenario_name, "hosts": len(state.hosts)})
    return scenarios


# ---------------------------------------------------------------------------
# Forum (bounties) et inscription
# ---------------------------------------------------------------------------

_CONTRACT_CACHE: tuple | None = None


def _raw_contracts() -> dict[str, dict]:
    """Contrats lus et validés depuis le disque. Cette lecture (49 fichiers et leurs scénarios)
    se trouvait sur chaque sondage du client : elle n'est refaite que si un fichier a changé."""
    global _CONTRACT_CACHE
    stamp = tuple(sorted((str(path), path.stat().st_mtime_ns) for folder in (CONTRACTS_DIR, SCENARIOS_DIR) for path in folder.glob("*.json")))
    if _CONTRACT_CACHE is None or _CONTRACT_CACHE[0] != stamp:
        try:
            loaded = contracts.load_all_contracts(CONTRACTS_DIR, SCENARIOS_DIR, known_ability_ids=set(ABILITIES))
        except ContractValidationError as exc:
            raise HTTPException(500, str(exc))
        _CONTRACT_CACHE = (stamp, loaded)
    return _CONTRACT_CACHE[1]


def _load_contracts() -> dict[str, dict]:
    from copy import deepcopy
    from engine.relationships import offers
    from engine.curriculum import definitions
    try:
        # Copie : les règles de progression ajustent titres et primes selon la carrière.
        return offers(career().data, definitions(career().data, deepcopy(_raw_contracts())))
    except ContractValidationError as exc:
        raise HTTPException(500, str(exc))


@app.get("/api/contracts")
async def list_contracts(forum: str | None = None):
    """Les bounties affichés sur le forum. Le guide n'est jamais envoyé."""
    from engine.community import forum_reason
    views = []
    active = career().view().get("active_contract") or {}
    for c in sorted(_load_contracts().values(), key=lambda c: (c["tier"], c.get("required_rep", 0), c["contract_id"])):
        if c.get('onboarding') or c.get('private_offer'): continue
        from engine.campaign import hidden_from_board
        if hidden_from_board(career().data, c['contract_id']): continue
        if forum_reason(career().data, c.get('bounty', {}).get('forum', 'breachboard')): continue
        view = contracts.bounty_view(c)
        reason = career().lock_reason(c)
        view.update(completed=c["contract_id"] in career().data["completed"], unlocked=not reason, locked_reason=reason, is_active=c["contract_id"] == active.get("contract_id"))
        if view["completed"]:
            view["announced_reward"] = view["reward"]
            view["reward"] = 0
        views.append(view)
    return [v for v in views if forum is None or v["forum"] == forum]


@app.get("/api/handles")
async def suggest_handles(count: int = 3, seed: int | None = None):
    """Pseudos proposés à l'inscription en un clic sur BreachBoard."""
    count = max(1, min(count, 10))
    rng = random.Random(seed)  # instance dédiée, jamais le random global
    return {"handles": generate_choices(rng, count)}


# ---------------------------------------------------------------------------
# Gestion de partie
# ---------------------------------------------------------------------------

@app.post("/api/games")
async def create_game(req: CreateGameRequest):
    if req.contract is not None:
        contract = _load_contracts().get(req.contract)
        if contract is None:
            raise HTTPException(404, f"Contrat inconnu: {req.contract}")
        # L'identité est celle de la carrière : un contrat ne la remplace pas en cours de route.
        req.handle = career().data.get("handle") or req.handle
        if not req.handle or not is_valid_handle(req.handle):
            raise HTTPException(
                400, "Pseudo invalide : 3 à 24 caractères, lettres, chiffres, _ - . uniquement."
            )
        if req.handle.casefold() in _reserved_handles():
            raise HTTPException(400, "Ce pseudo est déjà utilisé par un personnage ; choisis une autre identité.")
        active = career().data.get("active") or {}
        if active.get("status") == "RUNNING" and (active.get("contract") or {}).get("contract_id") == req.contract:
            return _resume_career_session()
        state = contracts.start_contract(
            contract, req.handle, SCENARIOS_DIR,
            rng_seed=req.rng_seed if req.rng_seed is not None else random.SystemRandom().randrange(2**63), known_ability_ids=set(ABILITIES),
        )
    else:
        scenario_path = SCENARIOS_DIR / f"{req.scenario}.json"
        if not scenario_path.exists():
            raise HTTPException(404, f"Scénario inconnu: {req.scenario}")
        try:
            state = load_scenario(scenario_path, rng_seed=req.rng_seed, known_ability_ids=set(ABILITIES))
        except ScenarioValidationError as exc:
            raise HTTPException(400, str(exc))

    if req.contract is not None:
        # Le moteur décide de ce qui suit l'opérateur d'un contrat au suivant (engine/mission_data.py).
        mission_data.inherit(state, mission_data.source_for_new_contract(career().data), contract)
        try:
            career().prepare(contract, state)
        except ValueError as exc:
            raise HTTPException(409, str(exc))
    game_id = uuid.uuid4().hex
    session = GameSession(id=game_id, loop=GameLoop(state, ABILITIES), tick_interval=req.tick_interval)
    GAMES[game_id] = session
    if req.contract is not None:
        shell_tools.prepare(state)
        career().checkpoint(state)
    return {"id": game_id, "state": serialize_state(state)}


@app.get("/api/games/{game_id}")
async def get_game(game_id: str):
    session = _get_session(game_id)
    return serialize_state(session.state)


@app.post("/api/games/{game_id}/start")
async def start_game(game_id: str):
    session = _get_session(game_id)
    if session.task is None or session.task.done():
        session.task = asyncio.create_task(_tick_loop(game_id))
    return {"status": "started"}


@app.post("/api/games/{game_id}/pause")
async def pause_game(game_id: str):
    session = _get_session(game_id)
    session.paused = True
    return {"status": "paused"}


@app.post("/api/games/{game_id}/resume")
async def resume_game(game_id: str):
    session = _get_session(game_id)
    session.paused = False
    return {"status": "resumed"}


@app.delete("/api/games/{game_id}")
async def delete_game(game_id: str):
    session = GAMES.pop(game_id, None)
    if session and session.task:
        session.task.cancel()
    CONNECTIONS.pop(game_id, None)
    return {"status": "deleted"}


class BuyRequest(BaseModel):
    item: str


class RouteRequest(BaseModel):
    route: str


@app.get("/api/profile")
async def get_profile():
    return career().view()



# Sauvegardes du jeu solo : toute restauration remplace la carrière entière.
class SaveRequest(BaseModel):
    name: str = Field(default='Sauvegarde manuelle', max_length=80)
    slot_id: str | None = None
    confirm: bool = False

class NewCareerRequest(BaseModel):
    handle: str
    confirm: bool = False
    play_mode: str = 'campaign'
    curriculum: Literal['current','classic'] = 'current'


def _checkpoint_live():
    if career().needs_recovery: return
    active = career().data.get('active') or {}
    for session in GAMES.values():
        if session.state.contract and session.state.conversation_id == active.get('conversation_id'):
            career().checkpoint(session.state)  # écrit déjà la carrière
            return
    career().save()


async def _stop_live_sessions():
    global _WORKSPACE
    sessions=list(GAMES.values())
    sockets=[socket for group in CONNECTIONS.values() for socket in group]
    # Révoquer les identifiants avant le premier await : aucune ancienne requête
    # ne doit agir sur le profil qui vient d’être restauré.
    GAMES.clear(); CONNECTIONS.clear(); _WORKSPACE=None
    career().reset_wallet_session()
    for session in sessions:
        session.paused=True
        if session.task: session.task.cancel()
    for socket in sockets:
        try: await socket.close()
        except Exception: pass


@app.post('/api/profile/enroll')
async def enroll_campaign():
    from copy import deepcopy
    from engine.curriculum import migrate
    from engine.save_store import SaveStore
    profile=career()
    if profile.needs_recovery:return profile.view()
    updated,changed=migrate(profile.data)
    if changed:
        previous=profile.data
        try:
            _checkpoint_live()
            updated,_=migrate(profile.data)
            SaveStore(profile.path).write(previous,'Avant adaptation de l’acte I')
            profile.data=updated
            profile.save()
        except (OSError,ValueError):
            profile.data=previous
            raise HTTPException(503,'Impossible d’actualiser la progression. La carrière et la mission en cours sont conservées.')
        active=profile.data.get('active') or {}
        for session in GAMES.values():
            if session.state.conversation_id==active.get('conversation_id') and active.get('status')=='RUNNING':
                session.state.contract=deepcopy(active['contract'])
    return profile.view()


@app.get('/api/saves')
async def list_saves():
    from engine.save_store import SaveStore
    return {'slots':SaveStore(career().path).list(), 'profile':career().view(), 'recovered':career().recovered}


@app.post('/api/saves/write')
async def write_save(req: SaveRequest):
    from engine.save_store import SaveStore
    try:
        if req.slot_id and not req.slot_id.startswith('manual-'):
            raise ValueError('Choisis un emplacement manuel.')
        if career().needs_recovery: raise ValueError('Charge un emplacement valide avant de sauvegarder.')
        _checkpoint_live()
        return SaveStore(career().path).write(career().data,req.name,req.slot_id,req.confirm)
    except ValueError as exc: raise HTTPException(400,str(exc))
    except OSError: raise HTTPException(503,'Impossible d’écrire cet emplacement. La mission reste ouverte ; réessaie la sauvegarde.')


@app.post('/api/saves/load')
async def load_save(req: SaveRequest):
    from engine.save_store import SaveStore
    if not req.confirm: raise HTTPException(409,'Confirme le chargement : il remplace la progression courante.')
    try:
        store = SaveStore(career().path)
        snapshot = store.read(req.slot_id or '')['profile']
        from engine.curriculum import migrate
        snapshot,_ = migrate(snapshot)
        _checkpoint_live()
        profile=career()
        if not profile.needs_recovery: store.write(profile.data,'Avant chargement','recovery',True,'recovery')
        profile.replace(snapshot)  # rétablit l'ancienne carrière en mémoire si l'écriture échoue
        # Détruire la session et les demandes ColdVault seulement après écriture réussie.
        await _stop_live_sessions()
        social.restart_clock(career())
        return career().view()
    except ValueError as exc: raise HTTPException(400,str(exc))
    except OSError: raise HTTPException(503,'Impossible d’écrire la sauvegarde. La partie courante et les demandes en attente sont conservées.')


@app.post('/api/saves/delete')
async def delete_save(req: SaveRequest):
    from engine.save_store import SaveStore
    if not req.confirm: raise HTTPException(409,'Confirme la suppression de cet emplacement.')
    try:
        path = SaveStore(career().path).path(req.slot_id or '')
        if not path.exists(): raise ValueError('Cet emplacement n’existe plus.')
        path.unlink()
        return {'deleted':req.slot_id}
    except ValueError as exc: raise HTTPException(400,str(exc))


@app.post('/api/profile/new')
async def new_career(req: NewCareerRequest):
    from engine.career import initial
    from engine.save_store import SaveStore
    if req.play_mode not in {'campaign', 'demo'}: raise HTTPException(400, 'Parcours inconnu.')
    if not is_valid_handle(req.handle): raise HTTPException(400,'Pseudo invalide : 3 à 24 caractères, lettres, chiffres, tiret, point ou underscore.')
    if req.handle.casefold() in _reserved_handles(): raise HTTPException(400,'Ce pseudo est déjà utilisé par un personnage ; choisis une autre identité.')
    if not req.confirm: raise HTTPException(409,'Confirme la nouvelle partie : la carrière courante sera archivée.')
    profile = career()
    store = SaveStore(profile.path)
    if not profile.needs_recovery:
        try:
            _checkpoint_live()
            # Tout ce que le joueur a produit est archivé ; une carrière vierge ou déjà archivée à l'identique ne l'est pas.
            if _has_content(profile.data) and not store.has_identical(profile.data):
                store.write(profile.data,'Avant nouvelle partie')
        except OSError:
            raise HTTPException(503,'Impossible d’archiver la carrière actuelle : la nouvelle partie n’a pas été créée. Vérifie l’espace disque et les droits du dossier de sauvegarde.')
        except ValueError:
            # Carrière invalide : elle ne peut pas devenir un emplacement. Une nouvelle partie est sa seule issue ;
            # le fichier brut est mis de côté pour ne rien détruire.
            try: _set_aside(profile.path)
            except OSError:
                raise HTTPException(503,'La carrière actuelle est invalide et n’a pas pu être mise de côté : la nouvelle partie n’a pas été créée.')
    fresh = initial()
    fresh['handle'] = req.handle
    fresh['campaign_version'] = 3 if req.curriculum == 'classic' else 4
    fresh['classic_progression'] = req.curriculum == 'classic'
    fresh['play_mode'] = req.play_mode
    try: profile.replace(fresh)
    except (OSError, ValueError):
        raise HTTPException(503,'Impossible d’écrire la nouvelle carrière. La partie courante est conservée.')
    # Les sessions ne sont détruites qu'après l'écriture réussie de la nouvelle carrière.
    await _stop_live_sessions()
    social.restart_clock(career())
    return career().view()


def _has_content(data: dict) -> bool:
    """Vrai dès que la carrière contient quelque chose que le joueur a fait ou obtenu.
    En cas de doute la réponse est oui : mieux vaut une archive de trop qu'une perte."""
    from engine.career import initial
    base = initial()
    if any(data.get(key) for key in ('completed','settled','active','workspace','inventory','forum_posts','career_events','choices','route_passes')): return True
    if data.get('play_seconds', 0) > 0 or data.get('reputation', 0) > 0 or data.get('tier', 0) > 0: return True
    if data.get('money', base['money']) != base['money'] or data.get('route', base['route']) != base['route']: return True
    characters = {name.casefold() for name in social.content()['profiles']}
    return any(str(message.get('sender','')).casefold() not in characters for message in data.get('conversations', {}).values())


def _set_aside(path) -> None:
    import shutil, time
    if path.exists(): shutil.copy2(path, path.with_name('career.invalid-'+str(time.time_ns())+'.json'))


@app.post('/api/profile/continue')
async def continue_campaign():
    from engine.onboarding import DEMO_STAGES
    if career().data.get('play_mode') != 'demo': raise HTTPException(400, 'La campagne est déjà active.')
    if not all(cid in career().data['completed'] for cid in DEMO_STAGES): raise HTTPException(409, 'Termine le dossier de démonstration avant de poursuivre.')
    career().data['play_mode'] = 'campaign'
    career().save()
    return career().view()


@app.post('/api/profile/menu')
async def return_menu():
    from engine.save_store import SaveStore
    for session in GAMES.values(): session.paused = True
    _checkpoint_live()
    # Autosauvegarde immédiate ; SaveStore.autosave ignore un état déjà présent dans l'emplacement le plus récent.
    if not career().needs_recovery:
        try: SaveStore(career().path).autosave(career().data,force=True)
        except (OSError, ValueError): pass  # la carrière vient d'être écrite : le retour au menu reste possible
    return career().view()


@app.get("/api/shop")
async def get_shop():
    from engine.community import shop_reason
    profile = career().data
    reason = shop_reason(profile)
    if reason: raise HTTPException(403, reason)
    from engine.economy import catalog
    return catalog(profile, CATALOG)


@app.post("/api/shop/buy")
async def buy_item(req: BuyRequest):
    try:
        result = career().request_purchase(req.item)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    _sync_inventory()
    return result


def _sync_inventory() -> None:
    """La mission en cours lit son propre inventaire : un achat fait pendant la mission
    (GPU, liste de mots, licence) doit y apparaître tout de suite."""
    active = career().data.get('active') or {}
    for session in GAMES.values():
        if session.state.contract and session.state.conversation_id == active.get('conversation_id'):
            if session.state.inventory != career().data['inventory']:
                session.state.inventory = list(career().data['inventory'])
                career().checkpoint(session.state)


@app.post("/api/profile/route")
async def select_route(req: RouteRequest):
    try:
        career().select_route(req.route)
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    return career().view()


class GuidanceRequest(BaseModel):
    enabled: bool


@app.post("/api/games/{game_id}/guidance")
async def set_guidance(game_id: str, req: GuidanceRequest):
    session = _get_session(game_id)
    session.state.guidance_enabled = req.enabled
    if session.state.contract: career().checkpoint(session.state)
    return {"enabled": req.enabled}


@app.post("/api/games/{game_id}/disconnect")
async def disconnect_game(game_id: str):
    session = _get_session(game_id)
    if session.loop.abandon():
        career().settle(game_id, session.state)
        await _broadcast(game_id)
    return serialize_state(session.state)


def _resume_career_session():
    active = career().data.get("active")
    if not active or active.get("status") != "RUNNING":
        raise HTTPException(404, "Aucune mission à reprendre.")
    for session in GAMES.values():
        if session.state.status == "RUNNING" and session.state.contract and session.state.conversation_id == active.get("conversation_id"):
            return {"id": session.id, "state": _with_transcripts(session.state), "resumed": True}
    state = state_from_dict(active)
    current_contract = _load_contracts().get(state.contract.get("contract_id")) if state.contract else None
    if current_contract and not state.contract.get('legacy_in_progress') and current_contract.get("terminal_revision", 0) > state.contract.get("terminal_revision", 0):
        from copy import deepcopy
        current_scenario = load_scenario(SCENARIOS_DIR / f"{current_contract['scenario']}.json")
        same_network = {h.id: (h.ip, h.primary_user) for h in state.hosts.values()} == {h.id: (h.ip, h.primary_user) for h in current_scenario.hosts.values()}
        if same_network:
            state.contract = deepcopy(current_contract)
            for filename, contents in current_contract.get("local_files", {}).items():
                state.terminal_files.setdefault(filename, contents)
            for host in state.hosts.values():
                template = current_scenario.hosts[host.id]
                host.os, host.role, host.phishing = template.os, template.role, template.phishing
            # Les objectifs et le guide suivent la révision : sinon un objectif pourrait viser une étape disparue.
            state.objectives = deepcopy(current_scenario.objectives)
            state.guide_index = min(state.guide_index, len(state.contract.get("guide", [])))
            known_steps = {step["id"] for step in state.contract.get("investigation_steps", [])}
            record = state.tool_data.get("investigation")
            if record: record["steps"] = [step for step in record.get("steps", []) if step in known_steps]
            revised = True
        else:
            state.contract["terminal_revision"] = current_contract["terminal_revision"]
            revised = False
            contracts.send(state, "Ce dossier a été révisé depuis ta sauvegarde, mais son réseau a changé : la mission sauvegardée conserve son réseau, ses comptes, ses consignes et ses choix. Les nouvelles consignes s’appliqueront à un nouveau départ de ce dossier.")
        if revised: contracts.send(state, "Les consignes et les validations de ce dossier ont été précisées. La mission sauvegardée conserve son réseau, ses comptes et ses choix. Écris objectif pour relire le but, ou aide pour un indice adapté à ta progression. Les outils Windows doivent toujours être transférés avant leur exécution.")
        career().checkpoint(state)
    if state.environment.pop('credential_migration', False) and state.contract:
        contracts.send(state, "Les anciennes empreintes artificielles du prototype ont été mises en cohérence avec les mots de passe du laboratoire. Le réseau et les comptes sont conservés ; consulte les fichiers du butin pour les valeurs actualisées.")
        career().checkpoint(state)
    if state.contract: state.inventory = list(career().data["inventory"])
    game_id = uuid.uuid4().hex
    GAMES[game_id] = GameSession(id=game_id, loop=GameLoop(state, ABILITIES), paused=True)
    return {"id": game_id, "state": _with_transcripts(state), "resumed": True}


def _with_transcripts(state: GameState) -> dict:
    """Reprise : le texte des consoles n'est envoyé qu'ici, pas à chaque diffusion."""
    from copy import deepcopy
    data = serialize_state(state)
    data["terminal_transcripts"] = deepcopy(state.tool_data.get("terminal_transcripts", {}))
    return data


@app.post("/api/profile/resume")
async def resume_career():
    return _resume_career_session()


# ---------------------------------------------------------------------------
# Actions joueur (Red / Blue)
# ---------------------------------------------------------------------------

@app.post("/api/games/{game_id}/action")
async def submit_action(game_id: str, action: ActionRequest):
    session = _get_session(game_id)
    if action.team != "red" or action.ability_id not in session.state.available_abilities.get("red", []):
        raise HTTPException(400, "Ce jeu solo accepte uniquement les actions Red disponibles.")
    if action.ability_id not in ABILITIES:
        raise HTTPException(400, f"Ability inconnue: {action.ability_id}")
    if action.target_id not in session.state.hosts:
        raise HTTPException(400, f"Cible inconnue: {action.target_id}")
    try:
        session.loop.submit(QueuedAction(
            team=action.team,
            ability_id=action.ability_id,
            target_id=action.target_id,
            credential_username=action.credential_username,
            credential_type=action.credential_type,
            user_username=action.user_username,
            alert_id=action.alert_id,
        ))
    except RuntimeError as exc:
        raise HTTPException(409, str(exc))
    if session.state.contract:
        career().checkpoint(session.state)
    return {"status": "queued", "resolves_next_tick": True}


def workspace() -> GameState:
    global _WORKSPACE, _WORKSPACE_REVISION
    revision = career().data.get("workspace_revision", 0)
    if _WORKSPACE is None or revision != _WORKSPACE_REVISION:  # le bureau a été mis à jour par une fin de mission
        _WORKSPACE_REVISION = revision
        saved = career().data.get("workspace")
        _WORKSPACE = state_from_dict(saved) if saved else GameState(hosts={}, users={})
        _WORKSPACE.available_abilities = {"red": [a.id for a in ABILITIES.values() if a.team == "red"]}
        shell_tools.prepare(_WORKSPACE)
    return _WORKSPACE


def _resolve_observations(loop: GameLoop) -> None:
    """Les lectures et comptes rendus peuvent achever un dossier sans tick offensif."""
    state = loop.state
    if not state.contract or not (state.contract.get('onboarding') or state.contract.get('investigation_steps')): return
    if loop.finish_if_won():
        career().settle(next((gid for gid,s in GAMES.items() if s.loop is loop), state.conversation_id),state)


def _terminal_request(state: GameState, req: TerminalRequest, loop: GameLoop | None) -> dict:
    if req.console_id not in state.terminals and len(state.terminals) >= 64:
        raise HTTPException(409, "La limite de 64 sessions de console est atteinte.")
    queued = False
    if state.contract: state.environment["world_minute"] = social.prepare(career())["minute"]
    before = console_sessions.public_contexts(state).get(req.console_id) or console_sessions.summary(state, console_sessions.initial(), req.console_id)
    with console_sessions.using(state, req.console_id):
        if not req.interrupt and req.line.strip() == "clear" and not before.get("password_prompt"):
            console_sessions.transcript(state, req.console_id).clear()
            result = terminal.TerminalResult(True, [], exit_code=0)
        elif req.interrupt:
            lines = console_sessions.interrupt(state)
            if loop:
                loop.cancel_console(req.console_id)
            state.terminal_last_exit = state.terminal_last_native_exit = 130
            result = terminal.TerminalResult(True, lines, exit_code=130)
        elif any(a.get("console_id", "main") == req.console_id and not a.get("params", {}).get("gophish_campaign_id") for a in state.pending_actions):
            result = terminal.TerminalResult(False, ["Une commande est encore en cours dans cette console. Attends son résultat ou utilise Ctrl+C."])
        else:
            result = terminal.parse(req.line, state, ABILITIES)
        if result.action:
            if loop is None:
                result = terminal.TerminalResult(False, ["Accepte un contrat pour agir sur son réseau."])
            else:
                try:
                    loop.submit(result.action)
                    queued = True
                except RuntimeError as exc:
                    result = terminal.TerminalResult(False, [str(exc)])
    if not (req.line.strip() == "clear" and not req.interrupt and not before.get("password_prompt")):
        console_sessions.record(state, req.console_id, ([] if req.interrupt else console_sessions.echo(before, req.line)) + list(result.output or []))
    if loop: _resolve_observations(loop)
    context = console_sessions.public_contexts(state)[req.console_id]
    return {"ok": result.ok, "output": result.output, "queued": queued, "console_id": req.console_id,
            "password_prompt": context["password_prompt"], "context": context, "open_url": result.open_url, "exit_code": None if context["password_prompt"] or (queued and not result.action.params.get("gophish_campaign_id")) else result.exit_code}


@app.get("/api/workspace/state")
async def workspace_state():
    return _with_transcripts(workspace())


@app.post("/api/workspace/terminal")
async def workspace_terminal(req: TerminalRequest):
    state = workspace()
    result = _terminal_request(state, req, None)
    career().data["workspace"] = state_to_dict(state)
    career().save()
    return result


@app.post("/api/games/{game_id}/terminal")
async def terminal_command(game_id: str, req: TerminalRequest):
    session = _get_session(game_id)
    result = _terminal_request(session.state, req, session.loop)
    if session.state.contract:
        career().checkpoint(session.state)
        if session.state.contract.get('onboarding') or session.state.contract.get('investigation_steps'):
            result['state'] = serialize_state(session.state)
    return result


@app.delete("/api/games/{game_id}/terminals/{console_id}")
async def close_terminal(game_id: str, console_id: str):
    session = _get_session(game_id)
    console_sessions.close(session.state, console_id)
    session.loop.cancel_console(console_id)
    if session.state.contract: career().checkpoint(session.state)
    return {"status": "closed"}


@app.delete("/api/workspace/terminals/{console_id}")
async def close_workspace_terminal(console_id: str):
    state = workspace()
    console_sessions.close(state, console_id)
    career().data["workspace"] = state_to_dict(state)
    career().save()
    return {"status": "closed"}


# ---------------------------------------------------------------------------
# WebSocket temps réel — §13.3 du blueprint, réduit à un broadcast état complet
# (pas de delta diff : à l'échelle du MVP, 3 hosts, ça n'a aucun intérêt).
# ---------------------------------------------------------------------------

@app.websocket("/ws/games/{game_id}")
async def game_ws(websocket: WebSocket, game_id: str):
    if game_id not in GAMES:
        await websocket.close(code=4404)
        return
    await websocket.accept()
    CONNECTIONS[game_id].append(websocket)
    await websocket.send_json(serialize_state(GAMES[game_id].state))
    try:
        while True:
            await websocket.receive_text()  # on n'attend rien du client, juste garder la connexion
    except WebSocketDisconnect:
        if websocket in CONNECTIONS.get(game_id, []):
            CONNECTIONS[game_id].remove(websocket)







class ChatRequest(BaseModel):
    peer: str | None = None
    channel: Literal["chordly", "telegrid", "sessyon"]
    text: str = Field(min_length=1, max_length=2000)


@app.post("/api/games/{game_id}/chat")
async def send_chat(game_id: str, req: ChatRequest):
    session = _get_session(game_id)
    if not req.text.strip():
        raise HTTPException(400, "Le message est vide.")
    if req.peer and (not session.state.contract or req.peer != session.state.contract["client"]["handle"]):
        raise HTTPException(400, "Cette conversation ne correspond pas au client du contrat actif.")
    try:
        reply = contracts.player_message(session.state, req.channel, req.text.strip(), defer=not contracts.wants_immediate_answer(req.text))
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    # Repéré avant la vérification des objectifs, qui peut ajouter le message de fin du client.
    player_index = max((i for i, m in enumerate(session.state.messages) if m.sender == session.state.player_handle), default=len(session.state.messages) - 1)
    _resolve_observations(session.loop)
    if session.state.contract: career().checkpoint(session.state)
    if reply:
        social.schedule(career(), kind="chat", target=session.state.contract["client"]["handle"], channel=req.channel,
            author=session.state.contract["client"]["handle"], text=reply,
            reply_to=f"{session.state.conversation_id}:{player_index}", delay=2 if req.channel == "chordly" else 4)
        career().save()
    await _broadcast(game_id)
    return serialize_state(session.state)


@app.get("/api/messages")
async def list_messages():
    return list(career().data.get("conversations", {}).values())


class ForumReplyRequest(BaseModel):
    handle: str
    text: str = Field(min_length=1, max_length=2000)


def _check_thread(thread_id: str) -> None:
    community = {t["id"]: t["forum"] for t in social.content()["threads"]}
    contract = _load_contracts().get(thread_id)
    forum = contract.get("bounty", {}).get("forum") if contract else community.get(thread_id)
    if forum is None: raise HTTPException(404, "Sujet introuvable.")
    from engine.community import forum_reason
    reason = forum_reason(career().data, forum)
    if reason: raise HTTPException(403, reason)


@app.get("/api/forum/threads/{thread_id}")
async def get_thread(thread_id: str, refresh: bool = False):
    """refresh : relecture automatique du sujet déjà ouvert. Elle ne compte pas
    comme une vue et n'écrit rien sur disque si rien n'a changé."""
    _check_thread(thread_id)
    dirty = False
    if not refresh:
        counts=career().data.setdefault('thread_views',{})
        counts[thread_id]=counts.get(thread_id,0)+1
        dirty = True
    social.prepare(career())
    active_id = (career().data.get('active') or {}).get('conversation_id')
    for session in GAMES.values():
        if session.state.conversation_id != active_id or session.state.status != 'RUNNING': continue
        from engine.investigation import observe_forum
        if observe_forum(session.state, thread_id):
            career().checkpoint(session.state)  # écrit aussi la carrière, vues comprises
            dirty = False
    if dirty: career().save()
    return career().data.get("forum_posts", {}).get(thread_id, [])


def _reserved_handles() -> set[str]:
    """Pseudos des personnages et des clients de contrats, en minuscules."""
    return {name.casefold() for name in set(social.content()["profiles"]) | {c["client"]["handle"] for c in _raw_contracts().values()}}


def _community_identity(handle: str) -> str:
    identity = career().data.get("handle", handle)
    if not is_valid_handle(handle) or handle != identity or handle.casefold() in _reserved_handles():
        raise HTTPException(400, "Utilise le pseudo de ton profil ; les comptes des autres membres sont réservés.")
    career().data.setdefault("handle", identity)
    return identity


@app.post("/api/forum/threads/{thread_id}")
async def reply_thread(thread_id: str, req: ForumReplyRequest):
    _check_thread(thread_id)
    if not is_valid_handle(req.handle) or not req.text.strip():
        raise HTTPException(400, "Pseudo ou réponse invalide.")
    social.prepare(career())
    topic = next((t for t in social.content()["threads"] if t["id"] == thread_id), {})
    if topic.get("locked"):
        raise HTTPException(409, "Ce sujet est verrouillé. Consulte la discussion générale.")
    identity = _community_identity(req.handle)
    posts = career().data.setdefault("forum_posts", {}).setdefault(thread_id, [])
    if len(posts) >= 200:
        raise HTTPException(409, "Ce sujet a atteint sa limite de réponses.")
    from engine.community import scores
    local_forum = topic.get("forum", _load_contracts().get(thread_id, {}).get("bounty", {}).get("forum", "breachboard"))
    posts.append({"author": req.handle, "text": req.text.strip(), "reputation": scores(career().data)[local_forum], "time": social.stamp(career().data["social"]["minute"]), "minute": career().data["social"]["minute"]})
    social.queue_forum_reply(career(), thread_id, identity)
    career().save()
    return posts


@app.get("/api/social")
async def social_world():
    social.refresh(career())
    return social.view(career(), _load_contracts())


class SocialChatRequest(BaseModel):
    handle: str
    peer: str
    channel: Literal["chordly", "telegrid", "sessyon"]
    text: str = Field(min_length=1, max_length=2000)


@app.post("/api/social/chat")
async def social_chat(req: SocialChatRequest):
    identity = _community_identity(req.handle)
    if not req.text.strip():
        raise HTTPException(400, "Le message est vide.")
    try:
        social.queue_chat(career(), req.channel, req.peer, identity, req.text.strip())
    except ValueError as exc:
        raise HTTPException(400, str(exc))
    career().save()
    return social.view(career(), _load_contracts())


class WaitWorldRequest(BaseModel):
    minutes: int = Field(default=5, ge=1, le=60)
    game_id: str | None = None


@app.post("/api/world/wait")
async def wait_world(req: WaitWorldRequest):
    profile = career()
    active = profile.data.get("active") or {}
    session = _get_session(req.game_id) if req.game_id else None
    if active.get("status") == "RUNNING" and (session is None or session.state.conversation_id != active.get("conversation_id")):
        raise HTTPException(409, "Reprends la mission sauvegardée avant de faire avancer son temps.")
    if session and session.state.status == "RUNNING" and session.paused:
        raise HTTPException(409, "La mission est en pause. Reprends-la avant d’attendre.")
    for _ in range(req.minutes):
        social.advance(profile, 1)
        if session and session.state.status == "RUNNING":
            session.state.environment["world_minute"] = profile.data["social"]["minute"]
            for _ in range(3):
                session.loop.tick()
                if session.state.status != "RUNNING": break
    if session: _persist(session)
    profile.save()
    if session: await _broadcast(session.id)
    return {"social": social.view(profile, _load_contracts()), "state": serialize_state(session.state) if session else None}


class ReadChatRequest(BaseModel):
    channel: Literal["chordly", "telegrid", "sessyon"]
    peer: str


@app.post("/api/social/read")
async def social_read(req: ReadChatRequest):
    if not any(c["id"] == req.peer and c["channel"] == req.channel for c in social.view(career(), _load_contracts())["contacts"]):
        raise HTTPException(404, "Conversation introuvable.")
    social.mark_read(career(), req.channel, req.peer)
    career().save()
    return {"status": "read"}


class GophishGuiRequest(BaseModel):
    username: str
    password: str
    method: Literal["GET", "POST"] = "GET"
    endpoint: Literal["snapshot", "campaigns", "groups", "templates", "pages", "smtp"] = "snapshot"
    payload: dict | None = None


def _gophish_status(state: GameState) -> dict:
    service = state.tool_services.get("gophish", {})
    return {"running": bool(service.get("running") and service.get("mode") in {"all", "admin"})}


def _gophish_gui(state: GameState, loop: GameLoop | None, req: GophishGuiRequest) -> dict:
    import shlex
    import json
    from copy import deepcopy
    if not _gophish_status(state)["running"]:
        raise HTTPException(409, "Unable to connect : le serveur GoPhish n'est pas démarré.")
    if req.username != "admin" or req.password != "lab-admin-password":
        raise HTTPException(401, "Invalid username/password")
    if req.endpoint != "snapshot":
        config = state.tool_services["gophish"]["config"]["admin_server"]
        scheme = "https" if config.get("use_tls") else "http"
        address = config["listen_url"].replace("0.0.0.0", "127.0.0.1")
        args = ["curl", "-k", "-H", "Authorization: " + shell_tools.API_KEY, "-X", req.method]
        if req.payload is not None: args += ["-d", json.dumps(req.payload)]
        args += [f"{scheme}://{address}/api/{req.endpoint}/"]
        result = _terminal_request(state, TerminalRequest(line=shlex.join(args), console_id="gui-gophish"), loop)
        if not result["ok"]: raise HTTPException(400, "\n".join(result["output"]))
        payload = json.loads(result["output"][-1])
        if isinstance(payload, dict) and payload.get("success") is False:
            raise HTTPException(400, payload["message"])
    shell_tools.prepare(state)
    return {"resources": deepcopy(state.tool_data["gophish"]), "api_key": shell_tools.API_KEY, "running": True}


@app.get("/api/workspace/gophish/status")
async def workspace_gophish_status():
    return _gophish_status(workspace())


@app.get("/api/games/{game_id}/gophish/status")
async def game_gophish_status(game_id: str):
    return _gophish_status(_get_session(game_id).state)


@app.post("/api/workspace/gophish")
async def workspace_gophish(req: GophishGuiRequest):
    state = workspace()
    result = _gophish_gui(state, None, req)
    career().data["workspace"] = state_to_dict(state)
    career().save()
    return result


@app.post("/api/games/{game_id}/gophish")
async def game_gophish(game_id: str, req: GophishGuiRequest):
    session = _get_session(game_id)
    result = _gophish_gui(session.state, session.loop, req)
    if session.state.contract: career().checkpoint(session.state)
    return result


class CompletionRequest(BaseModel):
    line: str = Field(default="", max_length=16384)
    caret: int = Field(default=0, ge=0, le=16384)
    console_id: str = Field(default="main", pattern=r"^[A-Za-z0-9_-]{1,64}$")


def _complete_terminal(state: GameState, req: CompletionRequest) -> dict:
    if req.console_id not in state.terminals and len(state.terminals) >= 64:
        raise HTTPException(409, "La limite de sessions de console est atteinte.")
    with console_sessions.using(state, req.console_id):
        return completion.complete(state, req.line, req.caret)


@app.post("/api/workspace/terminal/complete")
async def complete_workspace(req: CompletionRequest):
    return _complete_terminal(workspace(), req)


@app.post("/api/games/{game_id}/terminal/complete")
async def complete_game(game_id: str, req: CompletionRequest):
    return _complete_terminal(_get_session(game_id).state, req)


if __name__ == "__main__":
    import uvicorn
    uvicorn.run("api.main:app", host="127.0.0.1", port=8001, reload=False)


@app.get('/api/forum/messages')
async def forum_messages():
    from engine.onboarding import forum_unlocked
    if not forum_unlocked(career().data):raise HTTPException(403,'Forum non accessible.')
    return list(career().data.get('forum_messages',{}).values())


@app.post('/api/forum/messages/{message_id}/read')
async def read_forum_message(message_id: str):
    message=career().data.get('forum_messages',{}).get(message_id)
    if not message:raise HTTPException(404,'Message introuvable.')
    message['read']=True;career().save()
    return message


@app.post('/api/forum/messages/{message_id}/accept')
async def accept_forum_invitation(message_id: str):
    from engine.campaign import accept
    try:accept(career(),message_id)
    except ValueError as exc:raise HTTPException(409,str(exc))
    return career().view()


class WalletActionRequest(BaseModel):
    action: Literal['connect', 'unlock', 'disconnect', 'approve', 'cancel']
    request_id: str | None = None


@app.get('/api/wallet')
async def wallet_status():
    from engine.wallet import view
    return view(career())


@app.post('/api/wallet/device')
async def wallet_device(req: WalletActionRequest):
    try: result = career().wallet_action(req.action, req.request_id)
    except ValueError as exc: raise HTTPException(400, str(exc))
    _sync_inventory()
    return result


class BloodHoundImportRequest(BaseModel):
    path: str = Field(min_length=1, max_length=512)


@app.get('/api/games/{game_id}/bloodhound')
async def bloodhound_view(game_id: str):
    from engine.bloodhound import view
    return view(_get_session(game_id).state)


@app.post('/api/games/{game_id}/bloodhound/import')
async def bloodhound_import(game_id: str, req: BloodHoundImportRequest):
    from engine.bloodhound import import_archive
    session=_get_session(game_id)
    if session.state.status!='RUNNING':raise HTTPException(409,'Ouvre le dossier de collecte avant cet import.')
    try:result=import_archive(session.state,req.path)
    except ValueError as exc:raise HTTPException(400,str(exc))
    if session.state.contract: career().checkpoint(session.state)
    return result
