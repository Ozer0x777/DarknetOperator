"""
Tutoriel palier 0 (docs/03-red-progression.md §9, étape 1 bis) : scénario
tuto_p0, objectifs déclarés, identifiants pilotés par le scénario, pseudos.
"""
from __future__ import annotations

import json
import random
from pathlib import Path

import pytest

from support import command, phish, upload
from engine import ability_engine, terminal, win_conditions
from engine.game_loop import GameLoop, load_all_abilities
from engine.handles import generate_choices, generate_handle
from engine.models import ActionContext
from engine.persistence import state_from_dict, state_to_dict
from engine.scenario_loader import ScenarioValidationError, load_scenario

ROOT = Path(__file__).parent.parent
TUTO_PATH = ROOT / "scenarios" / "tuto_p0.json"
ABILITIES = load_all_abilities()


def tuto_state():
    return load_scenario(TUTO_PATH, known_ability_ids=set(ABILITIES))


def play(line, state, loop, console='main'):
    return command(state, loop, line, console)



# ---------------------------------------------------------------------------
# Scénario
# ---------------------------------------------------------------------------

def test_tutorial_starts_with_a_single_known_host_and_no_defender():
    state = tuto_state()
    assert state.discovered == {"poste-accueil"}
    assert state.scanned == set()
    assert state.available_abilities["blue"] == []
    assert state.objectives == [{"type": "host_compromised", "host": "srv-fichiers"}]


def test_tutorial_guided_path_through_the_terminal_wins():
    """Le chemin que le contact Chordly fera suivre au joueur, étape par étape."""
    state = tuto_state()
    loop = GameLoop(state, ABILITIES)

    play("nmap 10.20.0.0/24", state, loop)
    assert state.discovered == {"poste-accueil", "poste-compta", "srv-fichiers"}

    phish(state, loop)
    assert state.hosts["poste-accueil"].status == "HEALTHY"
    assert state.find_credential("m.leroux", "PLAINTEXT") is not None

    upload(state, loop, state.hosts['poste-accueil'], state.find_credential('m.leroux', 'PLAINTEXT'))
    play("impacket-psexec m.leroux:Password123!@10.20.0.21", state, loop)
    play('mimikatz "privilege::debug" "sekurlsa::logonpasswords" exit', state, loop)
    assert state.find_credential("it.presta", "NTLM_HASH") is not None

    assert state.status == "RUNNING"
    play(f"impacket-psexec -hashes :{state.find_credential('it.presta', 'NTLM_HASH').value} it.presta@10.20.0.10", state, loop, "server")
    assert state.hosts["srv-fichiers"].status == "COMPROMISED"
    assert state.status == "ENDED"
    assert state.winner == "RED"


def test_tutorial_fails_when_time_runs_out():
    state = tuto_state()
    loop = GameLoop(state, ABILITIES)
    for _ in range(state.max_ticks):
        loop.tick()
    assert state.status == "ENDED"
    assert state.winner == "BLUE"


def test_wrong_account_on_the_server_is_refused():
    """m.leroux n'est pas admin du serveur : psexec doit échouer."""
    state = tuto_state()
    loop = GameLoop(state, ABILITIES)
    play("nmap 10.20.0.0/24", state, loop)
    phish(state, loop)
    play("impacket-psexec m.leroux:Password123!@10.20.0.10", state, loop, "server")
    assert state.hosts["srv-fichiers"].status == "HEALTHY"
    assert state.status == "RUNNING"


# ---------------------------------------------------------------------------
# Identifiants pilotés par le scénario
# ---------------------------------------------------------------------------

def test_phishing_needs_a_primary_user():
    """Un serveur n'a pas d'utilisateur attitré : pas de phishing possible."""
    state = tuto_state()
    state.discovered.add("srv-fichiers")
    ctx = ActionContext(actor="red", target=state.hosts["srv-fichiers"], tick=1)
    result = ability_engine.resolve(ABILITIES["red.phishing_initial_access"], state, ctx)
    assert result.success is False
    assert result.reason == "prerequisite failed: target_has_primary_user"


