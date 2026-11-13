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
    api._resolve_observations(GameLoop(state, ABILITIES))
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
        while session.loop.pending(): session.loop.tick()
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


# --- Troisième revue : terminal, boucle de jeu, bureau, achats ---
from engine import terminal, console_sessions


def _state(contract_id):
    state = contracts.start_contract(contracts.load_all_contracts()[contract_id], 'Operator', known_ability_ids=set(ABILITIES))
    state.discovered = set(state.hosts)
    return state


def test_variables_reach_every_tool_and_are_expanded_once():
    state = _state('intro_terminal')
    run = lambda line: terminal.parse(line, state, ABILITIES)
    run('F=/home/operator/mission/preparation.txt')
    assert run('cat $F').ok and run('head -n 1 $F').ok and run('grep -c e $F').ok
    # Deux variables qui se citent : une seule passe, pas de récursion.
    run("export A='$B'"); run("export B='$A'")
    assert run('echo $A').output == ['$B']
    # Un ~ en tête d'affectation désigne le dossier personnel, comme dans bash.
    run('export KRB5CCNAME=~/administrator.ccache')
    assert state.terminal_env['KRB5CCNAME'] == '/home/operator/administrator.ccache'


def test_exit_in_the_local_console_keeps_variables_and_directory():
    state = _state('intro_campaign')
    run = lambda line: terminal.parse(line, state, ABILITIES)
    run('API_KEY=$(cat ~/gophish/api-key.txt)'); run('cd /tmp')
    result = run('exit')
    assert result.ok and 'locale' in result.output[0]
    assert state.terminal_env['API_KEY'] and state.terminal_cwd == '/tmp'


def test_mysql_redirect_with_inline_password_writes_the_rows():
    state = _state('act1_service')
    command = 'mysql --batch -h 10.61.7.10 -u ticket_ro --password=TicketRead2026! -D ticketing -e "SELECT * FROM tickets;" > /home/operator/loot/t.tsv'
    assert terminal.parse(command, state, ABILITIES).ok
    assert len(state.terminal_files['/home/operator/loot/t.tsv'].splitlines()) > 1


def test_smbclient_without_password_gives_a_readable_error():
    state = _state('act1_partage')
    result = terminal.parse('smbclient //10.61.2.10/public -U invite -c "ls"', state, ABILITIES)
    assert not result.ok and 'mot de passe requis' in result.output[0] and 'unpack' not in result.output[0]


def test_unknown_command_exit_code_follows_the_remote_system():
    state = _state('act1_service')
    linux = next(h for h in state.hosts.values() if not h.os.startswith('Windows'))
    console_sessions.enter(state, linux, 'svc', 'USER')
    assert terminal.parse('foobar', state, ABILITIES).exit_code == 127


def test_closed_console_is_not_recreated_by_a_pending_campaign():
    state = contracts.start_contract(contracts.load_all_contracts()['intro_campaign'], 'Operator', known_ability_ids=set(ABILITIES))
    loop = GameLoop(state, ABILITIES)
    def run(line, console):
        with console_sessions.using(state, console):
            result = terminal.parse(line, state, ABILITIES)
            if result.action: loop.submit(result.action)
        return result
    run('gophish --config /opt/gophish/config.json', 'mail')
    run('API_KEY=$(cat ~/gophish/api-key.txt)', 'api')
    assert run('curl -k -H "Authorization: $API_KEY" -H "Content-Type: application/json" -d @/home/operator/gophish/campaign.json https://127.0.0.1:3333/api/campaigns/', 'api').ok
    console_sessions.close(state, 'api'); loop.cancel_console('api')
    assert loop.pending()  # la campagne continue : GoPhish tourne dans l'autre console
    while loop.pending(): loop.tick()
    assert 'api' not in state.terminals and 'api' not in state.tool_data.get('terminal_transcripts', {})
    assert state.tool_data['gophish']['campaigns'][0]['results'][0]['status'] == 'Submitted Data'


