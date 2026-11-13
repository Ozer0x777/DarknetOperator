"""Invites interactives et frontières entre consoles Kali/cmd/PowerShell."""
from pathlib import Path
import pytest
from engine import terminal, console_sessions
from engine.game_loop import GameLoop, load_all_abilities
from engine.scenario_loader import load_scenario
from engine.persistence import state_to_dict, state_from_dict

ABILITIES = load_all_abilities()


def fresh():
    state = load_scenario(Path(__file__).parents[1]/'scenarios/tuto_p0.json')
    return state, GameLoop(state, ABILITIES)


def execute(state, loop, line, console='main'):
    with console_sessions.using(state, console):
        result = terminal.parse(line, state, ABILITIES)
        if result.action:
            result.action.console_id = console
            loop.submit(result.action)
    while loop.pending(): loop.tick()
    return result


def test_interactive_password_success_nested_shells_and_parent_environment():
    state, loop = fresh()
    execute(state,loop,'export MARKER=before','remote')
    execute(state,loop,'cd /tmp','remote')
    result = execute(state,loop,'impacket-psexec m.leroux@10.20.0.21','remote')
    assert result.output == ['Password:']
    context = console_sessions.public_contexts(state)['remote']
    assert context['password_label'] == 'Password:' and context['shell'] == 'bash'
    assert not console_sessions.public_contexts(state)['main']['password_prompt']
    execute(state,loop,'Password123!','remote')
    assert console_sessions.public_contexts(state)['remote']['display_cwd'] == 'C:\\Windows\\system32'
    execute(state,loop,'powershell','remote')
    assert console_sessions.public_contexts(state)['remote']['shell'] == 'powershell'
    execute(state,loop,'exit','remote')
    assert console_sessions.public_contexts(state)['remote']['shell'] == 'cmd'
    execute(state,loop,'exit','remote')
    context = state.terminals['remote']
    assert context['terminal_host'] is None and context['terminal_shell'] == 'bash'
    assert context['terminal_cwd'] == '/tmp' and context['terminal_env']['MARKER'] == 'before'


@pytest.mark.parametrize('password', ['', 'wrong', ' pass/@:word! '])
def test_password_is_literal_and_wrong_impacket_password_exits_prompt(password):
    state, loop = fresh()
    state.users['m.leroux'].password = ' pass/@:word! '
    execute(state,loop,'impacket-psexec m.leroux@10.20.0.21')
    result = execute(state,loop,password)
    assert not state.terminal_auth
    if password == ' pass/@:word! ':
        assert state.terminal_host == 'poste-accueil'
    else:
        assert not result.ok and state.terminal_host is None
    assert not any(password and password in h.message for h in state.history)


@pytest.mark.parametrize('line', ['impacket-psexec m.leroux@10.20.0.99', 'impacket-psexec --invented m.leroux@10.20.0.21'])
def test_unusable_command_does_not_request_a_password(line):
    state,loop = fresh()
    assert not execute(state,loop,line).ok
    assert not state.terminal_auth


def test_interrupt_and_saved_password_prompt():
    state,loop = fresh()
    execute(state,loop,'impacket-psexec m.leroux@10.20.0.21','remote')
    state = state_from_dict(state_to_dict(state))
    assert console_sessions.public_contexts(state)['remote']['password_label'] == 'Password:'
    with console_sessions.using(state,'remote'):
        console_sessions.interrupt(state)
    assert not console_sessions.public_contexts(state)['remote']['password_prompt']
    assert state.terminals['remote']['terminal_host'] is None


def test_forced_disconnect_from_powershell_restores_kali_not_windows_shell():
    state,loop = fresh()
    execute(state,loop,'export MARKER=keep','remote')
    execute(state,loop,'impacket-psexec m.leroux:Password123!@10.20.0.21','remote')
    execute(state,loop,'powershell','remote')
    state.hosts['poste-accueil'].status = 'ISOLATED'
    result = execute(state,loop,'whoami','remote')
    assert not result.ok and result.exit_code == 255
    context = state.terminals['remote']
    assert context['terminal_shell'] == 'bash' and context['terminal_host'] is None
    assert context['terminal_env']['MARKER'] == 'keep'
    assert not context['terminal_return_stack']


def test_ssh_banner_does_not_claim_a_different_cwd():
    state,loop = fresh()
    execute(state,loop,'ssh m.leroux@10.20.0.21')
    context = console_sessions.public_contexts(state)['main']
    assert context['password_label'] == "m.leroux@10.20.0.21's password:"
    result = execute(state,loop,'Password123!')
    assert all('C:\\Data>' not in line for line in result.output)
    assert state.terminal_cwd == '/Users/m.leroux'


def test_terminal_api_keeps_authentication_on_its_console(tmp_path, monkeypatch):
    import asyncio
    import httpx
    from api import main as api
    from engine.career import Career
    monkeypatch.setattr(api, '_CAREER', Career(tmp_path/'career.json'))
    monkeypatch.setattr(api, '_WORKSPACE', None)
    monkeypatch.setattr(api, 'GAMES', {})

    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api.app), base_url='http://test') as client:
            created = await client.post('/api/games', json={'contract':'tuto_p0','handle':'Operator'})
            gid = created.json()['id']
            endpoint = f'/api/games/{gid}/terminal'
            prompt = (await client.post(endpoint, json={'line':'impacket-psexec m.leroux@10.20.0.21','console_id':'remote'})).json()
            assert prompt['password_prompt'] and prompt['context']['password_label'] == 'Password:'
            assert prompt['exit_code'] is None
            other = (await client.post(endpoint, json={'line':'whoami','console_id':'main'})).json()
            assert not other['password_prompt'] and other['output'] == ['operator']
            login = (await client.post(endpoint, json={'line':'Password123!','console_id':'remote'})).json()
            assert login['ok'] and login['queued'] and not login['password_prompt']
            while api.GAMES[gid].loop.pending(): api.GAMES[gid].loop.tick()
            state = (await client.get(f'/api/games/{gid}')).json()
            assert state['terminals']['remote']['shell'] == 'cmd'
            assert state['terminals']['main']['shell'] == 'bash'
            assert not any('Password123!' in entry['message'] for entry in state['history'])
    asyncio.run(run())
