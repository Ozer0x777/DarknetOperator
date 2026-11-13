"""Campagne complète, persistance, routage et isolation du monde simulé."""
import asyncio
from pathlib import Path
import pytest
import httpx
from engine import contracts, terminal, trace
from engine.career import Career
from engine.game_loop import GameLoop, load_all_abilities, QueuedAction
from engine.models import Alert
from engine.persistence import state_from_dict, state_to_dict
from engine.scenario_loader import load_scenario
from api.main import app

ROOT = Path(__file__).parents[1]
ABILITIES = load_all_abilities()


def scenario(name='varenne'):
    return load_scenario(ROOT/'scenarios'/f'{name}.json',known_ability_ids=set(ABILITIES))


def alert(state, severity='CRITICAL'):
    state.alerts.append(Alert(state.next_alert_id(),'Test',severity,'test','poste-accueil',state.tick,state.tick))


def act(loop, aid, host='poste-accueil', username=None, ctype=None):
    loop.submit(QueuedAction('red',aid,host,username,ctype))
    while loop.pending() and loop.state.status=='RUNNING':
        loop.tick()
    entry=loop.state.history[-1]
    assert entry.success,(aid,entry.reason,entry.message)


def crack(loop, username):
    """Casse l'empreinte comme le joueur : hashcat sur le fichier du butin, avec la liste de mots."""
    from engine import terminal, console_sessions
    # La console principale est dans la session Windows : hashcat tourne dans une console Kali locale.
    with console_sessions.using(loop.state,'kali'):
        result=terminal.parse(f'hashcat -m 1000 ~/loot/{username}.ntlm /usr/share/wordlists/rockyou.txt',loop.state,ABILITIES)
        assert result.ok and result.action,result.output
        loop.submit(result.action)
    while loop.pending() and loop.state.status=='RUNNING':
        loop.tick()
    entry=loop.state.history[-1]
    assert entry.success,(entry.reason,entry.message)


def test_trace_exposure_never_ends_solo_and_old_alerts_do_not_accumulate():
    state=scenario();trace.configure(state,'direct');alert(state)
    trace.advance(state)
    assert state.status == 'RUNNING' and state.end_reason is None
    assert state.trace['exposed']
    progress = state.trace['progress']
    for _ in range(100): trace.advance(state)
    assert state.trace['progress'] == progress


def test_relay_exposure_remains_playable():
    state=scenario();trace.configure(state,'relay')
    for _ in range(30):alert(state)
    trace.advance(state)
    assert state.trace['burned']==['relay']
    for _ in range(30):alert(state)
    trace.advance(state)
    assert state.status == 'RUNNING' and state.end_reason is None


def test_blue_ai_waits_then_isolates():
    from engine import blue_ai
    state=scenario();alert(state)
    state.tick=9;blue_ai.advance(state)
    assert state.hosts['poste-accueil'].status!='ISOLATED'
    state.tick=10;blue_ai.advance(state)
    assert state.hosts['poste-accueil'].status=='ISOLATED'


def test_real_shell_uses_virtual_files_and_rejects_unknown_options(tmp_path):
    state=scenario('tuto_p0')
    assert terminal.parse('whoami',state,ABILITIES).output==['operator']
    assert terminal.parse('cat /etc/shadow',state,ABILITIES).ok is False
    assert terminal.parse('nmap --invented 10.20.0.21',state,ABILITIES).ok is False
    assert terminal.parse('nmap -sV -p 22,445 10.20.0.0/24',state,ABILITIES).ok
    assert terminal.parse('cat "unfinished',state,ABILITIES).ok is False
    # Une commande système destructrice n'est jamais déléguée au système.
    sentinel=tmp_path/'sentinel';sentinel.write_text('intact')
    assert terminal.parse(f'rm -rf {sentinel}',state,ABILITIES).ok  # -f sur un fichier virtuel absent
    assert sentinel.read_text()=='intact'


