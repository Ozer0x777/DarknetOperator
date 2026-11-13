"""
Brouillard de guerre + terminal Red (docs/03-red-progression.md §8, étape 1).
"""
from __future__ import annotations

from pathlib import Path

import pytest

from engine import ability_engine, terminal
from support import command, phish
from engine.game_loop import GameLoop, load_all_abilities
from engine.models import ActionContext
from engine.persistence import state_from_dict, state_to_dict
from engine.scenario_loader import ScenarioValidationError, load_scenario

ROOT = Path(__file__).parent.parent
SCENARIO_PATH = ROOT / "scenarios" / "mvp_demo.json"
ABILITIES = load_all_abilities()


def fogged_state(seed: int = 1):
    """mvp_demo, mais Red ne connaît que PC-01 (et n'en connaît pas les services)."""
    state = load_scenario(SCENARIO_PATH, rng_seed=seed, known_ability_ids=set(ABILITIES))
    state.discovered = {"pc-01"}
    state.scanned = set()
    return state


def run(line, state, loop=None):
    result = terminal.parse(line, state, ABILITIES)
    if result.action and loop:
        loop.submit(result.action)
    return result


# ---------------------------------------------------------------------------
# Brouillard de guerre (moteur)
# ---------------------------------------------------------------------------

def test_mvp_demo_without_fog_field_knows_everything():
    state = load_scenario(SCENARIO_PATH, known_ability_ids=set(ABILITIES))
    assert state.discovered == set(state.hosts)
    assert state.scanned == set(state.hosts)


def test_red_cannot_target_undiscovered_host():
    state = fogged_state()
    ctx = ActionContext(actor="red", target=state.hosts["file-01"], tick=1)
    result = ability_engine.resolve(ABILITIES["red.recon_scan"], state, ctx)
    assert result.success is False
    assert result.reason == "prerequisite failed: target_discovered"


def test_recon_reveals_the_whole_subnet_and_its_services():
    state = fogged_state()
    ctx = ActionContext(actor="red", target=state.hosts["pc-01"], tick=1)
    assert ability_engine.resolve(ABILITIES["red.recon_scan"], state, ctx).success is True
    assert state.discovered == {"pc-01", "file-01", "dc-01"}
    assert state.scanned == {"pc-01", "file-01", "dc-01"}


def test_recon_does_not_reveal_other_subnets():
    state = fogged_state()
    state.hosts["dc-01"].ip = "10.0.0.10"
    ctx = ActionContext(actor="red", target=state.hosts["pc-01"], tick=1)
    ability_engine.resolve(ABILITIES["red.recon_scan"], state, ctx)
    assert "dc-01" not in state.discovered


def test_scenario_rejects_unknown_host_in_initially_discovered(tmp_path):
    bad = tmp_path / "bad.json"
    bad.write_text("""
    {"scenario_id": "bad", "hosts": [{"id": "h1", "hostname": "H1", "ip": "10.0.0.1"}],
     "users": [], "initially_discovered": ["ghost"]}
    """)
    with pytest.raises(ScenarioValidationError):
        load_scenario(bad)


def test_fog_survives_save_and_reload():
    state = fogged_state()
    restored = state_from_dict(state_to_dict(state))
    assert restored.discovered == {"pc-01"}
    assert restored.scanned == set()


# ---------------------------------------------------------------------------
# Terminal
# ---------------------------------------------------------------------------

def test_terminal_builds_action_from_ip_or_hostname():
    state = fogged_state()
    for ref in ("192.168.1.101", "PC-01", "pc-01"):
        result = run(f"nmap {ref}", state)
        assert result.ok, result.output
        assert result.action.ability_id == "red.recon_scan"
        assert result.action.target_id == "pc-01"


