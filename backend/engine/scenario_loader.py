"""Charge et valide le fichier de scénario JSON d'un contrat."""
from __future__ import annotations

import json
import random
from pathlib import Path

from .models import GameState, Host, Service, User
from .win_conditions import condition_error


class ScenarioValidationError(Exception):
    """Le JSON du scénario est structurellement correct mais référence
    quelque chose d'incohérent (ex: un utilisateur admin qui n'existe pas).
    Plutôt qu'une KeyError brute au premier tick, on échoue tôt et clairement."""


def load_scenario(
    path: Path,
    rng_seed: int | None = None,
    known_ability_ids: set[str] | None = None,
) -> GameState:
    data = json.loads(path.read_text(encoding='utf-8'))

    hosts = {}
    for h in data["hosts"]:
        hosts[h["id"]] = Host(
            id=h["id"],
            hostname=h["hostname"],
            ip=h["ip"],
            services=[Service(s["name"], s["port"], s.get("version", "")) for s in h.get("services", [])],
            edr_agent=h.get("edr_agent", False),
            admin_users=list(h.get("admin_users", [])),
            primary_user=h.get("primary_user"),
            cached_logons=list(h.get("cached_logons", [])),
            files=dict(h.get("files", {})), backups=h.get("backups", True),
            is_domain_controller=h.get("is_domain_controller", False),
            os=h.get("os", "Windows Server 2022"), role=h.get("role", ""), phishing=dict(h.get("phishing", {})),
        )

    users = {}
    for u in data["users"]:
        users[u["username"]] = User(
            username=u["username"],
            is_domain_admin=u.get("is_domain_admin", False),
            has_dcsync_rights=u.get("has_dcsync_rights", False), password=u.get("password"),
        )

    _validate(data, hosts, users, known_ability_ids)

    state = GameState(hosts=hosts, users=users)
    state.max_ticks = data.get("max_ticks", state.max_ticks)
    state.scenario_name = data.get("name", data.get("scenario_id", ""))
    state.available_abilities = data.get("available_abilities", {})
    state.objectives = list(data.get("objectives", []))
    state.defender = dict(data.get("defender", {}))
    state.domain = dict(data.get("domain", {}))
    state.environment = dict(data.get("environment", {}))
    # Brouillard de guerre : sans champ explicite, tout est connu. Les contrats
    # déclarent ce que le joueur connaît au départ (souvent un seul hôte, donné par le client).
    if "initially_discovered" in data:
        state.discovered = set(data["initially_discovered"])
        state.scanned = set(data.get("initially_scanned", []))
    else:
        state.discovered = set(hosts)
        state.scanned = set(hosts)
    if rng_seed is not None:
        state.rng = random.Random(rng_seed)
    elif "rng_seed" in data:
        state.rng = random.Random(data["rng_seed"])
    return state