def test_phishing_steals_the_credential_of_the_machine_user():
    state = tuto_state()
    state.discovered.add("poste-compta")
    ctx = ActionContext(actor="red", target=state.hosts["poste-compta"], tick=1)
    assert ability_engine.resolve(ABILITIES["red.phishing_initial_access"], state, ctx).success
    assert [c.username for c in state.loot] == ["s.benali"]


def test_mimikatz_on_a_machine_without_cached_logons_finds_nothing():
    # Test du mécanisme d'extraction, avec un accès SYSTEM fourni par la fixture.
    from engine.models import Credential
    state = tuto_state()
    host = state.hosts['poste-compta']
    host.status, host.compromised_by, host.access_level = 'COMPROMISED', 'red', 'SYSTEM'
    state.discovered.add(host.id)
    state.terminal_host, state.terminal_user, state.terminal_access = host.id, 's.benali', 'SYSTEM'
    credential = Credential('PLAINTEXT', 's.benali', 'fixture', host.id)
    state.loot.append(credential)
    result = ability_engine.resolve(ABILITIES['red.mimikatz_dump'], state, ActionContext('red', host, 1, credential))
    assert result.success
    assert [c.username for c in state.loot] == ['s.benali']


# ---------------------------------------------------------------------------
# Validation et sauvegarde
# ---------------------------------------------------------------------------

def _write(tmp_path, **overrides):
    data = json.loads(TUTO_PATH.read_text())
    data.update(overrides)
    path = tmp_path / "scenario.json"
    path.write_text(json.dumps(data))
    return path


def test_scenario_rejects_unknown_objective_type(tmp_path):
    path = _write(tmp_path, objectives=[{"type": "steal_everything"}])
    with pytest.raises(ScenarioValidationError, match="inconnu"):
        load_scenario(path)


def test_scenario_rejects_objective_on_unknown_host(tmp_path):
    path = _write(tmp_path, objectives=[{"type": "host_compromised", "host": "ghost"}])
    with pytest.raises(ScenarioValidationError, match="ghost"):
        load_scenario(path)


def test_scenario_rejects_unknown_cached_logon(tmp_path):
    data = json.loads(TUTO_PATH.read_text())
    data["hosts"][0]["cached_logons"] = ["fantome"]
    path = tmp_path / "scenario.json"
    path.write_text(json.dumps(data))
    with pytest.raises(ScenarioValidationError, match="fantome"):
        load_scenario(path)


def test_objectives_and_host_users_survive_save_and_reload():
    state = tuto_state()
    restored = state_from_dict(json.loads(json.dumps(state_to_dict(state))))
    assert restored.objectives == state.objectives
    assert restored.hosts["poste-accueil"].primary_user == "m.leroux"
    assert restored.hosts["poste-accueil"].cached_logons == ["it.presta"]


def test_mvp_demo_keeps_the_domain_victory_mode():
    state = load_scenario(ROOT / "scenarios" / "mvp_demo.json", known_ability_ids=set(ABILITIES))
    assert state.objectives == []
    state.domain_compromised = True
    assert win_conditions.check(state) == "RED"


# ---------------------------------------------------------------------------
# Pseudos BreachBoard
# ---------------------------------------------------------------------------

def test_handle_generation_is_deterministic():
    assert generate_handle(random.Random(7)) == generate_handle(random.Random(7))


def test_handle_choices_are_distinct_and_usable():
    choices = generate_choices(random.Random(3), count=5)
    assert len(set(choices)) == 5
    for handle in choices:
        assert 4 <= len(handle) <= 24
        assert handle.replace("_", "").isalnum()


def test_tutorial_refreshes_old_gophish_guide_but_preserves_custom_file():
    from engine import shell_tools
    state = tuto_state()
    filename = '/home/operator/gophish/README.txt'
    state.terminal_files[filename] = 'Laboratoire de jeu : profil API et ressources préconfigurés.\nConsole 2 : ancien guide'
    shell_tools.prepare(state)
    guide = state.terminal_files[filename]
    assert 'Une commande à la fois' in guide
    assert 'aucune sortie' in guide and 'Invalid API key' in guide
    assert 'CONSOLE 1' in guide and 'CONSOLE 2' in guide
    state.terminal_files[filename] = 'Mes notes personnelles'
    shell_tools.prepare(state)
    assert state.terminal_files[filename] == 'Mes notes personnelles'
