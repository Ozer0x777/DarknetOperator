"""Messages d'histoire du monde social : ils suivent la progression et les choix du joueur."""
from fnmatch import fnmatchcase

from engine import social
from engine.career import Career


def _career(tmp_path, completed=(), choices=None, tier=1, minute=0):
    career = Career(tmp_path / 'career.json')
    career.data.update(handle='NightShift', tier=tier, reputation=60, completed=list(completed), choices=dict(choices or {}))
    social.prepare(career)['minute'] = minute
    return career


def _texts(career):
    chats = [m['text'] for m in career.data.get('conversations', {}).values()]
    posts = [p['text'] for posts in career.data.get('forum_posts', {}).values() for p in posts]
    return chats + posts


def _published(career): return set(career.data['social']['published'])


def _wait(career, minutes):
    """Comme en jeu, l'horloge avance par petits pas : un message d'histoire s'arme à un pas et paraît à un suivant."""
    for _ in range(minutes // 10): social.advance(career, 10)


def test_story_message_waits_for_the_dossier_then_for_its_delay(tmp_path):
    career = _career(tmp_path, ['tuto_p0'])
    _wait(career, 3000)  # une longue attente ne suffit pas : il faut avoir terminé le dossier
    assert 'tls-contact' not in _published(career) and 'Madame_TLS' not in {c['id'] for c in social.contacts(career)}
    career.data['completed'].append('act1_portail')
    social.advance(career, 1)
    assert 'tls-contact' not in _published(career)  # le délai part de la fin du dossier, pas du début de la carrière
    _wait(career, 24 * 60)  # elle ne répond que le matin
    message = career.data['conversations']['tls-contact']
    assert message['peer'] == 'Madame_TLS' and 'NightShift' in message['text'] and '{handle}' not in message['text']
    _wait(career, 24 * 60)
    assert sum(m.get('id') == 'tls-contact' for m in career.data['conversations'].values()) == 1


def test_choice_reaction_matches_the_decision_and_never_both(tmp_path):
    for choice, expected, other in (('web_signaler', 'choix-contretemps-signaler', 'choix-contretemps-discret'),
                                    ('partage_discret', 'choix-contretemps-discret', 'choix-contretemps-signaler')):
        career = _career(tmp_path / choice, ['tuto_p0', 'dossier_contretemps'], {'contretemps': choice})
        _wait(career, 24 * 60)
        assert not {expected, other} & _published(career)  # la réaction arrive plus tard, après « Derrière la boutique »
        career.data['completed'].append('act1_boutique')
        _wait(career, 2 * 24 * 60)
        assert expected in _published(career) and other not in _published(career)
    untouched = _career(tmp_path / 'sans-choix', ['tuto_p0', 'act1_boutique'])
    _wait(untouched, 2 * 24 * 60)
    assert not {'choix-contretemps-signaler', 'choix-contretemps-discret'} & _published(untouched)


def test_public_choice_is_quoted_by_name_on_the_forum(tmp_path):
    career = _career(tmp_path, ['tuto_p0', 'act1_litige'], {'litige118': 'publication'})
    _wait(career, 2 * 24 * 60)
    posts = career.data['forum_posts']['act1-litige']
    assert any(p['id'] == 'regles-publication' and p['author'] == 'mod_echo' and 'NightShift' in p['text'] for p in posts)
    assert 'regles-mediation' not in _published(career)


def test_a_reply_never_appears_before_the_message_it_answers(tmp_path):
    """Chaque auteur a ses heures de présence : sans lien entre les messages, la réponse pouvait arriver la première."""
    for start in range(0, 24 * 60, 45):  # dossier terminé à toute heure du jour
        career = _career(tmp_path / str(start), ['tuto_p0', 'act1_service', 'act1_recommandation', 'act2_compte'], minute=start)
        _wait(career, 3 * 24 * 60)
        dispute = [p['id'] for p in career.data['forum_posts']['seller-dispute']]
        assert dispute.index('regles-1') < dispute.index('regles-2'), start
        posted = career.data['social']['posted']
        assert posted['regles-1'] < posted['regles-2'] and posted['hexane-depart'] < posted['hexane-silence'], start


def test_departed_member_stops_posting_and_answering(tmp_path):
    """hexane annonce son départ à la fin de l'acte I : plus de mesures, plus de réponse automatique dans ses fils."""
    career = _career(tmp_path, ['tuto_p0', 'act1_recommandation'])
    _wait(career, 3 * 24 * 60)
    assert any('ferme l’atelier' in text for text in _texts(career))
    assert not any(p.get('id') == 'life-extension-10' for posts in career.data['forum_posts'].values() for p in posts)
    thread = next(t for t in social.content()['threads'] if t.get('response', {}).get('author') == 'hexane')
    social.queue_forum_reply(career, thread['id'], 'NightShift')
    assert not career.data['social']['pending']
    present = _career(tmp_path / 'avant', ['tuto_p0'])
    social.queue_forum_reply(present, thread['id'], 'NightShift')
    assert [e['author'] for e in present.data['social']['pending']] == ['hexane']


def test_contact_who_writes_first_does_not_greet_twice(tmp_path):
    career = _career(tmp_path, ['tuto_p0', 'act1_portail'], minute=450)  # 16:30, elle est absente jusqu'au matin
    social.advance(career, 1)
    social.queue_chat(career, 'chordly', 'Madame_TLS', 'NightShift', 'Bonjour')
    _wait(career, 24 * 60)
    hers = [m['text'] for m in career.data['conversations'].values() if m.get('peer') == 'Madame_TLS' and m.get('sender') == 'Madame_TLS']
    assert len(hers) == 2 and sum(text.startswith('Bonjour') for text in hers) == 1


def test_older_save_receives_overdue_messages_spread_out_and_in_order(tmp_path):
    """Une sauvegarde d'avant les messages d'histoire ne les reçoit pas tous dans la même minute."""
    done = ['tuto_p0', 'act1_boutique', 'act1_service', 'act1_portail', 'mauvaise_adresse', 'act1_litige', 'act1_recommandation', 'act2_compte', 'act2_reseau']
    career = _career(tmp_path, done, {'litige118': 'mediation'}, tier=2, minute=140)
    for key in ('armed', 'posted'): del career.data['social'][key]  # état d'une sauvegarde antérieure
    _wait(career, 60)
    assert len(career.data['social']['late']) > 8
    early = [i for i in career.data['social']['posted'] if i in career.data['social']['late']]
    assert len(early) <= 1  # une heure plus tard, au plus un message en retard est paru
    _wait(career, 5 * 24 * 60)
    posted = career.data['social']['posted']
    assert posted['hexane-depart'] < posted['hexane-silence'] < posted['hexane-annonce']
    assert posted['hexane-annonce'] - posted['hexane-depart'] >= 2 * social.BACKLOG_SPACING
    assert len({posted[i] for i in career.data['social']['late'] if i in posted}) > 8


def test_missing_handle_does_not_break_the_world(tmp_path):
    career = _career(tmp_path, ['tuto_p0', 'act1_litige'], {'litige118': 'publication'})
    career.data['handle'] = None  # état sauvegardé sans pseudo
    _wait(career, 2 * 24 * 60)
    assert 'regles-publication' not in _published(career)  # il attend un pseudo plutôt que de remercier personne
    assert 'tls-accueil' in _published(career)
    career.data['handle'] = 'NightShift'
    _wait(career, 24 * 60)
    assert 'regles-publication' in _published(career)


def test_story_content_is_consistent_with_the_game():
    from engine.contracts import load_all_contracts
    content, every = social.content(), load_all_contracts()
    threads, contacts = {t['id'] for t in content['threads']}, {c['id'] for c in content['contacts']}
    decisions = {}
    for contract in every.values():
        for step in contract.get('investigation_steps', []):
            if step.get('exclusive_group'): decisions.setdefault(step['exclusive_group'], set()).add(step['id'])
    seen = set()
    for event in content['events']:
        assert event['kind'] in {'chat', 'forum'} and event['target'] in (contacts if event['kind'] == 'chat' else threads), event['id']
        assert event['author'] in content['profiles'], event['id']
        assert set(event.get('requires_completed', [])) <= set(every), event['id']
        for key, pattern in event.get('requires_choice', {}).items():
            assert any(fnmatchcase(value, pattern) for value in decisions.get(key, ())), event['id']
        if 'follows' in event: assert event['follows'] in seen, event['id']  # le message précédent existe et vient avant
        assert '—' not in event['text'] and ';' not in event['text'], event['id']
        seen.add(event['id'])
    for contact in content['contacts']:
        if 'opening_event' in contact: assert contact['opening_event'] in seen, contact['id']
    for name, profile in content['profiles'].items():
        if 'gone_after' in profile: assert profile['gone_after'] in every, name
    assert 'Madame_TLS' in content['profiles'] and 'Madame_TLS' in contacts
