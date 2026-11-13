"""Cursus actuel, compatibilité des sauvegardes et migration transactionnelle."""
import asyncio
import copy
from pathlib import Path
import httpx
import pytest
from api import main as api
from engine import contracts,curriculum,onboarding
from engine.career import Career
from engine.campaign import CHAPTERS
from engine.save_store import SaveStore
from curriculum_validation import qualify,CURRENT_PATHS


@pytest.fixture
def profile(tmp_path,monkeypatch):
    value=Career(tmp_path/'career.json')
    monkeypatch.setattr(api,'_CAREER',value);monkeypatch.setattr(api,'_WORKSPACE',None)
    monkeypatch.setattr(api,'GAMES',{});monkeypatch.setattr(api,'CONNECTIONS',{})
    return value


def test_default_new_game_uses_light_curriculum_and_defers_old_hash_exercises(profile):
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api.app),base_url='http://test') as client:
            result=await client.post('/api/profile/new',json={'handle':'NightShift','confirm':True})
            assert result.status_code==200 and result.json()['campaign_version']==4
            assert len(onboarding.stages(profile.data))==8 and 'intro_hash' not in onboarding.stages(profile.data)
            definitions=api._load_contracts()
            for cid in curriculum.VARIANTS:
                assert definitions[cid]['curriculum_version']==4
                text=definitions[cid]['brief']+' '.join(s['hint'] for s in definitions[cid].get('investigation_steps',[]))
                assert all(word not in text.casefold() for word in ['hashcat -','impacket-','mimikatz','checksec','gdb -','--offset'])
            assert definitions['tuto_p0']['reward']==355 and definitions['tuto_p0']['reputation']==5
            assert profile.lock_reason(definitions['intro_hash']) and profile.lock_reason(definitions['side_empreinte'])
    asyncio.run(run())


def test_two_complete_light_act1_and_act2_paths_without_act1_purchase(tmp_path):
    reports=asyncio.run(qualify(tmp_path))
    assert len(reports)==2
    for report in reports:
        assert report['act1']['chapters']==10 and report['act1']['side_jobs']==7
        assert not report['act1']['first_purchase']
        assert report['act2']['missions']==10 and report['act2']['sides']==6
    forbidden=('hashcat ','impacket-','mimikatz','checksec ','gdb ','ticketd.py')
    assert not any(word in line for ops in CURRENT_PATHS.values() for _,line in ops for word in forbidden)


def test_migration_is_pure_and_preserves_economy_choices_and_history(profile):
    profile.data.update(campaign_version=3,handle='NightShift',money=1234,tier=2,reputation=500,
        inventory=['wordlist','nullvad'],completed=['tuto_p0','act1_partage','act1_empreinte'],choices={'litige118':'mediation'},forum_invitation_accepted=True)
    profile.save();before=copy.deepcopy(profile.data)
    after,changed=curriculum.migrate(before)
    assert changed and before==profile.data and after['campaign_version']==4
    for key in ['money','inventory','completed','choices','reputation','wallet','settled','forum_invitation_accepted']:
        assert after[key]==before[key]
    assert after['legacy_completed']==before['completed']
    again,changed=curriculum.migrate(after)
    assert not changed and again==after
    definitions=curriculum.definitions(after,contracts.load_all_contracts())
    assert definitions['act1_empreinte']['scenario']=='act1_empreinte' # Rejeu historique conservé.
    assert definitions['act1_service']['scenario']=='act1_service_current'


@pytest.mark.parametrize('version',[1,2])
def test_older_high_tier_career_does_not_lose_its_community_access(profile,version):
    profile.data.update(campaign_version=version,tier=3,completed=['tuto_p0','rival','varenne','affiliation'],route='relay')
    before=copy.deepcopy(profile.data)
    after,changed=curriculum.migrate(before)
    assert not changed and after==before