def test_tick_loop_survives_an_error():
    async def run():
        async with _client() as client:
            await client.post('/api/profile/new', json={'handle': 'NightShift', 'confirm': True})
            game = (await client.post('/api/games', json={'contract': 'intro_terminal', 'handle': 'NightShift', 'rng_seed': 0})).json()
            session = api.GAMES[game['id']]
            session.tick_interval = 0.01
            session.loop.has_pending = lambda: True  # le tutoriel n'avance que si une action attend
            real_tick, calls = session.loop.tick, []
            def flaky():
                calls.append(1)
                if len(calls) == 1: raise RuntimeError('panne ponctuelle')
                return real_tick()
            session.loop.tick = flaky
            await client.post(f"/api/games/{game['id']}/start", json={})
            await asyncio.sleep(0.2)
            assert not session.task.done() and len(calls) > 2 and session.state.tick > 0
            session.state.status = 'ENDED'
            await asyncio.sleep(0.05)
    asyncio.run(run())


def test_state_without_contract_is_never_written_to_the_career():
    from engine.models import GameState
    session = api.GameSession(id='bureau', loop=GameLoop(GameState(hosts={}, users={}), ABILITIES))
    api._persist(session)
    assert not api.career().data.get('active')


def test_purchase_made_during_a_mission_reaches_the_mission():
    async def run():
        async with _client() as client:
            await client.post('/api/profile/new', json={'handle': 'NightShift', 'confirm': True})
            game = (await client.post('/api/games', json={'contract': 'intro_terminal', 'handle': 'NightShift', 'rng_seed': 0})).json()
            state = api.GAMES[game['id']].state
            api.career().data['inventory'].append('wordlist')  # achat confirmé pendant la mission
            api._sync_inventory()
            assert 'wordlist' in state.inventory and 'wordlist' in api.career().data['active']['inventory']
    asyncio.run(run())


def test_desk_files_follow_the_operator_across_missions_and_restarts():
    async def run():
        async with _client() as client:
            await client.post('/api/profile/new', json={'handle': 'NightShift', 'confirm': True})
            await _play(client, 'intro_terminal', ['echo mission > /home/operator/m1.txt', 'pwd', 'ls ~/mission', 'cat ~/mission/preparation.txt'])
            assert api.career().data['completed'] == ['intro_terminal']
            api.GAMES.clear(); api._CAREER = None; api._WORKSPACE = None  # relance du jeu : le bureau sert de terminal
            desk = lambda line: client.post('/api/workspace/terminal', json={'line': line, 'console_id': 'main'})
            assert (await desk('cat /home/operator/m1.txt')).json()['output'] == ['mission\n']
            await desk('echo bureau > /home/operator/notes.txt')
            third = await _play(client, 'intro_recon', [])
            assert third.terminal_files['/home/operator/m1.txt'] == 'mission\n'
            assert third.terminal_files['/home/operator/notes.txt'] == 'bureau\n'
    asyncio.run(run())


def test_contract_cannot_replace_the_career_identity_with_a_character_name():
    async def run():
        async with _client() as client:
            await client.post('/api/profile/new', json={'handle': 'NightShift', 'confirm': True})
            game = (await client.post('/api/games', json={'contract': 'intro_terminal', 'handle': 'k0rvid', 'rng_seed': 0})).json()
            assert api.GAMES[game['id']].state.player_handle == 'NightShift' and api.career().data['handle'] == 'NightShift'
            assert (await client.post('/api/profile/new', json={'handle': 'k0rvid', 'confirm': True})).status_code == 400
    asyncio.run(run())


def test_contract_files_are_read_once_until_they_change():
    first = api._raw_contracts()
    assert api._raw_contracts() is first
    path = api.CONTRACTS_DIR / 'intro_terminal.json'
    stamp = path.stat()
    os.utime(path, ns=(stamp.st_atime_ns, stamp.st_mtime_ns + 1_000_000))
    try: assert api._raw_contracts() is not first
    finally: os.utime(path, ns=(stamp.st_atime_ns, stamp.st_mtime_ns))