def test_save_restores_world_rng_and_terminal():
    state=scenario();trace.configure(state,'tor')
    state.terminal_files['/home/operator/test']='hello'
    restored=state_from_dict(state_to_dict(state))
    assert restored.trace==state.trace
    assert restored.terminal_files==state.terminal_files
    assert restored.rng.random()==state.rng.random()


def test_real_command_chain_and_authentication():
    state=scenario('tuto_p0');loop=GameLoop(state,ABILITIES)
    act(loop,'red.phishing_initial_access')
    result=terminal.parse('impacket-psexec m.leroux:Password123!@10.20.0.21',state,ABILITIES)
    assert result.ok
    loop.submit(result.action);loop.tick()
    assert state.terminal_host=='poste-accueil'
    from support import upload
    upload(state, loop, state.hosts["poste-accueil"], state.find_credential("m.leroux", "PLAINTEXT"))
    result=terminal.parse('mimikatz "privilege::debug" "sekurlsa::logonpasswords" exit',state,ABILITIES)
    assert result.ok
    loop.submit(result.action);loop.tick()
    credential=state.find_credential('it.presta','NTLM_HASH')
    assert len(credential.value)==32
    assert '/home/operator/loot/it.presta.ntlm' in state.terminal_files
    assert not terminal.parse('ssh it.presta:wrong@10.20.0.21',state,ABILITIES).ok


def test_campaign_all_tiers_and_settlement_once(tmp_path):
    career=Career(tmp_path/'career.json')
    loaded=contracts.load_all_contracts(known_ability_ids=set(ABILITIES))
    for cid in ['tuto_p0','morel','rival','varenne','affiliation','grand_compte']:
        contract=loaded[cid]
        if cid=='varenne':
            career.buy('nullvad');career.select_route('tor')
        if cid=='affiliation':career.buy('vesper')
        if cid=='grand_compte':career.buy('relay');career.select_route('relay')
        state=contracts.start_contract(contract,'Operator',known_ability_ids=set(ABILITIES))
        career.prepare(contract,state);loop=GameLoop(state,ABILITIES)
        primary=state.hosts['poste-accueil'].primary_user
        admin=state.hosts['poste-accueil'].cached_logons[0]
        act(loop,'red.recon_scan')
        if cid!='grand_compte':
            act(loop,'red.phishing_initial_access')
            act(loop,'red.psexec_lateral',username=primary,ctype='PLAINTEXT')
            act(loop,'red.mimikatz_dump',username=primary)
        if cid in ['morel','rival']:
            crack(loop,admin)
        if cid=='varenne':
            act(loop,'red.dcsync','srv-fichiers',username=admin)
            act(loop,'red.golden_ticket','srv-fichiers',username='krbtgt')
            assert not state.domain_compromised
            loop.submit(QueuedAction('red','red.psexec_lateral','srv-fichiers','krbtgt','KRBTGT_HASH',params={'kerberos_ticket':'/home/operator/administrator.ccache','ticket_user':'administrator'}))
            while loop.pending() and state.status=='RUNNING': loop.tick()
        elif cid!='rival':
            act(loop,'red.psexec_lateral','srv-fichiers',admin)
            if cid in ['morel','grand_compte']:
                act(loop,'red.exfiltrate','srv-fichiers')
            if cid=='grand_compte':act(loop,'red.destroy_backups','srv-fichiers')
            if cid in ['affiliation','grand_compte']:
                act(loop,'red.encrypt','poste-accueil')
                act(loop,'red.encrypt','srv-fichiers')
        assert state.contract_outcome=='SUCCESS',(cid,state.end_reason,state.trace)
        career.settle(cid,state)
        balance=career.data['money']
        career.settle(cid,state)
        assert career.data['money']==balance
        career=Career(tmp_path/'career.json')
    assert career.data['tier']==3
    assert career.data['reputation']==450
    assert len(career.data['completed'])==6


