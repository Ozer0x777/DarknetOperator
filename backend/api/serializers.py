"""Transforme un GameState en JSON pour l'API REST / WebSocket."""
from __future__ import annotations

from engine.models import GameState
from engine import trace
from engine.contracts import render
from engine.console_sessions import public_contexts
from engine.win_conditions import objective_met

HISTORY_TAIL = 40
ALERTS_TAIL = 40


def serialize_state(state: GameState) -> dict:
    result = {
        "trace": trace.summary(state),
        "end_reason": state.end_reason,
        "terminals": public_contexts(state),
        "terminal": {"user": state.terminal_user, "cwd": state.terminal_cwd, "hostname": state.hosts[state.terminal_host].hostname if state.terminal_host else "redteam"},
        "exfiltrated": list(state.exfiltrated),
        "tick": state.tick,
        "max_ticks": state.max_ticks,
        "status": state.status,
        "winner": state.winner,
        "scenario_name": state.scenario_name,
        "guidance_enabled": state.guidance_enabled,
        "domain_compromised": state.domain_compromised,
        "score": state.score,
        "available_abilities": state.available_abilities,
        "objectives": [
            {**o, "met": objective_met(state, o)} for o in state.objectives
        ],
        "player_handle": state.player_handle,
        "contract": _contract_summary(state),
        "messages": [
            {"id": f"{state.conversation_id}:{i}", "peer": state.contract["client"]["handle"] if state.contract else m.sender, "tick": m.tick, "channel": m.channel, "sender": m.sender, "text": m.text, "time": m.time}
            for i, m in enumerate(state.messages)
        ],
        # Brouillard de guerre : la vue Red ne doit afficher que ces hôtes.
        "discovered": sorted(state.discovered),
        "scanned": sorted(state.scanned),
        "cooldowns": {
            ability_id: available_at
            for ability_id, available_at in state.cooldowns.items()
            if available_at > state.tick
        },
        "hosts": [
            {
                "id": host.id,
                "hostname": host.hostname,
                "ip": host.ip,
                "status": host.status,
                "encrypted": host.encrypted,
                "os": host.os if host.id in state.tool_data.get("recon", {}).get("versions", []) else None,
                "services": _observed_services(state, host),
                "edr_agent": host.edr_agent if host.compromised_by == "red" else None,
                "admin_users": host.admin_users if host.compromised_by == "red" else [],
                "compromised_by": host.compromised_by,
            }
            for host in state.hosts.values() if host.id in state.discovered
        ],
        "users": [
            {
                "username": u.username,
                "status": u.status,
                "is_domain_admin": u.is_domain_admin,
                "has_dcsync_rights": u.has_dcsync_rights,
            }
            for u in state.users.values() if state.find_credential(u.username)
        ],
        "loot": [
            {
                "type": c.type,
                "username": c.username,
                "value": c.value,
                "source_host": c.source_host,
                "valid": c.valid,
            }
            for c in state.loot
        ],
        "firewall_blocks": [{"host_id": h, "port": p} for h, p in sorted(state.firewall_blocks)],
        "alerts": [
            {
                "id": a.id,
                "title": a.title,
                "severity": a.severity,
                "rule_id": a.rule_id,
                "host_id": a.host_id,
                "attack_tick": a.attack_tick,
                "detected_tick": a.detected_tick,
                "status": a.status,
            }
            for a in state.alerts[-ALERTS_TAIL:][::-1]
        ],
        "history": [
            {
                "tick": h.tick,
                "team": h.team,
                "message": h.message,
                "success": h.success,
                "reason": h.reason,
                "exit_code": h.exit_code,
                "console_id": h.console_id,
                "id": i,
            }
            for i, h in reversed(list(enumerate(state.history))[-HISTORY_TAIL:])
        ],
    }

    if state.status == "ENDED":
        from engine.security import incident_summary
        result["debrief"] = {
            "impact": incident_summary(state),
            "history": [{"tick": h.tick, "team": h.team, "message": h.message, "success": h.success} for h in state.history],
            "alerts": [{"detected_tick": a.detected_tick, "severity": a.severity, "title": a.title} for a in state.alerts],
            "logs": [{"tick": log.tick, "host": log.host_id, "event_id": log.event_id, "data": log.data} for log in state.logs],
            "trace": state.trace.get("events", []),
        }
    return result


def _contract_summary(state: GameState) -> dict | None:
    """Résumé du contrat pour l'interface. Le guide n'est pas envoyé : le
    joueur ne doit pas voir les étapes à venir."""
    contract = state.contract
    if contract is None:
        return None
    return {
        "contract_id": contract["contract_id"],
        "title": render(contract.get("bounty", {}).get("title", contract["contract_id"]), contract, state.player_handle),
        "goal": render(contract.get("bounty", {}).get("body", ""), contract, state.player_handle),
        "onboarding": bool(contract.get("onboarding")),
        "private_offer": bool(contract.get("private_offer")),
        "tier": contract["tier"],
        "channel": contract["channel"],
        "client": contract["client"]["handle"],
        "reward": contract["reward"],
        "outcome": state.contract_outcome,
        "payout": state.payout,
        # Le débriefing n'est révélé qu'à la fin du contrat.
        "debrief_hints": contract.get("debrief_hints", []) if state.contract_outcome else [],
    }


def _observed_services(state, host):
    if host.id not in state.scanned:
        return []
    observation = state.tool_data.get("recon", {}).get("observations", {}).get(host.id)
    if observation is not None:
        return observation["services"]
    # Anciennes sauvegardes : aucune observation détaillée n'existait.
    return [{"name": s.name, "port": s.port, "version": s.version if host.id in state.tool_data.get("recon", {}).get("versions", []) else ""} for s in host.services if host.id not in state.known_ports or s.port in state.known_ports[host.id]]
