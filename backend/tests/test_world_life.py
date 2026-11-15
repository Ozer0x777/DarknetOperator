"""Les événements sociaux restent cohérents dans le temps et après reprise."""
import asyncio
import json
from pathlib import Path
import httpx
import pytest
from engine import social, contracts, terminal, console_sessions, effects, win_conditions
from engine.career import Career
from engine.game_loop import GameLoop, load_all_abilities
from engine.models import ActionContext
from engine.persistence import state_from_dict, state_to_dict
from api.main import app, career, GAMES
from validation import play_campaign

ROOT = Path(__file__).parents[1]
ABILITIES = load_all_abilities()


def test_six_scenarios_through_public_terminal_api_and_eighteen_resumes():
    report = asyncio.run(play_campaign())
    assert len(report['scenarios']) == 6
    assert sum(s['resumes'] for s in report['scenarios']) == 18
    assert all(s['status'] == 'passed' for s in report['scenarios'])
    assert report['tier'] == 3


def test_world_life_is_authored_persistent_and_does_not_repeat(tmp_path):
    profile = Career(tmp_path/'career.json')
    social.advance(profile, 5)
    group = [m for m in profile.data['conversations'].values() if m['peer'] == 'atelier']
    assert len([m for m in group if not m.get('scene_id')]) == 3
    assert sum(m.get('scene_id') == 'atelier-miette' for m in group) == 1
    social.queue_chat(profile, 'chordly', 'miette', 'Operator', 'Salut, tu prends des notes ?')
    message_count = len(profile.data['conversations'])
    assert any(e['target'] == 'miette' for e in profile.data['social']['pending'])
    assert len(profile.data['conversations']) == message_count
    profile.save()
    profile = Career(profile.path)
    social.advance(profile, 2)
    reply = list(profile.data['conversations'].values())[-1]
    assert reply['sender'] == 'miette' and 'Operator' in reply['text']
    assert any(m.get('status') == 'read' for m in profile.data['conversations'].values())
    social.advance(profile, 0)
    assert list(profile.data['conversations'].values())[-1] == reply
    ids = [m['id'] for m in profile.data['conversations'].values()]
    assert len(ids) == len(set(ids))
    assert 'social' not in profile.view()


def test_clock_uses_elapsed_time_instead_of_poll_count(tmp_path):
    profile = Career(tmp_path/'career.json')
    social.refresh(profile, now=100)
    for _ in range(10): social.refresh(profile, now=105)
    assert profile.data['social']['minute'] == 0
    social.refresh(profile, now=112)
    assert profile.data['social']['minute'] == 2
    restored = Career(profile.path)
    social.refresh(restored, now=10000)
    assert restored.data['social']['minute'] == 2  # Pas de saut pendant la fermeture.


def test_forum_reply_arrives_later_and_survives_reload(tmp_path):
    profile = Career(tmp_path/'career.json')
    social.prepare(profile)
    social.queue_forum_reply(profile, 'welcome', 'Operator')
    initial = len(profile.data['forum_posts']['welcome'])
    profile.save()
    profile = Career(profile.path)
    social.advance(profile, 3)
    posts = profile.data['forum_posts']['welcome']
    assert len(posts) == initial + 1
    assert posts[-1]['author'] == 'mod_echo' and posts[-1]['response_to'] == 'Operator'
    social.queue_forum_reply(profile, 'welcome', 'Operator')
    assert not any(e['kind'] == 'forum' for e in profile.data['social']['pending'])


def test_social_views_do_not_reveal_locked_communities(tmp_path):
    profile = Career(tmp_path/'career.json')
    social.advance(profile, 100)
    view = social.view(profile)
    assert all(t['forum'] == 'breachboard' for t in view['threads'])
    assert all(c['channel'] == 'chordly' for c in view['contacts'])
    assert all(m['channel'] == 'chordly' for m in view['messages'])
    profile.data.update(tier=2, route='tor')
    social.advance(profile, 0)
    view = social.view(profile)
    assert any(t['forum'] == 'exployt' for t in view['threads'])
    assert any(m['peer'] == 'veille' for m in view['messages'])
    assert not any(m['channel'] == 'sessyon' for m in view['messages'])


def test_social_api_rejects_locked_threads_and_false_identity():
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
            view = (await client.get('/api/social')).json()
            assert len(view['threads']) >= 8
            assert all('response' not in t for t in view['threads'])
            assert (await client.post('/api/forum/threads/maintenance', json={'handle':'Operator','text':'Bonjour'})).status_code == 409
            career().data['handle'] = 'Operator'
            assert (await client.post('/api/forum/threads/welcome', json={'handle':'mod_echo','text':'Bonjour'})).status_code == 400
            assert (await client.post('/api/social/chat', json={'handle':'Operator','peer':'passations','channel':'sessyon','text':'Salut'})).status_code == 400
            result = await client.post('/api/social/chat', json={'handle':'Operator','peer':'atelier','channel':'chordly','text':'Salut'} )
            assert result.status_code == 200
            assert result.json()['messages'][-1]['sender'] == 'Operator'
            assert (await client.post('/api/social/read', json={'channel':'chordly','peer':'atelier'})).status_code == 200
    asyncio.run(run())


