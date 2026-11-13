"""Parcours de référence de l'acte I par l'API locale ; profils temporaires uniquement."""
import asyncio
import json
import tempfile
from pathlib import Path
import httpx
from api import main as api
from engine.career import Career
from engine.campaign import CHAPTERS

# c : terminal Kali ; s : seconde console (session distante) ; f : forum ; m : message Chordly.
PATHS = {
'intro_terminal':[('c','pwd'),('c','ls ~/mission'),('c','cat ~/mission/preparation.txt')],
'intro_recon':[('c','nmap -sV 10.20.0.0/24')],
'intro_login':[('s','ssh m.leroux@10.20.0.21'),('s','Password123!')],
'intro_transfer':[('c','smbclient //10.20.0.10/C$ -U it.presta%Maintenance2026! -c "get Data/contrats_2026.xlsx /home/operator/loot/contrats_2026.xlsx"')],
'intro_evidence':[('c','cat ~/mission/inventaire_ancien.txt'),('c','cat ~/mission/changement_recent.txt'),('c','echo "serveur migre" > ~/mission/conclusion.txt')],
'intro_campaign':[('g','gophish --config /opt/gophish/config.json'),('c','API_KEY=$(cat ~/gophish/api-key.txt)'),('c','curl -k -H "Authorization: $API_KEY" -H "Content-Type: application/json" -d @/home/operator/gophish/campaign.json https://127.0.0.1:3333/api/campaigns/')],
'intro_hash':[('c','hashcat -m 1000 ~/mission/exercice.ntlm /usr/share/wordlists/rockyou.txt')],
'intro_windows':[('s','ssh m.leroux@10.20.0.21'),('s','Password123!'),('s',r'type C:\Users\m.leroux\note.txt'),('s',r'copy C:\Users\m.leroux\note.txt C:\Users\m.leroux\preuve.txt')],
'tuto_p0':[('c','nmap -sV 10.20.0.0/24'),('c','API_KEY=$(cat ~/gophish/api-key.txt)'),('c','curl -k -H "Authorization: $API_KEY" -H "Content-Type: application/json" -d @/home/operator/gophish/campaign.json https://127.0.0.1:3333/api/campaigns/'),('s','impacket-psexec m.leroux:Password123!@10.20.0.21'),('c','smbclient //10.20.0.21/C$ -U m.leroux%Password123! -c "put /home/operator/tools/mimikatz.exe Tools/mimikatz.exe"'),('s',r'C:\Tools\mimikatz.exe "privilege::debug" "sekurlsa::logonpasswords" exit'),('c','impacket-psexec -hashes :{it_hash} it.presta@10.20.0.10')],
'act1_partage':[('f','act1-partages'),('c','nmap -sV 10.61.2.10'),('c','smbclient -L 10.61.2.10 -N'),('c','smbclient //10.61.2.10/public -N -c "ls"'),('c','smbclient //10.61.2.10/public -N -c "get courant/NC-26-041.txt /home/operator/loot/nacre.txt"'),('c','cat ~/loot/nacre.txt'),('m','livraison NC-26-041')],
'act1_echantillon':[('f','act1-echantillon-annonce'),('c','cat ~/mission/annonce.txt'),('c','sqlite3 ~/loot/echantillon.db < ~/mission/echantillon.sql'),('c','sqlite3 ~/loot/echantillon.db ".tables"'),('c','sqlite3 ~/loot/echantillon.db ".schema clients"'),('c','sqlite3 ~/loot/echantillon.db "SELECT date, COUNT(*) FROM clients GROUP BY date;"'),('m','rapport NX-26 36 anciennes 4 recentes')],
'act1_boutique':[('f','act1-pivoine'),('c','nmap -sV 10.61.4.20'),('c','curl http://10.61.4.20/'),('c','sqlmap -u "http://10.61.4.20/produit?id=1" -p id --batch --dbs'),('c','sqlmap -u "http://10.61.4.20/produit?id=1" -D pivoine --tables --batch'),('c','sqlmap -u "http://10.61.4.20/produit?id=1" -D pivoine -T commandes --columns --batch'),('c','sqlmap -u "http://10.61.4.20/produit?id=1" -D pivoine -T commandes --dump --batch --output-dir=/home/operator/loot/sqlmap'),('c','head -n 5 ~/loot/sqlmap/10.61.4.20/dump/pivoine/commandes.csv'),('m','livraison PV-26 commandes')],
'act1_portail':[('f','act1-verre'),('c','cat ~/mission/acces-verre.txt'),('c','curl -H "Cookie: session=ambre-client" "http://10.61.5.20/api/document?id=102" > ~/loot/verre.csv'),('c','cat ~/loot/verre.csv'),('m','preuve VA-26-204 Orme')],
'act1_empreinte':[('c','cat ~/mission/passation.txt'),('c','hashcat -m 1000 ~/mission/planning.ntlm ~/mission/mots.txt'),('c','hashcat -m 1000 --show ~/mission/planning.ntlm'),('s','ssh planning@10.61.6.21'),('s','Atelier2026!'),('s','cat /home/planning/README.txt'),('c','scp planning@10.61.6.21:/srv/planning/OR-26-311.csv ~/loot/planning.csv'),('c','Atelier2026!'),('c','cat ~/loot/planning.csv'),('m','livraison OR-26-311')],
'act1_service':[('f','act1-ticketd'),('c','cat ~/lab/README.txt'),('c','nmap -sV 10.61.7.30'),('c','nc -nv 10.61.7.30 5000'),('c','checksec --file=/home/operator/lab/ticketd'),('c','gdb -q /home/operator/lab/ticketd -ex "info functions" -ex quit'),('s','python3 ~/lab/ticketd.py --host 10.61.7.30 --port 5000 --offset 72 --ret 0x4011d6'),('s','whoami'),('s','cat /home/svc.ticket/README.txt'),('s','cat /etc/ticketd/database.ini'),('c','mysql -h 10.61.7.10 -u ticket_ro -p -D ticketing -e "SELECT * FROM tickets;" > ~/loot/tickets.tsv'),('c','TicketRead2026!'),('c','cat ~/loot/tickets.tsv'),('m','livraison TK-26 tickets')],
'mauvaise_adresse':[('c','cat ~/mission/enquete.txt'),('c','curl http://10.48.1.20/mentions.txt'),('f','aquila-homonymes'),('m','Aquila Conseil et Aquila Fret sont distinctes : AF-26-118.'),('f','aquila-portail'),('c','curl http://10.48.8.31/mentions.txt'),('m','AQF-PORTAIL 10.48.8.31 AF-26-118'),('c','nmap -sV 10.48.8.31'),('c','curl http://10.48.8.31/robots.txt'),('c','curl http://10.48.8.31/exports/support.env.old > ~/loot/support.env'),('c','grep -n SSH ~/loot/support.env'),('s','ssh svc.portail@10.48.8.31'),('s','PortailFret2026!'),('s',r'type C:\Users\svc.portail\Documents\reprise.txt'),('s',r'type C:\Users\svc.portail\Documents\connecteur.ini'),('c','nmap -sV 10.48.8.0/24'),('c','smbclient //10.48.8.10/C$ -U svc.docs%DocsFret2026! -c "get Data/Livraisons/2026/AF-26-118.csv /home/operator/loot/livraison.csv"'),('c','head -n 4 ~/loot/livraison.csv'),('m','livraison AF-26-118')],
'act1_litige':[('c','cat ~/mission/litige.txt'),('f','act1-litige'),('c','sqlite3 ~/loot/litige.db < ~/mission/litige.sql'),('c','sqlite3 ~/loot/litige.db "SELECT source, reference, date FROM livraisons;"'),('m','{choice} dossier 118')],
'act1_recommandation':[('f','act1-boreal'),('c','nmap -sV 10.61.10.20'),('c','curl http://10.61.10.20/')],
}
FINALS={
'sqlmap':[('c','sqlmap -u "http://10.61.10.20/bordereau?id=1" --batch --dbs'),('c','sqlmap -u "http://10.61.10.20/bordereau?id=1" -D boreal -T bordereaux --dump --where="statut=\'valide\'" --batch --output-dir=/home/operator/loot/sqlmap'),('c','cat ~/loot/sqlmap/10.61.10.20/dump/boreal/bordereaux.csv'),('m','livraison BR-26 sqlmap')],
'connecteur':[('c','curl http://10.61.10.20/robots.txt'),('c','curl http://10.61.10.20/support/database.env.old'),('c','mysql -h 10.61.10.10 -u boreal_ro -p -D boreal -e "SELECT * FROM bordereaux WHERE statut=\'valide\';" > ~/loot/boreal.tsv'),('c','BorealRead2026!'),('c','cat ~/loot/boreal.tsv'),('m','livraison BR-26 connecteur')]
}


