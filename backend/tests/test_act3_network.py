"""Frontières réseau : un scan ne crée ni route, ni service, ni droit."""
import json
from pathlib import Path
import pytest
from engine import contracts, terminal, console_sessions
from engine.game_loop import GameLoop, load_all_abilities
from engine.persistence import state_from_dict, state_to_dict
from engine.scenario_loader import load_scenario, ScenarioValidationError
from support import command

ROOT = Path(__file__).parents[1]
ABILITIES = load_all_abilities()


def lab():
    contract = contracts.load_contract(ROOT/'contracts/act2_pivot.json', known_ability_ids=set(ABILITIES))
    state = contracts.start_contract(contract, 'Operator', known_ability_ids=set(ABILITIES))
    state.environment['network_routes'] = {'operator':['10.71.1.0/24'], 'bridge':['10.71.1.0/24','10.72.0.0/24']}
    state.environment['systems']['bridge']['installed_tools'].append('nmap')
    return state, GameLoop(state, ABILITIES)


def test_discovery_filtered_but_service_accessible_and_pn_not_firewall_bypass():
    state, loop = lab()
    state.environment['discovery_rules'] = [{'source':'operator','target':'bridge','action':'deny'}]
    command(state, loop, 'nmap -sV -p 22 10.71.1.10')
    assert 'Host seems down' in state.history[-1].message
    assert 'bridge' not in state.scanned and not state.known_ports.get('bridge')
    command(state, loop, 'nmap -Pn -sV -p 22,80 10.71.1.10')
    assert '22/tcp  open' in state.history[-1].message
    assert '80/tcp  closed' in state.history[-1].message
    assert state.known_ports['bridge'] == [22]
    state.environment['network_rules'].insert(0, {'source':'operator','target':'bridge','port':22,'action':'deny'})
    command(state, loop, 'nmap -Pn -p 22 10.71.1.10')
    assert '22/tcp  filtered' in state.history[-1].message


def test_unknown_literal_and_subnet_scan_require_observable_discovery():
    state, loop = lab()
    state.environment['discovery_rules'] = [{'source':'*','target':'fixed','action':'deny'}]
    command(state, loop, 'nmap -sn 10.71.1.0/24')
    assert 'fixed' not in state.discovered
    assert 'intranet' not in state.discovered
    command(state, loop, 'nmap -Pn -sV -p 22 10.71.1.11')
    assert 'fixed' in state.discovered and '22/tcp  open' in state.history[-1].message


def test_routes_survive_save_and_do_not_leak_between_consoles():
    state, loop = lab()
    command(state, loop, 'nmap -Pn -p 80 10.72.0.20')
    assert '80/tcp  filtered' in state.history[-1].message
    with console_sessions.using(state, 'relay'):
        state.terminal_host = 'bridge'
        state.terminal_user = 'ops'
    command(state, loop, 'nmap -p 80 10.72.0.20', 'relay')
    assert '80/tcp  open' in state.history[-1].message
    state = state_from_dict(state_to_dict(state)); loop = GameLoop(state, ABILITIES)
    command(state, loop, 'nmap -Pn -p 80 10.72.0.20', 'fresh')
    assert '80/tcp  filtered' in state.history[-1].message
    assert state.tool_data['recon']['observations']['intranet']['source'] == 'operator'


def test_tunnel_rechecks_path_when_firewall_changes_after_authentication():
    state, loop = lab()
    command(state, loop, 'ssh -N -L 8080:10.72.0.20:80 ops@10.71.1.10', 'tunnel')
    command(state, loop, 'Relais2026!', 'tunnel')
    assert command(state, loop, 'curl http://127.0.0.1:8080/registre.txt', 'read').ok
    state.environment['network_routes']['operator'] = []
    result = terminal.parse('curl http://127.0.0.1:8080/registre.txt',state,ABILITIES)
    assert not result.ok


@pytest.mark.parametrize('field,value', [
    ('network_routes', {'ghost':['10.0.0.0/24']}),
    ('network_routes', {'operator':['10.0.0.999/24']}),
    ('network_routes', {'operator':'10.0.0.0/24'}),
    ('discovery_rules', [{'source':'operator','target':'bridge','action':'maybe'}]),
])
def test_invalid_network_tables_rejected(tmp_path, field, value):
    data=json.loads((ROOT/'scenarios/act2_pivot.json').read_text())
    data['environment'][field]=value
    path=tmp_path/'invalid.json';path.write_text(json.dumps(data))
    with pytest.raises(ScenarioValidationError):load_scenario(path)