# --- Points restants : kill, droits Windows, joignabilité, structure ---
def test_kill_only_frees_the_console_waiting_for_that_process():
    state = _state('intro_campaign')
    with console_sessions.using(state, 'mail'): pass
    state.terminals['mail']['terminal_foreground'] = 2
    state.tool_services['autre'] = {'pid': 1, 'running': True, 'owner': 'mail'}
    assert terminal.parse('kill 1', state, ABILITIES).ok
    assert not state.tool_services['autre']['running'] and state.terminals['mail']['terminal_foreground'] == 2
    state.tool_services['attendu'] = {'pid': 2, 'running': True, 'owner': 'mail'}
    assert terminal.parse('kill 2', state, ABILITIES).ok and state.terminals['mail']['terminal_foreground'] is None


def test_windows_reads_respect_declared_permissions():
    state = _state('tuto_p0')
    host = state.hosts['poste-accueil']
    host.files['/Users/admin/secret.txt'] = 'confidentiel'
    host.files['/Users/m.leroux/note.txt'] = 'libre'
    state.environment['file_permissions'] = {'poste-accueil': {'/Users/admin': ['admin']}}
    console_sessions.enter(state, host, 'm.leroux', 'USER')
    run = lambda line: terminal.parse(line, state, ABILITIES)
    denied = run(r'type C:\Users\admin\secret.txt')
    assert not denied.ok and denied.output == ['Accès refusé.']
    assert run(r'type C:\Users\m.leroux\note.txt').output == ['libre']
    run('powershell')
    assert 'denied' in run(r'Get-Content C:\Users\admin\secret.txt').output[0]
    assert 'denied' in run(r'Copy-Item C:\Users\admin\secret.txt C:\Users\m.leroux\copie.txt').output[0]
    assert '/Users/m.leroux/copie.txt' not in host.files


def test_isolated_host_is_unreachable_for_every_tool():
    state = _state('act1_service')
    database = state.hosts[next(spec['host'] for spec in state.environment['databases'].values())]
    query = 'mysql --batch -h %s -u ticket_ro --password=TicketRead2026! -D ticketing -e "SELECT * FROM tickets;"' % database.ip
    assert terminal.parse(query, state, ABILITIES).ok and state.reachable(database, 3306)
    database.status = 'ISOLATED'
    assert not state.reachable(database, 3306)
    refused = terminal.parse(query, state, ABILITIES)
    assert not refused.ok and 'Cannot connect' in refused.output[0]
    assert database.status == 'ISOLATED'  # un outil ne lève pas l'isolement décidé par la défense
    assert not state.reachable(None, 22) and not state.reachable(database, 9999)


def test_uname_keeps_its_answers_after_cleanup():
    state = _state('intro_terminal')
    assert terminal.parse('uname -a', state, ABILITIES).output[0].startswith('Linux ')
    assert terminal.parse('id', state, ABILITIES).output[0].startswith('uid=1000(operator)')
    assert terminal.parse('uname -x', state, ABILITIES).output == ['uname: arguments non pris en charge par cette version.']
    assert terminal.parse('whoami', state, ABILITIES).output == ['operator']


def test_board_visibility_and_chat_keywords_live_in_the_engine():
    from engine import campaign
    act1 = {'campaign_version': 4, 'completed': [], 'forum_invitation_accepted': False}
    assert campaign.hidden_from_board(act1, 'morel') and campaign.hidden_from_board(act1, 'side_empreinte')
    assert not campaign.hidden_from_board(act1, 'act1_partage')
    assert not campaign.hidden_from_board({**act1, 'forum_invitation_accepted': True}, 'morel')
    assert not campaign.hidden_from_board({'campaign_version': 1}, 'morel')
    for text in ('Aide !', 'où est mon argent ?', 'tu me payes quand', 'rappelle-moi l’objectif'):
        assert contracts.wants_immediate_answer(text), text
    assert not contracts.wants_immediate_answer('bien reçu')


def test_mission_end_goes_through_one_engine_path():
    state = _state('intro_terminal')
    loop = GameLoop(state, ABILITIES)
    assert not loop.finish_if_won() and state.status == 'RUNNING' and not loop.has_pending()
    state.tick = state.max_ticks
    assert loop.finish_if_won() and (state.status, state.winner, state.end_reason) == ('ENDED', 'BLUE', 'timeout')
    assert not loop.finish_if_won() and not loop.abandon()  # déjà terminée
    other = GameLoop(_state('intro_terminal'), ABILITIES)
    assert other.abandon() and (other.state.winner, other.state.end_reason) == ('BLUE', 'disconnected')
    assert other.state.contract_outcome == 'FAILED'


