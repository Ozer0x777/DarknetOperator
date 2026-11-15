"""Choix narratifs : contexte, persistance, branches et publication limitée au client."""
import asyncio
import copy
import json

import httpx
import pytest

import api.main as api
from engine import conversation_scenes as scenes, social
from engine.career import Career


def _career(tmp_path, tls=False):
    career = Career(tmp_path / 'career.json')
    career.data.update(handle='NightShift', tier=2, reputation=80, route='tor', campaign_version=4,
                       completed=['tuto_p0', 'act1_portail'] if tls else [])
    world = social.prepare(career)
    if tls:
        world['published'].append('tls-contact')
        social.prepare(career)
    return career


def _choose(career, scene_id, option):
    scene = next(s for s in scenes.content()['scenes'] if s['id'] == scene_id)
    scenes.choose(career, scene['channel'], scene['peer'], scene_id, option, 'NightShift')


def test_npc_asks_first_and_only_exposes_available_option_texts(tmp_path):
    career = _career(tmp_path)
    world = social.view(career)
    choices = world['scene_choices']
    assert len(choices) == 1 and choices[0]['id'] == 'k0rvid-premiers-pas'
    assert len(choices[0]['options']) == 3
    assert all(set(o) == {'id', 'text'} for o in choices[0]['options'])
    assert set(choices[0]) == {'id', 'peer', 'channel', 'author', 'question', 'options'}
    assert career.data['conversations']['scene:k0rvid-premiers-pas']['sender'] == 'k0rvid'
    assert not career.data['social']['scenes']['choices']
    # Aucun compte à rebours ne choisit une réponse.
    social.advance(career, 10000)
    assert career.data['social']['scenes']['active']['k0rvid'] == 'k0rvid-premiers-pas'
    assert not career.data['social']['scenes']['choices']


def test_response_is_saved_replied_once_and_cannot_be_replaced_by_a_replayed_request(tmp_path):
    career = _career(tmp_path)
    _choose(career, 'k0rvid-premiers-pas', 'autonome')
    assert career.data['social']['bonds']['k0rvid']['working_style'] == 'autonome'
    player = career.data['conversations']['scene:answer:k0rvid-premiers-pas']
    assert player['sender'] == 'NightShift'
    assert len(career.data['social']['pending']) == 1
    snapshot = copy.deepcopy(career.data)
    _choose(career, 'k0rvid-premiers-pas', 'autonome')
    assert career.data == snapshot
    with pytest.raises(ValueError): _choose(career, 'k0rvid-premiers-pas', 'direct')
    career.save()
    restored = Career(career.path)
    social.advance(restored, 2)
    answer = restored.data['social']['scenes']['choices']['k0rvid-premiers-pas']
    assert restored.data['conversations'][answer['reply_id']]['sender'] == 'k0rvid'
    assert restored.data['conversations'][player['id']]['status'] == 'read'
    assert restored.view()['relationships']['k0rvid']['bond']['working_style'] == 'autonome'
    before = len(restored.data['conversations'])
    social.advance(restored, 0)
    assert len(restored.data['conversations']) == before


@pytest.mark.parametrize('channel,peer,scene,option', [
    ('chordly', 'k0rvid', 'invente', 'autonome'),
    ('chordly', 'k0rvid', 'k0rvid-premiers-pas', 'invente'),
    ('telegrid', 'k0rvid', 'k0rvid-premiers-pas', 'autonome'),
    ('chordly', 'miette', 'k0rvid-premiers-pas', 'autonome'),
    ('chordly', 'Madame_TLS', 'tls-premier-lien', 'attirance'),
])
def test_choices_cannot_be_forged_or_used_before_the_contact_is_met(tmp_path, channel, peer, scene, option):
    career = _career(tmp_path)
    with pytest.raises(ValueError): scenes.choose(career, channel, peer, scene, option, 'NightShift')
    assert not career.data['social']['scenes']['choices']
    assert not career.data['social'].get('bonds')


def test_tls_relation_is_an_explicit_choice_and_respects_professional_distance(tmp_path):
    career = _career(tmp_path, tls=True)
    _choose(career, 'tls-premier-lien', 'professionnel')
    relation = career.view()['relationships']['Madame_TLS']
    assert relation['label'] == 'Lien professionnel choisi'
    social.advance(career, 2)
    social.queue_chat(career, 'chordly', 'Madame_TLS', 'NightShift', 'Tu me plais')
    assert 'professionnel' in career.data['social']['pending'][-1]['text']
    assert career.data['social']['bonds']['Madame_TLS']['stance'] == 'professionnel'
    assert not social._conditions_met(career.data, next(e for e in social.content()['events'] if e['id'] == 'tls-rituel'))
    _choose(career, 'k0rvid-premiers-pas', 'accompagne')
    assert career.data['social']['bonds']['Madame_TLS']['stance'] == 'professionnel'