async def play(profile,variant='sqlmap',side_jobs=True,output=None,*,paths=None,finals=None,curriculum='classic',buy_first=True):
    saved=(api._CAREER,api._WORKSPACE,api.GAMES,api.CONNECTIONS)
    api._CAREER=profile;api._WORKSPACE=None;api.GAMES={};api.CONNECTIONS={}
    records=[];total_commands=0;resumes=0;first_purchase=False;side_count=0
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api.app),base_url='http://test') as client:
            created=await client.post('/api/profile/new',json={'handle':'NightShift','confirm':True,'curriculum':curriculum})
            assert created.status_code==200,created.text
            selected_paths=paths or PATHS
            selected_finals=finals or FINALS
            sequence=list(selected_paths)
            for cid in sequence:
                world=(await client.get('/api/social')).json()
                definition=api._load_contracts()[cid]
                if cid in {'intro_terminal','tuto_p0'}:
                    assert (await client.get('/api/shop')).status_code==403
                    assert not (await client.get('/api/profile')).json()['access']['forums']['breachboard']['unlocked']
                if definition.get('offer_channel')=='forum':
                    pm=next((m for m in world['forum_messages'] if m.get('contract_id')==cid),None)
                    assert pm,(cid,'private forum offer absent')
                    assert (await client.post('/api/forum/messages/'+pm['id']+'/read',json={})).status_code==200
                start=await client.post('/api/games',json={'contract':cid,'handle':'NightShift','rng_seed':0})
                assert start.status_code==200,(cid,start.text)
                gid=start.json()['id'];record={'contract_id':cid,'initial':start.json()['state'],'operations':[]}
                operations=selected_paths[cid]+(selected_finals[variant] if cid=='act1_recommandation' else [])
                for index,(kind,line) in enumerate(operations):
                    state=api.GAMES[gid].state
                    if '{it_hash}' in line:line=line.replace('{it_hash}',state.find_credential('it.presta','NTLM_HASH').value)
                    line=line.replace('{choice}','publier' if variant=='sqlmap' else 'mediation')
                    before=api.serialize_state(state)
                    if kind=='f':response=await client.get('/api/forum/threads/'+line)
                    elif kind=='m':response=await client.post(f'/api/games/{gid}/chat',json={'channel':'chordly','peer':definition['client']['handle'],'text':line})
                    else:
                        console={'c':'main','s':'remote','g':'gophish'}[kind]
                        response=await client.post(f'/api/games/{gid}/terminal',json={'line':line,'console_id':console})
                        assert response.status_code==200 and response.json()['ok'],(cid,line,response.text)
                        total_commands+=1
                    assert response.status_code==200,(cid,line,response.text)
                    while api.GAMES[gid].loop.pending():api.GAMES[gid].loop.tick()
                    api.career().checkpoint(api.GAMES[gid].state)
                    record['operations'].append(dict(kind=kind,line=line,before=before,response=response.json(),state=api.serialize_state(api.GAMES[gid].state)))
                    if index==len(operations)//2 and api.GAMES[gid].state.status=='RUNNING':
                        # Une vraie reprise API en milieu de chaque dossier.
                        api.GAMES.pop(gid)
                        resumed=await client.post('/api/profile/resume',json={})
                        assert resumed.status_code==200,resumed.text
                        gid=resumed.json()['id'];resumes+=1
                state=api.GAMES[gid].state
                assert state.contract_outcome=='SUCCESS',(cid,state.status,state.objectives,state.tool_data.get('facts'))
                api.career().settle(gid,state)
                record['success']=api.serialize_state(state)
                record['economy']={'balance':profile.data['money'],'tier':profile.data['tier'],'reputation':profile.view()['forum_reputation']}
                expected_reactions = {'act1_partage','act1_boutique','act1_empreinte','mauvaise_adresse','act1_litige'}
                if cid in expected_reactions:
                    assert 'relationship:'+cid in profile.data['conversations']
                    assert sum(m.get('id')=='relationship:'+cid for m in profile.data['conversations'].values()) == 1
                records.append(record)
                if cid == 'tuto_p0':
                    # Premier achat réel, sans créditer ni forcer le profil.
                    before = (await client.get('/api/profile')).json()
                    assert before['money']==740 and before['forum_reputation']['breachboard']==40
                    assert before['journey']['contract_id']=='act1_partage'
                    assert (await client.get('/api/shop')).status_code==200
                    if buy_first:
                        purchase=await client.post('/api/shop/buy',json={'item':'wordlist'})
                        assert purchase.status_code==200 and not purchase.json()['paid']
                        nonce=purchase.json()['wallet']['pending']['id']
                        assert profile.data['money']==740
                        assert (await client.post('/api/wallet/device',json={'action':'approve','request_id':nonce})).status_code==400
                        for action in ('connect','unlock'):
                            assert (await client.post('/api/wallet/device',json={'action':action})).status_code==200
                        paid=await client.post('/api/wallet/device',json={'action':'approve','request_id':nonce})
                        assert paid.status_code==200 and paid.json()['balance']==590
                        assert (await client.post('/api/wallet/device',json={'action':'approve','request_id':nonce})).status_code==400
                        slot=await client.post('/api/saves/write',json={'name':'Après le premier achat'})
                        assert slot.status_code==200
                        loaded=await client.post('/api/saves/load',json={'slot_id':slot.json()['id'],'confirm':True})
                        assert loaded.status_code==200 and loaded.json()['money']==590
                        assert 'wordlist' in loaded.json()['inventory'] and not loaded.json()['wallet']['unlocked']
                        ledger=profile.data['wallet']['entries'];balance=0
                        for entry in ledger:
                            balance+=entry['amount']
                            assert balance==entry['balance']
                        assert balance==590
                        assert sum(post.get('id')=='review:tuto_p0' for post in profile.data['forum_posts']['introductions'])==1
                        record['first_purchase']={'item':'wordlist','before':740,'after':590,'restored':True}
                        first_purchase=True

            assert profile.view()['campaign']['completed']==10
            assert not profile.data.get('forum_invitation_accepted')
            world_before_accept=(await client.get('/api/social')).json()
            profile_before_accept=profile.view()
            invitation=next(m for m in (await client.get('/api/forum/messages')).json() if m.get('invitation')=='exployt')
            assert not invitation.get('accepted')
            assert ('publication documentée' if variant=='sqlmap' else 'médiation privée') in invitation['body']
            assert ('voie SQLmap' if variant=='sqlmap' else 'connecteur SQL limité') in invitation['body']
            assert profile.view()['relationships']['nullroute']['label'] == 'Contradiction acceptée'
            assert profile.view()['relationships']['bytewarden']['label'] == ('Preuves publiques assumées' if variant=='sqlmap' else 'Médiation de confiance')
            assert (await client.post('/api/forum/messages/act1-invitation/accept',json={})).status_code==200
            assert profile.data['tier']>=2 and profile.data['forum_invitation_accepted']
            assert (await client.post('/api/shop/buy',json={'item':'nullvad'})).status_code==200
            assert (await client.post('/api/profile/route',json={'route':'tor'})).status_code==200
            assert (await client.get('/api/forum/threads/tor')).status_code==200
            side_balance=profile.data['money']
            side_income=0
            if side_jobs:
                for cid,contract in api._load_contracts().items():
                    if not contract.get('side_job') or contract.get('act') == 2 or profile.lock_reason(contract):continue
                    start=await client.post('/api/games',json={'contract':cid,'handle':'NightShift'})
                    assert start.status_code==200,(cid,start.text)
                    gid=start.json()['id'];solutions=contract.get('reference_commands') or [contract['investigation_steps'][0]['hint'].split('`')[1]]
                    for line in ['cat ~/mission/bon.txt','cat ~/mission/entree.txt',*solutions]:
                        response=await client.post(f'/api/games/{gid}/terminal',json={'line':line})
                        assert response.json()['ok'],(cid,line,response.text)
                        while api.GAMES[gid].loop.pending():api.GAMES[gid].loop.tick()
                    response=await client.post(f'/api/games/{gid}/chat',json={'channel':'chordly','peer':'miette','text':'livraison '+cid[5:]})
                    assert response.status_code==200,response.text
                    state=api.GAMES[gid].state
                    assert state.contract_outcome=='SUCCESS',(cid,state.objectives)
                    api.career().settle(gid,state)
                    side_income+=contract['reward'];side_count+=1
            assert profile.data['money']-side_balance==side_income
            report=dict(first_purchase=first_purchase,variant=variant,chapters=10,missions=len(sequence),side_jobs=side_count,resumes=resumes,terminal_commands=total_commands,side_income=side_income,invitation_accepted=True,choices=profile.data.get('choices'),profile=profile.view())
            if output:
                output.parent.mkdir(parents=True,exist_ok=True)
                output.write_text(json.dumps(dict(report=report,records=records,world_before_accept=world_before_accept,profile_before_accept=profile_before_accept),ensure_ascii=False)+'\n', encoding='utf-8')
            return report
    finally:api._CAREER,api._WORKSPACE,api.GAMES,api.CONNECTIONS=saved


async def main(output):
    output.mkdir(parents=True,exist_ok=True)
    reports=[]
    with tempfile.TemporaryDirectory(prefix='act1-qualification-') as directory:
        for variant in FINALS:
            reports.append(await play(Career(Path(directory)/(variant+'.json')),variant,True,output/('act1-'+variant+'.json')))
    (output/'act1-qualification.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2)+'\n', encoding='utf-8')
    print('Acte I : deux parcours complets, dix chapitres, huit petits contrats et invitation acceptée.')

if __name__=='__main__':
    import sys
    asyncio.run(main(Path(sys.argv[1]) if len(sys.argv)>1 else Path('build/validation')))
