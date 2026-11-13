"""Corrections de revue du moteur utilisé par le jeu Godot."""
import api.main as api
from engine import contracts
from engine.game_loop import GameLoop, load_all_abilities
from engine.models import Credential
from engine.win_conditions import condition_error, objective_met
from support import command, phish

ABILITIES = load_all_abilities()


def tutorial():
    state = contracts.start_contract(contracts.load_all_contracts()['tuto_p0'], 'Operator', known_ability_ids=set(ABILITIES))
    return state, GameLoop(state, ABILITIES)


def test_malformed_objectives_are_rejected_at_load_time():
    assert 'file' in condition_error({'type': 'file_exfiltrated', 'host': 'h'}, {'h'}, set())
    assert 'typo' in condition_error({'type': 'http_read', 'host': 'h', 'path': '/', 'typo': 1}, {'h'}, set())
    assert condition_error({'type': 'file_exfiltrated', 'host': 'h', 'file': '/a'}, {'h'}, set()) is None


def test_hash_recovered_is_false_for_an_account_without_password():
    state, _ = tutorial()
    state.users['m.leroux'].password = None
    assert objective_met(state, {'type': 'hash_recovered', 'username': 'm.leroux'}) is False
    assert objective_met(state, {'type': 'hash_recovered', 'username': 'absent'}) is False


def test_observation_check_reports_timeout_when_time_runs_out():
    state = contracts.start_contract(contracts.load_all_contracts()['intro_terminal'], 'Operator')
    state.tick = state.max_ticks
    api._resolve_observations(state)
    assert state.status == 'ENDED' and state.winner == 'BLUE' and state.end_reason == 'timeout'


def test_idle_ticks_do_not_rewrite_the_save():
    state, loop = tutorial()
    session = api.GameSession(id='g', loop=loop)
    writes = []
    original = api.Career.checkpoint
    api.Career.checkpoint = lambda self, s: writes.append(s.tick)
    try:
        api._checkpoint_if_changed(session)
        for _ in range(5):
            state.tick += 1
            api._checkpoint_if_changed(session)
        assert len(writes) == 1
        state.messages.append(state.messages[0])
        api._checkpoint_if_changed(session)
        assert len(writes) == 2
        session.saved_at -= api.CHECKPOINT_IDLE_SECONDS
        api._checkpoint_if_changed(session)
        assert len(writes) == 3
    finally:
        api.Career.checkpoint = original


def test_pass_the_hash_logon_is_flagged_but_password_logon_is_not():
    state, loop = tutorial()
    phish(state, loop)
    command(state, loop, 'impacket-psexec m.leroux:Password123!@10.20.0.21')
    assert next(l for l in state.logs if l.event_id == '4624').data['KeyLength'] == 128
    command(state, loop, 'exit')
    state.discovered.add('srv-fichiers')
    state.loot.append(Credential('NTLM_HASH', 'it.presta', 'ca61eb63ab385fa4039002a79909c534', 'poste-accueil'))
    command(state, loop, 'impacket-psexec -hashes :ca61eb63ab385fa4039002a79909c534 it.presta@10.20.0.10')
    hashed = [l for l in state.logs if l.event_id == '4624' and l.host_id == 'srv-fichiers']
    assert hashed and hashed[-1].data['KeyLength'] == 0
    from engine import siem
    assert siem._match_pass_the_hash(hashed[-1])


# --- Seconde revue : forum, autosauvegardes, nouvelle partie, données entre missions ---
import asyncio
import glob
import os
import stat
import time
import httpx


def _client():
    return httpx.AsyncClient(transport=httpx.ASGITransport(app=api.app, raise_app_exceptions=False), base_url='http://test')


async def _play(client, contract_id, lines):
    game = (await client.post('/api/games', json={'contract': contract_id, 'handle': 'NightShift', 'rng_seed': 0})).json()
    session = api.GAMES[game['id']]
    for line in lines:
        await client.post(f"/api/games/{game['id']}/terminal", json={'line': line, 'console_id': 'main'})
        while session.loop._queue: session.loop.tick()
    if session.state.status == 'ENDED': api.career().settle(game['id'], session.state)
    return session.state


