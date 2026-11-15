"""Voix des contacts, limites et mémoire à travers les sauvegardes."""
import copy
import json

import pytest

from engine import contracts, dialogue, social
from engine.career import Career
from engine.game_loop import load_all_abilities
from engine.persistence import state_from_dict, state_to_dict


def _career(tmp_path):
    career = Career(tmp_path / 'career.json')
    career.data.update(handle='NightShift', tier=2, reputation=80,
                       completed=['tuto_p0', 'act1_portail'], route='tor')
    social.prepare(career)
    return career


def test_all_contacts_have_their_own_authored_voice():
    contacts = social.content()['contacts']
    for topic in ('greeting', 'thanks', 'personal', 'fatigue', 'trust', 'ransom', 'dispute', 'defense', 'boundary', 'unknown'):
        by_author = {}
        for contact in contacts:
            lines = contact['dialogue'][topic]
            assert lines and all(isinstance(line, str) and line.strip() for line in lines)
            previous = by_author.setdefault(contact['response_author'], lines)
            if topic != 'unknown':
                assert previous == lines  # même voix, sauf relance adaptée au groupe
        assert len({tuple(lines) for lines in by_author.values()}) == len(by_author)


@pytest.mark.parametrize('text, expected', [
    ('Tu me plais mais je ne veux pas de romance', 'boundary'),
    ('Je ne t’aime pas', 'boundary'),
    ('Bonjour, je suis épuisé', 'fatigue'),
    ('Est-ce que tu es une espionne ?', 'suspicion'),
    ('Quel thé tu aimes ?', 'personal'),
    ('Le thème de ce fichier est quelconque', 'unknown'),
    ('pokemon', 'unknown'),
])
def test_intent_does_not_turn_a_refusal_or_a_substring_into_flirting(text, expected):
    assert dialogue.intent(text) == expected


def test_private_exchange_does_not_invent_a_relationship_choice(tmp_path):
    career = _career(tmp_path)
    before = copy.deepcopy(career.data.get('choices', {}))
    social.queue_chat(career, 'chordly', 'Madame_TLS', 'NightShift', 'Tu me plais')
    pending = career.data['social']['pending'][-1]
    assert 'sourire' in pending['text']
    assert career.data.get('choices', {}) == before
    assert 'Madame_TLS' not in career.view()['relationships']
    # Répondre et restaurer ne transforme pas une intention en choix de carrière.
    social.advance(career, 10)
    career.save()
    restored = Career(career.path)
    social.queue_chat(restored, 'chordly', 'Madame_TLS', 'NightShift', 'Tu me plais')
    assert restored.data['social']['pending'][-1]['text'] != pending['text']
    assert restored.data.get('choices', {}) == before
    assert restored.data['social']['dialogue']['Madame_TLS']['replies']['flirt'] == 2


def test_pending_reply_does_not_consume_another_authored_line(tmp_path):
    career = _career(tmp_path)
    social.queue_chat(career, 'chordly', 'Madame_TLS', 'NightShift', 'Tu me plais')
    memory = copy.deepcopy(career.data['social']['dialogue']['Madame_TLS'])
    social.queue_chat(career, 'chordly', 'Madame_TLS', 'NightShift', 'Tu me plais encore')
    assert career.data['social']['dialogue']['Madame_TLS'] == memory
    assert len([p for p in career.data['social']['pending'] if p['target'] == 'Madame_TLS']) == 1


def test_reply_memory_is_separate_for_each_contact(tmp_path):
    career = _career(tmp_path)
    social.queue_chat(career, 'chordly', 'Madame_TLS', 'NightShift', 'Quel café tu aimes ?')
    social.queue_chat(career, 'chordly', 'miette', 'NightShift', 'Quel café tu aimes ?')
    memory = career.data['social']['dialogue']
    assert memory['Madame_TLS'] is not memory['miette']
    assert memory['Madame_TLS']['replies'] == memory['miette']['replies'] == {'personal': 1}
    answers = [p['text'] for p in career.data['social']['pending']]
    assert len(set(answers)) == 2


def test_relation_reply_remembers_the_actual_decision_without_overriding_a_boundary(tmp_path):
    career = _career(tmp_path)
    career.data['completed'].append('mauvaise_adresse')
    career.data.setdefault('choices', {})['litige118'] = 'mediation'
    social.queue_chat(career, 'chordly', 'bytewarden', 'NightShift', 'Tu me fais confiance ?')
    assert 'intervention privée' in career.data['social']['pending'][-1]['text']
    social.advance(career, 10)
    social.queue_chat(career, 'chordly', 'bytewarden', 'NightShift', 'Je ne veux pas reparler du litige')
    assert '118' not in career.data['social']['pending'][-1]['text']


def test_seed_revision_preserves_player_posts_and_received_history(tmp_path):
    career = _career(tmp_path)
    posts = career.data['forum_posts']['welcome']
    posts[0]['text'] = 'Ancienne réplique'
    posts.append(dict(id='player:1', author='NightShift', text='Mon message', minute=0))
    career.data['conversations']['tls-contact'] = dict(id='tls-contact', text='Ancien échange reçu')
    career.data['social']['content_version'] = 1
    before = social._signature(career)
    social.prepare(career)
    assert social._signature(career) != before
    assert posts[0]['text'] == social.content()['threads'][0]['posts'][0]['text']
    assert posts[-1]['text'] == 'Mon message'
    assert career.data['conversations']['tls-contact']['text'] == 'Ancien échange reçu'
    social.prepare(career)
    assert len(posts) == 3


def test_mission_smalltalk_uses_the_client_voice_and_survives_restore():
    abilities = load_all_abilities()
    state = contracts.start_contract(contracts.load_all_contracts()['act1_boutique'], 'NightShift', known_ability_ids=set(abilities))
    contracts.player_message(state, 'chordly', 'Parle-moi de toi')
    assert 'livres' in state.messages[-1].text
    restored = state_from_dict(state_to_dict(state))
    assert restored.tool_data['dialogue'] == state.tool_data['dialogue']
    # Les demandes d'aide de mission restent prioritaires sur la conversation personnelle.
    contracts.player_message(restored, 'chordly', 'Je suis fatigué, donne un indice')
    assert 'livres' not in restored.messages[-1].text
    assert restored.tool_data['dialogue'] == state.tool_data['dialogue']


def test_asking_how_the_character_feels_is_not_a_request_for_the_walkthrough():
    abilities = load_all_abilities()
    state = contracts.start_contract(contracts.load_all_contracts()['intro_terminal'], 'NightShift', known_ability_ids=set(abilities))
    assert not contracts.wants_immediate_answer('Bonjour, comment tu vas ?')
    contracts.player_message(state, 'chordly', 'Bonjour, comment tu vas ?')
    assert 'comptes rendus' in state.messages[-1].text
    assert contracts.wants_immediate_answer('Comment tu vas ? Et comment utiliser SQLmap ?')
    assert contracts.wants_immediate_answer('Comment tu vas ? Donne un indice')


def test_cover_never_exposes_the_author_only_reveal():
    public = json.dumps(social.content(), ensure_ascii=False).casefold()
    for spoiler in ('fsb', 'faire tomber le joueur', 'officier infiltr', 'love interest', 'agent infiltr'):
        assert spoiler not in public
