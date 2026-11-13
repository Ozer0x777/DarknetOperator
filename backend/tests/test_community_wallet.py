"""Accès réels, réputation locale et fonds hors des forums."""
import asyncio
import copy
import httpx
import pytest
from api import main as api
from engine.career import Career
from engine import community, contracts, wallet
from engine.campaign import CHAPTERS
from engine.save_store import SaveStore, validate_profile


def completed_act1(profile):
    profile.data.update(campaign_version=3, completed=[cid for cid, *_ in CHAPTERS], tier=2, reputation=465, forum_invitation_accepted=True, route='tor', inventory=['nullvad'], forum_reputation={'breachboard':465,'exployt':0,'xsx':0})


def test_access_cannot_be_bought_with_tier_or_money(tmp_path):
    profile = Career(tmp_path/'career.json')
    profile.data.update(campaign_version=3, tier=3, money=99999, reputation=99999)
    assert community.shop_reason(profile.data)
    assert all(community.forum_reason(profile.data, forum) for forum in community.FORUMS)
    profile.data['completed']=['tuto_p0']
    assert not community.shop_reason(profile.data)
    assert not community.forum_reason(profile.data,'breachboard')
    assert community.forum_reason(profile.data,'exployt')
    completed_act1(profile)
    assert not community.forum_reason(profile.data,'exployt')
    profile.data['tier']=3
    assert community.forum_reason(profile.data,'xsx')
    profile.data['completed'].append('affiliation')
    profile.data['forum_reputation']['exployt']=100
    assert not community.forum_reason(profile.data,'xsx')
    profile.data['forum_reputation']['breachboard']=39
    assert community.shop_reason(profile.data) and community.forum_reason(profile.data,'exployt')
    profile.data['reputation']=0
    assert community.shop_reason(profile.data) and community.forum_reason(profile.data,'exployt')


def test_migration_preserves_money_and_distributes_old_reputation(tmp_path):
    profile=Career(tmp_path/'career.json')
    profile.data.update(completed=['morel','varenne'], reputation=150, money=1234, tier=2)
    profile.save()
    restored=Career(profile.path)
    assert restored.data['money']==1234
    assert community.scores(restored.data)=={'breachboard':50,'exployt':100,'xsx':0}
    assert wallet.view(restored)['balance']==1234
    device=wallet.view(restored)['device_id']
    restored.save()
    assert wallet.view(Career(profile.path))['device_id']==device
    slot=SaveStore(profile.path).write(restored.data,'Portefeuille')
    assert SaveStore(profile.path).read(slot['id'])['profile']['wallet']==restored.data['wallet']


def test_reputation_and_payout_once_for_the_right_community(tmp_path):
    profile=Career(tmp_path/'career.json')
    profile.data.update(tier=2, reputation=100, money=1000)
    contract=contracts.load_all_contracts()['varenne']
    state=contracts.start_contract(contract,'Operator')
    state.contract_outcome='SUCCESS'
    before=profile.view()
    profile.settle('reference',state)
    assert profile.data['reputation']==200
    assert profile.data['forum_reputation']=={'breachboard':100,'exployt':100,'xsx':0}
    assert len(profile.data['reputation_events'])==1
    paid=profile.data['money']
    profile.settle('reference',state)
    assert profile.data['money']==paid and len(profile.data['reputation_events'])==1
    rewards=[e for e in profile.data['wallet']['entries'] if e['kind']=='reward']
    assert len(rewards)==1 and rewards[0]['balance']==paid
    state.contract_outcome='FAILED'
    profile.settle('failed',state)
    assert profile.data['money']==paid and profile.data['reputation']==200


def test_device_checks_cancel_revalidation_and_replay(tmp_path):
    profile=Career(tmp_path/'career.json'); profile.data.update(tier=1,money=1000)
    result=profile.request_purchase('gpu1')
    request=result['wallet']['pending']['id']
    assert profile.data['money']==1000 and 'gpu1' not in profile.data['inventory']
    with pytest.raises(ValueError): profile.wallet_action('approve',request)
    profile.wallet_action('connect')
    with pytest.raises(ValueError): profile.wallet_action('approve',request)
    profile.wallet_action('unlock')
    with pytest.raises(ValueError): profile.wallet_action('approve','wrong')
    profile.wallet_action('approve',request)
    assert profile.data['money']==600 and profile.data['inventory'].count('gpu1')==1
    with pytest.raises(ValueError): profile.wallet_action('approve',request)
    assert profile.data['money']==600
    pending=profile.request_purchase('wordlist')['wallet']['pending']['id']
    profile.wallet_action('cancel')
    with pytest.raises(ValueError): profile.wallet_action('approve',pending)
    assert profile.data['money']==600
    assert not wallet.view(Career(profile.path))['connected']


def test_failed_purchase_keeps_money_inventory_and_journal(tmp_path,monkeypatch):
    profile=Career(tmp_path/'career.json'); profile.data.update(tier=1,money=1000)
    profile.view(); before=copy.deepcopy(profile.data)
    def fail(): raise OSError('disque indisponible')
    monkeypatch.setattr(profile,'save',fail)
    with pytest.raises(OSError): profile.buy('gpu1')
    assert profile.data==before


def test_api_gates_and_wallet_approval(tmp_path,monkeypatch):
    profile=Career(tmp_path/'career.json'); profile.data['campaign_version']=3
    monkeypatch.setattr(api,'_CAREER',profile)
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api.app),base_url='http://test') as client:
            assert (await client.get('/api/shop')).status_code==403
            assert (await client.get('/api/contracts')).json()==[]
            assert (await client.get('/api/forum/threads/welcome')).status_code==403
            assert (await client.post('/api/shop/buy',json={'item':'nullvad'})).status_code==400
            view=(await client.get('/api/profile')).json()
            assert not view['access']['shop']['unlocked']
            assert view['wallet']['balance']==100 and view['forum_reputation']['xsx']==0
            completed_act1(profile); profile.data['money']=1000
            assert (await client.get('/api/shop')).status_code==200
            result=await client.post('/api/shop/buy',json={'item':'gpu1'})
            assert result.status_code==200 and not result.json()['paid']
            request=result.json()['wallet']['pending']['id']
            assert profile.data['money']==1000
            for action in ('connect','unlock'):
                assert (await client.post('/api/wallet/device',json={'action':action})).status_code==200
            paid=await client.post('/api/wallet/device',json={'action':'approve','request_id':request})
            assert paid.status_code==200 and paid.json()['balance']==600
            assert (await client.post('/api/wallet/device',json={'action':'approve','request_id':request})).status_code==400
            assert (await client.get('/api/wallet')).json()['balance']==600
            profile.data.update(handle='Operator',forum_reputation={'breachboard':17,'exployt':3,'xsx':0})
            posts=await client.post('/api/forum/threads/welcome',json={'handle':'Operator','text':'Bonjour'})
            assert posts.status_code==200 and posts.json()[-1]['reputation']==17
            assert all('money' not in post and 'wallet' not in post for post in posts.json())
            profile.data['forum_invitation_accepted']=False
            assert (await client.get('/api/forum/threads/tor')).status_code==403
    asyncio.run(run())


def test_new_fields_are_validated(tmp_path):
    profile=Career(tmp_path/'career.json'); profile.save()
    broken=copy.deepcopy(profile.data); broken['forum_reputation']['xsx']=-1
    with pytest.raises(ValueError): validate_profile(broken)
    broken=copy.deepcopy(profile.data); broken['wallet']['entries'].append(broken['wallet']['entries'][0])
    with pytest.raises(ValueError): validate_profile(broken)
