"""Plusieurs sessions, GoPhish authentique côté syntaxe, API curl et événements ciblés."""
import asyncio
import json
import httpx
from api.main import app, GAMES, career
from engine import console_sessions, terminal
from engine.game_loop import GameLoop, load_all_abilities
from engine.scenario_loader import load_scenario
from engine.persistence import state_from_dict, state_to_dict
from pathlib import Path

ABILITIES=load_all_abilities()


def test_consoles_have_independent_directories_and_survive_save():
    state=load_scenario(Path(__file__).parents[1]/'scenarios/tuto_p0.json')
    with console_sessions.using(state,'term-2'):
        assert terminal.parse('cd /tmp',state,ABILITIES).ok
        terminal.parse('KEY=console2',state,ABILITIES)
        terminal.parse('echo shared > /tmp/shared.txt',state,ABILITIES)
    with console_sessions.using(state,'main'):
        assert terminal.parse('pwd',state,ABILITIES).output==['/home/operator']
        assert 'KEY' not in state.terminal_env
        assert terminal.parse('cat /tmp/shared.txt',state,ABILITIES).output==['shared\n']
    restored=state_from_dict(state_to_dict(state))
    with console_sessions.using(restored,'term-2'):
        assert terminal.parse('pwd',restored,ABILITIES).output==['/tmp']
        assert restored.terminal_env['KEY']=='console2'


def test_cli_gophish_campaign_across_two_consoles():
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
            async def workspace(line,cid='main'):
                return (await client.post('/api/workspace/terminal',json={'line':line,'console_id':cid})).json()
            assert '/opt/gophish/gophish' in (await workspace('which gophish'))['output']
            assert 'gophish' in (await workspace('ls /usr/bin'))['output']
            assert (await workspace('gophish --config /opt/gophish/config.json'))['context']['foreground']
            # Le service et les consoles persistent lors de l'acceptation du contrat.
            game=(await client.post('/api/games',json={'contract':'tuto_p0','handle':'Operator'})).json()
            gid=game['id'];state=GAMES[gid].state
            async def command(line,cid='main',interrupt=False):
                return (await client.post(f'/api/games/{gid}/terminal',json={'line':line,'console_id':cid,'interrupt':interrupt})).json()
            assert not (await command('pwd'))['ok']  # Serveur au premier plan.
            assert (await command('API_KEY=$(cat ~/gophish/api-key.txt)','term-2'))['ok']
            url='https://127.0.0.1:3333/api/'
            response=await command(f'curl -k -H "Authorization: $API_KEY" {url}groups/','term-2')
            assert json.loads(response['output'][0])[0]['name']=='Briefing'
            response=await command(f'curl -k -H "Authorization: $API_KEY" -H "Content-Type: application/json" -d @/home/operator/gophish/campaign.json {url}campaigns/','term-2')
            assert response['queued'],response
            while GAMES[gid].loop.pending(): GAMES[gid].loop.tick()
            assert state.find_credential('m.leroux','PLAINTEXT')
            assert state.history[-1].console_id=='term-2'
            assert state.terminals['main']['terminal_foreground'] is not None
            result=await command(f'curl -k -H "Authorization: $API_KEY" {url}campaigns/1/results','term-2')
            assert json.loads(result['output'][0])['results'][0]['status']=='Submitted Data'
            assert (await command('','term-2',True))['ok']
            assert state.tool_services['gophish']['running']  # Ctrl+C dans une autre console n'arrête pas le serveur.
            assert (await command('','main',True))['ok']
            assert not state.tool_services['gophish']['running']
            assert (await command('pwd'))['output']==['/home/operator']
    asyncio.run(run())


def test_password_prompt_does_not_capture_another_console():
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
            game=(await client.post('/api/games',json={'contract':'tuto_p0','handle':'Operator'})).json();gid=game['id']
            async def command(line,cid):return (await client.post(f'/api/games/{gid}/terminal',json={'line':line,'console_id':cid})).json()
            assert (await command('ssh m.leroux@10.20.0.21','main'))['password_prompt']
            result=await command('whoami','term-2')
            assert result['output']==['operator'] and not result['password_prompt']
            assert GAMES[gid].state.terminals['main']['terminal_auth']
    asyncio.run(run())


