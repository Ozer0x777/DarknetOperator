"""Parcours, conséquences et arbitrages économiques persistants."""
import copy
import pytest
from engine.career import Career, CATALOG
from engine import contracts, economy, journey, hashcat_model
from engine.campaign import CHAPTERS
from engine.onboarding import STAGES
from engine.save_store import SaveStore, validate_profile
from engine.game_loop import GameLoop, QueuedAction
from engine.ntlm import nt_hash


def advanced(tmp_path, money=2000):
    profile = Career(tmp_path/'career.json')
    profile.data.update(campaign_version=3, completed=list(dict.fromkeys(STAGES+[row[0] for row in CHAPTERS])),
                        tier=2, reputation=465, forum_reputation={'breachboard':465,'exployt':0,'xsx':0},
                        forum_invitation_accepted=True, inventory=['nullvad'], route='tor', money=money)
    return profile


def finish(profile, cid, ident, success=True):
    state = contracts.start_contract(contracts.load_all_contracts()[cid], 'NightShift')
    state.status='ENDED'; state.winner='RED' if success else 'BLUE'
    state.contract_outcome='SUCCESS' if success else 'FAILED'
    state.conversation_id=ident
    profile.settle(ident,state)
    return state


def test_all_rewards_and_bonus_are_one_time_even_with_new_game_id(tmp_path):
    profile=Career(tmp_path/'career.json')
    profile.data['campaign_version']=3
    first=finish(profile,'morel','first')
    money=profile.data['money']; reputation=profile.data['reputation']
    replay=finish(profile,'morel','replay')
    assert first.payout>0 and replay.payout==0
    assert profile.data['money']==money and profile.data['reputation']==reputation
    assert len([e for e in profile.data['wallet']['entries'] if e['kind']=='reward'])==1
    assert any('aucune nouvelle prime' in message['text'] for message in profile.data['conversations'].values())


def test_failed_vpn_route_is_covered_after_reload_and_never_debits_twice(tmp_path):
    profile=advanced(tmp_path,50)
    definition=contracts.load_all_contracts()['varenne']
    first=contracts.start_contract(definition,'NightShift')
    profile.prepare(definition,first)
    assert profile.data['money']==0 and profile.data['route_passes']==['varenne:vpn']
    first.status='ENDED';first.winner='BLUE';first.contract_outcome='FAILED'
    profile.settle('failed',first)
    assert profile.data['forum_reputation']['exployt']==0
    profile=Career(profile.path)
    second=contracts.start_contract(definition,'NightShift')
    profile.prepare(definition,second)
    assert profile.data['money']==0
    assert len([entry for entry in profile.data['wallet']['entries'] if entry['kind']=='route'])==1
    second.status='ENDED';second.winner='RED';second.contract_outcome='SUCCESS'
    profile.settle('recovered',second)
    assert profile.data['money']==1000 and profile.data['forum_reputation']['exployt']==100
    events=profile.data['career_events']
    assert [event['outcome'] for event in events]==['FAILED','SUCCESS']
    slot=SaveStore(profile.path).write(profile.data,'Après reprise')
    restored=SaveStore(profile.path).read(slot['id'])['profile']
    assert restored['career_events']==events and restored['route_passes']==['varenne:vpn']


def test_relay_failure_does_not_require_buying_another_pass(tmp_path):
    profile=advanced(tmp_path,0)
    profile.data.update(tier=3, reputation=665, completed=profile.data['completed']+['affiliation'], inventory=['nullvad','vesper','relay'],route='relay')
    profile.data['forum_reputation']['exployt']=100
    definition=contracts.load_all_contracts()['grand_compte']
    first=contracts.start_contract(definition,'NightShift');profile.prepare(definition,first)
    assert 'relay' not in profile.data['inventory']
    first.status='ENDED';first.contract_outcome='FAILED';profile.settle('relay-fail',first)
    profile=Career(profile.path)
    second=contracts.start_contract(definition,'NightShift');profile.prepare(definition,second)
    assert profile.data['money']==0 and profile.data['route_passes']==['grand_compte:relay']
    assert 'relay' not in profile.data['inventory']


def test_gpu_upgrade_quote_reserve_and_confirmation_price_revalidation(tmp_path):
    profile=advanced(tmp_path,2000)
    profile.data['inventory'].append('gpu1')
    quote=profile.request_purchase('gpu2')['wallet']['pending']
    assert quote['amount']==800
    profile.wallet_action('connect');profile.wallet_action('unlock')
    profile.wallet_action('approve',quote['id'])
    assert profile.data['money']==1200 and 'gpu2' in profile.data['inventory']
    profile.data['inventory'].remove('gpu1')
    with pytest.raises(ValueError,match='supérieur'): profile.purchase_item('gpu1')
    # Réserver les frais d'une route imposée, sans bloquer son activation gratuite.
    other=advanced(tmp_path/'reserve',425)
    with pytest.raises(ValueError,match='Garde 50'): other.request_purchase('gpu1')
    assert next(item for item in economy.catalog(other.data,CATALOG) if item['id']=='gpu1')['reason'].startswith('Garde 50')
    assert other.request_purchase('vesper')['paid']
    quoted=profile.request_purchase('wordlist')['wallet']['pending']
    profile.data['inventory'].append('wordlist')
    with pytest.raises(ValueError,match='déjà acquis'):profile.wallet_action('approve',quoted['id'])
    assert profile.data['money']==1200
    changed=advanced(tmp_path/'changed',2000)
    changed.data['inventory'].append('gpu1')
    pending=changed.request_purchase('gpu2')['wallet']['pending']
    changed.data['inventory'].remove('gpu1')
    changed.wallet_action('connect');changed.wallet_action('unlock')
    with pytest.raises(ValueError,match='prix a changé'): changed.wallet_action('approve',pending['id'])
    assert changed.data['money']==2000 and 'gpu2' not in changed.data['inventory']


