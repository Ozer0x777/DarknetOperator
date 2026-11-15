"""
Sérialisation du GameState pour sauvegarde et restauration explicites.
Ce module ne fournit pas de stockage automatique ni de base SQLite.

Seul point délicat : random.Random n'est pas JSON-natif. getstate() renvoie
des tuples, qui deviennent des listes après un aller-retour JSON ; il faut
les retransformer en tuples avant setstate() (random.setstate l'exige).
"""
from __future__ import annotations

from dataclasses import fields

from .models import (
    Alert, Credential, GameState, HistoryEntry, Host, LogEvent, Message,
    Service, User,
)


def _restore(cls, row: dict):
    """Recrée un objet sauvegardé en ignorant les champs que sa classe n'a plus : retirer un
    champ d'un modèle ne doit pas rendre les anciennes sauvegardes illisibles."""
    known = {f.name for f in fields(cls)}
    return cls(**{key: value for key, value in row.items() if key in known})


def _tupleify(value):
    if isinstance(value, list):
        return tuple(_tupleify(v) for v in value)
    return value


def state_to_dict(state: GameState) -> dict:
    return {
        "hosts": [
            {
                "id": h.id, "hostname": h.hostname, "ip": h.ip, "status": h.status,
                "services": [{"name": s.name, "port": s.port, "version": s.version} for s in h.services],
                "edr_agent": h.edr_agent, "admin_users": h.admin_users, "os": h.os, "encrypted": h.encrypted, "role": h.role, "phishing": h.phishing,
                "compromised_by": h.compromised_by, "isolated_at_tick": h.isolated_at_tick,
                "primary_user": h.primary_user, "cached_logons": h.cached_logons,
                "is_domain_controller": h.is_domain_controller, "access_level": h.access_level, "files": h.files, "backups": h.backups,
            }
            for h in state.hosts.values()
        ],
        "users": [
            {
                "username": u.username, "status": u.status,
                "is_domain_admin": u.is_domain_admin, "has_dcsync_rights": u.has_dcsync_rights, "password": u.password,
            }
            for u in state.users.values()
        ],
        "loot": [
            {"type": c.type, "username": c.username, "value": c.value,
             "source_host": c.source_host, "valid": c.valid}
            for c in state.loot
        ],
        "logs": [{"event_id": l.event_id, "host_id": l.host_id, "tick": l.tick, "data": l.data}
                 for l in state.logs],
        "alerts": [
            {"id": a.id, "title": a.title, "severity": a.severity, "rule_id": a.rule_id,
             "host_id": a.host_id, "attack_tick": a.attack_tick, "detected_tick": a.detected_tick,
             "status": a.status}
            for a in state.alerts
        ],
        "history": [
            {"tick": h.tick, "team": h.team, "message": h.message, "success": h.success, "reason": h.reason, "console_id": h.console_id, "exit_code": h.exit_code}
            for h in state.history
        ],
        "domain_compromised": state.domain_compromised,
        "tick": state.tick,
        "max_ticks": state.max_ticks,
        "status": state.status,
        "winner": state.winner,
        "rng_state": state.rng.getstate(),
        "next_alert_seq": state.next_alert_seq,
        "scenario_name": state.scenario_name,
        "available_abilities": state.available_abilities,
        "discovered": sorted(state.discovered),
        "scanned": sorted(state.scanned),
        "objectives": state.objectives,
        "contract": state.contract,
        "player_handle": state.player_handle,
        "messages": [
            {"tick": m.tick, "channel": m.channel, "sender": m.sender, "text": m.text, "time": m.time}
            for m in state.messages
        ],
        "guide_index": state.guide_index,
        "contract_outcome": state.contract_outcome,
        **{key: getattr(state, key) for key in ("conversation_id", "trace", "defender", "inventory", "exfiltrated", "end_reason", "payout", "terminal_host", "terminal_user", "terminal_access", "terminal_shell", "terminal_last_exit", "terminal_last_native_exit", "terminal_return_stack", "guidance_enabled", "terminal_auth", "terminal_cwd", "terminal_files", "terminals", "terminal_env", "terminal_foreground", "terminal_network_path", "tool_services", "tool_data", "pending_actions", "known_ports", "domain", "environment")},
    }


