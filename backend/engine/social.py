"""Communauté locale persistante : conversations, présences et événements écrits.

L'horloge avance uniquement quand le jeu tourne. Un tick social représente une
minute fictive pour six secondes réelles. Aucun rattrapage pendant la fermeture,
aucun accès réseau, aucun contenu généré au hasard à chaque rafraîchissement.
"""
from __future__ import annotations

from copy import deepcopy
from datetime import datetime, timedelta
from functools import lru_cache
from .world_time import wait_until_available
from pathlib import Path
import json
import time

EPOCH = datetime(2026, 11, 9, 9, 0)
# Sur une sauvegarde antérieure aux messages d'histoire, ceux qui sont déjà dus arrivent étalés.
BACKLOG_SPACING = 60
FORUM_TIERS = {'breachboard': 0, 'exployt': 2, 'xsx': 3}


@lru_cache(maxsize=1)
def content() -> dict:
    return json.loads((Path(__file__).parents[1] / 'data/social_world.json').read_text(encoding='utf-8'))


def stamp(minute: int) -> str:
    return (EPOCH + timedelta(minutes=minute)).strftime('%d/%m %H:%M')


def prepare(career) -> dict:
    world = career.data.setdefault('social', {'minute': 0, 'sequence': 0, 'published': [], 'pending': [], 'seen': {}, 'milestones': [], 'armed': {}, 'posted': {}})
    world['content_version'] = content()['version']
    unlocked_at = world.setdefault('unlocked_at', {})
    for contact in contacts(career): unlocked_at.setdefault('chat:' + contact['id'], world['minute'])
    for forum in FORUM_TIERS:
        if forum_allowed(career, forum): unlocked_at.setdefault('forum:' + forum, world['minute'])
    for thread in content()['threads']:
        posts = career.data.setdefault('forum_posts', {}).setdefault(thread['id'], [])
        for index, post in enumerate(thread.get('posts', [])):
            ident = f"seed:{thread['id']}:{index}"
            seeded = next((p for p in posts if p.get('id') == ident), None)
            if seeded is not None:
                # Révision éditoriale des seuls messages de fond. Les messages du
                # joueur et les conversations déjà reçues restent des archives.
                seeded['text'] = post['text']
                continue
            posts.insert(index, _post(ident, post['author'], post['text'], post['minute']))
    # Les anciennes contributions du joueur n'avaient pas d'identifiant.
    # Migration additive : conserver texte, auteur et ordre, puis figer le marqueur.
    for thread_id, posts in career.data.get('forum_posts', {}).items():
        for index, post in enumerate(posts):
            post.setdefault('id', f'legacy-post:{thread_id}:{index}')
    archive = career.data.setdefault('conversations', {})
    from .campaign import enabled
    if enabled(career.data) and career.data.get('play_mode') == 'demo':
        archive.setdefault('journey:welcome', _message('journey:welcome', 'k0rvid', 'chordly', 'k0rvid', 'Salut. Je te propose trois essais pour prendre tes marques. Après, miette aimerait un second regard sur son dossier. Rien à acheter, on part avec ce que tu as. Écris aide si tu bloques. Si tu continues après la démo, tu garderas cette sauvegarde.', 0))
    if enabled(career.data) and career.data.get('play_mode') != 'demo':
        from .onboarding import stages
        count=len(stages(career.data))-1
        archive.setdefault('journey:welcome', _message('journey:welcome', 'k0rvid', 'chordly', 'k0rvid', f'Salut. Avant de te confier Ravelle, je te propose {count} exercices courts. Pas pour te faire perdre du temps : je veux voir comment tu vérifies un résultat. La carte en dessous te donnera les pièces. Rien à acheter.\n\nSi tu bloques, écris aide. Les primes arrivent dans ColdVault. Tu peux fermer le jeu et reprendre plus tard, je ne vais pas te demander de tout faire ce soir.', 0))
    from .curriculum import current
    if current(career.data) and career.data.get('forum_invitation_accepted'):
        ident='act2:introduction'
        archive.setdefault(ident,_message(ident,'cendre','telegrid','cendre','Salut. Bytewarden m’a transmis ta recommandation. Cendre. Je reprends les passations et je vérifie l’état des machines, parfois plus longtemps que les autres ne le voudraient.\n\nPour commencer, j’ai une empreinte et une petite liste. Je fournis les deux, pas de GPU à acheter. On vérifiera l’accès après la correspondance. Configure VPN + Tor avec l’accès NullVad gratuit, puis ouvre « Une vieille passation » ici. Tes primes restent dans ColdVault. Pour Exployt, on construit une réputation à part de BreachBoard.',world['minute']))
    for contact in contacts(career):
        if contact['kind'] != 'group': continue
        ident = 'group:' + contact['id']
        archive.setdefault(ident, _message(ident, contact['id'], contact['channel'], contact['members'][0], contact['bio'], -60))
    from .conversation_scenes import prepare as prepare_scenes
    prepare_scenes(career, world, contacts(career), content()['profiles'])
    return world


