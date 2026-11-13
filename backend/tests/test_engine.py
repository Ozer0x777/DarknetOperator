"""
Suite de tests du moteur, sur un réseau de test à trois machines : des cas
isolés, chacun devant pouvoir échouer indépendamment des autres.
"""
from __future__ import annotations

from pathlib import Path

import pytest

from engine import ability_engine, noise, siem
from engine.game_loop import GameLoop, QueuedAction, load_all_abilities
from engine.models import ActionContext
from engine.scenario_loader import ScenarioValidationError, load_scenario

ROOT = Path(__file__).parent.parent
SCENARIO_PATH = ROOT / "tests" / "fixtures" / "reseau_ad.json"  # réseau de test, hors des scénarios du jeu
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

def test_pass_the_hash_rule_fires():
    from engine.models import LogEvent

    state = fresh_state()
    log = LogEvent(event_id="4624", host_id="file-01", tick=1,
                    data={"LogonType": 3, "LogonProcessName": "NtLmSsp", "KeyLength": 0})
    state.logs.append(log)
    alerts = siem.evaluate(state, [log])
    assert len(alerts) == 1
    assert alerts[0].status == "NEW"


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