def test_automatic_thread_refresh_neither_counts_a_view_nor_rewrites_the_save(monkeypatch):
    async def run():
        async with _client() as client:
            await client.post('/api/profile/new', json={'handle': 'NightShift', 'confirm': True})
            monkeypatch.setattr(api, '_check_thread', lambda thread_id: None)
            assert (await client.get('/api/forum/threads/welcome')).status_code == 200
            assert api.career().data['thread_views']['welcome'] == 1
            written = os.stat(api.career().path).st_mtime_ns
            for _ in range(5):
                assert (await client.get('/api/forum/threads/welcome', params={'refresh': 'true'})).status_code == 200
            assert api.career().data['thread_views']['welcome'] == 1
            assert os.stat(api.career().path).st_mtime_ns == written
    asyncio.run(run())


def test_autosave_slots_never_hold_the_same_state_twice():
    async def run():
        async with _client() as client:
            await client.post('/api/profile/new', json={'handle': 'NightShift', 'confirm': True})
            game = (await client.post('/api/games', json={'contract': 'intro_terminal', 'handle': 'NightShift', 'rng_seed': 0})).json()
            from engine.save_store import SaveStore
            folder = api.career().path.parent / 'slots'
            for index in range(3):
                # Trois états anciens et différents : une commande entre chaque écriture.
                await client.post(f"/api/games/{game['id']}/terminal", json={'line': f'echo etape-{index}', 'console_id': 'main'})
                SaveStore(api.career().path).write(api.career().data, 'Autosauvegarde', f'auto-{index}', True, 'auto')
                old = time.time() - 600 - index * 100
                os.utime(folder / f'auto-{index}.json', (old, old))
            stamps = lambda: {name: os.stat(name).st_mtime for name in glob.glob(str(folder / 'auto-*.json'))}
            before = stamps()
            await client.post(f"/api/games/{game['id']}/terminal", json={'line': 'pwd', 'console_id': 'main'})
            # La commande, le retour au menu puis « Quitter » : un seul emplacement doit changer en tout.
            for _ in range(3): assert (await client.post('/api/profile/menu', json={})).status_code == 200
            after = stamps()
            assert sum(after[name] != before[name] for name in before) == 1
            checksums = [SaveStore(api.career().path).read(f'auto-{index}')['checksum'] for index in range(3)]
            assert len(set(checksums)) == 3
    asyncio.run(run())


def test_failed_autosave_does_not_break_the_checkpoint():
    async def run():
        async with _client() as client:
            await client.post('/api/profile/new', json={'handle': 'NightShift', 'confirm': True})
            game = (await client.post('/api/games', json={'contract': 'intro_terminal', 'handle': 'NightShift', 'rng_seed': 0})).json()
            folder = api.career().path.parent / 'slots'
            folder.mkdir(parents=True, exist_ok=True)
            for name in glob.glob(str(folder / 'auto-*.json')): os.remove(name)
            os.chmod(folder, stat.S_IRUSR | stat.S_IXUSR)
            try:
                response = await client.post(f"/api/games/{game['id']}/terminal", json={'line': 'pwd', 'console_id': 'main'})
            finally:
                os.chmod(folder, stat.S_IRWXU)
            assert response.status_code == 200 and response.json()['output'] == ['/home/operator']
            assert 'pwd' in ''.join(api.career().data['active']['tool_data']['terminal_transcripts']['main'])
    asyncio.run(run())