def _post(ident: str, author: str, text: str, minute: int) -> dict:
    profile = content()['profiles'].get(author, {})
    return dict(id=ident, author=author, text=text, minute=minute, time=stamp(minute),
                reputation=profile.get('reputation', 0), age=profile.get('age', 1), role=profile.get('role', 'Membre'))


def _message(ident: str, peer: str, channel: str, sender: str, text: str, minute: int, **extra) -> dict:
    return dict(id=ident, peer=peer, channel=channel, sender=sender, text=text, minute=minute,
                time=stamp(minute), status='sent', **extra)


def contacts(career) -> list[dict]:
    from .onboarding import forum_unlocked
    if not forum_unlocked(career.data):
        ids = {'k0rvid'}
        if career.data.get('play_mode') == 'demo' and 'intro_evidence' in career.data['completed']: ids.add('miette')
        return [deepcopy(c) for c in content()['contacts'] if c['id'] in ids]
    return [deepcopy(c) for c in content()['contacts'] if c['tier'] <= career.data['tier'] and all(cid in career.data['completed'] for cid in c.get('requires_completed', [])) and (not c.get('requires_any_completed') or any(cid in career.data['completed'] for cid in c['requires_any_completed']))]


def forum_allowed(career, forum: str) -> bool:
    from .community import forum_reason
    return not forum_reason(career.data, forum)