# --- Chaîne Active Directory complète au terminal, cassage honnête ---
def test_full_domain_chain_can_be_played_through_the_terminal():
    from pathlib import Path
    from engine.scenario_loader import load_scenario
    state = load_scenario(Path(__file__).parent / 'fixtures' / 'reseau_ad.json', rng_seed=0, known_ability_ids=set(ABILITIES))
    loop = GameLoop(state, ABILITIES)
    def run(line, console='main'):
        with console_sessions.using(state, console):
            result = terminal.parse(line, state, ABILITIES)
            if result.action: loop.submit(result.action)
        while loop.pending() and state.status == 'RUNNING': loop.tick()
        return result
    domain, sid = state.domain['name'], state.domain['sid']
    run('nmap -sV 192.168.1.0/24')
    run('gophish --config /opt/gophish/config.json', 'mail')
    run('API_KEY=$(cat ~/gophish/api-key.txt)', 'api')
    run('curl -k -H "Authorization: $API_KEY" -H "Content-Type: application/json" -d @/home/operator/gophish/campaign.json https://127.0.0.1:3333/api/campaigns/', 'api')
    password = next(c.value for c in state.loot if c.username == 'jdoe' and c.type == 'PLAINTEXT')
    run(f'impacket-psexec jdoe:{password}@192.168.1.101', 'win')
    run(f'smbclient //192.168.1.101/C$ -U jdoe%{password} -c "put /home/operator/tools/mimikatz.exe Tools/mimikatz.exe"', 'api')
    run(r'C:\Tools\mimikatz.exe "privilege::debug" "sekurlsa::logonpasswords" exit', 'win')
    backup = next(c.value for c in state.loot if c.username == 'svc_backup' and c.type == 'NTLM_HASH')
    run(f'impacket-secretsdump -just-dc -hashes :{backup} {domain}/svc_backup@192.168.1.10', 'api')
    krbtgt = next(c.value for c in state.loot if c.type == 'KRBTGT_HASH')
    run(f'impacket-ticketer -nthash {krbtgt} -domain-sid {sid} -domain {domain} administrator', 'api')
    run('export KRB5CCNAME=~/administrator.ccache', 'api')
    run(f'impacket-psexec -k -no-pass {domain}/administrator@DC-01', 'api')
    assert state.domain_compromised and (state.status, state.winner) == ('ENDED', 'RED')


def test_cracking_needs_a_wordlist_match():
    from engine.game_loop import QueuedAction
    from engine.ntlm import nt_hash
    state = _state('intro_hash')  # dossier où hashcat est disponible
    assert 'red.crack_hash' in state.available_abilities['red']
    loop = GameLoop(state, ABILITIES)
    target = next(iter(state.hosts.values()))
    account = next(name for name, user in state.users.items() if user.password)
    secret = nt_hash(state.users[account].password)
    state.loot.append(Credential('NTLM_HASH', account, secret, target.id))
    cracked = lambda: any(c.username == account and c.type == 'PLAINTEXT' for c in state.loot)
    # Action directe, sans dictionnaire : refusée, rien n'est révélé.
    loop.submit(QueuedAction('red', 'red.crack_hash', target.id, account, 'NTLM_HASH'))
    while loop.pending(): loop.tick()
    assert not state.history[-1].success and 'crack_input_present' in state.history[-1].reason
    assert not cracked()
    # hashcat avec une liste qui ne contient pas le mot de passe : échec, rien n'est révélé.
    state.terminal_files['/home/operator/loot/presta.ntlm'] = secret + '\n'
    state.terminal_files['/home/operator/mots.txt'] = 'azerty\nmotdepasse\n'
    result = terminal.parse('hashcat -m 1000 ~/loot/presta.ntlm ~/mots.txt', state, ABILITIES)
    loop.submit(result.action)
    while loop.pending(): loop.tick()
    assert not state.history[-1].success and state.history[-1].reason == 'wordlist_exhausted'
    assert not cracked()
