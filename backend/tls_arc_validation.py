"""Trois liens TLS par l'API, avec emplacements manuels avant/après chaque choix."""
import asyncio
import copy
import json
import tempfile
from pathlib import Path

import httpx
from api import main as api
from engine.career import Career
from engine.onboarding import CURRENT_STAGES
from engine.save_store import atomic_json

PATHS={
 'professionnel':[('tls-premier-lien','professionnel'),('tls-arc-exposition','forme'),('tls-arc-desaccord','independance'),('tls-arc-veille','communique'),('tls-arc-limite','refus'),('tls-arc-retour','questionner')],
 'amitie':[('tls-premier-lien','amitie'),('tls-arc-exposition','histoire'),('tls-arc-desaccord','transparence'),('tls-arc-veille','resume'),('tls-arc-limite','public_seulement'),('tls-arc-retour','conserver')],
 'attirance':[('tls-premier-lien','attirance'),('tls-arc-exposition','histoire'),('tls-arc-desaccord','acces'),('tls-arc-veille','communique'),('tls-arc-limite','note_privee'),('tls-arc-retour','limiter')]}


async def play(output:Path):
    previous=(api._CAREER,api._WORKSPACE,api._WORKSPACE_REVISION,api.GAMES,api.CONNECTIONS)
    records=[];resumes=0
    try:
        with tempfile.TemporaryDirectory(prefix='darknet-tls-arc-') as folder:
            for stance,path in PATHS.items():
                profile=Career(Path(folder)/stance/'career.json')
                profile.data.update(campaign_version=4,handle='NightShift',tier=1,reputation=220,
                    completed=list(dict.fromkeys(CURRENT_STAGES+['act1_partage','act1_echantillon','act1_boutique','act1_portail'])))
                api._CAREER=profile;api._WORKSPACE=None;api._WORKSPACE_REVISION=None;api.GAMES={};api.CONNECTIONS={}
                from engine import social
                social.prepare(profile)['published'].append('tls-contact')
                profile.save()
                steps=[]
                async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api.app),base_url='http://test') as client:
                    async def restore(name):
                        nonlocal resumes
                        saved=await client.post('/api/saves/write',json={'name':name})
                        assert saved.status_code==200,saved.text
                        loaded=await client.post('/api/saves/load',json={'slot_id':saved.json()['id'],'confirm':True})
                        assert loaded.status_code==200,loaded.text
                        resumes+=1
                    for scene_id,option_id in path:
                        before=(await client.get('/api/social')).json()
                        scene=next(s for s in before['scene_choices'] if s['peer']=='Madame_TLS')
                        assert scene['id']==scene_id,(scene_id,scene['id'])
                        if scene_id=='tls-arc-exposition':
                            # Point de départ consultable avec REDTEAM_SAVE_DIR,
                            # indépendant de la vraie carrière du joueur.
                            atomic_json(output/'tls-arc-playtest'/stance/'career.json',profile.data)
                        await restore('Avant '+scene_id)
                        assert (await client.get('/api/social')).json()['scene_choices']==before['scene_choices']
                        payload=dict(handle='NightShift',peer='Madame_TLS',channel='chordly',scene_id=scene_id,option_id=option_id)
                        response=await client.post('/api/social/choice',json=payload)
                        assert response.status_code==200,response.text
                        response=response.json()
                        await restore('Après '+scene_id)
                        waited=await client.post('/api/world/wait',json={'minutes':2})
                        assert waited.status_code==200,waited.text
                        published=(await client.get('/api/social')).json()
                        choices=profile.data['social']['scenes']['choices']
                        reply_id=choices[scene_id]['reply_id']
                        assert reply_id in profile.data['conversations']
                        steps.append(dict(scene_id=scene_id,option_id=option_id,request=payload,before=copy.deepcopy(before),
                                          response=copy.deepcopy(response),published=copy.deepcopy(published),reply_id=reply_id))
                    assert profile.data['social']['bonds']['Madame_TLS']['stance']==stance
                    received=profile.data['social'].get('transmissions',{})
                    sent_private=any(d['classification']=='privé' for t in received.values() for d in t['documents'])
                    assert sent_private==(stance=='attirance')
                    records.append(dict(stance=stance,steps=steps,bond=copy.deepcopy(profile.data['social']['bonds']['Madame_TLS'])))
        output.mkdir(parents=True,exist_ok=True)
        report=dict(scope='Arc après la prise de contact ; contexte de campagne acquis, API locale et temps simulé, sans testeur humain.',resumes=resumes,routes=records)
        (output/'tls-arc-replays.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
        print(f'Arc TLS : trois liens, cinq scènes après le premier lien, {resumes} reprises manuelles avant/après les choix.')
        return report
    finally:
        api._CAREER,api._WORKSPACE,api._WORKSPACE_REVISION,api.GAMES,api.CONNECTIONS=previous


if __name__=='__main__':
    import sys
    asyncio.run(play(Path(sys.argv[1]) if len(sys.argv)>1 else Path(__file__).parents[1]/'build/validation'))