def test_api_profile_shop_disconnect_and_resume():
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
            assert (await client.get('/api/profile')).json()['tier']==0
            assert (await client.post('/api/shop/buy',json={'item':'gpu3'})).status_code==400
            game=(await client.post('/api/games',json={'contract':'tuto_p0','handle':'Operator'})).json()
            assert (await client.post('/api/games',json={'contract':'tuto_p0','handle':'Operator'})).json()['id']==game['id']
            assert (await client.post('/api/profile/resume',json={})).json()['id']==game['id']
            ended=(await client.post(f"/api/games/{game['id']}/disconnect",json={})).json()
            assert ended['end_reason']=='disconnected'
            assert ended['contract']['outcome']=='FAILED'
            assert 'debrief' in ended
            assert (await client.post('/api/games',json={'scenario':'../../x'})).status_code==422
    asyncio.run(run())


def test_pending_actions_resume_without_being_lost():
    state=scenario('tuto_p0')
    loop=GameLoop(state,ABILITIES)
    command=terminal.parse('nmap -sn 10.20.0.0/24',state,ABILITIES)
    loop.submit(command.action)
    restored=state_from_dict(state_to_dict(state))
    resumed=GameLoop(restored,ABILITIES)
    assert len(resumed.pending())==1
    resumed.tick()
    assert restored.discovered==set(restored.hosts)
    assert restored.scanned==set()
    assert restored.pending_actions==[]


def test_scan_ports_and_target_are_respected():
    state=scenario('tuto_p0');loop=GameLoop(state,ABILITIES)
    command=terminal.parse('nmap -p 22 10.20.0.21',state,ABILITIES)
    loop.submit(command.action);loop.tick()
    assert state.discovered=={'poste-accueil'}
    from api.serializers import serialize_state
    public=serialize_state(state)
    assert len(public['hosts'])==1
    assert [s['port'] for s in public['hosts'][0]['services']]==[22]
    assert '445/tcp' not in state.history[-1].message


def test_suspicious_contract_still_pays_verified_success(tmp_path):
    career=Career(tmp_path/'career.json');career.data.update(tier=1,money=1000,reputation=100)
    loaded=contracts.load_all_contracts(known_ability_ids=set(ABILITIES))
    contract=loaded['offre_urgente'];bounty=contracts.bounty_view(contract)
    assert bounty['client']['forum_rep']==0
    assert bounty['client']['account_age_days']==1
    assert 'sting' not in bounty
    state=contracts.start_contract(contract,'Operator',known_ability_ids=set(ABILITIES))
    career.prepare(contract,state)
    state.status,state.winner='ENDED','RED';contracts.advance(state)
    assert state.contract_outcome == 'SUCCESS'
    career.settle('trap',state)
    assert career.data['money']==3500
    assert career.data['reputation']==100


def test_cli_ticket_requires_correct_domain_and_secret():
    from engine.models import Credential
    state=scenario();state.discovered=set(state.hosts)
    state.loot.append(Credential('KRBTGT_HASH','krbtgt','a'*32,'srv-fichiers'))
    line=f"impacket-ticketer -nthash {'a'*32} -domain-sid {state.domain['sid']} -domain {state.domain['name']} administrator"
    result=terminal.parse(line,state,ABILITIES)
    assert result.ok
    assert result.action.ability_id=='red.golden_ticket'
    assert not terminal.parse(line.replace(state.domain['name'],'wrong.lab'),state,ABILITIES).ok


def test_api_health_shop_and_disconnect():
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
            assert (await client.get('/api/health')).json()['application']=='RedTeamSimulator'
            assert (await client.post('/api/shop/buy',json={'item':'gpu3'})).status_code==400
            response=await client.post('/api/games',json={'contract':'tuto_p0','handle':'Operator'})
            assert response.status_code==200
            gid=response.json()['id']
            assert (await client.post('/api/profile/resume',json={})).json()['id']==gid
            ended=(await client.post(f'/api/games/{gid}/disconnect',json={})).json()
            assert ended['end_reason']=='disconnected'
            assert ended['contract']['outcome']=='FAILED'
            assert 'debrief' in ended
    asyncio.run(run())