def test_terminal_hides_undiscovered_hosts_like_missing_ones():
    state = fogged_state()
    hidden = run("nmap 192.168.1.20", state)        # FILE-01 existe mais n'est pas découvert
    missing = run("nmap 192.168.1.250", state)      # n'existe pas
    assert not hidden.ok and not missing.ok
    assert hidden.output[0].replace("192.168.1.20", "X") == missing.output[0].replace("192.168.1.250", "X")


def test_terminal_checks_transport_before_authentication():
    from engine.models import Service
    state = fogged_state()
    # Le poste expose SMB dans le scénario : on le retire pour vérifier d'abord l'absence de transport.
    state.hosts['pc-01'].services = [service for service in state.hosts['pc-01'].services if service.port != 445]
    result = run("impacket-psexec jdoe:wrong@192.168.1.101", state)
    assert not result.ok and "STATUS_CONNECTION_DISCONNECTED" in result.output[0]
    assert not state.terminal_auth
    state.hosts['pc-01'].services.append(Service('SMB', 445))
    result = run("impacket-psexec jdoe:wrong@192.168.1.101", state)
    assert not result.ok and "authentication failed" in result.output[0]


def test_terminal_reports_usage_on_wrong_syntax():
    state = fogged_state()
    assert not run("psexec pc-01", state).ok
    assert not run("impacket-psexec pc-01 --with jdoe", state).ok


def test_terminal_unknown_command():
    state = fogged_state()
    result = run("outil_inexistant", state)
    assert not result.ok
    assert "commande inconnue" in result.output[0]


def test_help_lists_only_scenario_tools_and_details_one():
    state = fogged_state()
    state.available_abilities["red"] = ["red.recon_scan"]
    listing = "\n".join(run("help", state).output)
    assert "nmap [-sV]" in listing
    assert "psexec" not in listing
    detail = run("help nmap", state)
    assert detail.ok and detail.output[0] == "usage : nmap {target}"


def test_hosts_shows_only_known_machines_and_scan_state():
    state = fogged_state()
    out = "\n".join(run("hosts", state).output)
    assert "PC-01" in out and "non scanné" in out
    assert "FILE-01" not in out and "DC-01" not in out


def test_full_chain_through_the_terminal():
    """Un joueur qui ne connaît que PC-01 au départ arrive jusqu'à FILE-01
    uniquement avec des commandes tapées au terminal."""
    state = fogged_state()
    loop = GameLoop(state, ABILITIES)

    phish(state, loop)
    assert state.hosts["pc-01"].status == "HEALTHY"

    assert run("nmap 192.168.1.0/24", state, loop).ok
    loop.tick()
    assert "file-01" in state.discovered

    # Fixture de mécanismes : simule une session SYSTEM déjà établie.
    state.hosts["pc-01"].status = "COMPROMISED"
    state.hosts["pc-01"].compromised_by = "red"
    state.hosts["pc-01"].access_level = "SYSTEM"
    from engine.deployment import TOOL_MARKERS
    state.hosts['pc-01'].files['/Tools/mimikatz.exe'] = TOOL_MARKERS['mimikatz']
    state.terminal_host, state.terminal_user, state.terminal_access = 'pc-01', 'jdoe', 'SYSTEM'
    state.terminals['main'].update(terminal_host='pc-01', terminal_user='jdoe', terminal_access='SYSTEM')
    assert run('mimikatz "privilege::debug" "sekurlsa::logonpasswords" exit', state, loop).ok
    loop.tick()
    assert state.find_credential("svc_backup") is not None

    # L'EDR de FILE-01 peut bloquer psexec (10 %) : on retente après la recharge.
    for _ in range(10):
        if state.hosts["file-01"].status == "COMPROMISED":
            break
        if command(state, loop, f"impacket-psexec -hashes :{state.find_credential('svc_backup', 'NTLM_HASH').value} svc_backup@192.168.1.20", "kali").ok:
            for _ in range(5):
                loop.tick()
    assert state.hosts["file-01"].status == "COMPROMISED"
    assert "[compromis]" in "\n".join(run("hosts", state).output)
