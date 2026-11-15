"""
Contrats Red (docs/03-red-progression.md §3 et §6).

Un contrat = un fichier `contracts/<id>.json` posé sur un scénario (topologie).
Il apporte le client, l'annonce sur le forum, la prime et un guide : une suite
d'étapes `{"when": <condition>, "message": "..."}` envoyées sur la messagerie
du client au fil de la progression. Les conditions sont celles du registre
win_conditions.OBJECTIVES : aucun cas particulier par contrat ici.

Les messages expliquent les objectifs et les syntaxes reconnues dans le
laboratoire. Ils ne pilotent aucun programme ni réseau extérieur au jeu.
"""
from __future__ import annotations

import json
import re
from .social import stamp
from pathlib import Path

from .models import GameState, Message
from .scenario_loader import ScenarioValidationError, load_scenario
from .win_conditions import condition_error, objective_met

CONTRACTS_DIR = Path(__file__).parent.parent / "contracts"
SCENARIOS_DIR = Path(__file__).parent.parent / "scenarios"

CHANNELS = {"chordly", "telegrid", "sessyon"}
FORUMS = {"breachboard", "exployt", "xsx"}
REQUIRED = ("contract_id", "scenario", "tier", "channel", "client", "brief", "reward",
            "success_message", "failure_message")


class ContractValidationError(Exception):
    """Le contrat référence un scénario, un hôte ou une condition incohérents."""


def load_contract(
    path: Path,
    scenarios_dir: Path = SCENARIOS_DIR,
    known_ability_ids: set[str] | None = None,
) -> dict:
    data = json.loads(path.read_text(encoding='utf-8'))
    cid = data.get("contract_id", path.stem)

    missing = [key for key in REQUIRED if key not in data]
    if missing:
        raise ContractValidationError(f"Contrat '{cid}' : champs manquants {missing}.")
    if data["channel"] not in CHANNELS:
        raise ContractValidationError(
            f"Contrat '{cid}' : messagerie inconnue '{data['channel']}' "
            f"(possibles : {', '.join(sorted(CHANNELS))})."
        )
    forum = data.get("bounty", {}).get("forum")
    if forum is not None and forum not in FORUMS:
        raise ContractValidationError(f"Contrat '{cid}' : forum inconnu '{forum}'.")

    scenario_path = scenarios_dir / f"{data['scenario']}.json"
    if not scenario_path.exists():
        raise ContractValidationError(f"Contrat '{cid}' : scénario introuvable '{data['scenario']}'.")
    try:
        state = load_scenario(scenario_path, known_ability_ids=known_ability_ids)
    except ScenarioValidationError as exc:
        raise ContractValidationError(f"Contrat '{cid}' : scénario invalide ({exc}).") from exc

    host_ids, usernames = set(state.hosts), set(state.users)
    for where, conditions in (
        ("objectives", data.get("objectives", [])),
        ("guide", [step.get("when", {}) for step in data.get("guide", [])]),
    ):
        for condition in conditions:
            error = condition_error(condition, host_ids, usernames)
            if error:
                raise ContractValidationError(f"Contrat '{cid}', {where} : {error}.")
    steps = data.get('investigation_steps', [])
    ids = [step.get('id') for step in steps]
    if len(ids) != len(set(ids)) or any(not isinstance(i,str) or not i for i in ids):
        raise ContractValidationError(f"Contrat '{cid}' : étapes d’enquête invalides ou dupliquées.")
    for step in steps:
        if not step.get('tokens') or any(not isinstance(t,str) or not t for t in step['tokens']):
            raise ContractValidationError(f"Contrat '{cid}' : une enquête exige des références de compte rendu.")
        for key in ('response','already','missing','hint'):
            if not isinstance(step.get(key),str) or not step[key]:
                raise ContractValidationError(f"Contrat '{cid}' : réponse d’enquête manquante ({key}).")
        for condition in step.get('requires', []):
            error = condition_error(condition, host_ids, usernames)
            if error: raise ContractValidationError(f"Contrat '{cid}', enquête : {error}.")
            if condition.get('type') == 'investigation_step' and condition.get('step') not in ids:
                raise ContractValidationError(f"Contrat '{cid}' : étape d’enquête inconnue.")
        if any(host not in host_ids for host in step.get('discover', [])):
            raise ContractValidationError(f"Contrat '{cid}' : hôte d’enquête inconnu.")
    phases = []
    for step in steps:
        authored = step.get('help_stages', [])
        if not isinstance(authored, list):
            raise ContractValidationError(f"Contrat '{cid}' : phases d’aide invalides.")
        seen = set()
        for phase in authored:
            if not isinstance(phase, dict) or not isinstance(phase.get('id'), str) or not phase['id'] or phase['id'] in seen:
                raise ContractValidationError(f"Contrat '{cid}' : identifiant de phase d’aide invalide.")
            seen.add(phase['id'])
            if not isinstance(phase.get('requires'), list) or not phase['requires'] or not isinstance(phase.get('hint'), str) or not phase['hint'].strip() or not phase.get('hints'):
                raise ContractValidationError(f"Contrat '{cid}' : phase d’aide incomplète.")
            for condition in phase['requires']:
                if not isinstance(condition, dict): raise ContractValidationError(f"Contrat '{cid}' : condition d’aide invalide.")
                error = condition_error(condition, host_ids, usernames)
                if error: raise ContractValidationError(f"Contrat '{cid}', aide : {error}.")
                if condition.get('type') == 'investigation_step' and condition.get('step') not in ids:
                    raise ContractValidationError(f"Contrat '{cid}' : dépendance d’aide inconnue.")
            phases.append(phase)
    if "intro" in data and not isinstance(data["intro"], str):
        raise ContractValidationError(f"Contrat '{cid}' : 'intro' doit être un texte.")
    for node in [data, *data.get("guide", []), *data.get("investigation_steps", []), *phases]:
        if "summary" in node and (not isinstance(node["summary"],str) or not node["summary"].strip()):
            raise ContractValidationError(f"Contrat '{cid}' : résumé du guide invalide.")
        if "hints" in node and (not isinstance(node["hints"], list) or not node["hints"] or any(not isinstance(text,str) or not text.strip() for text in node["hints"])):
            raise ContractValidationError(f"Contrat '{cid}' : indices progressifs invalides.")
    for step in data.get("guide", []):
        if not step.get("message"):
            raise ContractValidationError(f"Contrat '{cid}' : une étape du guide n'a pas de message.")
    return data


