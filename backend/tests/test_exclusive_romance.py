"""L'attirance est réservée à Madame_TLS ; les autres liens restent platoniques."""
import copy

import pytest

from engine import conversation_scenes as scenes, social
from engine.career import Career


CONTACTS = list({c['response_author']: c for c in social.content()['contacts']
                 if c['response_author'] != 'Madame_TLS'}.values())


def test_only_tls_can_define_a_romantic_choice_or_condition():
    for scene in scenes.content()['scenes']:
        for version in [scene, *scene.get('variants', [])]:
            options = version.get('options', [])
            for option in (options.values() if isinstance(options, dict) else options):
                stance = option.get('effects', {}).get('stance')
                if stance == 'attirance': assert scene['author'] == 'Madame_TLS'
                elif stance is not None: assert stance in scenes.FRIENDLY_STANCES
            for author, fields in version.get('requires_bond', {}).items():
                if 'attirance' in fields.get('stance', []): assert author == 'Madame_TLS'


@pytest.mark.parametrize('contact', CONTACTS, ids=[c['response_author'] for c in CONTACTS])
def test_other_characters_do_not_reciprocate_flirting_or_change_the_link(tmp_path, contact):
    career = Career(tmp_path / 'career.json')
    career.data.update(handle='NightShift', campaign_version=4, tier=3, completed=[
        'tuto_p0', 'act1_partage', 'act1_boutique', 'act1_empreinte', 'mauvaise_adresse',
        'act1_recommandation', 'act2_polkit', 'act2_pivot', 'act2_service'])
    social.prepare(career)
    before = copy.deepcopy(career.data['social'].get('bonds', {}))
    social.queue_chat(career, contact['channel'], contact['id'], 'NightShift', 'Tu me plais')
    pending = career.data['social']['pending'][-1]
    assert pending['text'] == contact['dialogue']['flirt'][0]
    assert career.data['social'].get('bonds', {}) == before
    assert not career.data['social']['scenes']['choices']


@pytest.mark.parametrize('value', ['attirance', 'romance', 'amour'])
def test_even_a_cached_non_tls_option_cannot_create_a_romantic_link(tmp_path, value):
    career = Career(tmp_path / 'career.json')
    career.data.update(handle='NightShift', campaign_version=4)
    world = social.prepare(career)
    scene = world['scenes']['resolved']['k0rvid-premiers-pas']
    scene['options'][0]['effects']['stance'] = value
    before = copy.deepcopy(career.data)
    with pytest.raises(ValueError, match='Seule Madame_TLS'):
        scenes.choose(career, 'chordly', 'k0rvid', scene['id'], scene['options'][0]['id'], 'NightShift')
    assert career.data == before


def test_tls_keeps_the_explicit_attraction_path(tmp_path):
    career = Career(tmp_path / 'career.json')
    career.data.update(handle='NightShift', campaign_version=4, tier=1, completed=['tuto_p0','act1_portail'])
    social.prepare(career)['published'].append('tls-contact')
    social.prepare(career)
    scenes.choose(career, 'chordly', 'Madame_TLS', 'tls-premier-lien', 'attirance', 'NightShift')
    career.save()
    restored = Career(career.path)
    assert restored.data['social']['bonds']['Madame_TLS']['stance'] == 'attirance'