def advance(career, minutes: int = 1) -> None:
    """Avance explicite pour tests et horloge ; idempotence assurée par les ids."""
    world = prepare(career)
    world['minute'] += max(0, minutes)
    minute = world['minute']
    unlocked = {c['id']: c for c in contacts(career)}
    events = content()['events']
    if 'armed' not in world:
        # Première lecture d'une sauvegarde plus ancienne : ces messages auraient dû paraître au fil des dossiers.
        world['late'] = [e['id'] for e in events if _is_story(e) and _conditions_met(career.data, e)]
    armed, posted, late = world.setdefault('armed', {}), world.setdefault('posted', {}), world.get('late', [])
    handle, gone, backlog = career.data.get('handle') or '', _gone(career.data), 0
    for event in events:
        if event['id'] in world['published']: continue
        story = _is_story(event)
        if not story and event['author'] in gone:
            world['published'].append(event['id'])  # un personnage parti ne poste plus ses messages de fond
            continue
        if '{handle}' in event['text'] and not handle: continue
        start = 0
        if story:
            # Un message d'histoire attend ses dossiers, ses choix et le message auquel il fait suite.
            if not _conditions_met(career.data, event) or event.get('follows', event['id']) not in world['published'] + [event['id']]: continue
            if event['id'] not in armed:
                backlog += event['id'] in late
                armed[event['id']] = minute + (BACKLOG_SPACING * backlog if event['id'] in late else 0)
            start = armed[event['id']]
        due = start + event['after']
        if due > minute: continue
        author_ready = due + wait_until_available(due, content()['profiles'].get(event['author'], {}).get('availability'))
        if author_ready > minute: continue
        text = event['text'].replace('{handle}', handle)
        if event['kind'] == 'chat':
            if event['target'] not in unlocked: continue
            contact = unlocked[event['target']]
            posted_at = max(author_ready, world['unlocked_at'].get('chat:' + contact['id'], minute))
            career.data['conversations'].setdefault(event['id'], _message(event['id'], contact['id'], contact['channel'], event['author'], text, posted_at))
        else:
            thread = next(t for t in content()['threads'] if t['id'] == event['target'])
            if not forum_allowed(career, thread['forum']): continue
            posted_at = max(author_ready, world['unlocked_at'].get('forum:' + thread['forum'], minute))
            career.data['forum_posts'][thread['id']].append(_post(event['id'], event['author'], text, posted_at))
        world['published'].append(event['id'])
        posted[event['id']] = posted_at
    due = [event for event in world['pending'] if event['due'] <= minute]
    world['pending'] = [event for event in world['pending'] if event['due'] > minute]
    for event in due:
        if event['kind'] == 'forum':
            post = _post(event['id'], event['author'], event['text'], event['due'])
            if event.get('response_to'): post['response_to'] = event['response_to']
            career.data['forum_posts'].setdefault(event['target'], []).append(post)
        else:
            career.data['conversations'].setdefault(event['id'], _message(event['id'], event['target'], event['channel'], event['author'], event['text'], event['due']))
            original = career.data['conversations'].get(event.get('reply_to'))
            if original: original['status'] = 'read'
    for cid in career.data['completed']:
        if cid in world['milestones']: continue
        world['milestones'].append(cid)
        followups = {
            'tuto_p0': ('miette', 'chordly', 'J’ai vu que ton profil avait changé de palier. Bien joué. Tu gardes tes notes pour la suite ?'),
            'morel': ('k0rvid', 'chordly', 'Document reçu. Garde une copie de ta chronologie. Je préfère pouvoir vérifier le transfert qu’avoir juste un « terminé ».'),
            'rival': ('k0rvid', 'chordly', 'Le contrat de passage est réglé. Les discussions de relay sont sur Telegrid. Et lis les règles d’Exployt avant d’y publier quoi que ce soit.'),
            'varenne': ('relay', 'telegrid', 'Vérification de l’accès archivée. Dans le compte rendu, la création du ticket et son utilisation font deux étapes séparées.'),
            'affiliation': ('relay', 'telegrid', 'Le règlement de l’affiliation est sur ton profil. Spectre veut des passations datées. Précise toujours les limites de l’accès fourni.'),
            'grand_compte': ('spectre', 'sessyon', 'Dossier clos. Les conditions vérifiées et le montant réglé sont archivés. Une isolation ultérieure ne restaure pas les fichiers chiffrés.'),
        }
        if cid in followups:
            author, channel, text = followups[cid]
            _schedule(career, kind='chat', target=author, channel=channel, author=author, text=text, delay=3)


def _is_story(event: dict) -> bool:
    """Un message de fond paraît à une minute fixe de la carrière. Un message d'histoire déclare
    `requires_completed` (dossiers terminés), `requires_choice` (décision de carrière, motif à la
    fnmatch) ou `follows` (message auquel il fait suite) : son délai `after` part du moment où
    ces conditions sont réunies, ce qui permet à un personnage de réagir quelques dossiers
    après un choix, toujours après le message qu'il commente."""
    return any(key in event for key in ('requires_completed', 'requires_choice', 'requires_bond', 'follows'))


def _conditions_met(data: dict, event: dict) -> bool:
    from fnmatch import fnmatchcase
    if any(cid not in data['completed'] for cid in event.get('requires_completed', [])): return False
    choices = data.get('choices', {})
    for author, fields in event.get('requires_bond', {}).items():
        bond = data.get('social', {}).get('bonds', {}).get(author, {})
        if any(bond.get(key) not in values for key, values in fields.items()): return False
    return all(fnmatchcase(str(choices.get(key, '')), pattern) for key, pattern in event.get('requires_choice', {}).items())


