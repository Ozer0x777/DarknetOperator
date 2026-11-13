"""
Bruit de fond du réseau cible.

Génère, à chaque tick, des logs "légitimes" qui ne correspondent à AUCUNE
règle SIEM (siem.py) : logons normaux, accès SMB normaux. Le flux de la défense
contient ainsi autre chose que les actions du joueur, et le rapport de fin de
mission montre une activité ordinaire autour d'elles.
"""
from __future__ import annotations

from .models import GameState, LogEvent

LEGITIMATE_LOGON_CHANCE = 0.25   # par tick, par host non compromis/isolé
LEGITIMATE_SMB_CHANCE = 0.15
# Le bruit sert de décor au flux de la défense : seuls les plus récents sont gardés. Sans limite,
# une longue mission accumulait des milliers d'entrées réécrites à chaque sauvegarde et noyait
# le rapport final. Les événements des actions et de la défense, eux, sont tous conservés.
NOISE_LIMIT = 300
NOISE_NOTES = ("logon interactif normal", "accès partage normal")


def is_noise(log: LogEvent) -> bool:
    return log.data.get("note") in NOISE_NOTES


def generate(state: GameState) -> list[LogEvent]:
    noise_logs: list[LogEvent] = []

    for host in state.hosts.values():
        if host.status in ("ISOLATED", "ENCRYPTED"):
            continue  # un host coupé du réseau n'a plus d'activité normale

        if state.rng.random() < LEGITIMATE_LOGON_CHANCE:
            noise_logs.append(LogEvent(
                event_id="4624",
                host_id=host.id,
                tick=state.tick,
                data={"LogonType": 2, "LogonProcessName": "User32", "note": "logon interactif normal"},
            ))

        if host.has_service("SMB", 445) and state.rng.random() < LEGITIMATE_SMB_CHANCE:
            noise_logs.append(LogEvent(
                event_id="5140",
                host_id=host.id,
                tick=state.tick,
                data={"ShareName": "DATA", "note": "accès partage normal"},
            ))

    state.logs.extend(noise_logs)
    excess = sum(1 for log in state.logs if is_noise(log)) - NOISE_LIMIT
    if excess > 0:
        kept = []
        for log in state.logs:  # les plus anciens bruits partent en premier
            if excess > 0 and is_noise(log):
                excess -= 1
                continue
            kept.append(log)
        state.logs[:] = kept
    return noise_logs