def test_tls_next_question_waits_for_the_reply_and_progression_and_can_change_the_link(tmp_path):
    career = _career(tmp_path, tls=True)
    _choose(career, 'tls-premier-lien', 'amitie')
    career.data['completed'] += ['act2_compte', 'act2_pivot', 'act2_service', 'act2_binome']
    social.prepare(career)
    assert 'Madame_TLS' not in career.data['social']['scenes']['active']
    social.advance(career, 2)
    social.prepare(career)
    for ident, option in [('tls-arc-exposition', 'histoire'), ('tls-arc-desaccord', 'independance'),
                          ('tls-arc-veille', 'refus'), ('tls-arc-limite', 'refus'), ('tls-arc-retour', 'conserver')]:
        _choose(career, ident, option)
        social.advance(career, 2)
        social.prepare(career)
    assert career.data['social']['scenes']['active']['Madame_TLS'] == 'tls-dehors'
    _choose(career, 'tls-dehors', 'musique')
    social.advance(career, 2)
    social.prepare(career)
    _choose(career, 'tls-information', 'refus')
    social.advance(career, 2)
    social.prepare(career)
    _choose(career, 'tls-culture', 'musees')
    social.advance(career, 2)
    social.prepare(career)
    _choose(career, 'tls-lien-confirme', 'attirance')
    bond = career.data['social']['bonds']['Madame_TLS']
    assert {key: bond[key] for key in ('stance','shared_interest','disclosure','cultural_interest')} == {
        'stance': 'attirance', 'shared_interest': 'musique', 'disclosure': 'refus_membres', 'cultural_interest': 'musees'}
    assert bond['arc_resolution'] == 'comparaison_conservee'
    assert career.data.get('choices', {}) == {}  # décisions de mission indépendantes
    social.advance(career, 2)
    social.queue_chat(career, 'chordly', 'Madame_TLS', 'NightShift', 'Parlons de Traverse')
    assert 'garde cette limite' in career.data['social']['pending'][-1]['text']


def test_departed_character_does_not_keep_a_reply_button(tmp_path):
    career = _career(tmp_path, tls=True)
    career.data['completed'].append('act1_partage')
    # Une question d'atelier d'abord, puis hexane.
    _choose(career, 'atelier-miette', 'partager')
    social.advance(career, 2)
    social.prepare(career)
    assert career.data['social']['scenes']['active']['atelier'] == 'atelier-hexane'
    career.data['completed'].append('act1_recommandation')
    social.prepare(career)
    assert career.data['social']['scenes']['active'].get('atelier') != 'atelier-hexane'
    with pytest.raises(ValueError): _choose(career, 'atelier-hexane', 'observer')


def test_tls_cultural_interests_have_specific_replies_without_claiming_system_expertise(tmp_path):
    from engine import dialogue
    career = _career(tmp_path, tls=True)
    tls = next(c for c in social.contacts(career) if c['id'] == 'Madame_TLS')
    assert 'coupes' in dialogue.reply(tls, 'Tu aimes la mode ?', {}, 'NightShift')
    assert 'musées' in dialogue.reply(tls, 'Tu vas dans les musées ?', {}, 'NightShift')
    assert 'CTI' in dialogue.reply(tls, 'Ton métier, c’est quoi ?', {}, 'NightShift')
    assert dialogue.intent('mode 1000') == 'unknown'


def test_every_character_has_a_scene_and_conditions_are_valid():
    from engine.contracts import load_all_contracts
    definitions = scenes.content()['scenes']
    profiles = social.content()['profiles']
    assert {s['author'] for s in definitions} == set(profiles)
    seen = set()
    contacts = {c['id']: c for c in social.content()['contacts']}
    for scene in definitions:
        assert scene['id'] not in seen
        if 'follows' in scene: assert scene['follows'] in seen
        assert scene['channel'] == contacts[scene['peer']]['channel']
        assert len(scene['options']) == 3
        assert len({o['id'] for o in scene['options']}) == 3
        assert set(scene.get('requires_completed', [])) <= set(load_all_contracts())
        for option in scene['options']:
            assert option['text'] and option['reply']
            assert all(isinstance(value, str) for value in option.get('effects', {}).values())
        seen.add(scene['id'])
    public = json.dumps(definitions, ensure_ascii=False).casefold()
    assert 'fsb' not in public and 'faire tomber le joueur' not in public


def test_choice_api_is_transactional_on_disk_failure_and_rejects_changed_options(tmp_path, monkeypatch):
    async def run():
        api._CAREER = _career(tmp_path)
        payload = dict(handle='NightShift', channel='chordly', peer='k0rvid', scene_id='k0rvid-premiers-pas', option_id='direct')
        before = copy.deepcopy(api.career().data)
        saved = Career.save
        monkeypatch.setattr(Career, 'save', lambda self: (_ for _ in ()).throw(OSError('disque plein')))
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api.app), base_url='http://test') as client:
            response = await client.post('/api/social/choice', json=payload)
            assert response.status_code == 503
            assert api.career().data == before
            monkeypatch.setattr(Career, 'save', saved)
            response = await client.post('/api/social/choice', json=payload)
            assert response.status_code == 200
            count = len(api.career().data['conversations'])
            assert (await client.post('/api/social/choice', json=payload)).status_code == 200
            assert len(api.career().data['conversations']) == count
            payload['option_id'] = 'autonome'
            assert (await client.post('/api/social/choice', json=payload)).status_code == 409
            assert Career(api.career().path).data['social']['bonds']['k0rvid']['working_style'] == 'direct'
    asyncio.run(run())
