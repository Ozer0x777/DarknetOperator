from pathlib import Path
from engine import completion, console_sessions
from engine.scenario_loader import load_scenario


def test_completion_commands_paths_and_no_execution():
    state = load_scenario(Path(__file__).parents[1] / 'scenarios/tuto_p0.json')
    result = completion.complete(state, 'goph', 4)
    assert result['line'] == 'gophish '
    assert not state.tool_services
    state.terminal_files['/home/operator/report.txt'] = 'example'
    result = completion.complete(state, 'cat rep suffix', 7)
    assert result['line'] == 'cat report.txt  suffix'
    assert completion.complete(state, 'cd /ho', 6)['line'] == 'cd /home/'
    assert '--config' in completion.complete(state, 'gophish --c', 11)['candidates']


def test_completion_isolated_console_and_password():
    state = load_scenario(Path(__file__).parents[1] / 'scenarios/tuto_p0.json')
    state.terminal_files['/tmp/example.txt'] = 'example'
    with console_sessions.using(state, 'second'):
        state.terminal_cwd = '/tmp'
        assert completion.complete(state, 'cat ex', 6)['line'] == 'cat example.txt '
        state.terminal_auth = {'user': 'test'}
        assert completion.complete(state, 'goph', 4)['candidates'] == []
    with console_sessions.using(state, 'main'):
        assert completion.complete(state, 'cat ex', 6)['candidates'] == []


def test_completion_http_endpoint():
    import asyncio
    import httpx
    from api.main import app

    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
            result = await client.post('/api/workspace/terminal/complete', json={'line': 'goph', 'caret': 4, 'console_id': 'second'})
            assert result.status_code == 200
            assert result.json()['line'] == 'gophish '
            assert (await client.post('/api/workspace/terminal/complete', json={'console_id': '../bad'})).status_code == 422
    asyncio.run(run())


def test_windows_completion_uses_cmd_commands_and_windows_paths():
    state = load_scenario(Path(__file__).parents[1] / 'scenarios/morel.json')
    state.terminal_host = 'srv-fichiers'
    state.terminal_cwd = '/srv'
    assert completion.complete(state, 'ipc', 3)['line'] == 'ipconfig '
    line = 'type C:\\Data\\contr'
    assert completion.complete(state, line, len(line))['line'] == 'type C:\\Data\\contrats_2026.xlsx '
    assert completion.complete(state, 'unam', 4)['candidates'] == []
