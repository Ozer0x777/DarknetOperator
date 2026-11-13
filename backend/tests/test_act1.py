"""L'acte complet, les limites des outils, les droits et la porte narrative."""
import asyncio
import copy
import json
from pathlib import Path
import pytest
from act1_validation import play
from engine.career import Career
from engine import contracts,terminal,campaign
from engine.game_loop import load_all_abilities
from engine.console_sessions import using
from engine.persistence import state_to_dict,state_from_dict

ROOT=Path(__file__).parents[1]
ABILITIES=load_all_abilities()

def state(cid):return contracts.start_contract(contracts.load_contract(ROOT/'contracts'/f'{cid}.json',known_ability_ids=set(ABILITIES)),'Operator')

def run(line,s):
    with using(s,'main'):return terminal.parse(line,s,ABILITIES)

@pytest.mark.parametrize('variant',['sqlmap','connecteur'])
def test_full_act1_two_finals_and_all_side_jobs(tmp_path,variant):
    profile=Career(tmp_path/(variant+'.json'))
    report=asyncio.run(play(profile,variant,True))
    assert report['chapters']==10 and report['side_jobs']==8 and report['resumes']>=12
    assert report['side_income']==380
    assert report['choices']['litige118']==('publication' if variant=='sqlmap' else 'mediation')
    assert len(profile.data['forum_messages'])>=4
    assert sum(m.get('invitation')=='exployt' for m in profile.data['forum_messages'].values())==1
    posts=profile.data['forum_posts']['act1-litige']
    assert any(p.get('id')=='act1-litige-resolution' for p in posts)==(variant=='sqlmap')
    loaded=Career(profile.path)
    assert loaded.data['choices']==profile.data['choices']
    assert loaded.view()['campaign']['invitation_accepted']


def test_sqlmap_real_data_scope_and_incomplete_dump_rejected():
    s=state('act1_boutique')
    assert not run('sqlmap -u "http://10.61.4.20/recherche?q=rose" --batch --dbs',s).ok
    assert not run('sqlmap -u "http://10.61.4.20/produit?id=1" -p q --batch --dbs',s).ok
    assert not run('sqlmap -u "http://10.61.4.20/produit?id=1" -D pivoine -T personnel --dump',s).ok
    assert not run('sqlmap -u "http://10.61.4.20/produit?id=1" --os-shell',s).ok
    assert run('sqlmap -u "http://10.61.4.20/produit?id=1" -D pivoine -T commandes -C id --dump --output-dir=/home/operator/loot/sqlmap',s).ok
    expected=s.contract['investigation_steps'][0]['requires'][2]
    from engine.win_conditions import objective_met
    assert not objective_met(s,expected)
    assert run('sqlmap -u "http://10.61.4.20/produit?id=1" -D pivoine -T commandes --dump --output-dir=/home/operator/loot/sqlmap',s).ok
    assert not objective_met(s,expected)  # Un export doit également être inspecté.
    assert run('head -n 5 ~/loot/sqlmap/10.61.4.20/dump/pivoine/commandes.csv',s).ok
    assert objective_met(s,expected)
    csv=s.terminal_files[expected['path']]
    assert len(csv.splitlines())==13 and csv.startswith('id,reference,date,client,montant')


def test_sqlite_does_not_read_host_files_and_queries_read_real_tables():
    s=state('act1_echantillon')
    assert run('sqlite3 ~/loot/a.db < ~/mission/echantillon.sql',s).ok
    assert not run('sqlite3 ~/loot/a.db "ATTACH DATABASE \'/etc/passwd\' AS stolen;"',s).ok
    assert not run('sqlite3 ~/loot/a.db "SELECT load_extension(\'x\');"',s).ok
    assert not run('sqlite3 ~/loot/a.db "SELECT readfile(\'/etc/passwd\');"',s).ok
    assert run('sqlite3 ~/loot/a.db "SELECT \'2024-03-12\',36;"',s).ok
    assert not s.tool_data['queries'][-1]['tables']
    assert run('sqlite3 ~/loot/a.db "SELECT date,COUNT(*) FROM clients GROUP BY date;"',s).ok
    assert s.tool_data['queries'][-1]['tables']==['clients']
    restored=state_from_dict(state_to_dict(s))
    assert run('sqlite3 ~/loot/a.db "SELECT COUNT(*) FROM clients;"',restored).output==['40']


