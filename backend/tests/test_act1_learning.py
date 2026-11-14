"""Aide liée aux preuves, progression et réactions de carrière persistantes."""
import asyncio
import copy
import json
from pathlib import Path
import httpx
import pytest
from api import main as api
from engine import contracts, investigation, terminal, relationships
from engine.game_loop import load_all_abilities
from engine.career import Career
from engine.persistence import state_to_dict, state_from_dict

ABILITIES=load_all_abilities()
def state(cid):return contracts.start_contract(contracts.load_all_contracts()[cid],'NightShift')
def run(s,line):
    result=terminal.parse(line,s,ABILITIES)
    assert result.ok,(line,result.output)
    return result


def test_sql_help_stays_on_current_evidence_and_resumes_per_phase():
    s=state('act1_echantillon')
    assert '36' not in s.contract['brief'] and '4 recentes' not in s.contract['brief']
    first=investigation.help_text(s)
    assert 'vendeur' in first and first.startswith('Indice 1/2')
    run(s,'cat ~/mission/annonce.txt')
    next_phase=investigation.help_text(s)
    assert next_phase.startswith('Indice 1/2') and 'Regroupe' in next_phase
    s=state_from_dict(state_to_dict(s))
    assert investigation.help_text(s).startswith('Indice 2/2')
    assert 'SELECT date, COUNT(*)' in investigation.help_text(s,detailed=True)
    run(s,'sqlite3 ~/loot/libre.db < ~/mission/echantillon.sql')
    run(s,'sqlite3 ~/loot/libre.db "SELECT date,COUNT(*) FROM clients GROUP BY date;"')
    ready=investigation.help_text(s)
    assert 'preuves qu’il faut' in ready and 'compte rendu' in ready
    assert not investigation.flags(s)  # L’aide ne soumet rien à la place du joueur.


def test_service_help_unlocks_parameters_after_observation_and_retains_local_console():
    s=state('act1_service')
    assert 'offset 72' not in investigation.help_text(s,detailed=True)
    investigation.observe_forum(s,'act1-ticketd')
    run(s,'checksec --file=/home/operator/lab/ticketd')
    run(s,'gdb -q /home/operator/lab/ticketd -ex "info functions" -ex quit')
    assert investigation.help_text(s).startswith('Indice 1/2')
    assert 'offset 72' in investigation.help_text(s,detailed=True)
    run(s,'python3 ~/lab/ticketd.py --host 10.61.7.30 --port 5000 --offset 72 --ret 0x4011d6')
    assert 'database.ini' in investigation.help_text(s,detailed=True)
    run(s,'cat /etc/ticketd/database.ini')
    detail=investigation.help_text(s,detailed=True)
    assert 'Dans Kali' in detail and 'mysql -h' in detail and 'script' not in detail
    restored=state_from_dict(state_to_dict(s))
    assert 'mysql -h' in investigation.help_text(restored,detailed=True)
    assert restored.terminal_host=='ticket-app'


def test_open_investigation_does_not_skip_unconfirmed_attribution():
    s=state('mauvaise_adresse')
    investigation.observe_forum(s,'aquila-portail')
    # Même un indice partiel de la future cible ne doit pas faire sauter l’attribution.
    assert 'identité de la société' in investigation.help_text(s)
    run(s,'curl http://10.48.1.20/mentions.txt')
    investigation.observe_forum(s,'aquila-homonymes')
    investigation.answer(s,'Aquila Conseil et Aquila Fret sont distinctes : AF-26-118')
    assert 'adresse actuelle' in investigation.help_text(s)


@pytest.mark.parametrize('choice,expected',[('publication','public'),('mediation','privé')])
def test_choice_changes_next_brief_and_relation_but_not_reward(choice,expected):
    raw=contracts.load_all_contracts()
    data={'completed':['mauvaise_adresse','act1_litige'],'choices':{'litige118':choice}}
    first=relationships.offers(data,raw)
    second=relationships.offers(data,raw)
    cid='act1_recommandation'
    assert first[cid]==second[cid]
    assert expected in first[cid]['brief']
    assert first[cid]['reward']==raw[cid]['reward']
    assert 'nullroute' in relationships.view(data)
    assert choice not in raw[cid]['brief']


