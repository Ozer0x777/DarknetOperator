"""Sécurité automatique des cibles : obstacles temporaires du jeu solo Red Team."""
from .models import GameState, HistoryEntry, ActionContext
from . import effects


def advance(state: GameState) -> None:
    settings = state.defender
    if not settings.get("enabled"):
        return
    recovery = state.tool_data.setdefault("security_recovery", {})
    # Les anciennes sauvegardes isolées reçoivent aussi une voie de rétablissement.
    for host in state.hosts.values():
        if host.status == "ISOLATED" and host.id not in recovery:
            names = {c.username for c in state.loot if c.source_host == host.id}
            users = {name: "ACTIVE" for name in names if name in state.users and state.users[name].status == "DISABLED"}
            recovery[host.id] = {"due": state.tick + 6, "status": "COMPROMISED" if host.compromised_by else "HEALTHY", "users": users, "credentials": [i for i, c in enumerate(state.loot) if c.username in users]}
            state.max_ticks += 6
            state.history.append(HistoryEntry(state.tick, "blue", f"Sécurité de la cible : rétablissement de {host.hostname} prévu au tick {state.tick + 6}.", True))
    for host_id, record in recovery.items():
        if record.get("done") or state.tick < record["due"]:
            continue
        host = state.hosts[host_id]
        if host.status == "ISOLATED":
            host.status = record["status"]
            host.isolated_at_tick = None
        for username, status in record["users"].items():
            state.users[username].status = status
        for index in record["credentials"]:
            if index < len(state.loot):
                state.loot[index].valid = True
        record["done"] = True
        state.history.append(HistoryEntry(state.tick, "blue", f"Maintenance terminée : {host.hostname} est de nouveau accessible. Reconnecte ta console si nécessaire.", True))
    reaction = settings.get("reaction_ticks", 6)
    for alert in state.alerts:
        if alert.status != "NEW" or state.tick - alert.detected_tick < reaction:
            continue
        alert.status = "ACK"
        host = state.hosts[alert.host_id]
        # Un seul confinement par machine : pas de boucle qui condamne un objectif.
        if alert.severity not in {"HIGH", "CRITICAL"} or host.id in recovery:
            continue
        record = {"due": state.tick + 6, "status": host.status, "users": {}, "credentials": []}
        recovery[host.id] = record
        effects.isolate_host(state, ActionContext(actor="blue", target=host, tick=state.tick))
        if settings.get("disable_accounts", False):
            names = {c.username for c in state.loot if c.source_host == host.id and c.username in state.users and state.users[c.username].status == "ACTIVE"}
            record["credentials"] = [i for i, c in enumerate(state.loot) if c.username in names and c.valid]
            for name in names:
                user = state.users.get(name)
                if user and user.status == "ACTIVE":
                    record["users"][name] = user.status
                    effects.disable_user(state, ActionContext("blue", host, state.tick, user=user))
        state.history.append(HistoryEntry(state.tick, "blue", f"Sécurité de la cible : {host.hostname} isolé temporairement. Rétablissement prévu au tick {record['due']}. La mission continue ; travaille ailleurs ou attends dans les paramètres.", True))
        # Le temps de confinement ne consomme pas le délai disponible pour l'objectif.
        state.max_ticks += 6
