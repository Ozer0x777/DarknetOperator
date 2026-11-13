"""Solutions équivalentes, preuves à jour, aide et transactions de reprise."""
import asyncio
import copy
import json
from pathlib import Path
import httpx
import pytest
from api import main as api
from engine import contracts, terminal, investigation
from engine.game_loop import GameLoop, load_all_abilities
from engine.career import Career
from engine.win_conditions import objective_met
from engine.persistence import state_to_dict, state_from_dict

ABILITIES=load_all_abilities()


def state(cid):return contracts.start_contract(contracts.load_all_contracts()[cid],'NightShift')


def run(s,line):return terminal.parse(line,s,ABILITIES)


def litige():
    s=state('act1_litige')
    assert run(s,'cat -n ~/mission/litige.txt').ok
    assert run(s,'sqlite3 ~/loot/autre.db<~/mission/litige.sql').ok
    assert run(s,'sqlite3 ~/loot/autre.db "SELECT date, reference, source FROM livraisons ORDER BY date;"').ok
    investigation.observe_forum(s,'act1-litige')
    return s


def test_same_sql_piece_different_filename_and_column_order_is_accepted():
    s=litige()
    answer=investigation.answer(s,'Je choisis la publication du lot 118.')
    assert answer and s.tool_data['decisions']['litige118']=='publication'
    assert s.tool_data['investigation']['steps']==['publication']


def test_ambiguous_question_and_negative_statement_never_choose_for_player():
    s=litige()
    assert 'plusieurs décisions' in investigation.answer(s,'Publier le dossier 118 ou mediation du dossier 118 ?')
    assert not s.tool_data['decisions']
    investigation.answer(s,'Je ne veux pas publier le dossier 118.')
    assert not s.tool_data['decisions']
    investigation.answer(s,'Aucune publication du lot 118.')
    assert not s.tool_data['decisions']
    investigation.answer(s,'Puis-je publier le dossier 118 ?')
    assert not s.tool_data['decisions']
    investigation.answer(s,'Je confirme une médiation du lot 118.')
    assert s.tool_data['decisions']['litige118']=='mediation'
    restored=state_from_dict(state_to_dict(s))
    investigation.answer(restored,'publier dossier 118')
    assert restored.tool_data['decisions']['litige118']=='mediation'


def test_dictionary_and_fake_query_results_cannot_replace_the_provided_piece():
    s=state('act1_echantillon')
    s.terminal_files['/home/operator/faux.sql']="CREATE TABLE clients(date TEXT,n INTEGER);INSERT INTO clients VALUES('2024-03-12',36),('2026-11-05',4);"
    assert run(s,'sqlite3 ~/loot/faux.db < ~/faux.sql').ok
    assert run(s,'sqlite3 ~/loot/faux.db "SELECT date,n FROM clients"').ok
    assert run(s,'cat ~/mission/annonce.txt').ok
    assert 'Il manque' in investigation.answer(s,'Bilan NX-26 : 36 anciennes et 4 recentes.')
    assert not investigation.flags(s)
    assert run(s,'sqlite3 ~/loot/verif.db < ~/mission/echantillon.sql').ok
    assert run(s,'sqlite3 ~/loot/verif.db "SELECT COUNT(1) AS nombre,date FROM clients GROUP BY date;"').ok
    assert investigation.answer(s,'Bilan NX‑26 : 36 anciennes et 4 récentes.')
    assert investigation.flags(s)==['echantillon_verifie']


def test_export_rename_reorder_and_reading_same_artifact_are_verified():
    s=state('act1_boutique')
    assert run(s,'sqlmap -u "http://10.61.4.20/produit?id=1" -D pivoine -T commandes -C reference,id,date,client,montant --dump --batch --output-dir=/home/operator/loot/autre').ok
    cond=next(c for c in s.contract['investigation_steps'][0]['requires'] if c['type']=='table_export')
    assert not objective_met(s,cond)
    path='/home/operator/loot/autre/10.61.4.20/dump/pivoine/commandes.csv'
    assert run(s,'head -n 4 '+path).ok
    assert objective_met(s,cond)
    s.terminal_files[path]=s.terminal_files[path].replace('PV-26','PV-24')
    assert not objective_met(s,cond)


