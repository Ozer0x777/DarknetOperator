"""
Moteur de règles SIEM minimal — même principe déclaratif que les abilities
(§5.6 du blueprint), réduit aux 3 règles nécessaires au MVP :
Pass-the-Hash, exécution Mimikatz, DCSync.
"""
from __future__ import annotations

from .models import Alert, GameState, LogEvent


def _match_pass_the_hash(log: LogEvent) -> bool:
    return (
        log.event_id == "4624"
        and log.data.get("LogonType") == 3
        and log.data.get("LogonProcessName") == "NtLmSsp"
        and log.data.get("KeyLength") == 0
    )


def _match_mimikatz(log: LogEvent) -> bool:
    return log.event_id == "4663" and "lsass" in str(log.data.get("TargetObject", "")).lower()


def _match_dcsync(log: LogEvent) -> bool:
    return log.event_id == "4662" and log.data.get("ObjectType") == "DS-Replication-Get-Changes"


RULES = [
    ("SIEM-RULE-011", "Service d’administration distante créé", "MEDIUM", lambda log: log.event_id == "7045"),
    ("SIEM-RULE-010", "Chiffrement massif détecté", "CRITICAL", lambda log: log.event_id == "SIM-ENCRYPT"),
    ("SIEM-RULE-002", "Authentification NTLM atypique — à qualifier", "HIGH", _match_pass_the_hash),
    ("SIEM-RULE-004", "Mimikatz Execution", "CRITICAL", _match_mimikatz),
    ("SIEM-RULE-005", "DCSync Detected", "CRITICAL", _match_dcsync),
]


def evaluate(state: GameState, new_logs: list[LogEvent]) -> list[Alert]:
    """Évalue les règles sur les logs générés CE tick et renvoie les nouvelles alertes."""
    new_alerts = []
    for log in new_logs:
        for rule_id, title, severity, matcher in RULES:
            if matcher(log):
                alert = Alert(
                    id=state.next_alert_id(),
                    title=title,
                    severity=severity,
                    rule_id=rule_id,
                    host_id=log.host_id,
                    attack_tick=log.tick,
                    detected_tick=state.tick,
                )
                state.alerts.append(alert)
                new_alerts.append(alert)
                # §11 du blueprint, simplifié : le SIEM qui détecte rapporte des
                # points à Blue indépendamment de ce qu'il en fait ensuite —
                # le containment effectif est récompensé séparément (abilities Blue).
                state.score["blue"] = state.score.get("blue", 0) + (10 if severity == "CRITICAL" else 5)
    return new_alerts