def test_ssh_authentication_uses_real_prompt_and_limits_retries():
    state=scenario('tuto_p0');loop=GameLoop(state,ABILITIES)
    act(loop,'red.phishing_initial_access')
    result=terminal.parse('ssh m.leroux@10.20.0.21',state,ABILITIES)
    assert result.ok and 'password:' in result.output[0]
    assert state.terminal_auth
    assert terminal.parse('Password123!',state,ABILITIES).ok
    assert state.terminal_host=='poste-accueil' and not state.terminal_auth
    terminal.parse('exit',state,ABILITIES)
    terminal.parse('ssh m.leroux@10.20.0.21',state,ABILITIES)
    for _ in range(3):assert not terminal.parse('wrong',state,ABILITIES).ok
    assert not state.terminal_auth and state.terminal_host is None


def test_authentic_terminal_path_completes_tutorial_without_legacy_flags():
    state=scenario('tuto_p0');loop=GameLoop(state,ABILITIES)
    def run(line):
        result=terminal.parse(line,state,ABILITIES)
        assert result.ok,result.output
        if result.action:
            loop.submit(result.action)
            while loop.pending() and state.status=='RUNNING':loop.tick()
            assert state.history[-1].success,state.history[-1].message
    run('nmap -sV 10.20.0.0/24')
    act(loop,'red.phishing_initial_access')  # Campagne GoPhish via son interface.
    run('impacket-psexec m.leroux:Password123!@10.20.0.21')
    from support import upload
    upload(state, loop, state.hosts["poste-accueil"], state.find_credential("m.leroux", "PLAINTEXT"))
    run('mimikatz "privilege::debug" "sekurlsa::logonpasswords" exit')
    cred=state.find_credential('it.presta','NTLM_HASH')
    run('exit')
    while state.is_on_cooldown('red.psexec_lateral',state.tick+1):loop.tick()
    run(f'impacket-psexec -hashes :{cred.value} it.presta@10.20.0.10')
    assert state.status=='ENDED' and state.winner=='RED'


def test_only_one_engine_can_write_a_profile(tmp_path):
    from desktop_server import acquire_profile_lock
    lock=acquire_profile_lock(tmp_path)
    try:
        with pytest.raises(RuntimeError,match='autre moteur'):
            acquire_profile_lock(tmp_path)
    finally:
        lock.close()
    next_lock=acquire_profile_lock(tmp_path)
    next_lock.close()


def test_isolation_closes_an_open_remote_terminal():
    state=scenario('tuto_p0')
    state.terminal_host='poste-accueil'
    state.terminal_user='m.leroux'
    state.hosts['poste-accueil'].status='ISOLATED'
    result=terminal.parse('cat /srv/private',state,ABILITIES)
    assert not result.ok
    assert 'Connection closed' in result.output[0]
    assert state.terminal_host is None


def test_security_recovery_survives_save_and_does_not_repeat():
    from engine import blue_ai
    from engine.models import Credential
    state = scenario('grand_compte')
    host = state.hosts['poste-accueil']
    username = next(iter(state.users))
    state.loot.append(Credential('PLAINTEXT', username, 'test', host.id))
    host.status, host.compromised_by = 'COMPROMISED', 'red'
    alert(state)
    state.tick = 7
    limit = state.max_ticks
    blue_ai.advance(state)
    assert host.status == 'ISOLATED'
    assert state.users[username].status == 'DISABLED'
    assert not state.loot[0].valid
    state = state_from_dict(state_to_dict(state))
    state.tick = 13
    blue_ai.advance(state)
    assert state.hosts[host.id].status == 'COMPROMISED'
    assert state.users[username].status == 'ACTIVE' and state.loot[0].valid
    assert state.max_ticks == limit + 6
    alert(state)
    state.tick += 20
    blue_ai.advance(state)
    assert state.hosts[host.id].status == 'COMPROMISED'


def test_legacy_isolated_save_gets_recovery():
    from engine import blue_ai
    state = scenario()
    state.hosts['poste-accueil'].status = 'ISOLATED'
    blue_ai.advance(state)
    state.tick += 6
    blue_ai.advance(state)
    assert state.hosts['poste-accueil'].status == 'HEALTHY'
