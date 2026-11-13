"""Acte II : refus réels, preuves, tunnel, annuaire et transitions persistantes."""
import asyncio
import copy
import json
from pathlib import Path
import pytest
from act2_validation import play
from engine import contracts,terminal,console_sessions,bloodhound
from engine.game_loop import load_all_abilities
from engine.career import Career
from engine.persistence import state_to_dict,state_from_dict
from engine.directory_tools import ticket,matches,ldap_filter

ABILITIES=load_all_abilities()
def state(cid='act2_polkit'):return contracts.start_contract(contracts.load_all_contracts()[cid],'NightShift')
def run(s,line,console='main'):
    with console_sessions.using(s,console):return terminal.parse(line,s,ABILITIES)
def ssh(s,ref='10.71.1.10',user='ops',password='Relais2026!',console='main'):
    assert run(s,'ssh '+user+'@'+ref,console).ok
    assert run(s,password,console).ok


@pytest.mark.parametrize('variant',['pivot','smb'])
def test_complete_act2_from_act1_with_six_side_jobs_and_reloads(tmp_path,variant):
    profile=Career(tmp_path/(variant+'.json'))
    report=asyncio.run(play(profile,variant))
    assert report['missions']==10 and report['sides']==6 and report['resumes']>=16
    assert len(report['records'])==16
    loaded=Career(profile.path)
    assert loaded.view()['act2']['completed']==10
    assert loaded.view()['relationships']['quartz']['label']=='Partenaire confirmé'


def test_polkit_patch_backport_blocks_root_despite_same_displayed_version():
    s=state();ssh(s,'10.71.1.11')
    assert run(s,'pkexec --version').output==['pkexec version 0.105']
    assert 'deb11u1' in '\n'.join(run(s,'dpkg-query -W policykit-1').output)
    assert run(s,'gcc /home/ops/cve-2021-4034.c -o /home/ops/check').ok
    assert not run(s,'/home/ops/check').ok
    assert not run(s,'cat /root/secret.txt').ok
    assert s.terminals['main']['terminal_user']=='ops'
    assert 'polkit:root' not in s.tool_data.get('facts',{})
    assert run(s,'exit').ok
    ssh(s)
    assert run(s,'pkexec --version').output==['pkexec version 0.105']
    assert run(s,'gcc /home/ops/cve-2021-4034.c -o /home/ops/check').ok
    assert run(s,'/home/ops/check').ok
    assert 'uid=0(root)' in run(s,'id').output[0]
    assert run(s,'cat /root/passation.txt').ok


def test_tunnel_is_port_scoped_bound_to_process_and_restored_with_owner():
    s=state('act2_pivot')
    assert not run(s,'curl -f http://10.72.0.20/registre.txt').ok
    assert run(s,'ssh -N -L 8080:10.72.0.20:80 ops@10.71.1.10','tunnel').ok
    assert run(s,'Relais2026!','tunnel').ok
    assert not run(s,'whoami','tunnel').ok # La console reste occupée.
    assert run(s,'curl -f http://127.0.0.1:8080/registre.txt').ok
    assert '127.0.0.1:8080' in '\n'.join(run(s,'ss -lntp').output)
    assert 'ssh -N -L 8080' in '\n'.join(run(s,'ps aux').output)
    assert not run(s,'curl -f http://127.0.0.1:8081/registre.txt').ok
    assert not run(s,'curl -f http://10.72.0.20/registre.txt').ok # Pas de route globale magique.
    restored=state_from_dict(state_to_dict(s))
    assert run(restored,'curl -f http://127.0.0.1:8080/registre.txt').ok
    with console_sessions.using(restored,'tunnel'):console_sessions.interrupt(restored)
    assert not run(restored,'curl -f http://127.0.0.1:8080/registre.txt').ok
    assert '8080' not in '\n'.join(run(restored,'ss -lntp').output)


def test_tunnel_bad_auth_and_binding_collision_do_not_grant_access():
    s=state('act2_pivot')
    assert run(s,'ssh -N -L 8080:10.72.0.20:80 ops@10.71.1.10','a').ok
    for _ in range(3):assert not run(s,'wrong','a').ok
    assert not s.tool_services
    assert run(s,'ssh -N -L 8080:10.72.0.20:80 ops@10.71.1.10','a').ok
    assert run(s,'Relais2026!','a').ok
    assert not run(s,'ssh -N -L 8080:10.72.0.20:80 ops@10.71.1.10','b').ok
    console_sessions.close(s,'a')
    assert not run(s,'curl -f http://127.0.0.1:8080/registre.txt').ok