@pytest.mark.parametrize('response', ['ignored', 'reported'])
def test_phishing_can_fail_without_inventing_a_shell_or_credentials(response):
    contract = contracts.load_contract(ROOT/'contracts/tuto_p0.json', known_ability_ids=set(ABILITIES))
    state = contracts.start_contract(contract, 'Operator', known_ability_ids=set(ABILITIES))
    state.hosts['poste-accueil'].phishing['response'] = response
    loop = GameLoop(state, ABILITIES)
    def run(line, console='main'):
        with console_sessions.using(state, console):
            result = terminal.parse(line, state, ABILITIES)
            assert result.ok, result.output
            if result.action: loop.submit(result.action)
    run('gophish --config /opt/gophish/config.json', 'mail')
    run('API_KEY=$(cat ~/gophish/api-key.txt)')
    run('curl -k -H "Authorization: $API_KEY" -d @/home/operator/gophish/campaign.json https://127.0.0.1:3333/api/campaigns/')
    restored = state_from_dict(state_to_dict(state))
    loop = GameLoop(restored, ABILITIES)
    while loop.pending(): loop.tick()
    assert restored.loot == []
    assert restored.hosts['poste-accueil'].status == 'HEALTHY'
    campaign = restored.tool_data['gophish']['campaigns'][0]
    assert campaign['status'] == 'Completed'
    assert campaign['results'][0]['status'] == ('Email Reported' if response == 'reported' else 'Email Opened')
    if response == 'reported': assert any(a.rule_id == 'USER-REPORT' for a in restored.alerts)


def test_isolation_does_not_decrypt_a_host():
    contract = contracts.load_contract(ROOT/'contracts/affiliation.json', known_ability_ids=set(ABILITIES))
    state = contracts.start_contract(contract, 'Operator', known_ability_ids=set(ABILITIES))
    for key in ['poste-accueil','srv-fichiers']:
        ctx = ActionContext('red', state.hosts[key], 1)
        effects.encrypt_host(state, ctx)
        effects.isolate_host(state, ctx)
    assert win_conditions.objective_met(state, state.objectives[0])
    restored = state_from_dict(state_to_dict(state))
    assert win_conditions.objective_met(restored, restored.objectives[0])


def test_help_is_optional_and_available_without_auto_guidance():
    contract = contracts.load_contract(ROOT/'contracts/morel.json', known_ability_ids=set(ABILITIES))
    state = contracts.start_contract(contract, 'Operator', known_ability_ids=set(ABILITIES))
    assert not state.guidance_enabled
    state.discovered.add('srv-fichiers')
    contracts.advance(state)
    assert len(state.messages) == 1
    contracts.player_message(state, 'chordly', 'aide')
    assert 'réseau découvert' in state.messages[-1].text
    assert state_from_dict(state_to_dict(state)).guidance_enabled is False


def test_mission_contact_replies_later_but_help_remains_immediate():
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
            game = (await client.post('/api/games', json={'contract':'tuto_p0','handle':'Operator'})).json()
            gid = game['id']
            before = len(game['state']['messages'])
            answer = (await client.post(f'/api/games/{gid}/chat', json={'channel':'chordly','peer':'k0rvid','text':'Bonjour'})).json()
            assert len(answer['messages']) == before + 1  # Réponse pas encore reçue.
            social.advance(career(), 2)
            archive = (await client.get('/api/messages')).json()
            reply = archive[-1]
            assert reply['sender'] == 'k0rvid' and 'Operator' in reply['text']
            answer = (await client.post(f'/api/games/{gid}/chat', json={'channel':'chordly','text':'aide'})).json()
            assert answer['messages'][-1]['sender'] == 'k0rvid'
            original = next(m for m in career().data['conversations'].values() if m['text'] == 'Bonjour')
            assert original['status'] == 'read'  # Un checkpoint n’annule pas l’accusé de lecture.
    asyncio.run(run())


