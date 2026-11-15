"""Sauvegardes, reprise et règlement : ce qui ne doit jamais faire perdre une carrière."""
import asyncio
import copy
import shutil
from pathlib import Path

import httpx
import pytest

import api.main as api
from engine import contracts
from engine.career import Career
from engine.game_loop import GameLoop, load_all_abilities
from engine.persistence import state_from_dict, state_to_dict

ABILITIES = load_all_abilities()
SAVES = Path(__file__).parent / 'fixtures' / 'saves'


def _client(): return httpx.AsyncClient(transport=httpx.ASGITransport(app=api.app), base_url='http://test')


@pytest.mark.parametrize('revision', sorted(p.name for p in SAVES.iterdir() if p.is_dir()))
def test_save_written_by_an_older_engine_still_resumes(revision, tmp_path):
    """Vraies sauvegardes d'anciens commits : score, joueurs, pare-feu, cooldowns et action en attente à l'ancien format."""
    shutil.copytree(SAVES / revision, tmp_path / 'saves')

    async def run():
        async with _client() as client:
            profile = (await client.get('/api/profile')).json()
            assert profile['has_active'] and not profile['recovery_required'] and profile['handle'] == 'NightShift'
            resumed = await client.post('/api/profile/resume', json={})
            assert resumed.status_code == 200, resumed.text
            session = api.GAMES[resumed.json()['id']]
            assert [a.ability_id for a in session.loop.pending()] == ['red.recon_scan']
            for _ in range(3): session.loop.tick()
            assert session.state.status == 'RUNNING' and not session.loop.pending() and session.state.history[-1].success
            for line in ('pwd', 'hosts', 'help'):
                assert (await client.post(f"/api/games/{resumed.json()['id']}/terminal", json={'line': line})).status_code == 200
            assert (await client.get('/api/social')).status_code == 200
            slots = (await client.get('/api/saves')).json()['slots']
            assert slots and all(slot['valid'] for slot in slots)
            assert (await client.post('/api/saves/load', json={'slot_id': 'auto-0', 'confirm': True})).status_code == 200
            assert (await client.post('/api/profile/resume', json={})).status_code == 200
    asyncio.run(run())
    # La carrière réécrite par la version actuelle se relit telle quelle.
    api._CAREER = None
    assert Career().data['handle'] == 'NightShift'


def test_fields_removed_from_a_model_do_not_break_loading():
    state = contracts.start_contract(contracts.load_all_contracts()['tuto_p0'], 'Operator', known_ability_ids=set(ABILITIES))
    from engine.models import Alert, Credential, HistoryEntry, LogEvent
    state.history.append(HistoryEntry(1, 'red', 'commande résolue', True))
    state.loot.append(Credential('PLAINTEXT', 'm.leroux', 'x', 'poste-accueil'))
    state.logs.append(LogEvent('4624', 'poste-accueil', 1, {}))
    state.alerts.append(Alert(1, 'Alerte', 'LOW', 'R', 'poste-accueil', 1, 1))
    loop = GameLoop(state, ABILITIES)
    loop.tick()
    saved = state_to_dict(state)
    for key in ('loot', 'logs', 'alerts', 'history', 'messages'):
        assert saved[key], key
        for row in saved[key]: row['champ_retire_depuis'] = 'ancienne valeur'
    restored = state_from_dict(saved)
    assert state_to_dict(restored) == state_to_dict(state)


def _won_tutorial():
    contract = contracts.load_all_contracts()['intro_terminal']
    state = contracts.start_contract(contract, 'NightShift', known_ability_ids=set(ABILITIES))
    state.status, state.winner, state.end_reason = 'ENDED', 'RED', 'objectives'
    contracts.advance(state)
    assert state.contract_outcome == 'SUCCESS'
    return contract, state