def test_active_hash_training_keeps_queue_contract_and_original_reward(profile):
    async def run():
        profile.data.update(campaign_version=3,handle='NightShift',completed=onboarding.STAGES[:6],money=385,tier=0,reputation=30)
        profile.save()
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api.app),base_url='http://test') as client:
            created=await client.post('/api/games',json={'contract':'intro_hash','handle':'NightShift','rng_seed':0})
            assert created.status_code==200,created.text
            gid=created.json()['id'];session=api.GAMES[gid]
            command=await client.post(f'/api/games/{gid}/terminal',json={'line':'hashcat -m 1000 ~/mission/exercice.ntlm /usr/share/wordlists/rockyou.txt'})
            assert command.status_code==200 and session.loop._queue
            queued=len(session.loop._queue);reward=session.state.contract['reward'];before=profile.data['money']
            enrolled=await client.post('/api/profile/enroll',json={})
            assert enrolled.status_code==200 and enrolled.json()['campaign_version']==4
            assert api.GAMES[gid] is session and len(session.loop._queue)==queued
            assert session.state.contract['legacy_in_progress'] and session.state.contract['reward']==reward
            assert onboarding.next_stage(profile.data)=='intro_hash'
            assert any(s['name']=='Avant adaptation de l’acte I' for s in SaveStore(profile.path).list())
            while session.loop._queue:session.loop.tick()
            assert session.state.contract_outcome=='SUCCESS'
            profile.settle(gid,session.state)
            assert profile.data['money']==before+reward
            assert 'intro_hash' in profile.data['legacy_completed']
            assert onboarding.next_stage(profile.data)=='intro_windows'
            assert api._load_contracts()['tuto_p0']['reward']==300 # Pas de double réaffectation.
    asyncio.run(run())


def test_pinned_active_offer_does_not_double_trust_bonus_or_revoke_wallet(profile):
    async def run():
        profile.data.update(campaign_version=3,handle='NightShift',tier=1,money=1000,reputation=500,
            forum_reputation={'breachboard':500,'exployt':0,'xsx':0},completed=list(dict.fromkeys(onboarding.STAGES+[cid for cid,*_ in CHAPTERS[:-1]])),
            choices={'contretemps':'web_signaler','litige118':'mediation'},trust_offer='act1_recommandation')
        profile.save()
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api.app),base_url='http://test') as client:
            created=await client.post('/api/games',json={'contract':'act1_recommandation','handle':'NightShift'})
            assert created.status_code==200,created.text
            gid=created.json()['id'];reward=api.GAMES[gid].state.contract['reward']
            bought=await client.post('/api/shop/buy',json={'item':'wordlist'})
            assert bought.status_code==200 and not bought.json()['paid']
            nonce=bought.json()['wallet']['pending']['id'];before=profile.data['money']
            assert (await client.post('/api/profile/enroll',json={})).status_code==200
            assert api._load_contracts()['act1_recommandation']['reward']==reward
            assert api._load_contracts()['act1_recommandation']['reward']==reward
            assert profile.wallet_session()['pending']['id']==nonce and profile.data['money']==before
            assert api.GAMES[gid].state.contract['legacy_in_progress']
    asyncio.run(run())


def test_loading_old_slot_migrates_remaining_content_but_keeps_slot_and_active(profile):
    async def run():
        profile.data.update(campaign_version=3,handle='NightShift',tier=1,money=1000,reputation=500,
            completed=list(dict.fromkeys(onboarding.STAGES+[cid for cid,*_ in CHAPTERS[:5]])))
        original=contracts.start_contract(api._load_contracts()['act1_empreinte'],'NightShift')
        original.terminal_files['/home/operator/notes-personnelles.txt']='Mes observations sauvegardées'
        profile.checkpoint(original)
        store=SaveStore(profile.path);slot=store.write(profile.data,'Avant adaptation')
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api.app),base_url='http://test') as client:
            loaded=await client.post('/api/saves/load',json={'slot_id':slot['id'],'confirm':True})
            assert loaded.status_code==200 and loaded.json()['campaign_version']==4
            assert store.read(slot['id'])['profile']['campaign_version']==3
            resumed=await client.post('/api/profile/resume',json={})
            assert resumed.status_code==200,resumed.text
            s=api.GAMES[resumed.json()['id']].state
            assert s.contract['scenario']=='act1_empreinte' and s.contract['legacy_in_progress']
            assert s.terminal_files['/home/operator/notes-personnelles.txt']=='Mes observations sauvegardées'
            assert s.conversation_id==original.conversation_id
    asyncio.run(run())


def test_migration_write_failure_keeps_live_contract_and_profile(profile,monkeypatch):
    async def run():
        profile.data.update(campaign_version=3,handle='NightShift')
        profile.save()
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api.app),base_url='http://test') as client:
            created=await client.post('/api/games',json={'contract':'intro_terminal','handle':'NightShift'})
            assert created.status_code==200
            gid=created.json()['id'];session=api.GAMES[gid]
            monkeypatch.setattr(profile,'save',lambda: (_ for _ in ()).throw(OSError('disk full')))
            response=await client.post('/api/profile/enroll',json={})
            assert response.status_code==503,response.text
            assert profile.data['campaign_version']==3 and not session.state.contract.get('legacy_in_progress')
            assert api.GAMES[gid] is session and session.state.status=='RUNNING'
    asyncio.run(run())