def test_ldap_authentication_scope_filter_and_empty_results():
    s=state('act2_annuaire')
    prefix='ldapsearch -x -H ldap://10.71.2.10 -D audit@orbe.lab -w '
    assert not run(s,prefix+'wrong -b "DC=orbe,DC=lab" "(objectClass=*)"').ok
    assert not run(s,prefix+'Audit2026! -b "DC=inconnu,DC=lab" "(objectClass=*)"').ok
    response=run(s,prefix+'Audit2026! -b "DC=orbe,DC=lab" "(&(objectClass=user)(servicePrincipalName=*))" sAMAccountName')
    assert response.ok and 'svc.backup' in '\n'.join(response.output)
    assert not any('sAMAccountName: audit' in row for row in response.output)
    response=run(s,prefix+'Audit2026! -b "DC=orbe,DC=lab" "(sAMAccountName=missing)"')
    assert response.ok and not response.output
    assert not run(s,prefix+'Audit2026! -b "DC=orbe,DC=lab" "(&(broken)"').ok


def test_kerberoast_crypto_does_not_accept_password_without_checksum_match():
    value=ticket('Service2026!','svc.backup','orbe.lab','MSSQLSvc/archive:1433','fixture')
    assert value.startswith('$krb5tgs$23$*svc.backup$')
    assert matches(value,'Service2026!') and not matches(value,'wrong')
    assert not matches(value[:-2]+'00','Service2026!')
    s=state('act2_service')
    assert not run(s,'impacket-GetUserSPNs orbe.lab/audit:wrong -dc-ip 10.71.2.10 -request').ok
    s.users['svc.backup'].status='DISABLED'
    assert run(s,'impacket-GetUserSPNs orbe.lab/audit:Audit2026! -dc-ip 10.71.2.10').ok
    assert s.tool_data['facts']['kerberos:spns']['users']==[]


def test_hashcat_13100_exhausted_and_show_follow_actual_dictionary():
    s=state('act2_service')
    assert run(s,'impacket-GetUserSPNs orbe.lab/audit:Audit2026! -dc-ip 10.71.2.10 -request -outputfile /home/operator/loot/tickets.txt').ok
    s.terminal_files['/home/operator/wrong.txt']='not-a-password\n'
    assert not run(s,'hashcat -m 13100 ~/loot/tickets.txt ~/wrong.txt').ok
    assert not run(s,'hashcat -m 13100 --show ~/loot/tickets.txt').output
    assert run(s,'hashcat -m 13100 ~/loot/tickets.txt ~/mission/services.txt').ok
    assert 'Service2026!' in '\n'.join(run(s,'hashcat -m 13100 --show ~/loot/tickets.txt').output)


def test_bloodhound_rejects_forged_or_altered_archive():
    s=state('act2_annuaire');s.terminal_files['/home/operator/loot/fake.zip']='VIRTUAL-ZIP\n{}'
    with pytest.raises(ValueError):bloodhound.import_archive(s,'/home/operator/loot/fake.zip')
    assert not s.tool_data.get('bloodhound')


def test_windows_inventory_matches_session_and_requires_executable_transfer():
    s=state('act2_annuaire');ssh(s,'10.71.2.21','audit','Audit2026!')
    assert run(s,'whoami /all').ok
    assert 'audit' in '\n'.join(run(s,'whoami /all').output)
    assert '10.0.22621.2428' in '\n'.join(run(s,'systeminfo').output)
    assert not run(s,r'C:\Users\audit\sharphound.exe --CollectionMethods Group').ok
    assert run(s,'powershell').ok
    assert '10.0.22621.2428' in '\n'.join(run(s,'Get-CimInstance Win32_OperatingSystem').output)
    assert 'KB5031354' in '\n'.join(run(s,'Get-HotFix').output)
    assert not run(s,'uname -a').ok


def test_act2_gates_cannot_skip_invitation_or_previous_dossier(tmp_path):
    profile=Career(tmp_path/'career.json');definitions=contracts.load_all_contracts()
    assert profile.lock_reason(definitions['act2_passation'])
    profile.data.update(tier=2,forum_invitation_accepted=True,route='tor',inventory=['nullvad'],completed=['tuto_p0','act1_recommandation'],forum_reputation={'breachboard':500,'exployt':0,'xsx':0},reputation=500)
    assert not profile.lock_reason(definitions['act2_passation'])
    assert profile.lock_reason(definitions['act2_pivot'])
    assert profile.lock_reason(definitions['act2_side_tunnel'])