def test_settlement_is_all_or_nothing(tmp_path, monkeypatch):
    career = Career(tmp_path / 'career.json')
    career.data['handle'] = 'NightShift'
    career.save()
    contract, state = _won_tutorial()
    before = copy.deepcopy(career.data)

    # 1. L'écriture échoue : rien ne reste en mémoire, la mission n'est pas marquée réglée.
    real_save = Career.save
    monkeypatch.setattr(Career, 'save', lambda self: (_ for _ in ()).throw(OSError('disque plein')))
    with pytest.raises(OSError): career.settle('partie-1', state)
    assert career.data == before and state.payout == 0

    # 2. Une étape intermédiaire échoue : pas de mission « réglée » sans prime.
    monkeypatch.setattr(Career, 'save', real_save)
    from engine import journey
    real_record = journey.record
    monkeypatch.setattr(journey, 'record', lambda *args: (_ for _ in ()).throw(RuntimeError('étape défaillante')))
    with pytest.raises(RuntimeError): career.settle('partie-1', state)
    assert career.data == before and 'partie-1' not in career.data['settled']

    # 3. Nouvel essai : le règlement passe, une seule fois.
    monkeypatch.setattr(journey, 'record', real_record)
    career.settle('partie-1', state)
    paid = career.data['money']
    assert 'partie-1' in career.data['settled'] and contract['contract_id'] in career.data['completed'] and paid == before['money'] + contract['reward']
    career.settle('partie-1', state)
    assert career.data['money'] == paid and Career(career.path).data['money'] == paid


def test_failed_settlement_is_retried_by_the_next_player_action(monkeypatch):
    async def run():
        async with _client() as client:
            await client.post('/api/profile/new', json={'handle': 'NightShift', 'confirm': True})
            game = (await client.post('/api/games', json={'contract': 'intro_terminal', 'handle': 'NightShift', 'rng_seed': 0})).json()
            session = api.GAMES[game['id']]
            real_save = Career.save
            monkeypatch.setattr(Career, 'save', lambda self: (_ for _ in ()).throw(OSError('disque plein')))
            refused = await client.post(f"/api/games/{game['id']}/disconnect", json={})
            assert refused.status_code == 503 and session.state.status == 'ENDED'
            assert api._unsettled(session) and game['id'] not in api.career().data['settled']
            monkeypatch.setattr(Career, 'save', real_save)
            # Le disque est revenu : la commande suivante règle la mission restée en suspens.
            assert (await client.post(f"/api/games/{game['id']}/terminal", json={'line': 'pwd'})).status_code == 200
            assert not api._unsettled(session) and game['id'] in api.career().data['settled']
            events = api.career().data.get('career_events', [])
            assert [event['outcome'] for event in events] == ['FAILED']
            assert (await client.post(f"/api/games/{game['id']}/disconnect", json={})).status_code == 200
            assert len(api.career().data.get('career_events', [])) == 1
    asyncio.run(run())


def test_tick_loop_retries_a_refused_settlement(monkeypatch):
    async def run():
        async with _client() as client:
            await client.post('/api/profile/new', json={'handle': 'NightShift', 'confirm': True})
            game = (await client.post('/api/games', json={'contract': 'intro_terminal', 'handle': 'NightShift', 'rng_seed': 0})).json()
            session = api.GAMES[game['id']]
            session.tick_interval = 0.01
            session.loop.has_pending = lambda: True  # le tutoriel n'avance que si une action attend
            session.state.tick = session.state.max_ticks - 1  # le prochain tick termine la mission
            real_save, failures = Career.save, []
            def flaky(self):
                if len(failures) < 2:
                    failures.append(1); raise OSError('fichier verrouillé')
                return real_save(self)
            monkeypatch.setattr(Career, 'save', flaky)
            await client.post(f"/api/games/{game['id']}/start", json={})
            await asyncio.sleep(0.4)
            assert session.state.status == 'ENDED' and len(failures) == 2
            assert not api._unsettled(session) and game['id'] in api.career().data['settled']
    asyncio.run(run())
