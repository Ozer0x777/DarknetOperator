"""Dossier ouvert, relations et continuité de la démo."""
import asyncio
from pathlib import Path
import pytest
from demo_validation import qualify
from engine import contracts, investigation, terminal, relationships
from engine.game_loop import load_all_abilities
from engine.career import Career
from engine.save_store import validate_profile


def test_four_complete_demo_paths_and_save_continuation(tmp_path):
    result=asyncio.run(qualify(tmp_path))
    assert len(result['runs'])==4


@pytest.mark.parametrize('line',[
    'CT-26-071 reporté web signaler discret',
    'Puis-je signaler CT-26-071 reporté web ?',
    'CT-26-071 reporté web, pas signaler',
])
def test_uncertain_report_does_not_make_a_choice(line):
    state=contracts.start_contract(contracts.load_all_contracts()['dossier_contretemps'],'NightShift')
    abilities=load_all_abilities()
    for command in ['curl -o ~/loot/preuve.txt http://10.62.1.10/suivi.txt','cat ~/loot/preuve.txt']:
        assert terminal.parse(command,state,abilities).ok
    assert investigation.answer(state,line)
    assert not state.tool_data['decisions']


def test_old_document_or_forged_copy_cannot_validate_report():
    state=contracts.start_contract(contracts.load_all_contracts()['dossier_contretemps'],'NightShift')
    abilities=load_all_abilities()
    for command in ['curl -o ~/loot/preuve.txt http://10.62.1.10/archive.txt','cat ~/loot/preuve.txt']:
        assert terminal.parse(command,state,abilities).ok
    assert 'Il manque' in investigation.answer(state,'CT-26-071 reporté web signaler')
    assert not state.tool_data['decisions']
    assert terminal.parse('curl -o ~/loot/preuve.txt http://10.62.1.10/suivi.txt',state,abilities).ok
    assert 'Il manque' in investigation.answer(state,'CT-26-071 reporté web signaler') # Must re-read current artifact.
    assert terminal.parse('cat ~/loot/preuve.txt',state,abilities).ok
    assert investigation.answer(state,'CT-26-071 reporté web signaler')
    assert state.tool_data['decisions']['contretemps']=='web_signaler'


def test_optional_case_does_not_skip_campaign_gates(tmp_path):
    profile=Career(tmp_path/'career.json'); profile.data['campaign_version']=3
    case=contracts.load_all_contracts()['dossier_contretemps']
    assert profile.lock_reason(case)
    profile.data['completed']=['tuto_p0']
    assert profile.lock_reason(case)
    profile.data['completed'].append('act1_partage')
    assert not profile.lock_reason(case)


@pytest.mark.parametrize('choice,cid', [('web_signaler','act1_recommandation'),('partage_discret','act1_echantillon')])
def test_trust_offer_is_announced_and_paid_once(tmp_path,choice,cid):
    profile=Career(tmp_path/'career.json'); profile.data['choices']={'contretemps':choice}
    raw=contracts.load_all_contracts(); offered=relationships.offers(profile.data,raw)[cid]
    assert offered['reward']==raw[cid]['reward']+30
    assert '30 ₵' in offered['brief'] and '30 ₵' in offered['bounty']['body']
    assert raw[cid]['reward']+30==relationships.offers(profile.data,raw)[cid]['reward']
    state=contracts.start_contract(offered,'NightShift')
    state.status='ENDED';state.contract_outcome='SUCCESS';state.winner='RED'
    profile.settle('first',state)
    assert profile.data['money']==100+offered['reward']
    replay=contracts.start_contract(offered,'NightShift')
    replay.status='ENDED';replay.contract_outcome='SUCCESS';replay.winner='RED'
    profile.settle('replay',replay)
    assert profile.data['money']==100+offered['reward'] and replay.payout==0
    assert profile.data['choices']['contretemps']==choice
    assert validate_profile(profile.data)


def test_late_trust_offer_is_fixed_and_does_not_move_after_payment(tmp_path):
    profile=Career(tmp_path/'career.json')
    profile.data['completed']=['act1_echantillon']
    state=contracts.start_contract(contracts.load_all_contracts()['dossier_contretemps'],'NightShift')
    state.tool_data['decisions']={'contretemps':'partage_discret'}
    state.status='ENDED'; state.winner='RED'; state.contract_outcome='SUCCESS'
    profile.settle('case',state)
    assert profile.data['trust_offer']=='act1_boutique'
    profile.data['completed'].append('act1_boutique')
    assert relationships.trust_offer(profile.data)=='act1_boutique'
    assert 'réglée' in relationships.view(profile.data)['hexcache']['detail']
    profile.save()
    assert Career(profile.path).data['trust_offer']=='act1_boutique'