def test_new_career_archives_player_content_and_reports_write_failure():
    async def run():
        async with _client() as client:
            await client.post('/api/profile/new', json={'handle': 'NightShift', 'confirm': True})
            folder = api.career().path.parent / 'slots'
            manual = lambda: len(glob.glob(str(folder / 'manual-*.json')))
            for _ in range(3): await client.post('/api/profile/new', json={'handle': 'NightShift', 'confirm': True})
            assert manual() == 0  # aucune archive d'une carrière vierge
            # Un fichier créé dans le bureau, sans aucun contrat, est déjà du contenu à archiver.
            await client.post('/api/workspace/terminal', json={'line': 'echo notes-importantes > /home/operator/notes.txt', 'console_id': 'main'})
            assert (await client.post('/api/profile/new', json={'handle': 'NightShift', 'confirm': True})).status_code == 200
            assert manual() == 1
            await _play(client, 'intro_terminal', ['pwd', 'ls ~/mission', 'cat ~/mission/preparation.txt'])
            assert api.career().data['completed'] == ['intro_terminal']
            os.chmod(folder, stat.S_IRUSR | stat.S_IXUSR)
            try:
                refused = await client.post('/api/profile/new', json={'handle': 'NightShift', 'confirm': True})
            finally:
                os.chmod(folder, stat.S_IRWXU)
            assert refused.status_code == 503 and 'archiver' in refused.json()['detail']
            assert api.career().data['completed'] == ['intro_terminal']  # carrière courante intacte
            assert (await client.post('/api/profile/new', json={'handle': 'NightShift', 'confirm': True})).status_code == 200
            assert manual() == 2 and api.career().data['completed'] == []
    asyncio.run(run())


def test_invalid_career_can_still_start_a_new_game_without_being_destroyed():
    async def run():
        async with _client() as client:
            await client.post('/api/profile/new', json={'handle': 'NightShift', 'confirm': True})
            await _play(client, 'intro_terminal', ['pwd'])
            api.career().data['active'] = {'status': 'RUNNING', 'hosts': 'cassé'}  # mission sauvegardée invalide
            api.GAMES.clear()
            response = await client.post('/api/profile/new', json={'handle': 'NightShift', 'confirm': True})
            assert response.status_code == 200 and api.career().data.get('active') is None
            assert glob.glob(str(api.career().path.parent / 'career.invalid-*.json'))
    asyncio.run(run())


def test_new_contract_does_not_inherit_evidence_or_defender_state():
    async def run():
        async with _client() as client:
            await client.post('/api/profile/new', json={'handle': 'NightShift', 'confirm': True, 'curriculum': 'classic'})
            first = await _play(client, 'intro_terminal', ['pwd', 'ls ~/mission', 'cat ~/mission/preparation.txt'])
            assert objective_met(first, {'type': 'file_read', 'path': '/home/operator/mission/preparation.txt'})
            second = await _play(client, 'intro_recon', ['nmap -sV 10.20.0.0/24'])
            assert objective_met(second, {'type': 'service_observed', 'host': 'poste-accueil', 'port': 22})
            from engine.ntlm import nt_hash
            digest = nt_hash('Password123!')
            second.tool_data['security_recovery'] = {'poste-accueil': {'due': 0, 'status': 'HEALTHY', 'users': {}, 'credentials': []}}
            second.tool_data['human_memory'] = {'ravelle.lab:POSTE-ACCUEIL:m.leroux': {'contacts': 9, 'subjects': ['x'], 'last_minute': 1}}
            second.tool_data['vfs_dirs'] = {'operator': ['/home/operator/notes'], 'poste-accueil': ['/srv/ancien-client']}
            second.tool_data['file_audit'] = [{'path': '/tmp/x'}]
            second.tool_data['hashcat'] = {'pot': {digest: 'Password123!'}}
            api.career().checkpoint(second)
            third = await _play(client, 'intro_login', [])
            assert not objective_met(third, {'type': 'file_read', 'path': '/home/operator/mission/preparation.txt'})
            assert not objective_met(third, {'type': 'service_observed', 'host': 'poste-accueil', 'port': 22})
            for key in ('security_recovery', 'human_memory', 'file_audit', 'recon'): assert key not in third.tool_data
            assert third.tool_data['vfs_dirs'] == {'operator': ['/home/operator/notes']}
            # Le potfile suit l'opérateur, mais un hash d'une autre mission ne valide pas un objectif.
            assert third.tool_data['hashcat']['pot'][digest] == 'Password123!'
            assert not objective_met(third, {'type': 'hash_recovered', 'username': 'm.leroux'})
            from engine.mission_data import note_cracked
            note_cracked(third, [digest])
            assert objective_met(third, {'type': 'hash_recovered', 'username': 'm.leroux'})
            # Le texte des consoles, lui, est conservé d'une mission à l'autre.
            assert any('nmap -sV' in line for line in third.tool_data['terminal_transcripts']['main'])
    asyncio.run(run())