def load_all_contracts(
    contracts_dir: Path = CONTRACTS_DIR,
    scenarios_dir: Path = SCENARIOS_DIR,
    known_ability_ids: set[str] | None = None,
) -> dict[str, dict]:
    contracts = {}
    for path in sorted(contracts_dir.glob("*.json")):
        data = load_contract(path, scenarios_dir, known_ability_ids)
        contracts[data["contract_id"]] = data
    return contracts


def start_contract(
    contract: dict,
    player_handle: str,
    scenarios_dir: Path = SCENARIOS_DIR,
    rng_seed: int | None = None,
    known_ability_ids: set[str] | None = None,
) -> GameState:
    """Crée la partie d'un contrat accepté et envoie le premier message du client."""
    state = load_scenario(
        scenarios_dir / f"{contract['scenario']}.json",
        rng_seed=rng_seed,
        known_ability_ids=known_ability_ids,
    )
    if contract.get("objectives"):
        state.objectives = list(contract["objectives"])
    state.contract = contract
    state.guidance_enabled = contract["tier"] == 0
    state.player_handle = player_handle
    if state.environment:
        env = state.environment
        known = state.hosts.get(env.get("briefing_host"))
        text = f"DOSSIER DE MISSION - {env['organization']}\nSecteur : {env['sector']}\nHoraires : {env['business_hours']} ({env['timezone']})\nCréneau : {env['initial_time']}\nAdresse connue : {known.ip if known else 'non fournie'}\nContact connu : {env['known_contact']}\n\n{env['context']}\n\nLes noms, adresses et documents appartiennent au laboratoire. Les durées sont accélérées.\nUne collecte d’identifiants ne crée pas automatiquement une session distante.\nAide facultative : demande aide au client, ou help outil dans le terminal.\n"
        state.terminal_files['/home/operator/mission/briefing.txt'] = text
    if contract.get('onboarding'):
        state.terminal_files.update({
            '/home/operator/mission/preparation.txt': 'Dossier reçu. Lire, vérifier, puis conclure ; aucun outil à exécuter dans ce document.\n',
            '/home/operator/mission/inventaire_ancien.txt': 'ARCHIVE 2024 - serveur en .99, informations non revérifiées.\n',
            '/home/operator/mission/changement_recent.txt': 'CHG clos le 02/11/2026 - serveur migre ; ancienne adresse retirée.\n'})
        if contract['contract_id'] == 'intro_hash':
            from .models import Credential
            from .ntlm import nt_hash
            digest = nt_hash(state.users['support.exercice'].password)
            state.loot.append(Credential('NTLM_HASH','support.exercice',digest,'poste-accueil'))
            state.terminal_files['/home/operator/mission/exercice.ntlm'] = digest+'\n'
    if state.environment.get("endpoint_policies") and any(any(path.startswith("/Users/Public/Documents/Support/") for path in host.files) for host in state.hosts.values()):
        state.terminal_files['/home/operator/mission/briefing.txt'] += "\nENQUÊTE : les documents du support se trouvent sous C:\\Users\\Public\\Documents\\Support sur le poste d'accueil. Comparer les dates avant de suivre une adresse. Une session Windows permet Get-Service et Test-NetConnection nom -Port port dans PowerShell. Les politiques locales se lisent dans C:\\ProgramData\\LabEndpoint\\policy.txt.\n"
    state.terminal_files.update(contract.get("local_files", {}))
    _send(state, contract["brief"])
    return state


