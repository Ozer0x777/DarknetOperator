"""Rapport de qualification : deux variantes et une défaite reprise par contrat.

Le même corpus alimente le rejeu Godot des commandes et des états de l'API.
Ce programme utilise uniquement des profils temporaires.
"""
from __future__ import annotations
import asyncio
import json
import tempfile
from pathlib import Path
import httpx
from api import main as api
from engine.career import Career
from validation import play_campaign, CONTRACT_IDS


async def failure_paths() -> list[dict]:
    saved = (api._CAREER, api._WORKSPACE, api.GAMES.copy())
    records = []
    try:
        with tempfile.TemporaryDirectory(prefix='redteam-failures-') as directory:
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api.app),base_url='http://test') as client:
                for cid in CONTRACT_IDS:
                    api._CAREER = Career(Path(directory)/f'{cid}.json')
                    api._WORKSPACE = None
                    api.GAMES.clear()
                    api.career().data.update(tier=3,reputation=1000,money=10000,inventory=['nullvad','vesper','relay'],route='relay' if cid=='grand_compte' else ('tor' if cid in {'varenne','affiliation'} else 'nullvad'))
                    result = await client.post('/api/games',json={'contract':cid,'handle':'Operator','rng_seed':0})
                    assert result.status_code == 200,(cid,result.text)
                    game=result.json();gid=game['id']
                    ip=api.GAMES[gid].state.hosts['poste-accueil'].ip
                    if api.GAMES[gid].state.terminal_host:
                        await client.post(f'/api/games/{gid}/terminal',json={'line':'exit'})
                    queued=await client.post(f'/api/games/{gid}/terminal',json={'line':f'nmap -sV {ip}'})
                    assert queued.json()['queued']
                    assert (await client.post(f'/api/games/{gid}/pause',json={})).status_code==200
                    api.GAMES.pop(gid)
                    restored=(await client.post('/api/profile/resume',json={})).json()
                    gid=restored['id'];session=api.GAMES[gid]
                    assert session.paused and session.loop._queue
                    await client.post(f'/api/games/{gid}/resume',json={})
                    # Le délai est explicitement écoulé. Aucun objectif ni résultat n'est injecté.
                    while session.state.status=='RUNNING':session.loop.tick()
                    api.career().settle(gid,session.state)
                    failed=(await client.get(f'/api/games/{gid}')).json()
                    assert failed['winner']=='BLUE' and failed['end_reason']=='timeout'
                    assert failed['contract']['outcome']=='FAILED' and failed['contract']['payout']==0
                    assert failed.get('debrief')
                    records.append({'contract_id':cid,'initial':game['state'],'resumed':restored['state'],'failure':failed,'profile':api.career().view(),'contracts':(await client.get('/api/contracts')).json()})
    finally:
        api._CAREER,api._WORKSPACE=saved[:2]
        api.GAMES.clear();api.GAMES.update(saved[2])
    return records


async def qualify(output: Path):
    replays=[]
    standard=await play_campaign(variant='standard',replays=replays)
    alternative=await play_campaign(variant='alternative',replays=replays)
    failures=await failure_paths()
    report={'scope':'API/CLI et corpus pour rejeu Godot ; aucune session graphique humaine ni exécution des outils réels',
            'success_paths':12,'failure_paths':len(failures),'resumes':sum(s['resumes'] for r in (standard,alternative) for s in r['scenarios'])+len(failures),
            'campaigns':[standard,alternative],'failures':[{'contract_id':f['contract_id'],'reason':f['failure']['end_reason'],'payout':0} for f in failures]}
    output.mkdir(parents=True,exist_ok=True)
    (output/'qualification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n', encoding='utf-8')
    (output/'ui-replays.json').write_text(json.dumps({'successes':replays,'failures':failures},ensure_ascii=False)+'\n', encoding='utf-8')
    print(f"Qualification : {report['success_paths']} parcours réussis, {report['failure_paths']} défaites, {report['resumes']} reprises")
    return report


if __name__=='__main__':
    import sys
    asyncio.run(qualify(Path(sys.argv[1]) if len(sys.argv)>1 else Path('build/validation')))
