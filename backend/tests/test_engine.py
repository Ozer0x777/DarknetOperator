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
# Filtrage réseau déclaré par le scénario (`network_rules`)
# ---------------------------------------------------------------------------

def test_network_rule_blocks_psexec():
    from engine.models import Credential

    def attempt(state):
        state.loot.append(Credential(type="NTLM_HASH", username="svc_backup", value="x", source_host="pc-01"))
        ctx = ActionContext(actor="red", target=state.hosts["file-01"], tick=1, credential=state.find_credential("svc_backup"))
        return ability_engine.resolve(ABILITIES["red.psexec_lateral"], state, ctx)

    # Sans règle : psexec réussit, à chaque fois (aucun tirage aléatoire ne s'en mêle).
    assert all(attempt(fresh_state(seed)).success for seed in range(20))

    # Le port 445 de FILE-01 est filtré : la même action échoue sur ce prérequis.
    state = fresh_state()
    state.environment["network_rules"] = [{"target": "file-01", "port": 445, "source": "*", "action": "deny"}]
    assert state.is_blocked("file-01", 445) is True
    result = attempt(state)
    assert result.success is False
    assert result.reason == "prerequisite failed: not_blocked_by_firewall"
    assert state.hosts["file-01"].status == "HEALTHY"


# ---------------------------------------------------------------------------
# Validation de scénario : une incohérence est refusée au chargement, avec un message clair
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
      "objectives": [{"type": "host_compromised", "host": "h1"}],
      "available_abilities": {"red": ["red.does_not_exist"]}
    }
    """)
    with pytest.raises(ScenarioValidationError, match="red.does_not_exist"):
        load_scenario(bad, known_ability_ids=set(ABILITIES))


def _scenario(tmp_path, **changes):
    import json
    data = {"scenario_id": "bad", "hosts": [{"id": "h1", "hostname": "H1", "ip": "10.0.0.1"}], "users": [],
            "objectives": [{"type": "host_compromised", "host": "h1"}], "available_abilities": {"red": []}}
    data.update(changes)
    path = tmp_path / "scenario.json"
    path.write_text(json.dumps({key: value for key, value in data.items() if value is not None}))
    return path


def test_scenario_without_objectives_is_rejected(tmp_path):
    """Sans objectif, la mission ne pourrait finir qu'en échec : le chargeur la refuse."""
    assert load_scenario(_scenario(tmp_path)).objectives
    for objectives in (None, []):
        with pytest.raises(ScenarioValidationError, match="aucun objectif"):
            load_scenario(_scenario(tmp_path, objectives=objectives))


def test_scenario_declares_only_the_player_tools(tmp_path):
    with pytest.raises(ScenarioValidationError, match="blue"):
        load_scenario(_scenario(tmp_path, available_abilities={"red": [], "blue": []}))


def test_shipped_abilities_only_use_known_predicates_and_effects():
    """Les gestes de la défense automatique ne sont pas des effets d'ability."""
    from engine import effects, predicates
    assert "isolate_host" not in effects.REGISTRY and "disable_user" not in effects.REGISTRY
    for ability in ABILITIES.values():
        assert all(effect["type"] in effects.REGISTRY for effect in ability.effects), ability.id
        assert all(req["type"] in predicates.REGISTRY for req in ability.requires), ability.id


# ---------------------------------------------------------------------------
# SIEM : détection
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
    loop.submit(QueuedAction('red.golden_ticket', 'dc-01', 'krbtgt', 'KRBTGT_HASH'))
    loop.tick()
    assert not state.domain_compromised and state.status == 'RUNNING'
    assert '/home/operator/administrator.ccache' in state.terminal_files
    loop.submit(QueuedAction('red.psexec_lateral', 'dc-01', 'krbtgt', 'KRBTGT_HASH', params={'kerberos_ticket': '/home/operator/administrator.ccache', 'ticket_user': 'administrator'}))
    loop.tick()
    assert state.domain_compromised and state.winner == 'RED'


def test_isolated_controller_rejects_ticket_authentication():
    from engine.models import Credential, Service
    state = fresh_state()
    state.hosts['dc-01'].services.append(Service('SMB', 445))
    state.domain = {'name': 'example.lab'}
    state.loot.append(Credential('KRBTGT_HASH', 'krbtgt', 'a'*32, 'dc-01'))
    loop = GameLoop(state, ABILITIES)
    loop.submit(QueuedAction('red.golden_ticket', 'dc-01', 'krbtgt', 'KRBTGT_HASH'))
    loop.tick()
    state.hosts['dc-01'].status = 'ISOLATED'
    loop.submit(QueuedAction('red.psexec_lateral', 'dc-01', 'krbtgt', 'KRBTGT_HASH', params={'kerberos_ticket': '/home/operator/administrator.ccache', 'ticket_user': 'administrator'}))
    loop.tick()
    assert not state.domain_compromised
    assert not state.history[-1].success
    assert state.history[-1].reason == 'prerequisite failed: target_status_not'


def test_actions_rejected_after_game_ended():
    state = fresh_state()
    state.status = "ENDED"
    loop = GameLoop(state, ABILITIES)
    with pytest.raises(RuntimeError):
        loop.submit(QueuedAction("red.recon_scan", "pc-01"))
