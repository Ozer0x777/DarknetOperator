"""Parcours du chapitre 8 par l'API, sans injection de preuves ni d'identifiants."""
import asyncio
import json
from pathlib import Path
import httpx
from api import main as api
from engine.career import Career
from engine.persistence import state_from_dict, state_to_dict
from engine.investigation import flags
from engine import contracts

ROOT = Path(__file__).parents[1]


def test_private_offer_requires_recommendation(tmp_path, monkeypatch):
    from engine import social
    profile = Career(tmp_path/'career.json')
    monkeypatch.setattr(api, '_CAREER', profile)
    catalog = contracts.load_all_contracts()
    assert profile.lock_reason(catalog['mauvaise_adresse'])
    assert not any(o['id']=='mauvaise_adresse' for o in social.view(profile,catalog)['offers'])
    profile.data.update(tier=1, completed=['tuto_p0','morel'])
    first = social.view(profile,catalog)
    second = social.view(profile,catalog)
    assert any(o['id']=='mauvaise_adresse' and o['peer']=='nullroute' for o in first['offers'])
    assert any(c['id']=='nullroute' for c in first['contacts'])
    assert len([m for m in second['messages'] if m['id']=='offer:mauvaise_adresse']) == 1


def test_enquiry_access_wrong_file_resume_and_delivery(tmp_path, monkeypatch):
    profile = Career(tmp_path/'career.json')
    # Point de départ : carrière ayant terminé Morel. La mission elle-même est vierge.
    profile.data.update(tier=1, completed=['tuto_p0','morel'], handle='Operator')
    monkeypatch.setattr(api,'_CAREER',profile)
    monkeypatch.setattr(api,'GAMES',{})
    monkeypatch.setattr(api,'CONNECTIONS',{})
    monkeypatch.setattr(api,'_WORKSPACE',None)
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api.app),base_url='http://test') as client:
            board=(await client.get('/api/contracts')).json()
            assert not any(c['contract_id']=='mauvaise_adresse' for c in board)
            social_state=(await client.get('/api/social')).json()
            assert any(c['id']=='nullroute' for c in social_state['contacts'])
            discussion=await client.post('/api/social/chat',json={'channel':'chordly','peer':'nullroute','handle':'Operator','text':'Salut'})
            assert discussion.status_code==200,discussion.text
            result=await client.post('/api/games',json={'contract':'mauvaise_adresse','handle':'Operator'})
            assert result.status_code==200,result.text
            gid=result.json()['id']
            def state(): return api.GAMES[gid].state
            async def command(line,console='main',ok=True):
                response=await client.post(f'/api/games/{gid}/terminal',json={'line':line,'console_id':console})
                assert response.status_code==200,response.text
                assert response.json()['ok'] is ok,(line,response.text)
                while api.GAMES[gid].loop._queue: api.GAMES[gid].loop.tick()
                return response.json()
            async def chat(text):
                response=await client.post(f'/api/games/{gid}/chat',json={'channel':'chordly','peer':'nullroute','text':text})
                assert response.status_code==200,response.text
                return response.json()
            proof='Aquila Conseil et Aquila Fret sont distinctes : AF-26-118.'
            await chat(proof)
            assert not flags(state())
            await command('curl http://10.48.1.20/mentions.txt')
            await chat(proof)
            assert not flags(state())  # Le message du forum est aussi une preuve requise.
            assert (await client.get('/api/forum/threads/aquila-homonymes')).status_code==200
            await chat(proof)
            assert flags(state()) == ['erreur_prouvee']
            await chat(proof)
            assert flags(state()) == ['erreur_prouvee']
            await client.get('/api/forum/threads/aquila-portail')
            await command('curl http://10.48.8.31/mentions.txt')
            await chat('AQF-PORTAIL 10.48.8.30 AF-26-118')
            assert 'cible_confirmee' not in flags(state())
            await chat('AQF-PORTAIL 10.48.8.310 AF-26-118')
            assert 'cible_confirmee' not in flags(state())
            await chat('AQF-PORTAIL 10.48.8.31 AF-26-118')
            assert 'cible_confirmee' in flags(state())
            await command('nmap -sV 10.48.8.31')
            await command('curl -f http://10.48.8.31/exports/inconnu',ok=False)
            await command('curl http://10.48.8.31/robots.txt')
            await command('curl http://10.48.8.31/exports/support.env.old > ~/loot/support.env')
            await command('grep -n SSH ~/loot/support.env')
            await command('ssh svc.portail@10.48.8.31','remote')
            secret=await command('PortailFret2026!','remote')
            assert state().terminals['remote']['terminal_access']=='USER'
            await command(r'type C:\Users\svc.portail\Documents\reprise.txt','remote')
            await command(r'type C:\Users\svc.portail\Documents\connecteur.ini','remote')
            await command('nmap -sV 10.48.8.0/24')
            await command('smbclient //10.48.8.10/C$ -U svc.portail%PortailFret2026! -c "ls"',ok=False)
            await command('smbclient //10.48.8.10/C$ -U svc.docs%DocsFret2026! -c "ls"')
            await command('smbclient //10.48.8.10/C$ -U svc.docs%DocsFret2026! -c "get Data/Livraisons/2024/AF-118.csv /home/operator/loot/archive.csv"')
            await command('grep -n AF-24 ~/loot/archive.csv')
            await chat('livraison AF-26-118')
            assert state().status=='RUNNING' and 'livraison_validee' not in flags(state())
            # Sauvegarde réelle, puis rechargement des observations et des consoles.
            await client.post('/api/saves/write',json={'name':'Avant le vrai fichier'})
            profile.checkpoint(state())
            restored=Career(profile.path)
            loaded=state_from_dict(restored.data['active'])
            assert flags(loaded)==['erreur_prouvee','cible_confirmee']
            assert 'aquila-portail' in loaded.tool_data['investigation']['threads']
            api.GAMES[gid].loop=api.GameLoop(loaded,api.ABILITIES)
            await command('smbclient //10.48.8.10/C$ -U svc.docs%DocsFret2026! -c "get Data/Livraisons/2026/AF-26-118.csv /home/operator/loot/livraison.csv"')
            await command('cat ~/loot/livraison.csv | grep AF-26-118 | cut -d ";" -f 4 | sort | uniq')
            await command('wc -l ~/loot/livraison.csv')
            await command('sha256sum ~/loot/livraison.csv')
            original=state().terminal_files['/home/operator/loot/livraison.csv']
            await command('echo faux > ~/loot/livraison.csv')
            await chat('livraison AF-26-118')
            assert state().status=='RUNNING'
            await command('smbclient //10.48.8.10/C$ -U svc.docs%DocsFret2026! -c "get Data/Livraisons/2026/AF-26-118.csv /home/operator/loot/livraison.csv"')
            assert state().terminal_files['/home/operator/loot/livraison.csv']==original
            await command('head -n 4 ~/loot/livraison.csv')
            await chat('livraison AF-26-118')
            assert state().contract_outcome=='SUCCESS'
            assert 'mauvaise_adresse' in profile.data['completed']
            balance=profile.data['money']
            profile.settle(gid,state())
            assert profile.data['money']==balance
            # Le dossier rejoué ne réutilise ni les réponses ni les lectures précédentes.
            replay=await client.post('/api/games',json={'contract':'mauvaise_adresse','handle':'Operator'})
            assert replay.status_code==200,replay.text
            replay_state=api.GAMES[replay.json()['id']].state
            assert not flags(replay_state) and not replay_state.tool_data['read_http']
    asyncio.run(run())