def test_new_windows_session_does_not_inherit_system_from_another_console(tmp_path):
    contract = contracts.load_contract(ROOT/'contracts/grand_compte.json', known_ability_ids=set(ABILITIES))
    state = contracts.start_contract(contract, 'Operator', known_ability_ids=set(ABILITIES))
    profile = Career(tmp_path/'career.json')
    profile.data.update(tier=3, reputation=350, money=1000, inventory=['vesper','relay'], route='relay')
    profile.prepare(contract, state)
    host = state.hosts['poste-accueil']
    user = host.cached_logons[0]
    with console_sessions.using(state, 'second'):
        assert terminal.parse(f'ssh {user}@{host.ip}', state, ABILITIES).ok
        assert terminal.parse(state.find_credential(user,'PLAINTEXT').value, state, ABILITIES).ok
        assert state.terminal_access == 'USER'
        assert not terminal.parse('mimikatz "privilege::debug" "sekurlsa::logonpasswords" exit', state, ABILITIES).ok
        assert not terminal.parse('vssadmin delete shadows /all /quiet', state, ABILITIES).ok
    with console_sessions.using(state, 'main'):
        assert state.terminal_access == 'SYSTEM'


def test_domain_information_requires_lookup_instead_of_scan_magic():
    contract = contracts.load_contract(ROOT/'contracts/varenne.json', known_ability_ids=set(ABILITIES))
    state = contracts.start_contract(contract, 'Operator', known_ability_ids=set(ABILITIES))
    loop = GameLoop(state, ABILITIES)
    result = terminal.parse('nmap -sV 10.53.12.0/24', state, ABILITIES)
    loop.submit(result.action); loop.tick()
    assert 'VERSION' in state.history[-1].message
    assert state.domain['sid'] not in state.history[-1].message
    assert not terminal.parse('impacket-lookupsid -domain-sids unknown:wrong@10.53.12.10', state, ABILITIES).ok


def test_api_console_waits_for_command_but_campaign_survives_curl_interrupt():
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
            gid = (await client.post('/api/games', json={'contract':'tuto_p0','handle':'Operator'})).json()['id']
            async def command(line='', console='main', interrupt=False):
                return (await client.post(f'/api/games/{gid}/terminal', json={'line':line,'console_id':console,'interrupt':interrupt})).json()
            scan = await command('nmap -sV 10.20.0.0/24')
            assert scan['context']['pending'] == 1
            assert not (await command('pwd'))['ok']
            GAMES[gid].loop.tick()
            assert (await command('pwd'))['ok']
            await command('gophish --config /opt/gophish/config.json', 'mail')
            await command('API_KEY=$(cat ~/gophish/api-key.txt)')
            await command('curl -k -H "Authorization: $API_KEY" -d @/home/operator/gophish/campaign.json https://127.0.0.1:3333/api/campaigns/')
            await command(interrupt=True)
            while GAMES[gid].loop.pending(): GAMES[gid].loop.tick()
            assert GAMES[gid].state.find_credential('m.leroux','PLAINTEXT')
    asyncio.run(run())


def test_resuming_an_old_mission_does_not_replace_its_network_or_accounts():
    async def run():
        from engine.scenario_loader import load_scenario
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url='http://test') as client:
            old_contract = contracts.load_contract(ROOT/'contracts/morel.json', known_ability_ids=set(ABILITIES))
            old_contract['terminal_revision'] = 0
            state = contracts.start_contract(old_contract,'Operator',known_ability_ids=set(ABILITIES))
            state.hosts['poste-accueil'].ip = '10.20.0.21'  # Ancien environnement encore sauvegardé.
            career().checkpoint(state)
            answer = await client.post('/api/profile/resume',json={})
            assert answer.status_code == 200
            restored = GAMES[answer.json()['id']].state
            assert restored.hosts['poste-accueil'].ip == '10.20.0.21'
            assert restored.contract['terminal_revision'] == 5
            assert 'conserve son réseau' in restored.messages[-1].text
    asyncio.run(run())


def test_payout_uses_integer_credits_and_advertised_affiliate_share(tmp_path):
    profile = Career(tmp_path/'career.json')
    loaded = contracts.load_all_contracts(known_ability_ids=set(ABILITIES))
    affiliate = contracts.start_contract(loaded['affiliation'], 'Operator', known_ability_ids=set(ABILITIES))
    affiliate.inventory = ['vesper']
    affiliate.contract_outcome = 'SUCCESS'
    for host in affiliate.hosts.values(): host.backups = False
    profile.settle('affiliation', affiliate)
    assert affiliate.payout == 450  # Part opérateur annoncée : 30 % de 1 500.
    final = contracts.start_contract(loaded['grand_compte'], 'Operator', known_ability_ids=set(ABILITIES))
    final.contract_outcome = 'SUCCESS'
    final.exfiltrated = {'archive': 'fichier fictif'}
    for host in final.hosts.values(): host.backups = False
    profile.settle('final', final)
    assert final.payout == 4025  # 3 500 + 15 %, sans perte d’un crédit par flottant.
