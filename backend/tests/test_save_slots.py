"""Sauvegardes de carrière : intégrité, restauration, pause et confirmations."""
import asyncio
import json
from pathlib import Path
import httpx
import pytest
from engine.career import Career, initial
from engine.save_store import SaveStore
from api import main as api


def test_slot_integrity_confirmation_and_traversal(tmp_path):
    store = SaveStore(tmp_path/'career.json')
    meta = store.write(initial(),'Départ')
    assert store.read(meta['id'])['profile'] == initial()
    with pytest.raises(ValueError): store.write(initial(),'Oops',meta['id'])
    with pytest.raises(ValueError): store.path('../../career')
    path = store.path(meta['id'])
    data = json.loads(path.read_text()); data['profile']['money'] = 9000
    path.write_text(json.dumps(data))
    with pytest.raises(ValueError,match='endommagée'): store.read(meta['id'])
    assert not store.list()[0]['valid']


def test_autosave_rotation_preserves_manual_slots(tmp_path):
    store = SaveStore(tmp_path/'career.json')
    manual = store.write(initial(),'Manuelle')
    for value in range(5):
        data = initial(); data['money'] = value
        store.autosave(data,force=True)
    rows = store.list()
    assert len(rows) == 4
    assert store.read(manual['id'])['profile']['money'] == 100
    assert sorted(store.read('auto-'+str(i))['profile']['money'] for i in range(3)) == [2,3,4]


def test_corrupt_current_profile_recovers_previous_and_preserves_evidence(tmp_path):
    career = Career(tmp_path/'career.json'); career.save()
    career.data['money'] = 200; career.save()
    career.path.write_text('{broken')
    restored = Career(career.path)
    assert restored.recovered and restored.data['money'] == 100
    assert list(tmp_path.glob('career.corrupt-*.json'))
    assert Career(career.path).data['money'] == 100


def test_api_manual_save_restore_and_new_career(tmp_path,monkeypatch):
    profile = Career(tmp_path/'career.json')
    monkeypatch.setattr(api,'_CAREER',profile)
    monkeypatch.setattr(api,'_WORKSPACE',None)
    monkeypatch.setattr(api,'GAMES',{})
    monkeypatch.setattr(api,'CONNECTIONS',{})
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api.app),base_url='http://test') as client:
            created = (await client.post('/api/games',json={'contract':'tuto_p0','handle':'Operator'})).json()
            gid = created['id']
            await client.post(f'/api/games/{gid}/terminal',json={'line':'impacket-psexec m.leroux@10.20.0.21','console_id':'remote'})
            slot = (await client.post('/api/saves/write',json={'name':'Avant connexion'})).json()
            original = json.loads(json.dumps(profile.data))
            profile.data['money'] = 500
            assert (await client.post('/api/saves/load',json={'slot_id':slot['id']})).status_code == 409
            assert profile.data['money'] == 500
            loaded = await client.post('/api/saves/load',json={'slot_id':slot['id'],'confirm':True})
            assert loaded.status_code == 200 and profile.data == original
            assert not api.GAMES
            resumed = (await client.post('/api/profile/resume',json={})).json()
            assert resumed['state']['terminals']['remote']['password_prompt']
            assert api.GAMES[resumed['id']].paused
            rows = (await client.get('/api/saves')).json()['slots']
            assert any(row['kind']=='recovery' for row in rows)
            assert (await client.post('/api/profile/menu',json={})).status_code == 200
            assert api.GAMES[resumed['id']].paused
            assert (await client.post('/api/profile/new',json={'handle':'NewPlayer'})).status_code == 409
            response = await client.post('/api/profile/new',json={'handle':'NewPlayer','confirm':True})
            assert response.status_code == 200
            assert profile.data['handle'] == 'NewPlayer' and profile.data['active'] is None
            assert profile.data['money'] == 100 and not api.GAMES
            assert (await client.post('/api/saves/delete',json={'slot_id':slot['id']})).status_code == 409
            assert (await client.post('/api/saves/delete',json={'slot_id':slot['id'],'confirm':True})).status_code == 200
    asyncio.run(run())


def test_bad_slot_load_does_not_mutate_current_profile(tmp_path,monkeypatch):
    profile = Career(tmp_path/'career.json'); profile.data['money'] = 333
    store = SaveStore(profile.path); slot = store.write(profile.data,'Cassée')
    store.path(slot['id']).write_text('{}')
    monkeypatch.setattr(api,'_CAREER',profile)
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api.app),base_url='http://test') as client:
            response = await client.post('/api/saves/load',json={'slot_id':slot['id'],'confirm':True})
            assert response.status_code == 400 and profile.data['money'] == 333
    asyncio.run(run())


def test_two_damaged_profile_files_allow_explicit_slot_recovery(tmp_path):
    path = tmp_path/'career.json'
    slot = SaveStore(path).write(initial(),'Copie valide')
    path.write_text('broken-primary')
    path.with_suffix('.previous').write_text('broken-previous')
    career = Career(path)
    assert career.needs_recovery and career.view()['recovery_required']
    assert path.read_text() == 'broken-primary'
    with pytest.raises(ValueError): career.save()
    assert SaveStore(path).read(slot['id'])['profile']['money'] == 100


def test_missing_primary_recovers_previous(tmp_path):
    path = tmp_path/'career.json'
    path.with_suffix('.previous').write_text(json.dumps(initial()))
    career = Career(path)
    assert career.recovered and path.exists()


def test_workspace_consoles_are_restored_after_slot_load(tmp_path,monkeypatch):
    profile = Career(tmp_path/'career.json'); profile.data['handle'] = 'Operator'
    monkeypatch.setattr(api,'_CAREER',profile)
    monkeypatch.setattr(api,'_WORKSPACE',None)
    monkeypatch.setattr(api,'GAMES',{})
    monkeypatch.setattr(api,'CONNECTIONS',{})
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api.app),base_url='http://test') as client:
            await client.post('/api/workspace/terminal',json={'line':'export NOTE=conserve','console_id':'term-3'})
            saved = (await client.post('/api/saves/write',json={'name':'Bureau'})).json()
            await client.post('/api/workspace/terminal',json={'line':'export NOTE=remplace','console_id':'term-3'})
            await client.post('/api/saves/load',json={'slot_id':saved['id'],'confirm':True})
            state = (await client.get('/api/workspace/state')).json()
            assert 'term-3' in state['terminals']
            output = (await client.post('/api/workspace/terminal',json={'line':'echo $NOTE','console_id':'term-3'})).json()
            assert output['output'] == ['conserve']
    asyncio.run(run())