def test_reread_is_required_after_file_replacement():
    s=state('intro_terminal')
    assert run(s,'cat -n ~/mission/preparation.txt').ok
    condition={'type':'file_read','path':'/home/operator/mission/preparation.txt'}
    assert objective_met(s,condition)
    assert run(s,'echo nouveau>~/mission/preparation.txt').ok
    assert not objective_met(s,condition)
    assert run(s,'head ~/mission/preparation.txt').ok
    assert objective_met(s,condition)


def test_curl_output_options_match_redirection_and_keep_failure_target_unchanged():
    s=state('act1_portail')
    result=run(s,'curl --header="Cookie: session=ambre-client" --url="http://10.61.5.20/api/document?id=102" --output=~/loot/preuve.csv')
    assert result.ok and result.output==[]
    original=s.terminal_files['/home/operator/loot/preuve.csv']
    assert run(s,'curl -f -o~/loot/preuve.csv http://10.61.5.20/absent').ok is False
    assert s.terminal_files['/home/operator/loot/preuve.csv']==original
    assert run(s,'cat --number ~/loot/preuve.csv').ok
    investigation.observe_forum(s,'act1-verre')
    assert investigation.answer(s,'Constat VA‑26‑204 pour Orme.')
    assert investigation.flags(s)==['verre_preuve']


def test_act1_hints_are_progressive_and_persist_without_revealing_commands_first():
    s=state('act1_service')
    contracts.player_message(s,'chordly','indice')
    first=s.messages[-1].text
    assert first.startswith('Indice 1/2') and '0x4011d6' not in first and 'offset 72' not in first
    s=state_from_dict(state_to_dict(s))
    contracts.player_message(s,'chordly','indice')
    assert s.messages[-1].text.startswith('Indice 2/2')
    contracts.player_message(s,'chordly','aide complète')
    assert 'checksec --file=' in s.messages[-1].text
    assert 'offset 72' not in s.messages[-1].text  # Le rappel reste dans la phase d’observation.


def test_unknown_command_gives_a_suggestion_without_execution():
    s=state('intro_recon')
    assert not run(s,'namp -sV 10.20.0.0/24').ok
    # La suggestion est une aide syntaxique et ne doit pas découvrir de machine.
    assert 'nmap' in run(s,'nmp -sV 10.20.0.0/24').output[0]
    assert 'srv-fichiers' not in s.discovered
    assert 'invite' in run(s,'└─$ nmap -sV 10.20.0.0/24').output[0]


def test_failed_load_keeps_live_session_and_unsigned_wallet_request(tmp_path,monkeypatch):
    profile=Career(tmp_path/'career.json');profile.data.update(tier=1,money=1000)
    monkeypatch.setattr(api,'_CAREER',profile);monkeypatch.setattr(api,'_WORKSPACE',None)
    monkeypatch.setattr(api,'GAMES',{});monkeypatch.setattr(api,'CONNECTIONS',{})
    async def play():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api.app),base_url='http://test') as client:
            created=(await client.post('/api/games',json={'contract':'tuto_p0','handle':'NightShift'})).json()
            gid=created['id']
            pending=(await client.post('/api/shop/buy',json={'item':'gpu1'})).json()['wallet']['pending']['id']
            for action in ['connect','unlock']:await client.post('/api/wallet/device',json={'action':action})
            slot=(await client.post('/api/saves/write',json={'name':'Avant signature'})).json()
            old=profile.data;save=profile.save
            def fail_commit():
                if profile.data is not old:raise OSError('disque indisponible')
                save()
            monkeypatch.setattr(profile,'save',fail_commit)
            loaded=await client.post('/api/saves/load',json={'slot_id':slot['id'],'confirm':True})
            assert loaded.status_code==503
            assert profile.data is old and gid in api.GAMES and not api.GAMES[gid].paused
            assert profile.wallet_session()['pending']['id']==pending and profile.wallet_session()['unlocked']
            assert profile.data['money']==1000
            monkeypatch.setattr(profile,'save',save)
            during=[]
            class ClosingSocket:
                async def close(self):
                    during.append((await client.post('/api/wallet/device',json={'action':'approve','request_id':pending})).status_code)
                    during.append((await client.post(f'/api/games/{gid}/terminal',json={'line':'pwd'})).status_code)
            api.CONNECTIONS[gid]=[ClosingSocket()]
            assert (await client.post('/api/saves/load',json={'slot_id':slot['id'],'confirm':True})).status_code==200
            assert during==[400,404]
            assert not api.GAMES and not profile.wallet_session()['connected'] and profile.wallet_session()['pending'] is None
            assert (await client.post('/api/wallet/device',json={'action':'approve','request_id':pending})).status_code==400
            assert profile.data['money']==1000 and 'gpu1' not in profile.data['inventory']
    asyncio.run(play())