def test_failed_api_authentication_and_invalid_campaign_never_queue():
    state=load_scenario(Path(__file__).parents[1]/'scenarios/tuto_p0.json')
    with console_sessions.using(state,'main'):
        terminal.parse('gophish &',state,ABILITIES)
        result=terminal.parse('curl -k https://127.0.0.1:3333/api/campaigns/',state,ABILITIES)
        assert json.loads(result.output[0])['success'] is False
        assert result.action is None
        failed=terminal.parse('curl -kf https://127.0.0.1:3333/api/campaigns/',state,ABILITIES)
        assert not failed.ok and '(22)' in failed.output[0]
        assert terminal.parse('curl -k https://example.com/api/campaigns/',state,ABILITIES).action is None


def test_gophish_graphical_interface_uses_the_same_campaign_api():
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
            game=(await client.post('/api/games',json={'contract':'tuto_p0','handle':'Operator'})).json();gid=game['id']
            base=f'/api/games/{gid}'
            assert not (await client.get(base+'/gophish/status')).json()['running']
            await client.post(base+'/terminal',json={'line':'gophish --config /opt/gophish/config.json','console_id':'main'})
            assert (await client.get(base+'/gophish/status')).json()['running']
            auth={'username':'admin','password':'wrong'}
            assert (await client.post(base+'/gophish',json=auth)).status_code==401
            auth['password']='lab-admin-password'
            snapshot=(await client.post(base+'/gophish',json=auth)).json()
            assert snapshot['resources']['groups'][0]['name']=='Briefing'
            payload=json.loads(GAMES[gid].state.terminal_files['/home/operator/gophish/campaign.json'])
            response=await client.post(base+'/gophish',json={**auth,'method':'POST','endpoint':'campaigns','payload':payload})
            assert response.status_code==200,response.text
            while GAMES[gid].loop.pending(): GAMES[gid].loop.tick()
            snapshot=(await client.post(base+'/gophish',json=auth)).json()
            assert snapshot['resources']['campaigns'][0]['results'][0]['status']=='Submitted Data'
            response=(await client.post(base+'/terminal',json={'line':'xdg-open https://127.0.0.1:3333','console_id':'term-2'})).json()
            assert response['open_url']=='https://127.0.0.1:3333'
    asyncio.run(run())


def test_closing_a_console_cancels_only_its_pending_actions():
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
            game=(await client.post('/api/games',json={'contract':'tuto_p0','handle':'Operator'})).json();gid=game['id']
            for cid in ['main','term-2']:
                await client.post(f'/api/games/{gid}/terminal',json={'line':'nmap 10.20.0.21','console_id':cid})
            await client.delete(f'/api/games/{gid}/terminals/main')
            loop=GAMES[gid].loop
            assert len(loop.pending())==1 and loop.pending()[0].console_id=='term-2'
            loop.tick()
            assert loop.state.history[-1].console_id=='term-2'
    asyncio.run(run())


def test_saved_history_keeps_its_console_identity():
    state=load_scenario(Path(__file__).parents[1]/'scenarios/tuto_p0.json')
    loop=GameLoop(state,ABILITIES)
    with console_sessions.using(state,'term-9'):
        parsed=terminal.parse('nmap 10.20.0.21',state,ABILITIES)
        loop.submit(parsed.action)
    loop.tick()
    restored=state_from_dict(state_to_dict(state))
    assert restored.history[-1].console_id=='term-9'


def test_purchased_relay_access_can_be_used_from_a_new_console(tmp_path):
    from engine import contracts
    from engine.career import Career
    profile=Career(tmp_path/'career.json')
    profile.data.update(tier=3,reputation=350,money=1000,inventory=['vesper','relay'],route='relay')
    contract=contracts.load_contract(Path(__file__).parents[1]/'contracts/grand_compte.json',known_ability_ids=set(ABILITIES))
    state=contracts.start_contract(contract,'Operator',known_ability_ids=set(ABILITIES))
    profile.prepare(contract,state)
    with console_sessions.using(state,'term-3'):
        result=terminal.parse(f"ssh {state.hosts['poste-accueil'].cached_logons[0]}@{state.hosts['poste-accueil'].ip}",state,ABILITIES)
        assert result.ok and state.terminal_auth
        assert terminal.parse(state.find_credential(state.hosts['poste-accueil'].cached_logons[0],'PLAINTEXT').value,state,ABILITIES).ok
        assert state.terminal_host=='poste-accueil'