def test_relationship_feedback_is_not_duplicated_or_rewritten_by_replay(tmp_path):
    profile=Career(tmp_path/'career.json');profile.data['campaign_version']=3
    profile.data['completed']=['tuto_p0','act1_partage','act1_echantillon','act1_boutique','act1_portail','act1_empreinte','act1_service','mauvaise_adresse']
    s=state('act1_litige');s.tool_data['decisions']={'litige118':'mediation'}
    s.status='ENDED';s.winner='RED';s.contract_outcome='SUCCESS'
    profile.settle('one',s)
    original=copy.deepcopy(profile.data['conversations']['relationship:act1_litige'])
    balance=profile.data['money']
    replay=state('act1_litige');replay.tool_data['decisions']={'litige118':'publication'}
    replay.status='ENDED';replay.winner='RED';replay.contract_outcome='SUCCESS'
    profile.settle('two',replay)
    assert profile.data['conversations']['relationship:act1_litige']==original
    assert profile.data['money']==balance
    loaded=Career(profile.path)
    assert loaded.view()['relationships']['bytewarden']['label']=='Médiation de confiance'
    assert loaded.data['choices']['litige118']=='mediation'


@pytest.mark.parametrize('fault',['duplicate','unknown_condition','empty_hints'])
def test_bad_authored_help_is_rejected(tmp_path,fault):
    d=contracts.load_all_contracts()['act1_service']
    phases=d['investigation_steps'][0]['help_stages']
    if fault=='duplicate':phases.append(copy.deepcopy(phases[0]))
    elif fault=='unknown_condition':phases[0]['requires']=[{'type':'invented'}]
    else:phases[0]['hints']=[]
    file=tmp_path/'bad.json';file.write_text(json.dumps(d))
    with pytest.raises(contracts.ContractValidationError):contracts.load_contract(file)


def test_old_active_save_receives_new_help_without_losing_notes(tmp_path):
    async def play():
        previous=api._CAREER,api._WORKSPACE,api.GAMES,api.CONNECTIONS
        try:
            profile=Career(tmp_path/'career.json')
            api._CAREER=profile;api._WORKSPACE=None;api.GAMES={};api.CONNECTIONS={}
            s=state('act1_service')
            s.contract['terminal_revision']-=1
            s.contract['investigation_steps'][0].pop('help_stages')
            del s.terminal_files['/home/operator/mission/reperes.txt']
            s.terminal_files['/home/operator/mes-notes.txt']='Mes observations'
            run(s,'checksec --file=/home/operator/lab/ticketd')
            profile.checkpoint(s)
            async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api.app),base_url='http://test') as client:
                result=await client.post('/api/profile/resume',json={})
                assert result.status_code==200,result.text
                resumed=api.GAMES[result.json()['id']].state
                assert resumed.contract['investigation_steps'][0]['help_stages']
                assert resumed.terminal_files['/home/operator/mes-notes.txt']=='Mes observations'
                assert 'NX' in resumed.terminal_files['/home/operator/mission/reperes.txt']
                assert 'lab:checksec' in resumed.tool_data['facts']
        finally: api._CAREER,api._WORKSPACE,api.GAMES,api.CONNECTIONS=previous
    asyncio.run(play())


def test_direct_valid_delivery_does_not_require_optional_help_observations():
    s=state('act1_partage')
    run(s,'smbclient //10.61.2.10/public -N -c "get courant/NC-26-041.txt /home/operator/loot/ma-copie.txt"')
    run(s,'cat ~/loot/ma-copie.txt')
    assert 'preuves qu’il faut' in investigation.help_text(s)
    assert 'smb:list:nacre-fichiers:public' not in s.tool_data.get('facts',{})
    investigation.answer(s,'livraison NC-26-041')
    assert investigation.flags(s)==['partage_livre']


def test_ready_litige_help_keeps_both_decisions_open():
    s=state('act1_litige')
    run(s,'cat ~/mission/litige.txt')
    run(s,'sqlite3 ~/loot/litige.db < ~/mission/litige.sql')
    run(s,'sqlite3 ~/loot/litige.db "SELECT source,reference,date FROM livraisons;"')
    investigation.observe_forum(s,'act1-litige')
    message=investigation.help_text(s)
    assert 'publier dossier 118' in message and 'mediation dossier 118' in message
    assert not s.tool_data.get('decisions')