def _validate(
    data: dict,
    hosts: dict[str, Host],
    users: dict[str, User],
    known_ability_ids: set[str] | None,
) -> None:
    for h in data["hosts"]:
        referenced = [("admin_users", u) for u in h.get("admin_users", [])]
        referenced += [("cached_logons", u) for u in h.get("cached_logons", [])]
        if h.get("primary_user"):
            referenced.append(("primary_user", h["primary_user"]))
        for field_name, username in referenced:
            if username not in users:
                raise ScenarioValidationError(
                    f"Host '{h['hostname']}' référence l'utilisateur inconnu "
                    f"'{username}' dans '{field_name}' — vérifie la liste 'users' du scénario."
                )
    import ipaddress
    addresses = [host.ip for host in hosts.values()]
    if len(addresses) != len(set(addresses)):
        raise ScenarioValidationError("Des hôtes partagent la même adresse IP.")
    for host in hosts.values():
        try: ipaddress.ip_address(host.ip)
        except ValueError as exc: raise ScenarioValidationError(f"Adresse IP invalide : {host.ip}") from exc
        if host.phishing:
            if host.phishing.get("response") not in {"submitted", "ignored", "reported"} or not isinstance(host.phishing.get("delay_ticks"), int) or not 1 <= host.phishing["delay_ticks"] <= 60:
                raise ScenarioValidationError(f"Profil de réponse invalide pour {host.id}.")
        human = host.phishing.get('human_model')
        if human is not None:
            if not isinstance(human,dict) or any(not isinstance(human.get(key), (int,float)) or not 0 <= human[key] <= 1 for key in ('submit_probability','report_probability','suspicion')):
                raise ScenarioValidationError(f"Modèle de décision invalide pour {host.id}.")
            if any(not isinstance(human.get(key),int) for key in ('delay_min','delay_max')) or not 0 <= human['delay_min'] <= human['delay_max'] <= 30:
                raise ScenarioValidationError(f"Délais humains invalides pour {host.id}.")
        schedule = host.phishing.get('availability')
        if schedule is not None and (not isinstance(schedule, dict) or any(not isinstance(schedule.get(key), int) for key in ('start','end')) or not 0 <= schedule['start'] < 1440 or not 0 < schedule['end'] <= 1440 or schedule['start'] == schedule['end']):
            raise ScenarioValidationError(f"Horaires invalides pour {host.id}.")
        terms = host.phishing.get('blocked_subjects', [])
        if not isinstance(terms, list) or any(not isinstance(term, str) or not term for term in terms):
            raise ScenarioValidationError(f"Filtre de messagerie invalide pour {host.id}.")
        if host.is_domain_controller and host.os.startswith("Linux"):
            raise ScenarioValidationError("Un contrôleur AD de ce modèle doit déclarer son environnement Windows.")
    host_ids = set(hosts)
    if len(host_ids) != len(data["hosts"]):
        raise ScenarioValidationError("Des hosts ont des ids en double dans le scénario.")
    usernames = set(users)
    if len(usernames) != len(data["users"]):
        raise ScenarioValidationError("Des users ont des usernames en double dans le scénario.")

    env = data.get("environment", {})
    for host_id, routes in env.get('http_routes', {}).items():
        if host_id not in hosts or not isinstance(routes,dict) or not any(service.port in {80,443} for service in hosts[host_id].services):
            raise ScenarioValidationError('Routes HTTP sans serveur valide.')
        for route, filename in routes.items():
            files = list(filename.get('objects',{}).values()) if isinstance(filename,dict) and 'objects' in filename else [filename.get('file')] if isinstance(filename,dict) else [filename]
            if not isinstance(route,str) or not route.startswith('/') or any(file not in hosts[host_id].files for file in files):
                raise ScenarioValidationError('Route HTTP sans fichier valide.')
    from .data_tools import database_script
    import sqlite3
    databases=env.get('databases',{})
    for name,spec in databases.items():
        if not isinstance(name,str) or not name.replace('_','').isalnum() or spec.get('host') not in hosts:
            raise ScenarioValidationError('Base sans nom ou hôte valide.')
        try:database_script(spec)
        except (ValueError,KeyError,sqlite3.Error,TypeError) as exc:raise ScenarioValidationError('Schéma ou données SQL invalides.') from exc
        for account,grant in spec.get('accounts',{}).items():
            if not isinstance(grant.get('password'),str) or any(t not in spec['tables'] for t in grant.get('tables',[])):
                raise ScenarioValidationError('Droits SQL invalides.')
    for host_id,surfaces in env.get('sql_surfaces',{}).items():
        if host_id not in hosts:raise ScenarioValidationError('Surface SQL sur un hôte inconnu.')
        for route,surface in surfaces.items():
            if not route.startswith('/') or surface.get('database') not in databases or not surface.get('parameter'):
                raise ScenarioValidationError('Surface SQL incomplète.')
            if any(t not in databases[surface['database']]['tables'] for t in surface.get('tables',[])):
                raise ScenarioValidationError('Surface SQL avec une table inconnue.')
    for host_id,shares in env.get('shares',{}).items():
        if host_id not in hosts or not hosts[host_id].has_service('SMB',445):raise ScenarioValidationError('Partage sans service SMB.')
        for share in shares.values():
            if not share.get('path','').startswith('/') or any(u not in users and u!='*' for u in share.get('users',[])):
                raise ScenarioValidationError('Chemin ou identité de partage invalide.')
    for rule in env.get("network_rules", []):
        if not isinstance(rule, dict) or rule.get("source") not in host_ids | {"operator", "*"} or rule.get("target") not in host_ids or type(rule.get("port")) is not int or not 1 <= rule["port"] <= 65535 or rule.get("action") not in {"allow", "deny"}:
            raise ScenarioValidationError("Règle réseau invalide : source, cible, port ou action.")
    for host_id, policy in env.get("endpoint_policies", {}).items():
        if host_id not in host_ids or not hosts[host_id].edr_agent or not isinstance(policy, dict):
            raise ScenarioValidationError("Politique EDR sans hôte protégé valide.")
        for ability_id, disposition in policy.get("actions", {}).items():
            if disposition not in {"audit", "block"} or (known_ability_ids is not None and ability_id not in known_ability_ids):
                raise ScenarioValidationError("Action ou disposition EDR invalide.")

    for key in ("initially_discovered", "initially_scanned"):
        for host_id in data.get(key, []):
            if host_id not in host_ids:
                raise ScenarioValidationError(
                    f"'{key}' référence l'hôte inconnu '{host_id}' — vérifie la liste 'hosts'."
                )

    for objective in data.get("objectives", []):
        error = condition_error(objective, host_ids, usernames)
        if error:
            raise ScenarioValidationError(f"Objectif invalide : {error}.")

    if known_ability_ids is not None:
        declared = data.get("available_abilities", {})
        for team in ("red", "blue"):
            for ability_id in declared.get(team, []):
                if ability_id not in known_ability_ids:
                    raise ScenarioValidationError(
                        f"Scénario '{data.get('scenario_id')}' référence l'ability "
                        f"inconnue '{ability_id}' dans available_abilities.{team}."
                    )