def advance(state: GameState) -> None:
    """Appelé à la fin de chaque tick. Envoie le message de l'étape atteinte.

    Si le joueur a sauté des étapes (ex : phishing avant le scan), seul le
    message de l'étape la plus avancée part : le client ne commente pas ce
    que le joueur a déjà fait.
    """
    contract = state.contract
    if contract is None or state.contract_outcome is not None:
        return

    guide = contract.get("guide", [])
    reached = [
        i for i in range(state.guide_index, len(guide))
        if objective_met(state, guide[i]["when"])
    ]
    if reached and state.status == "RUNNING":
        if state.guidance_enabled: _send(state, guide[reached[-1]].get("summary", guide[reached[-1]]["message"]))
        state.guide_index = reached[-1] + 1

    if state.status == "ENDED":
        success = state.winner == "RED"
        state.contract_outcome = "SUCCESS" if success else "FAILED"
        _send(state, contract["success_message" if success else "failure_message"])


def render(text: str, contract: dict, player_handle: str | None = None, state: GameState | None = None) -> str:
    """Remplace {handle} et {reward}. replace plutôt que format : un texte
    de contrat peut contenir des accolades."""
    if state is not None:
        import re
        def credential_value(match):
            credential = state.find_credential(match[1], match[2])
            return credential.value if credential else '[identifiant non récupéré]'
        text = re.sub(r'\{credential:([^:{}]+):([^:{}]+)\}', credential_value, text)
    return (text.replace("{handle}", player_handle or "toi")
                .replace("{reward}", str(contract["reward"])))


def bounty_view(contract: dict) -> dict:
    """Ce que le forum affiche d'un contrat, avant qu'il soit accepté."""
    bounty = contract.get("bounty", {})
    return {
        "contract_id": contract["contract_id"],
        "tier": contract["tier"],
        "side_job": bool(contract.get("side_job")),
        "chapter": contract.get("chapter"),
        "affiliation": bool(contract.get("affiliation")),
        "forum": bounty.get("forum"),
        "channel": contract["channel"],
        "client": contract["client"],
        "title": render(bounty.get("title", contract["contract_id"]), contract),
        "body": render(bounty.get("body", ""), contract),
        "reward": contract["reward"],
        # Message du client AVANT acceptation (ex : invitation du tutoriel).
        "intro": render(contract["intro"], contract) if contract.get("intro") else None,
    }


