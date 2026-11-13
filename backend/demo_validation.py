"""Démo complète par API en mémoire : quatre fins, reprises et passage en campagne."""
import asyncio
import json
import tempfile
from pathlib import Path
import httpx
from api import main as api
from act1_validation import PATHS
from engine.career import Career
from engine.onboarding import DEMO_STAGES

ROUTES = {
    'web': ['curl http://10.62.1.10/', 'curl http://10.62.1.10/archive.txt', 'curl -o ~/loot/preuve.txt http://10.62.1.10/suivi.txt', 'cat ~/loot/preuve.txt'],
    'partage': ['smbclient -L 10.62.1.10 -N', 'smbclient //10.62.1.10/public -N -c "ls"', 'smbclient //10.62.1.10/public -N -c "get courant/CT-26-071.txt /home/operator/loot/preuve.txt"', 'cat ~/loot/preuve.txt'],
}


async def qualify(output):
    previous = api._CAREER, api._WORKSPACE, api.GAMES, api.CONNECTIONS
    records = []
    try:
        for route in ROUTES:
            for choice in ('signaler', 'discret'):
                with tempfile.TemporaryDirectory(prefix='darknet-demo-') as folder:
                    profile = Career(Path(folder)/'career.json')
                    api._CAREER=profile; api._WORKSPACE=None; api.GAMES={}; api.CONNECTIONS={}
                    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api.app), base_url='http://test') as client:
                        result=await client.post('/api/profile/new',json={'handle':'NightShift','confirm':True,'play_mode':'demo'})
                        assert result.status_code==200,result.text
                        assert (await client.post('/api/profile/continue',json={})).status_code==409
                        for cid in ('tuto_p0','dossier_contretemps','act1_partage'):
                            assert (await client.post('/api/games',json={'contract':cid,'handle':'NightShift'})).status_code==409,cid
                        gid=''
                        async def command(line):
                            r=await client.post(f'/api/games/{gid}/terminal',json={'line':line,'console_id':'main'})
                            assert r.status_code==200 and r.json()['ok'],(line,r.text)
                            while api.GAMES[gid].loop._queue: api.GAMES[gid].loop.tick()
                            profile.checkpoint(api.GAMES[gid].state)
                        for cid in DEMO_STAGES:
                            world=(await client.get('/api/social')).json()
                            assert sum(o['id']==cid for o in world['offers'])==1,(cid,world['offers'])
                            created=await client.post('/api/games',json={'contract':cid,'handle':'NightShift','rng_seed':0})
                            assert created.status_code==200,created.text
                            gid=created.json()['id']
                            if cid=='dossier_contretemps':
                                bad=await client.post(f'/api/games/{gid}/chat',json={'channel':'chordly','peer':'miette','text':f'CT-26-071 reporté {route} {choice}'})
                                assert bad.status_code==200 and not api.GAMES[gid].state.tool_data.get('decisions')
                                for line in ROUTES[route]: await command(line)
                                slot=await client.post('/api/saves/write',json={'name':'Avant la décision'})
                                assert slot.status_code==200
                                loaded=await client.post('/api/saves/load',json={'slot_id':slot.json()['id'],'confirm':True})
                                assert loaded.status_code==200,loaded.text
                                resumed=await client.post('/api/profile/resume',json={}); assert resumed.status_code==200,resumed.text
                                gid=resumed.json()['id']
                                answered=await client.post(f'/api/games/{gid}/chat',json={'channel':'chordly','peer':'miette','text':f'CT-26-071 est reporté, source {route} : je choisis {choice}.'})
                                assert answered.status_code==200,answered.text
                            else:
                                for _,line in PATHS[cid]: await command(line)
                            state=api.GAMES[gid].state
                            assert state.contract_outcome=='SUCCESS',(cid,state.status,state.tool_data)
                            profile.settle(gid,state)
                            assert (await client.get('/api/shop')).status_code==403
                            assert not profile.view()['forum_unlocked']
                        assert profile.view()['journey']['action']=='continue_campaign'
                        expected=route+'_'+choice
                        assert profile.data['choices']['contretemps']==expected
                        assert profile.view()['relationships']['miette']['label']=='Confiance établie'
                        money=profile.data['money']; assert money==340,money
                        raw=api.contracts.load_all_contracts()
                        offer='act1_recommandation' if choice=='signaler' else 'act1_echantillon'
                        assert api._load_contracts()[offer]['reward']==raw[offer]['reward']+30
                        assert api._load_contracts()[offer]['reward']==raw[offer]['reward']+30 # no repeated overlay
                        world=(await client.get('/api/social')).json()
                        miette=next(c for c in world['contacts'] if c['id']=='miette')
                        assert 'Confiance établie' in miette['bio']
                        # Replay has no new credit and cannot rewrite the original career decision.
                        created=await client.post('/api/games',json={'contract':'dossier_contretemps','handle':'NightShift'})
                        assert created.status_code==200,created.text
                        gid=created.json()['id']
                        for line in ROUTES[route]: await command(line)
                        other='discret' if choice=='signaler' else 'signaler'
                        await client.post(f'/api/games/{gid}/chat',json={'channel':'chordly','peer':'miette','text':f'CT-26-071 reporté {route} {other}'})
                        assert api.GAMES[gid].state.contract_outcome=='SUCCESS'
                        profile.settle(gid,api.GAMES[gid].state)
                        assert profile.data['money']==money and profile.data['choices']['contretemps']==expected
                        saved=await client.post('/api/saves/write',json={'name':'Fin de démo'})
                        continued=await client.post('/api/profile/continue',json={})
                        assert continued.status_code==200 and continued.json()['journey']['contract_id']=='intro_login',continued.text
                        assert profile.data['money']==money and not profile.view()['forum_unlocked']
                        profile=Career(profile.path); api._CAREER=profile
                        assert profile.data['play_mode']=='campaign' and profile.data['choices']['contretemps']==expected
                        loaded=await client.post('/api/saves/load',json={'slot_id':saved.json()['id'],'confirm':True})
                        assert loaded.status_code==200 and loaded.json()['play_mode']=='demo'
                        assert loaded.json()['journey']['action']=='continue_campaign'
                        records.append(dict(route=route,choice=choice,balance=money,reloaded=True,replay_preserved=True,continues_at='intro_login',trust_offer=offer,trust_bonus=30))
        output.mkdir(parents=True,exist_ok=True)
        report=dict(scope='API en mémoire, temps accéléré ; aucune validation graphique native.',runs=records)
        (output/'demo-qualification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n')
        print('Démo : quatre parcours complets, deux sources, deux décisions, sauvegardes rechargées et campagne poursuivie ; achats verrouillés.')
        return report
    finally: api._CAREER, api._WORKSPACE, api.GAMES, api.CONNECTIONS=previous


if __name__=='__main__':
    import sys
    asyncio.run(qualify(Path(sys.argv[1]) if len(sys.argv)>1 else Path('build/validation')))
