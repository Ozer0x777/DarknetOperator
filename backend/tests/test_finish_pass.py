"""Régressions de la passe de finition : orientation, canaux et budget réel."""
import copy
from engine.career import Career, CATALOG
from engine import contracts, curriculum, economy, social, journey, community
from engine.campaign import CHAPTERS
from engine.act2 import CHAPTERS as ACT2
from engine.onboarding import CURRENT_STAGES


def ready(tmp_path):
    p=Career(tmp_path/'career.json')
    p.data.update(campaign_version=4,tier=2,money=425,reputation=500,
        forum_reputation={'breachboard':500,'exployt':0,'xsx':0},
        completed=list(dict.fromkeys(CURRENT_STAGES+[row[0] for row in CHAPTERS])),
        inventory=['nullvad'],route='tor',forum_invitation_accepted=True)
    return p


def test_current_reserve_follows_next_act2_route_and_covered_retry(tmp_path):
    p=ready(tmp_path)
    assert economy.reserve(p.data)==50
    p.data['route']='relay'
    assert economy.reserve(p.data)==300
    p.data['inventory'].append('relay')
    assert economy.reserve(p.data)==0
    p.data['inventory'].remove('relay');p.data['route']='tor'
    assert 'Garde 50' in next(i for i in economy.catalog(p.data,CATALOG) if i['id']=='gpu1')['reason']
    p.data['route_passes']=['act2_passation:vpn']
    assert economy.reserve(p.data)==0
    p.data['completed'].append('act2_passation')
    assert economy.reserve(p.data)==50
    p.data['route_passes'].append('act2_compte:vpn')
    assert economy.reserve(p.data)==0
    p.data['completed']+= [cid for cid,*_ in ACT2 if cid not in p.data['completed']]
    assert economy.reserve(p.data)==0


def test_migrated_legacy_chain_keeps_its_relay_reserve(tmp_path):
    p=ready(tmp_path);p.data.update(tier=3,completed=p.data['completed']+['varenne','affiliation'])
    assert economy.reserve(p.data)==300
    p.data['act2_started']=True
    assert economy.reserve(p.data)==50


def test_offers_include_channel_and_explain_other_active_mission(tmp_path):
    p=ready(tmp_path)
    definitions=curriculum.definitions(p.data,contracts.load_all_contracts())
    first=definitions['act2_passation']
    p.data['active']={'status':'RUNNING','contract':copy.deepcopy(first)}
    world=social.view(p,definitions)
    active=next(o for o in world['offers'] if o['id']=='act2_passation')
    assert active['channel']=='telegrid' and active['active'] and not active['reason']
    others=[o for o in world['offers'] if o['id']!='act2_passation']
    assert others and all(o['reason'] and o['channel'] in {'chordly','telegrid','sessyon'} for o in others)
    assert journey.view(p.data)['title'].endswith(first['bounty']['title'])
    assert 'Indice' in journey.view(p.data)['detail']


def test_contact_does_not_leak_into_another_messenger(tmp_path):
    p=ready(tmp_path);p.data['tier']=1
    p.data['conversations']={'private':social._message('private','unique-peer','chordly','unique-peer','Test',0)}
    template=copy.deepcopy(contracts.load_all_contracts()['act2_passation'])
    template['private_offer']=False
    template['client']['handle']='unique-peer'
    world=social.view(p,{'test':template})
    assert not any(c['id']=='unique-peer' and c['channel']=='telegrid' for c in world['contacts'])


def test_cendre_intro_is_gated_stable_and_survives_reload(tmp_path):
    p=ready(tmp_path);p.data['forum_invitation_accepted']=False
    social.prepare(p)
    assert 'act2:introduction' not in p.data['conversations']
    p.data['forum_invitation_accepted']=True
    social.prepare(p)
    first=copy.deepcopy(p.data['conversations']['act2:introduction'])
    assert first['channel']=='telegrid' and first['peer']=='cendre'
    assert 'ColdVault' in first['text'] and 'séparément' in first['text']
    social.advance(p,5);p.save();reloaded=Career(p.path);social.prepare(reloaded)
    assert reloaded.data['conversations']['act2:introduction']==first
    assert community.scores(reloaded.data)=={'breachboard':500,'exployt':0,'xsx':0}
    assert reloaded.data['money']==425


def test_current_ravelle_all_player_text_matches_public_source(tmp_path):
    p=ready(tmp_path)
    d=curriculum.definitions(p.data,contracts.load_all_contracts())['tuto_p0']
    text=' '.join([d['bounty']['title'],d['brief'],d['failure_message'],*d['hints'],*d['debrief_hints']]).lower()
    assert not any(token in text for token in ['mimikatz','psexec','10.20.0.','accès serveur de fichiers','objectif est un accès administrateur'])
    assert 'mandat' in d['bounty']['title'] and 'date' in ' '.join(d['debrief_hints'])


def test_future_generated_offer_refreshes_without_overwriting_private_history(tmp_path):
    p=ready(tmp_path)
    p.data['completed']=[cid for cid in p.data['completed'] if cid not in {'act1_service','mauvaise_adresse','act1_litige','act1_recommandation'}]
    p.data['forum_invitation_accepted']=False;p.data['tier']=1
    p.data['conversations']={
        'offer:act1_service':social._message('offer:act1_service','nullroute','chordly','nullroute','Ancienne proposition de binaire.',12),
        'player:note':social._message('player:note','nullroute','chordly','operator','Ma note personnelle.',13)}
    definitions=curriculum.definitions(p.data,contracts.load_all_contracts())
    world=social.view(p,definitions)
    assert p.data['conversations']['offer:act1_service']['text']==definitions['act1_service']['intro']
    assert p.data['conversations']['offer:act1_service']['minute']==12
    assert p.data['conversations']['player:note']['text']=='Ma note personnelle.'
    assert any(o['id']=='act1_service' for o in world['offers'])
