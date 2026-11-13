"""Revue des débuts : erreurs plausibles, aide progressive et reprise sans perte."""
import asyncio
import copy
import json
from pathlib import Path
import httpx
import pytest
from api import main as api
from api.serializers import serialize_state
from engine import contracts
from engine.career import Career
from engine.persistence import state_to_dict, state_from_dict
from engine.game_loop import GameLoop


def state(cid='intro_terminal'):
    return contracts.start_contract(contracts.load_all_contracts()[cid],'NightShift')


def test_help_progresses_survives_reload_and_accepts_natural_requests():
    s=state()
    contracts.player_message(s,'chordly','un indice')
    assert s.messages[-1].text.startswith('Indice 1/2')
    s=state_from_dict(state_to_dict(s))
    contracts.player_message(s,'chordly','encore un indice')
    assert s.messages[-1].text.startswith('Indice 2/2') and 'cat ~/mission/preparation.txt' in s.messages[-1].text
    contracts.player_message(s,'chordly','aide')
    assert s.messages[-1].text.startswith('Rappel détaillé')
    assert s.contract['brief'] in s.messages[-1].text.replace('NightShift','{handle}')
    assert not s.contract_outcome and not s.history


def test_ravelle_hints_do_not_reveal_future_credentials_and_reset_on_progress():
    s=state('tuto_p0')
    contracts.player_message(s,'chordly','rappel détaillé')
    assert 'Rappel détaillé' in s.messages[-1].text and 'it.presta' not in s.messages[-1].text
    s.discovered.add('srv-fichiers');contracts.advance(s)
    automatic=s.messages[-1].text
    assert len(automatic)<400 and 'GoPhish' in automatic and 'API_KEY' not in automatic
    contracts.player_message(s,'chordly','indice')
    assert s.messages[-1].text.startswith('Indice 1/2')
    assert 'sekurlsa' not in s.messages[-1].text and 'it.presta' not in s.messages[-1].text
    contracts.player_message(s,'chordly','aide complète')
    assert 'API_KEY' in s.messages[-1].text and 'it.presta' not in s.messages[-1].text


def test_explicit_help_works_with_automatic_guidance_disabled():
    s=state('tuto_p0');s.guidance_enabled=False
    s.discovered.add('srv-fichiers');contracts.advance(s)
    assert len(s.messages)==1
    contracts.player_message(s,'chordly','guide complet')
    assert s.messages[-1].text.startswith('Rappel détaillé') and 'API_KEY' in s.messages[-1].text


def test_context_contains_public_goal_but_no_future_guide():
    s=state('tuto_p0')
    summary=serialize_state(s)['contract']
    assert '300' in summary['goal'] and '{reward}' not in summary['goal']
    assert 'hints' not in summary and 'guide' not in summary and 'it.presta' not in summary['goal']


def test_first_lesson_bad_command_help_save_resume_and_reward(tmp_path,monkeypatch):
    profile=Career(tmp_path/'career.json')
    monkeypatch.setattr(api,'_CAREER',profile);monkeypatch.setattr(api,'_WORKSPACE',None)
    monkeypatch.setattr(api,'GAMES',{});monkeypatch.setattr(api,'CONNECTIONS',{})
    async def play():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api.app),base_url='http://test') as client:
            assert (await client.post('/api/profile/new',json={'handle':'NightShift','confirm':True})).status_code==200
            world=(await client.get('/api/social')).json()
            assert sum(m['id']=='journey:welcome' for m in world['messages'])==1
            assert (await client.get('/api/shop')).status_code==403
            created=await client.post('/api/games',json={'contract':'intro_terminal','handle':'NightShift'})
            assert created.status_code==200;gid=created.json()['id']
            wrong=await client.post(f'/api/games/{gid}/terminal',json={'line':'cat ~/mission/preparaton.txt'})
            assert wrong.status_code==200 and not wrong.json()['ok']
            first=await client.post(f'/api/games/{gid}/chat',json={'channel':'chordly','peer':'k0rvid','text':'indice'})
            assert first.json()['messages'][-1]['text'].startswith('Indice 1/2')
            assert profile.data['money']==100
            slot=(await client.post('/api/saves/write',json={'name':'Bloqué au premier dossier'})).json()
            assert (await client.post('/api/saves/load',json={'slot_id':slot['id'],'confirm':True})).status_code==200
            resumed=await client.post('/api/profile/resume',json={})
            assert resumed.status_code==200;gid=resumed.json()['id']
            second=await client.post(f'/api/games/{gid}/chat',json={'channel':'chordly','peer':'k0rvid','text':'encore un indice'})
            assert second.json()['messages'][-1]['text'].startswith('Indice 2/2')
            done=await client.post(f'/api/games/{gid}/terminal',json={'line':'cat ~/mission/preparation.txt'})
            assert done.json()['state']['contract']['outcome']=='SUCCESS'
            view=(await client.get('/api/profile')).json()
            assert view['money']==125 and view['journey']['contract_id']=='intro_recon'
            assert not view['access']['shop']['unlocked']
    asyncio.run(play())


def test_novice_path_recovers_errors_through_the_first_real_contract(tmp_path):
    from first_hour_validation import qualify
    report=asyncio.run(qualify(tmp_path/'report'))
    assert report['dossiers']==9 and report['mistakes']==9 and report['resumes']==9
    assert report['records'][-1]['balance']==740
    assert report['next_step']['contract_id']=='act1_partage'


def test_invalid_guidance_is_rejected_at_load(tmp_path):
    original=Path(__file__).parents[1]/'contracts/intro_terminal.json'
    data=json.loads(original.read_text());data['hints']=['']
    path=tmp_path/'invalid.json';path.write_text(json.dumps(data))
    with pytest.raises(contracts.ContractValidationError,match='indices progressifs'):
        contracts.load_contract(path)