def state_from_dict(data: dict) -> GameState:
    import random as _random

    hosts = {
        h["id"]: Host(
            id=h["id"], hostname=h["hostname"], ip=h["ip"], status=h["status"],
            services=[Service(s["name"], s["port"], s.get("version", "")) for s in h["services"]],
            edr_agent=h["edr_agent"], admin_users=h["admin_users"],
            compromised_by=h["compromised_by"], isolated_at_tick=h["isolated_at_tick"],
            # .get : les sauvegardes antérieures à ces champs restent chargeables.
            primary_user=h.get("primary_user"), cached_logons=h.get("cached_logons", []),
            encrypted=h.get("encrypted", h.get("status") == "ENCRYPTED"), os=h.get("os", "Windows Server 2022"), role=h.get("role", ""), phishing=h.get("phishing", {}),
            is_domain_controller=h.get("is_domain_controller", False), access_level=h.get("access_level", "NONE"), files=h.get("files", {}), backups=h.get("backups", True),
        )
        for h in data["hosts"]
    }
    users = {
        u["username"]: User(
            username=u["username"], status=u["status"],
            is_domain_admin=u["is_domain_admin"], has_dcsync_rights=u["has_dcsync_rights"], password=u.get("password"),
        )
        for u in data["users"]
    }

    state = GameState(hosts=hosts, users=users)
    state.loot = [_restore(Credential, c) for c in data["loot"]]
    state.logs = [_restore(LogEvent, l) for l in data["logs"]]
    state.alerts = [_restore(Alert, a) for a in data["alerts"]]
    state.history = [_restore(HistoryEntry, h) for h in data["history"]]
    state.domain_compromised = data["domain_compromised"]
    state.tick = data["tick"]
    state.max_ticks = data["max_ticks"]
    state.status = data["status"]
    state.winner = data["winner"]
    # Les anciennes sauvegardes contiennent encore "score", "players", "firewall_blocks" et "cooldowns" : ces clés sont ignorées.
    state.next_alert_seq = data["next_alert_seq"]
    state.scenario_name = data["scenario_name"]
    state.available_abilities = data["available_abilities"]
    # Anciennes sauvegardes (avant le brouillard de guerre) : tout est connu.
    state.discovered = set(data.get("discovered", hosts))
    state.scanned = set(data.get("scanned", hosts))
    state.objectives = data.get("objectives", [])
    state.contract = data.get("contract")
    state.player_handle = data.get("player_handle")
    state.messages = [_restore(Message, m) for m in data.get("messages", [])]
    state.guide_index = data.get("guide_index", 0)
    state.contract_outcome = data.get("contract_outcome")

    state.rng = _random.Random()
    state.rng.setstate(_tupleify(data["rng_state"]))
    for key in ("conversation_id", "trace", "defender", "inventory", "exfiltrated", "end_reason", "payout", "terminal_host", "terminal_user", "terminal_access", "terminal_shell", "terminal_last_exit", "terminal_last_native_exit", "terminal_return_stack", "guidance_enabled", "terminal_auth", "terminal_cwd", "terminal_files", "terminals", "terminal_env", "terminal_foreground", "terminal_network_path", "tool_services", "tool_data", "pending_actions", "known_ports", "domain", "environment"):
        if key in data:
            setattr(state, key, data[key])
    legacy_users = {u['username'] for u in data['users'] if 'password' not in u}
    if legacy_users:
        import hashlib
        from .ntlm import nt_hash
        primary = {h.primary_user for h in state.hosts.values()}
        aliases = state.tool_data.setdefault('legacy_hash_aliases', {})
        extra_words = []
        for username in legacy_users:
            account = state.users[username]
            clear = next((c.value for c in reversed(state.loot) if c.username==username and c.type=='PLAINTEXT'), None)
            hashes = [c for c in state.loot if c.username==username and c.type=='NTLM_HASH']
            known_old = [c for c in hashes if c.value==hashlib.sha256(f'fictional:{c.source_host}:{username}'.encode()).hexdigest()[:32]]
            if hashes and not known_old and clear is None: continue
            account.password = clear or ('sim-password-'+username if known_old else ('Password123!' if username in primary else 'Maintenance2026!'))
            for credential in known_old:
                old = credential.value
                credential.value = nt_hash(account.password)
                aliases[old] = credential.value
                for filename, text in list(state.terminal_files.items()):
                    if text.strip()==old: state.terminal_files[filename] = text.replace(old,credential.value)
                for action in state.pending_actions:
                    if action.get('params',{}).get('credential_value')==old: action['params']['credential_value']=credential.value
            if known_old: extra_words.append(account.password)
        if extra_words:
            from .hashcat_model import prepare
            prepare(state)
            filename='/usr/share/wordlists/rockyou.txt'
            lines=state.terminal_files[filename].splitlines()
            state.terminal_files[filename]='\n'.join(dict.fromkeys(lines+extra_words))+'\n'
        state.environment['credential_migration'] = True
    return state