def test_checkpoint_preserves_queued_action_remote_shell_and_foreground_server(tmp_path,monkeypatch):
    profile=Career(tmp_path/'career.json')
    monkeypatch.setattr(api,'_CAREER',profile);monkeypatch.setattr(api,'_WORKSPACE',None)
    monkeypatch.setattr(api,'GAMES',{});monkeypatch.setattr(api,'CONNECTIONS',{})
    async def play():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api.app),base_url='http://test') as client:
            gid=(await client.post('/api/games',json={'contract':'tuto_p0','handle':'NightShift'})).json()['id']
            async def command(line,console):
                r=await client.post(f'/api/games/{gid}/terminal',json={'line':line,'console_id':console})
                assert r.status_code==200 and r.json()['ok'],r.text
                return r.json()
            await command('gophish --config /opt/gophish/config.json','server')
            await command('ssh m.leroux@10.20.0.21','remote');await command('Password123!','remote')
            await command('powershell','remote');await command("$env:NOTE='conserve'",'remote')
            queued=await command('nmap -sV 10.20.0.0/24','main')
            assert queued['queued']
            old=state_to_dict(api.GAMES[gid].state)
            slot=(await client.post('/api/saves/write',json={'name':'Trois consoles sensibles'})).json()
            assert (await client.post('/api/saves/load',json={'slot_id':slot['id'],'confirm':True})).status_code==200
            resumed=(await client.post('/api/profile/resume',json={})).json();gid=resumed['id']
            current=api.GAMES[gid]
            assert current.paused and state_to_dict(current.state)==old
            assert (await command('echo $env:NOTE','remote'))['output']==['conserve']
            while current.loop.pending():current.loop.tick()
            assert len(current.state.history)==len(old['history'])+1 and current.state.history[-1].success
            assert not current.state.pending_actions and 'srv-fichiers' in current.state.discovered
            assert current.state.tool_services['gophish']['running']
    asyncio.run(play())


def test_choice_slots_restore_the_right_branch_and_replay_does_not_rewrite_it(tmp_path,monkeypatch):
    from engine.campaign import CHAPTERS
    from engine.onboarding import STAGES
    profile=Career(tmp_path/'career.json')
    profile.data.update(campaign_version=3,tier=1,reputation=400,money=500,forum_reputation={'breachboard':400,'exployt':0,'xsx':0},completed=list(dict.fromkeys(STAGES+[row[0] for row in CHAPTERS[:8]])))
    monkeypatch.setattr(api,'_CAREER',profile);monkeypatch.setattr(api,'_WORKSPACE',None)
    monkeypatch.setattr(api,'GAMES',{});monkeypatch.setattr(api,'CONNECTIONS',{})
    async def play():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api.app),base_url='http://test') as client:
            created=await client.post('/api/games',json={'contract':'act1_litige','handle':'NightShift'})
            assert created.status_code==200,created.text
            gid=created.json()['id']
            for line in ['cat ~/mission/litige.txt','sqlite3 ~/loot/choix.db < ~/mission/litige.sql','sqlite3 ~/loot/choix.db "SELECT date,reference,source FROM livraisons;"']:
                r=await client.post(f'/api/games/{gid}/terminal',json={'line':line})
                assert r.status_code==200 and r.json()['ok'],r.text
            assert (await client.get('/api/forum/threads/act1-litige')).status_code==200
            before=(await client.post('/api/saves/write',json={'name':'Avant décision'})).json()['id']
            assert (await client.post('/api/saves/load',json={'slot_id':before,'confirm':True})).status_code==200
            gid=(await client.post('/api/profile/resume',json={})).json()['id']
            ambiguous=await client.post(f'/api/games/{gid}/chat',json={'channel':'chordly','peer':'bytewarden','text':'publier dossier 118 ou mediation dossier 118 ?'})
            assert ambiguous.status_code==200 and not profile.data.get('choices')
            selected=await client.post(f'/api/games/{gid}/chat',json={'channel':'chordly','peer':'bytewarden','text':'Médiation du lot 118.'})
            assert selected.json()['contract']['outcome']=='SUCCESS'
            assert profile.data['choices']['litige118']=='mediation' and profile.data['money']==760
            after=(await client.post('/api/saves/write',json={'name':'Médiation confirmée'})).json()['id']
            assert (await client.post('/api/saves/load',json={'slot_id':after,'confirm':True})).status_code==200
            assert profile.data['choices']['litige118']=='mediation'
            assert 'act1-litige-resolution' in profile.data['forum_messages']
            replay=state('act1_litige');replay.status='ENDED';replay.contract_outcome='SUCCESS';replay.tool_data['decisions']={'litige118':'publication'}
            profile.settle('training-replay',replay)
            assert profile.data['choices']['litige118']=='mediation' and profile.data['money']==760
            assert not any(post.get('id')=='act1-litige-resolution' for post in profile.data['forum_posts']['act1-litige'])
            # Charger explicitement le point antérieur est le moyen de changer de branche.
            assert (await client.post('/api/saves/load',json={'slot_id':before,'confirm':True})).status_code==200
            gid=(await client.post('/api/profile/resume',json={})).json()['id']
            public=await client.post(f'/api/games/{gid}/chat',json={'channel':'chordly','peer':'bytewarden','text':'Publication du lot 118.'})
            assert public.json()['contract']['outcome']=='SUCCESS'
            assert profile.data['choices']['litige118']=='publication' and profile.data['money']==760
            assert 'act1-litige-resolution' not in profile.data.get('forum_messages',{})
            assert sum(post.get('id')=='act1-litige-resolution' for post in profile.data['forum_posts']['act1-litige'])==1
    asyncio.run(play())


