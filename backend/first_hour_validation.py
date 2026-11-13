"""Parcours novice reproductible : erreurs, indices, sauvegarde puis reprise.

Temps accéléré et API en mémoire ; ne mesure pas une session humaine de 30–60 min.
"""
import asyncio
import json
import tempfile
from pathlib import Path
import httpx
from api import main as api
from act1_validation import PATHS
from engine.career import Career
from engine.onboarding import STAGES

MISTAKES = {
    'intro_terminal':'cat ~/mission/preparaton.txt',
    'intro_recon':'nmap --invented 10.20.0.0/24',
    'intro_login':'ssh inconnu@10.20.0.99',
    'intro_transfer':'cat ~/loot/absent.xlsx',
    'intro_evidence':'cat ~/mission/changement_recen.txt',
    'intro_campaign':'gophish --config /opt/gophish/absent.json',
    'intro_hash':'hashcat -m 1000 ~/mission/exercice.ntlm ~/mission/absent.txt',
    'intro_windows':r'type C:\Users\m.leroux\note.txt',
    'tuto_p0':'nmap --invented 10.20.0.0/24',
}


async def qualify(output):
    previous=(api._CAREER,api._WORKSPACE,api.GAMES,api.CONNECTIONS)
    records=[]
    try:
        with tempfile.TemporaryDirectory(prefix='darknet-first-hour-') as folder:
            profile=Career(Path(folder)/'career.json')
            api._CAREER=profile;api._WORKSPACE=None;api.GAMES={};api.CONNECTIONS={}
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api.app),base_url='http://test') as client:
                assert (await client.post('/api/profile/new',json={'handle':'NightShift','confirm':True,'curriculum':'classic'})).status_code==200
                for cid in STAGES:
                    created=await client.post('/api/games',json={'contract':cid,'handle':'NightShift','rng_seed':0})
                    assert created.status_code==200,(cid,created.text)
                    gid=created.json()['id']
                    async def command(line,console='main'):
                        result=await client.post(f'/api/games/{gid}/terminal',json={'line':line,'console_id':console})
                        assert result.status_code==200,result.text
                        while api.GAMES[gid].loop._queue:api.GAMES[gid].loop.tick()
                        return result.json()
                    bad=await command(MISTAKES[cid])
                    assert not bad['ok'],(cid,bad)
                    before=profile.data['money']
                    first=await client.post(f'/api/games/{gid}/chat',json={'channel':'chordly','peer':'k0rvid','text':'indice'})
                    assert first.json()['messages'][-1]['text'].startswith('Indice 1/2'),(cid,first.text)
                    slot=await client.post('/api/saves/write',json={'name':'Lecture en cours — '+cid})
                    assert slot.status_code==200
                    assert (await client.post('/api/saves/load',json={'slot_id':slot.json()['id'],'confirm':True})).status_code==200
                    resumed=await client.post('/api/profile/resume',json={})
                    assert resumed.status_code==200;gid=resumed.json()['id']
                    second=await client.post(f'/api/games/{gid}/chat',json={'channel':'chordly','peer':'k0rvid','text':'encore un indice'})
                    assert second.json()['messages'][-1]['text'].startswith('Indice 2/2')
                    assert profile.data['money']==before
                    for kind,line in PATHS[cid]:
                        if '{it_hash}' in line:
                            line=line.replace('{it_hash}',api.GAMES[gid].state.find_credential('it.presta','NTLM_HASH').value)
                        result=await command(line,{'c':'main','s':'remote','g':'gophish'}[kind])
                        assert result['ok'],(cid,line,result)
                    state=api.GAMES[gid].state
                    assert state.contract_outcome=='SUCCESS',cid
                    profile.settle(gid,state)
                    assert not profile.view()['access']['shop']['unlocked'] if cid!='tuto_p0' else profile.view()['access']['shop']['unlocked']
                    records.append(dict(contract=cid,mistake=MISTAKES[cid],hints=2,resumed=True,payout=state.payout,balance=profile.data['money']))
                assert profile.data['money']==740 and profile.data['forum_reputation']['breachboard']==40
                report=dict(scope='Parcours novice simulé par API ; temps accéléré, sans affichage natif ni durée humaine mesurée.',
                            dossiers=len(records),mistakes=len(records),resumes=len(records),records=records,next_step=profile.view()['journey'])
                output.mkdir(parents=True,exist_ok=True)
                (output/'first-hour-qualification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n', encoding='utf-8')
                print('Premiers pas : neuf dossiers, neuf erreurs corrigées, dix-huit indices et neuf sauvegardes rechargées ; première communauté ouverte à 740 ₵.')
                return report
    finally:api._CAREER,api._WORKSPACE,api.GAMES,api.CONNECTIONS=previous


if __name__=='__main__':
    import sys
    asyncio.run(qualify(Path(sys.argv[1]) if len(sys.argv)>1 else Path('build/validation')))