def test_each_gpu_and_premium_dictionary_has_an_actual_effect():
    def delay(inventory):
        state=contracts.start_contract(contracts.load_all_contracts()['intro_hash'],'NightShift')
        state.inventory=inventory
        loop=GameLoop(state)
        action=QueuedAction('red','red.crack_hash',next(iter(state.hosts)),params={'wordlist':'/home/operator/wordlist.txt'})
        loop.submit(action)
        return action.ready_tick-state.tick
    assert [delay([]),delay(['gpu1']),delay(['gpu2']),delay(['gpu3'])]==[9,5,3,2]
    assert delay(['wordlist'])==7 and delay(['gpu3','wordlist'])==1
    state=contracts.start_contract(contracts.load_all_contracts()['intro_hash'],'NightShift')
    state.inventory=['wordlist'];hashcat_model.prepare(state)
    free=state.terminal_files['/usr/share/wordlists/rockyou.txt'].splitlines()
    premium=state.terminal_files['/home/operator/wordlist.txt'].splitlines()
    assert set(free)<set(premium) and 'Atelier2026!' in premium
    state.terminal_files['/tmp/test.ntlm']=nt_hash('Atelier2026!')
    # Aucun hôte découvert : résolution locale du même dictionnaire fourni.
    state.discovered.clear();state.loot.clear()
    assert not hashcat_model.parse(['-m','1000','/tmp/test.ntlm','/usr/share/wordlists/rockyou.txt'],state).ok
    assert hashcat_model.parse(['-m','1000','/tmp/test.ntlm','/home/operator/wordlist.txt'],state).ok


def test_failures_are_persistent_private_and_idempotent(tmp_path):
    profile=advanced(tmp_path)
    before=profile.data['money']; reputation=copy.deepcopy(profile.data['forum_reputation'])
    first=finish(profile,'act1_partage','failed1',False)
    profile.settle('failed1',first)
    finish(profile,'act1_partage','failed2',False)
    assert len(profile.data['career_events'])==2
    assert profile.data['money']==before and profile.data['forum_reputation']==reputation
    assert any('Plusieurs tentatives' in message['text'] for message in profile.data['conversations'].values())
    assert not any(post.get('id','').startswith('outcome:') for posts in profile.data['forum_posts'].values() for post in posts)
    loaded=Career(profile.path)
    assert loaded.data['career_events']==profile.data['career_events']
    bad=copy.deepcopy(loaded.data);bad['route_passes']=['varenne:vpn','varenne:vpn']
    with pytest.raises(ValueError): validate_profile(bad)


def test_journey_does_not_skip_first_mission_or_force_a_purchase(tmp_path):
    profile=Career(tmp_path/'career.json');profile.data['campaign_version']=3
    assert journey.view(profile.data)['contract_id']=='intro_terminal'
    profile.data['completed']=STAGES[:-1]
    assert journey.view(profile.data)['contract_id']=='tuto_p0'
    profile.data['completed']=STAGES
    assert journey.view(profile.data)['contract_id']=='act1_partage'
    assert 'facultatifs' in journey.view(profile.data)['detail']


def test_next_piste_matches_the_actual_offer_channel(tmp_path):
    profile=Career(tmp_path/'career.json');profile.data['campaign_version']=3
    profile.data['completed']=STAGES.copy()
    definitions=contracts.load_all_contracts()
    for cid, *_ in CHAPTERS[1:]:
        step=journey.view(profile.data)
        assert step['contract_id']==cid
        expected='BreachBoard' if definitions[cid].get('offer_channel')=='forum' or cid=='act1_partage' else 'Chordly'
        assert step['app']==expected
        profile.data['completed'].append(cid)
    assert journey.view(profile.data)['app']=='BreachBoard'


def test_bounty_discloses_affiliation_before_acceptance():
    definitions=contracts.load_all_contracts()
    assert contracts.bounty_view(definitions['affiliation'])['affiliation']
    assert not contracts.bounty_view(definitions['grand_compte'])['affiliation']


def test_relay_reserve_is_protected_before_the_affiliation(tmp_path):
    profile=advanced(tmp_path,700)
    profile.data['completed'].append('varenne')
    assert profile.data['tier']==2 and economy.reserve(profile.data)==300
    with pytest.raises(ValueError,match='Garde 300'): profile.request_purchase('glasswing')
    assert profile.request_purchase('vesper')['paid']
    assert profile.data['money']==700
    profile.data['completed'].remove('varenne')
    profile.data['completed'].append('affiliation')
    profile.data['tier']=3
    assert economy.reserve(profile.data)==300