def test_direct_transfer_is_valid_without_mandatory_directory_listing():
    s=state('act1_partage');loop=GameLoop(s,ABILITIES)
    command = """smbclient //10.61.2.10/public -N -c 'get courant/NC-26-041.txt "/home/operator/loot/ma copie.txt"'"""
    result=run(s,command)
    assert result.ok
    if result.action:
        loop.submit(result.action)
        while loop.pending():loop.tick()
    assert run(s,'cat -n "~/loot/ma copie.txt"').ok
    assert investigation.answer(s,'Je vous ai livré NC‑26‑041.')
    assert investigation.flags(s)==['partage_livre']


def test_alternative_act1_paths_are_qualified_without_injecting_proofs(tmp_path):
    from mission_review_validation import qualify
    reports=asyncio.run(qualify(tmp_path/'reports'))
    assert len(reports)==2 and all(report['chapters']==10 for report in reports)
    assert all(report['invitation_accepted'] and report['first_purchase'] for report in reports)


def test_sqlite_copy_move_and_overwrite_follow_the_virtual_files():
    s=state('act1_echantillon')
    assert run(s,'sqlite3 ~/loot/source.db < ~/mission/echantillon.sql').ok
    assert run(s,'cp ~/loot/source.db "~/loot/ma copie.db"').ok
    assert run(s,'mv "~/loot/ma copie.db" ~/loot/renommee.db').ok
    assert run(s,'sqlite3 ~/loot/renommee.db "SELECT COUNT(1),date FROM clients GROUP BY date;"').ok
    condition=next(c for c in s.contract['investigation_steps'][0]['requires'] if c['type']=='query_result')
    assert objective_met(s,condition)
    assert run(s,'rm ~/loot/renommee.db').ok
    assert objective_met(s,condition)  # L’observation déjà faite reste une preuve.
    assert run(s,'echo detruit>~/loot/source.db').ok
    assert not run(s,'sqlite3 ~/loot/source.db "SELECT COUNT(*) FROM clients;"').ok


def test_curl_output_stays_on_the_remote_machine_when_run_remotely():
    from engine import console_sessions
    s=state('act1_portail');host=s.hosts['verre-portail']
    with console_sessions.using(s,'remote'):
        console_sessions.enter(s,host,'root','SYSTEM')
        result=run(s,'curl -H "Cookie: session=ambre-client" -o /tmp/remote.csv "http://10.61.5.20/api/document?id=102"')
        assert result.ok
        assert '/tmp/remote.csv' in host.files and '/tmp/remote.csv' not in s.terminal_files
