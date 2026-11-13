"""Reprises sensibles via API, sur des profils de test temporaires préparés."""
import json
import tempfile
from pathlib import Path
import httpx
from api import main as api
from engine.career import Career
from engine.campaign import CHAPTERS
from engine.onboarding import STAGES
from engine.persistence import state_to_dict


async def qualify(output):
    previous=(api._CAREER,api._WORKSPACE,api.GAMES,api.CONNECTIONS)
    checks=[]
    try:
        with tempfile.TemporaryDirectory(prefix='darknet-sensitive-save-') as folder:
            profile=Career(Path(folder)/'career.json')
            profile.data.update(tier=1,money=1000)
            api._CAREER=profile;api._WORKSPACE=None;api.GAMES={};api.CONNECTIONS={}
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api.app),base_url='http://test') as client:
                gid=(await client.post('/api/games',json={'contract':'tuto_p0','handle':'NightShift'})).json()['id']
                async def command(line,console='main'):
                    result=await client.post(f'/api/games/{gid}/terminal',json={'line':line,'console_id':console})
                    assert result.status_code==200 and result.json()['ok'],result.text
                    return result.json()
                await command('gophish --config /opt/gophish/config.json','server')
                await command('ssh m.leroux@10.20.0.21','remote')
                await command('Password123!','remote');await command('powershell','remote')
                await command("$env:NOTE='conserve'",'remote')
                assert (await command('nmap -sV 10.20.0.0/24'))['queued']
                old=state_to_dict(api.GAMES[gid].state)
                pending=(await client.post('/api/shop/buy',json={'item':'gpu1'})).json()['wallet']['pending']['id']
                for action in ['connect','unlock']:assert (await client.post('/api/wallet/device',json={'action':action})).status_code==200
                slot=(await client.post('/api/saves/write',json={'name':'Commande, session et appareil'})).json()['id']
                # Erreur d'écriture injectée au commit, après vérification de l'emplacement.
                old_data=profile.data;original_save=profile.save
                def fail_commit():
                    if profile.data is not old_data:raise OSError('Écriture de test refusée')
                    original_save()
                profile.save=fail_commit
                failed=await client.post('/api/saves/load',json={'slot_id':slot,'confirm':True})
                assert failed.status_code==503 and gid in api.GAMES and not api.GAMES[gid].paused
                assert profile.wallet_session()['pending']['id']==pending and profile.wallet_session()['unlocked']
                profile.save=original_save
                checks.append('Échec de commit : session, commande et demande non signée conservées')
                during=[]
                class ClosingSocket:
                    async def close(self):
                        during.append((await client.post('/api/wallet/device',json={'action':'approve','request_id':pending})).status_code)
                        during.append((await client.post(f'/api/games/{gid}/terminal',json={'line':'pwd'})).status_code)
                api.CONNECTIONS[gid]=[ClosingSocket()]
                assert (await client.post('/api/saves/load',json={'slot_id':slot,'confirm':True})).status_code==200
                assert during==[400,404]
                assert profile.wallet_session()['pending'] is None and not profile.wallet_session()['connected']
                assert (await client.post('/api/wallet/device',json={'action':'approve','request_id':pending})).status_code==400
                assert profile.data['money']==1000 and 'gpu1' not in profile.data['inventory']
                checks.append('Chargement réussi : ancien nonce ColdVault refusé, aucun débit')
                resumed=(await client.post('/api/profile/resume',json={})).json();gid=resumed['id']
                session=api.GAMES[gid]
                assert session.paused and state_to_dict(session.state)==old
                assert (await command('echo $env:NOTE','remote'))['output']==['conserve']
                while session.loop._queue:session.loop.tick()
                assert len(session.state.history)==len(old['history'])+1 and session.state.tool_services['gophish']['running']
                checks.append('Commande exécutée une fois après reprise, session distante et serveur conservés')
                # Fixture ciblée au chapitre du litige ; les preuves sont ensuite obtenues par commandes.
                profile=Career(Path(folder)/'choice.json')
                profile.data.update(campaign_version=3,tier=1,reputation=400,money=500,forum_reputation={'breachboard':400,'exployt':0,'xsx':0},completed=list(dict.fromkeys(STAGES+[row[0] for row in CHAPTERS[:8]])))
                api._CAREER=profile;api._WORKSPACE=None;api.GAMES={};api.CONNECTIONS={}
                gid=(await client.post('/api/games',json={'contract':'act1_litige','handle':'NightShift'})).json()['id']
                for line in ['cat ~/mission/litige.txt','sqlite3 ~/loot/choix.db<~/mission/litige.sql','sqlite3 ~/loot/choix.db "SELECT date,reference,source FROM livraisons;"']:await command(line)
                assert (await client.get('/api/forum/threads/act1-litige')).status_code==200
                before=(await client.post('/api/saves/write',json={'name':'Avant choix'})).json()['id']
                ambiguous=await client.post(f'/api/games/{gid}/chat',json={'channel':'chordly','peer':'bytewarden','text':'publier dossier 118 ou mediation dossier 118 ?'})
                assert ambiguous.status_code==200 and not profile.data.get('choices')
                private=await client.post(f'/api/games/{gid}/chat',json={'channel':'chordly','peer':'bytewarden','text':'Médiation du lot 118.'})
                assert private.json()['contract']['outcome']=='SUCCESS'
                after=(await client.post('/api/saves/write',json={'name':'Après médiation'})).json()['id']
                assert (await client.post('/api/saves/load',json={'slot_id':after,'confirm':True})).status_code==200
                assert profile.data['choices']['litige118']=='mediation' and 'act1-litige-resolution' in profile.data['forum_messages']
                assert (await client.post('/api/saves/load',json={'slot_id':before,'confirm':True})).status_code==200
                gid=(await client.post('/api/profile/resume',json={})).json()['id']
                public=await client.post(f'/api/games/{gid}/chat',json={'channel':'chordly','peer':'bytewarden','text':'Publication du lot 118.'})
                assert public.json()['contract']['outcome']=='SUCCESS' and profile.data['choices']['litige118']=='publication'
                assert profile.data['money']==760 and 'act1-litige-resolution' not in profile.data.get('forum_messages',{})
                checks.append('Choix ambigu non validé ; branches privée et publique restaurées sans mélange')
    finally:api._CAREER,api._WORKSPACE,api.GAMES,api.CONNECTIONS=previous
    output.mkdir(parents=True,exist_ok=True)
    (output/'save-review-qualification.json').write_text(json.dumps({'scope':'Profils temporaires préparés ; commandes réelles du simulateur et échec de commit injecté. Aucun profil personnel utilisé.','checks':checks},ensure_ascii=False,indent=2)+'\n')
    print('Reprises sensibles : commande en attente, session distante, choix narratif et demande ColdVault validés ; échec de commit sans perte de session.')
    return checks


if __name__=='__main__':
    import asyncio,sys
    asyncio.run(qualify(Path(sys.argv[1]) if len(sys.argv)>1 else Path('build/validation')))