def test_remote_software_availability_and_inventory_script_use_machine_data():
    s=state('act2_polkit')
    assert run(s,'scp ~/tools/linpeas.sh ops@10.71.1.10:/home/ops/linpeas.sh').ok
    assert run(s,'Relais2026!').ok
    ssh(s)
    assert not run(s,'impacket-GetUserSPNs orbe.lab/audit:Audit2026! -dc-ip 10.71.2.10').ok
    report=run(s,'bash /home/ops/linpeas.sh')
    assert report.ok and 'policykit-1 0.105-31' in '\n'.join(report.output)
    assert 'root' not in s.terminals['main']['terminal_user']


def test_collector_transfer_import_graph_and_tamper_are_causal():
    s=state('act2_annuaire')
    assert run(s,'scp ~/tools/sharphound.exe audit@10.71.2.21:C:/Users/audit/sharphound.exe').ok
    assert run(s,'Audit2026!').ok
    ssh(s,'10.71.2.21','audit','Audit2026!')
    assert run(s,r'C:\Users\audit\sharphound.exe --CollectionMethods Group,ObjectProps --OutputDirectory C:\Users\audit --ZipFileName test.zip').ok
    digest=s.tool_data['facts']['sharphound:collection']['digest']
    assert digest
    assert run(s,'exit').ok
    assert run(s,'scp audit@10.71.2.21:C:/Users/audit/test.zip ~/loot/test.zip').ok
    assert run(s,'Audit2026!').ok
    imported=bloodhound.import_archive(s,'/home/operator/loot/test.zip')
    assert len(imported['nodes'])==4 and len(imported['edges'])==2
    assert all(edge['type']=='MemberOf' for edge in imported['edges'])
    before=copy.deepcopy(s.tool_data['bloodhound'])
    s.terminal_files['/home/operator/loot/test.zip']+='tampered'
    with pytest.raises(ValueError):bloodhound.import_archive(s,'/home/operator/loot/test.zip')
    assert s.tool_data['bloodhound']==before


def test_ldap_escaped_wildcard_is_literal_not_a_presence_filter():
    assert ldap_filter(r'(cn=literal\2aname)')({'cn':'literal*name'})
    assert not ldap_filter(r'(cn=literal\2aname)')({'cn':'literal-other-name'})
    assert ldap_filter('(cn=literal*name)')({'cn':'literal-other-name'})


def test_refusal_is_not_recorded_from_a_negative_or_ambiguous_statement():
    from engine.investigation import answer
    s=state('act2_garant');assert run(s,'cat ~/mission/garant.txt').ok;ssh(s)
    assert run(s,'cat /home/ops/recu.txt').ok
    assert 'pas' in answer(s,'Je ne veux pas refuser AC-26-209.').casefold()
    assert not s.tool_data.get('decisions')
    assert 'plusieurs' in answer(s,'Refuser ou renegocier AC-26-209 ?')
    assert not s.tool_data.get('decisions')
    answer(s,'Je confirme renegocier AC-26-209.')
    assert s.tool_data['decisions']['act2_garant']=='renegociation'


def test_ldap_rootdse_is_public_but_linux_account_cannot_bind_to_ad():
    s=state('act2_annuaire')
    root=run(s,'ldapsearch -x -H ldap://10.71.2.10 -b "" -s base "(objectClass=*)" defaultNamingContext')
    assert root.ok and root.output==['dn:','defaultNamingContext: DC=orbe,DC=lab']
    assert not run(s,'ldapsearch -x -H ldap://10.71.2.10 -D ops@orbe.lab -w Relais2026! -b "DC=orbe,DC=lab" "(objectClass=*)"').ok
    assert not run(s,'ldapsearch -x -H ldap://10.71.2.10 -D audit@other.lab -w Audit2026! -b "DC=orbe,DC=lab" "(objectClass=*)"').ok


def test_first_act2_dossier_does_not_reveal_future_account_or_network():
    s=state('act2_passation')
    assert s.discovered=={'bridge'}
    assert '/home/operator/mission/acces.txt' not in s.terminal_files
    assert '/home/operator/mission/services.txt' not in s.terminal_files