def test_web_session_and_idor_are_different_checks():
    s=state('act1_portail')
    assert '401' in run('curl -i "http://10.61.5.20/api/document?id=102"',s).output[0]
    assert not run('curl -f "http://10.61.5.20/api/document?id=102"',s).ok
    assert '403' in run('curl -i -H "Cookie: session=ambre-client" "http://10.61.5.20/api/prive?id=102"',s).output[0]
    response=run('curl -H "Cookie: session=ambre-client" "http://10.61.5.20/api/document?id=102"',s)
    assert response.ok and 'VA-26-204' in response.output[0]
    assert not run('curl -f -H "Cookie: session=ambre-client" "http://10.61.5.20/api/document?id=999"',s).ok


def test_linux_service_permissions_and_sql_account_scope():
    s=state('act1_service')
    assert not run('python3 ~/lab/ticketd.py --host 10.61.7.30 --port 5000 --offset 71 --ret 0x4011d6',s).ok
    assert run('python3 ~/lab/ticketd.py --host 10.61.7.30 --port 5000 --offset 72 --ret 0x4011d6',s).ok
    assert s.terminal_access=='USER' and s.terminal_user=='svc.ticket'
    assert not run('cat /root/master.key',s).ok
    assert not run('cat /root/master.key | grep Privé',s).ok
    assert not run('cp /root/master.key /tmp/key',s).ok
    assert run('cat /etc/ticketd/database.ini',s).ok
    assert run('echo note > /home/svc.ticket/note.txt',s).ok
    assert s.hosts['ticket-app'].files['/home/svc.ticket/note.txt']=='note\n'
    assert '/home/svc.ticket/note.txt' not in s.terminal_files
    assert run('exit',s).ok
    assert not run('mysql -h 10.61.7.10 -u ticket_ro --password=wrong -D ticketing -e "SELECT * FROM tickets;"',s).ok
    assert not run('mysql -h 10.61.7.10 -u ticket_ro --password=TicketRead2026! -D ticketing -e "SELECT * FROM salaires;"',s).ok
    assert run('mysql --batch -h 10.61.7.10 -u ticket_ro --password=TicketRead2026! -D ticketing -e "SELECT COUNT(*) FROM tickets;"',s).output==['COUNT(*)\n6']


def test_share_permissions_no_traversal_and_side_reward_once(tmp_path):
    s=state('act1_partage')
    assert not run('smbclient //10.61.2.10/public -N -c "get ../prive/comptes.txt /home/operator/loot/secret"',s).ok
    assert not run('smbclient //10.61.2.10/public -N -c "put /tmp/foo new.txt"',s).ok
    assert run('smbclient //10.61.2.10/public -N -c "ls"',s).ok
    profile=Career(tmp_path/'career.json')
    side=state('side_tri');side.contract_outcome='SUCCESS';side.status='ENDED';side.winner='RED'
    profile.settle('first',side);balance=profile.data['money']
    profile.settle('first',side);assert profile.data['money']==balance
    other=state('side_tri');other.contract_outcome='SUCCESS';other.status='ENDED';other.winner='RED'
    profile.settle('second',other)
    assert profile.data['money']==balance and other.payout==0


def test_campaign_gate_and_invitation_cannot_be_forged(tmp_path):
    profile=Career(tmp_path/'career.json');profile.data.update(campaign_version=3,tier=3,completed=['tuto_p0'])
    assert profile.lock_reason(contracts.load_all_contracts()['act1_recommandation'])
    assert profile.lock_reason(contracts.load_all_contracts()['mauvaise_adresse'])
    profile.data['forum_messages']={'fake':{'invitation':'exployt'}}
    with pytest.raises(ValueError):campaign.accept(profile,'fake')
    from engine.social import forum_allowed
    assert not forum_allowed(profile,'exployt')
    # Les anciennes carrières conservent leurs accès et leur dossier 8 déjà disponible.
    profile.data.update(campaign_version=2,tier=1,completed=['tuto_p0','morel'])
    assert not profile.lock_reason(contracts.load_all_contracts()['mauvaise_adresse'])


def test_virtual_archive_members_and_traversal_rejected():
    s=state('side_comptage')
    assert run('tar -tf ~/mission/lot.tar',s).output==['ancien/lot.txt','courant/lot.txt']
    assert run('tar -xf ~/mission/lot.tar -C ~/loot',s).ok
    assert s.terminal_files['/home/operator/loot/courant/lot.txt']=='LOT-77;2026-11-07\n'
    s.terminal_files['/home/operator/mission/bad.tar']='VIRTUAL-TAR\n'+json.dumps({'../secret':'bad','normal':'good'})
    before=copy.deepcopy(s.terminal_files)
    assert not run('tar -xf ~/mission/bad.tar -C ~/loot',s).ok
    assert before==s.terminal_files