def _gone(data: dict) -> set[str]:
    """Personnages qui ont quitté le forum à ce stade de l'histoire (`gone_after` dans leur profil) :
    leurs messages de fond et leurs réponses automatiques cessent."""
    return {name for name, profile in content()['profiles'].items() if profile.get('gone_after') in data.get('completed', [])}


def refresh(career, now: float | None = None) -> None:
    """Le nombre de requêtes ne change pas la vitesse de l'horloge."""
    now = time.monotonic() if now is None else now
    before = _signature(career)
    prepare(career)
    previous = getattr(career, '_social_time', now)
    elapsed = max(0, int((now - previous) // 6))
    if not hasattr(career, '_social_time'):
        career._social_time = now
    elif elapsed:
        career._social_time = previous + elapsed * 6
        advance(career, min(elapsed, 10))
    # Le client interroge le monde social toutes les six secondes : la carrière n'est
    # réécrite que si l'horloge a avancé ou si un message, un sujet ou un contact est apparu.
    if _signature(career) != before: career.save()


def _signature(career) -> tuple:
    world = career.data.get('social')
    if world is None: return ()
    return (world.get('content_version'), world.get('minute'), world.get('sequence'), len(world.get('published', [])), len(world.get('pending', [])),
            len(world.get('scenes', {}).get('active', {})), len(world.get('scenes', {}).get('choices', {})),
            len(world.get('unlocked_at', {})), len(world.get('seen', {})), len(world.get('milestones', [])), len(world.get('armed', {})),
            len(career.data.get('conversations', {})), sum(len(posts) for posts in career.data.get('forum_posts', {}).values()))


def restart_clock(career) -> None:
    """Repart de maintenant : après un chargement ou une nouvelle partie, le temps passé au menu ne compte pas."""
    import time
    career._social_time = time.monotonic()


def schedule(career, *, kind, target, author, text, delay=2, **extra):
    """Planifie un message d'un personnage dans le monde social."""
    return _schedule(career, kind=kind, target=target, author=author, text=text, delay=delay, **extra)


def _schedule(career, *, kind, target, author, text, delay=2, **extra):
    world = prepare(career)
    world['sequence'] += 1
    ident = f"social:{world['sequence']}"
    due = world['minute'] + delay
    due += wait_until_available(due, content()['profiles'].get(author, {}).get('availability'))
    event = dict(id=ident, kind=kind, target=target, author=author, text=text, due=due, **extra)
    world['pending'].append(event)
    return ident


def queue_chat(career, channel: str, peer: str, handle: str, text: str) -> None:
    world = prepare(career)
    contact = next((c for c in contacts(career) if c['id'] == peer and c['channel'] == channel), None)
    if not contact: raise ValueError('Ce contact n’est pas disponible dans cette messagerie.')
    if len(world['pending']) >= 50: raise ValueError('Attends la réponse aux messages précédents.')
    if sum(m.get('peer') == peer and m.get('sender') == handle for m in career.data['conversations'].values()) >= 100:
        raise ValueError('La limite de cette conversation est atteinte.')
    world['sequence'] += 1
    ident = f"social:{world['sequence']}"
    career.data['conversations'][ident] = _message(ident, peer, channel, handle, text, world['minute'])
    pending = next((e for e in world['pending'] if e['kind'] == 'chat' and e['target'] == peer), None)
    if pending: return  # Pas une réponse identique pour chaque pression sur Entrée.
    previous = [m for m in career.data['conversations'].values() if m.get('peer') == peer and m.get('sender') == contact['response_author']]
    # Un contact qui va écrire le premier (`opening_event`) ne se présente pas deux fois.
    introduced = previous or contact.get('opening_event', '') not in world['published'] + ['']
    from .dialogue import intent, reply
    # Une salutation présente le contact une seule fois. Une question personnelle
    # reçoit déjà une vraie réponse, même si c'est le premier message du joueur.
    memory = world.setdefault('dialogue', {}).setdefault(peer, {})
    response = (contact['response'].replace('{handle}', handle)
                if not introduced and intent(text) in {'greeting', 'unknown'}
                else reply(contact, text, memory, handle))
    from .relationships import conversation_reply
    response = conversation_reply(career.data, peer, text) or response
    if peer == 'Madame_TLS':
        bond = world.get('bonds', {}).get(peer, {})
        if intent(text) == 'flirt' and bond.get('stance') == 'professionnel':
            response = 'Tu avais préféré garder un lien professionnel. Je respecte ce cadre. Si tu veux le changer, on prendra le temps de se le dire clairement.'
        elif intent(text) == 'people' and bond.get('disclosure') == 'refus_membres':
            response = 'Tu m’as dit que tu ne voulais pas devenir une source sur les membres. Je garde cette limite. On peut parler des mécanismes sans identifier tes contacts.'
    _schedule(career, kind='chat', target=peer, channel=channel, author=contact['response_author'], text=response, reply_to=ident, delay=2 if contact['response_author'] == 'miette' else 4)


def queue_forum_reply(career, thread_id: str, handle: str) -> None:
    world = prepare(career)
    topic = next((t for t in content()['threads'] if t['id'] == thread_id), None)
    if not topic or not topic.get('response') or topic['response']['author'] in _gone(career.data): return
    if any(e['kind'] == 'forum' and e['target'] == thread_id for e in world['pending']): return
    # Un membre ne répète pas le même accueil indéfiniment.
    if any(p.get('response_to') == handle for p in career.data['forum_posts'][thread_id]): return
    response = topic['response']
    ident = _schedule(career, kind='forum', target=thread_id, author=response['author'], text=response['text'].replace('{handle}', handle), delay=3)
    # La marque reste dans la file puis dans la réponse publiée.
    next(e for e in world['pending'] if e['id'] == ident)['response_to'] = handle


def mark_read(career, channel: str, peer: str) -> None:
    world = prepare(career)
    world['seen'][f'{channel}:{peer}'] = world['minute']


def view(career, contracts: dict | None = None) -> dict:
    world = prepare(career)
    profiles = deepcopy(content()['profiles'])
    threads = []
    for topic in content()['threads']:
        if not forum_allowed(career, topic['forum']): continue
        entry = {k: deepcopy(v) for k, v in topic.items() if k not in {'posts', 'response'}}
        author_profile = profiles.get(topic['author'], {})
        entry.setdefault('reputation', author_profile.get('reputation', 0))
        entry.setdefault('age', author_profile.get('age', 1))
        posts = career.data['forum_posts'][topic['id']]
        marker = world.get('forum_seen', {}).get(topic['id'])
        seen_index = next((i for i, post in enumerate(posts) if post['id'] == marker), -1)
        unread = len(posts) - seen_index - 1 if marker is not None else len(posts) + 1
        participants = list(dict.fromkeys([topic['author'], *[post['author'] for post in posts]]))
        entry.update(unread=unread, participants=participants,
                     category=topic.get('category', 'Vie du forum' if topic['section'] == 'Discussion' else topic['section']))
        entry.update(views=topic.get('views',0)+career.data.get('thread_views',{}).get(topic['id'],0), count=len(posts), last_author=posts[-1]['author'] if posts else topic['author'],
                     last_time=posts[-1]['time'] if posts else stamp(topic['created_minute']), last_minute=posts[-1].get('minute', 0) if posts else topic['created_minute'], created_time=stamp(topic['created_minute']))
        threads.append(entry)
    peers = contacts(career)
    for contract in (contracts or {}).values():
        author = contract['client']['handle']
        profiles.setdefault(author, dict(role='Membre', reputation=contract['client']['forum_rep'], age=contract['client']['account_age_days'], bio='Conditions de mission dans la conversation privée.'))
        # Ne crée pas de conversation privée avec un inconnu avant la rencontre.
        if any(m.get('peer') == author and m.get('channel') == contract['channel'] for m in career.data['conversations'].values()):
            peers.append(dict(id=author, name=author, channel=contract['channel'], kind='direct', members=[author], bio=profiles[author]['bio']))
    peers = list({(c['channel'], c['id']): c for c in peers}.values())
    for contact in peers:
        member = contact['members'][0]
        remaining = wait_until_available(world['minute'], profiles.get(member, {}).get('availability'))
        contact['presence'] = 'online' if remaining == 0 else 'offline'
        contact['status_text'] = 'En ligne' if remaining == 0 else f'Absent · prochain passage dans {remaining} min de jeu'
        pending = next((e for e in world['pending'] if e['kind'] == 'chat' and e['target'] == contact['id']), None)
        contact['typing'] = bool(remaining == 0 and pending and pending['due'] - world['minute'] <= 1)
    from .onboarding import enabled, next_stage
    offers=[]
    if enabled(career.data) and next_stage(career.data) and contracts:
        contract=contracts.get(next_stage(career.data))
        if contract and not career.lock_reason(contract):
            offers=[{'id':contract['contract_id'],'peer':contract['client']['handle'],'title':contract['bounty']['title'],'text':contract['bounty']['body'],'reward':contract['reward'],'channel':contract['channel']}]
    for contract in (contracts or {}).values():
        if not contract.get('private_offer') or career.lock_reason(contract): continue
        cid = contract['contract_id']
        if cid in career.data['completed']: continue
        peer = contract['client']['handle']
        if contract.get('offer_channel')=='forum':
            career.data.setdefault('forum_messages',{}).setdefault('offer:'+cid,dict(id='offer:'+cid,forum='breachboard',author=peer,subject=contract['bounty']['title'],body=contract['intro'],minute=world['minute'],read=False,contract_id=cid))
            career.data['forum_messages']['offer:'+cid]['body'] = contract['intro']
            continue
        ident = 'offer:'+cid
        message = _message(ident, peer, contract['channel'], peer, contract['intro'], world['minute'])
        if ident in career.data['conversations']:
            career.data['conversations'][ident]['text'] = contract['intro']
        career.data['conversations'].setdefault(ident, message)
        if not any(c['id']==peer and c['channel']==contract['channel'] for c in peers):
            peers.append(dict(id=peer,name=peer,channel=contract['channel'],kind='direct',members=[peer],bio=profiles.get(peer,{}).get('bio','Conditions du dossier dans cette conversation privée.'),presence='online',status_text='En ligne',typing=False))
        offers = [offer for offer in offers if offer['id'] != cid]
        offers.append({'id':cid,'peer':peer,'title':contract['bounty']['title'],'text':contract['bounty']['body'],'reward':contract['reward'],'channel':contract['channel']})
    active=career.data.get('active') or {}
    for offer in offers:
        offer['active']=active.get('status')=='RUNNING' and (active.get('contract') or {}).get('contract_id')==offer['id']
        offer['side_job']=bool((contracts or {}).get(offer['id'],{}).get('side_job'))
        offer['reason']='Un autre dossier est en cours. Reprends-le ou termine-le avant d’en ouvrir un nouveau.' if active.get('status')=='RUNNING' and not offer['active'] else ''
    from .relationships import view as relationship_view
    relations = relationship_view(career.data)
    for contact in peers:
        relation = relations.get(contact['id'])
        if relation:
            contact['bio'] = contact.get('bio', '') + '\n' + relation['label'] + ' - ' + relation['detail']
            profiles.setdefault(contact['id'], {}).update(relationship=relation)
    from .journey import view as next_step
    from .conversation_scenes import view as scene_choices
    return dict(journey=next_step(career.data),forum_messages=list(career.data.get('forum_messages',{}).values()),offers=offers, minute=world['minute'], time=stamp(world['minute']), threads=threads, profiles=profiles, contacts=peers,
                messages=list(career.data['conversations'].values()), scene_choices=scene_choices(world), forum_counts={k: len(v) for k, v in career.data['forum_posts'].items()})
