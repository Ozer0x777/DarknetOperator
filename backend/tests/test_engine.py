"""
Suite de tests du moteur. Remplace les simples `assert` de demo_cli.py par
de vrais cas isolés — chacun doit pouvoir échouer indépendamment des autres.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from engine import ability_engine, noise, siem
from engine.game_loop import GameLoop, QueuedAction, load_all_abilities
from engine.models import ActionContext
from engine.scenario_loader import ScenarioValidationError, load_scenario

ROOT = Path(__file__).parent.parent
SCENARIO_PATH = ROOT / "scenarios" / "mvp_demo.json"
ABILITIES = load_all_abilities()


def fresh_state(seed: int = 1):
    return load_scenario(SCENARIO_PATH, rng_seed=seed, known_ability_ids=set(ABILITIES))


# ---------------------------------------------------------------------------
# Résolution d'abilities
# ---------------------------------------------------------------------------

def test_psexec_fails_without_credential():
    state = fresh_state()
    ability = ABILITIES["red.psexec_lateral"]
    ctx = ActionContext(actor="red", target=state.hosts["file-01"], tick=1, credential=None)
    result = ability_engine.resolve(ability, state, ctx)
    assert result.success is False
    assert "credential_grants_admin_on_target" in result.reason


def test_psexec_fails_on_isolated_host():
    state = fresh_state()
    state.hosts["file-01"].status = "ISOLATED"
    ability = ABILITIES["red.psexec_lateral"]
    ctx = ActionContext(actor="red", target=state.hosts["file-01"], tick=1, credential=None)
    result = ability_engine.resolve(ability, state, ctx)
    assert result.success is False
    assert result.reason == "prerequisite failed: target_status_not"


# ---------------------------------------------------------------------------
# Firewall (gap identifié : "le firewall n'est jamais utilisé")
# ---------------------------------------------------------------------------

def test_block_ip_blocks_psexec():
    from engine.models import Credential

    state = fresh_state()
    state.loot.append(Credential(type="NTLM_HASH", username="svc_backup", value="x", source_host="pc-01"))
    file01 = state.hosts["file-01"]

    # Sans blocage : psexec doit réussir.
    ctx = ActionContext(actor="red", target=file01, tick=1, credential=state.find_credential("svc_backup"))
    assert ability_engine.resolve(ABILITIES["red.psexec_lateral"], state, ctx).success is True

    # Blue bloque le port 445 vers FILE-01.
    blue_ctx = ActionContext(actor="blue", target=file01, tick=2)
    ability_engine.resolve(ABILITIES["blue.block_ip"], state, blue_ctx)
    assert state.is_blocked("file-01", 445) is True

    # La même action Red échoue maintenant à cause du firewall (tick 10 pour
    # être sûr d'être hors du cooldown de 4 ticks de psexec_lateral).
    ctx2 = ActionContext(actor="red", target=file01, tick=10, credential=state.find_credential("svc_backup"))
    result = ability_engine.resolve(ABILITIES["red.psexec_lateral"], state, ctx2)
    assert result.success is False
    assert result.reason == "prerequisite failed: not_blocked_by_firewall"


# ---------------------------------------------------------------------------
# Cooldowns (gap identifié : "pas de cooldown sur les actions")
# ---------------------------------------------------------------------------

def test_cooldown_blocks_immediate_reuse():
    state = fresh_state()
    host = state.hosts["dc-01"]

    ctx1 = ActionContext(actor="blue", target=host, tick=1)
    r1 = ability_engine.resolve(ABILITIES["blue.isolate_host"], state, ctx1)
    assert r1.success is True

    # isolate_host a un cooldown de 10 ticks (§5.4 du blueprint, 30s / tick 3s).
    host.status = "HEALTHY"  # on retire juste l'effet pour isoler le test du cooldown
    ctx2 = ActionContext(actor="blue", target=host, tick=2)
    r2 = ability_engine.resolve(ABILITIES["blue.isolate_host"], state, ctx2)
    assert r2.success is False
    assert r2.reason == "on_cooldown"

    ctx3 = ActionContext(actor="blue", target=host, tick=11)
    r3 = ability_engine.resolve(ABILITIES["blue.isolate_host"], state, ctx3)
    assert r3.success is True


# ---------------------------------------------------------------------------
# Validation de scénario (gap identifié : "KeyError brute, pas de message clair")
# ---------------------------------------------------------------------------

def test_scenario_rejects_unknown_admin_user(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("""
    {
      "scenario_id": "bad",
      "hosts": [{"id": "h1", "hostname": "H1", "ip": "10.0.0.1", "admin_users": ["ghost"]}],
      "users": []
    }
    """)
    with pytest.raises(ScenarioValidationError):
        load_scenario(bad)


def test_scenario_rejects_unknown_ability_id(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("""
    {
      "scenario_id": "bad",
      "hosts": [{"id": "h1", "hostname": "H1", "ip": "10.0.0.1"}],
      "users": [],
      "available_abilities": {"red": ["red.does_not_exist"], "blue": []}
    }
    """)
    with pytest.raises(ScenarioValidationError):
        load_scenario(bad, known_ability_ids=set(ABILITIES))


# ---------------------------------------------------------------------------
# SIEM : détection + triage (ack change vraiment le statut)
# ---------------------------------------------------------------------------

def test_pass_the_hash_rule_fires_and_can_be_acknowledged():
    from engine.models import LogEvent

    state = fresh_state()
    log = LogEvent(event_id="4624", host_id="file-01", tick=1,
                    data={"LogonType": 3, "LogonProcessName": "NtLmSsp", "KeyLength": 0})
    state.logs.append(log)
    alerts = siem.evaluate(state, [log])
    assert len(alerts) == 1
    assert alerts[0].status == "NEW"

    # L'ack passe par la vraie boucle de jeu pour vérifier que le paramètre
    # choisi par le joueur (alert_id) est bien injecté jusqu'à l'effet.
    loop = GameLoop(state, ABILITIES)
    loop.submit(QueuedAction("blue", "blue.acknowledge_alert", "file-01", alert_id=alerts[0].id))
    loop.tick()
    assert state.alerts[0].status == "ACK"


def test_background_noise_never_triggers_a_siem_rule():
    state = fresh_state(seed=7)
    for t in range(1, 30):
        state.tick = t
        new_logs = noise.generate(state)
        assert siem.evaluate(state, new_logs) == []


# ---------------------------------------------------------------------------
# Boucle de jeu + conditions de victoire
# ---------------------------------------------------------------------------

def test_offline_ticket_then_authenticated_access_wins():
    from engine.models import Credential, Service
    state = fresh_state()
    state.hosts['dc-01'].services.append(Service('SMB', 445))
    state.domain = {'name': 'example.lab'}
    state.loot.append(Credential('KRBTGT_HASH', 'krbtgt', 'a'*32, 'dc-01'))
    state.hosts['dc-01'].edr_agent = False
    loop = GameLoop(state, ABILITIES)
    loop.submit(QueuedAction('red', 'red.golden_ticket', 'dc-01', 'krbtgt', 'KRBTGT_HASH'))
    loop.tick()
    assert not state.domain_compromised and state.status == 'RUNNING'
    assert '/home/operator/administrator.ccache' in state.terminal_files
    loop.submit(QueuedAction('red', 'red.psexec_lateral', 'dc-01', 'krbtgt', 'KRBTGT_HASH', params={'kerberos_ticket': '/home/operator/administrator.ccache', 'ticket_user': 'administrator'}))
    loop.tick()
    assert state.domain_compromised and state.winner == 'RED'


def test_isolated_controller_rejects_ticket_authentication():
    from engine.models import Credential, Service
    state = fresh_state()
    state.hosts['dc-01'].services.append(Service('SMB', 445))
    state.domain = {'name': 'example.lab'}
    state.loot.append(Credential('KRBTGT_HASH', 'krbtgt', 'a'*32, 'dc-01'))
    loop = GameLoop(state, ABILITIES)
    loop.submit(QueuedAction('red', 'red.golden_ticket', 'dc-01', 'krbtgt', 'KRBTGT_HASH'))
    loop.tick()
    state.hosts['dc-01'].status = 'ISOLATED'
    loop.submit(QueuedAction('red', 'red.psexec_lateral', 'dc-01', 'krbtgt', 'KRBTGT_HASH', params={'kerberos_ticket': '/home/operator/administrator.ccache', 'ticket_user': 'administrator'}))
    loop.tick()
    assert not state.domain_compromised
    assert not state.history[-1].success
    assert state.history[-1].reason == 'prerequisite failed: target_status_not'


def test_actions_rejected_after_game_ended():
    state = fresh_state()
    state.status = "ENDED"
    loop = GameLoop(state, ABILITIES)
    with pytest.raises(RuntimeError):
        loop.submit(QueuedAction("red", "red.recon_scan", "pc-01"))