# Mots qui orientent la réponse du client. L'API s'en sert aussi pour savoir si le joueur
# attend une réponse immédiate : une seule liste, pour qu'elles ne divergent plus.
HELP_WORDS = ("aide", "bloqu", "comment", "perdu", "indice", "rappel", "guide")
PAYMENT_WORDS = ("paiement", "prime", "argent", "paye")
OBJECTIVE_WORDS = ("objectif", "mission", "contrat")


def _asks_help(text: str) -> bool:
    # « Comment tu vas ? » est une question au personnage. « Comment utiliser
    # SQLmap ? » reste une demande d'aide, y compris après une salutation.
    lower = re.sub(r'comment\s+(?:tu vas|vas-tu|ça va|ca va|allez-vous|vous allez)', '', text.casefold())
    return any(word in lower for word in HELP_WORDS)


def wants_immediate_answer(text: str) -> bool:
    """Vrai si le message demande de l'aide, l'objectif ou le paiement : le client répond sans délai."""
    lower = text.casefold()
    return _asks_help(text) or any(word in lower for word in PAYMENT_WORDS + OBJECTIVE_WORDS)


def send(state: GameState, text: str) -> None:
    """Ajoute un message du client à la conversation de la mission."""
    _send(state, text)


def _send(state: GameState, text: str) -> None:
    contract = state.contract
    state.messages.append(
        Message(tick=state.tick, channel=contract["channel"],
                sender=contract["client"]["handle"],
                text=render(text, contract, state.player_handle, state), time=stamp(state.environment.get("world_minute", state.tick)))
    )


def player_message(state: GameState, channel: str, text: str, *, defer: bool = False) -> str | None:
    """Dialogue de PNJ déterministe ; aucune IA ni messagerie externe n'est appelée."""
    contract = state.contract
    if contract is None or contract["channel"] != channel:
        raise ValueError("Cette conversation n'est pas celle du contrat actif.")
    if len(state.messages) >= 200:
        raise ValueError("Cette conversation a atteint sa limite de messages pour la mission.")
    state.messages.append(Message(state.tick, channel, state.player_handle or "operator", text, stamp(state.environment.get("world_minute", state.tick))))
    lower = text.casefold()
    from .investigation import answer as investigation_answer, help_text
    from .guidance import hint
    asking_help = _asks_help(text)
    detailed_help = any(word in lower for word in ("compl", "détaill", "detaill", "rappel"))
    progressive = hint(state, detailed=detailed_help) if asking_help and not contract.get("investigation_steps") else None
    narrative = investigation_answer(state, text)
    if narrative is not None:
        answer = narrative
    elif progressive is not None:
        answer = progressive
    elif contract.get("investigation_steps") and asking_help:
        answer = help_text(state,detailed=detailed_help) or contract["brief"]
    elif any(word in lower for word in PAYMENT_WORDS):
        answer = f"Ce contrat t'a rapporté {state.payout} ₵. C'est dans ton profil." if state.contract_outcome == "SUCCESS" else f"La prime annoncée, c'est {contract['reward']} ₵. Ce que tu touches vraiment dépend du résultat et des conditions du contrat."
    elif asking_help:
        previous = state.guide_index - 1
        guide = contract.get("guide", [])
        answer = guide[previous]["message"] if 0 <= previous < len(guide) else contract["brief"]
    elif any(word in lower for word in OBJECTIVE_WORDS):
        answer = contract.get("bounty", {}).get("body", contract["brief"])
    else:
        from .dialogue import intent, reply
        from .social import content
        topic = intent(text)
        authored = contract.get('dialogue', {})
        contact = next((c for c in content()['contacts'] if c['id'] == contract['client']['handle']), None)
        if topic in {'greeting', 'thanks'} and authored.get('greeting' if topic == 'greeting' else 'ack'):
            answer = authored['greeting' if topic == 'greeting' else 'ack']
        elif contact:
            memory = state.tool_data.setdefault('dialogue', {}).setdefault(contact['id'], {})
            answer = reply(contact, text, memory, state.player_handle or 'operator')
        else:
            answer = authored.get('fallback', authored.get('ack', 'Je ne suis pas sûr de comprendre. Tu peux préciser ?'))
    if defer and narrative is None: return render(answer, contract, state.player_handle, state)
    _send(state, answer)
    return None
