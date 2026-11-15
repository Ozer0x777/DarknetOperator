"""Questions de personnages et réponses explicites, persistantes et sans délai de choix."""
from copy import deepcopy
from functools import lru_cache
import json
import hashlib
from pathlib import Path

from .world_time import wait_until_available

FRIENDLY_STANCES = frozenset({'professionnel', 'amitie', 'rivalite_amicale', 'reserve',
                             'dialogue', 'exigeant', 'humour', 'complicite'})


def _validate_effects(author: str, effects: dict) -> None:
    stance = effects.get('stance')
    allowed = FRIENDLY_STANCES | ({'attirance'} if author == 'Madame_TLS' else set())
    if stance is not None and stance not in allowed:
        raise ValueError('Seule Madame_TLS peut mener à une relation amoureuse. Les autres liens restent professionnels ou amicaux.')


@lru_cache(maxsize=1)
def content() -> dict:
    data = json.loads((Path(__file__).parents[1] / 'data/conversation_scenes.json').read_text(encoding='utf-8'))
    for scene in data['scenes']:
        for option in scene['options']:
            _validate_effects(scene['author'], option.get('effects', {}))
        for variant in scene.get('variants', []):
            for option in variant.get('options', {}).values():
                _validate_effects(scene['author'], option.get('effects', {}))
    return data


def _state(world: dict) -> dict:
    state = world.setdefault('scenes', {'active': {}, 'choices': {}})
    state.setdefault('resolved', {})
    return state


def _matches(requirements: dict, world: dict) -> bool:
    if any(ident not in world.get("documents", {}) for ident in requirements.get("requires_documents", [])):
        return False
    for author, fields in requirements.get('requires_bond', {}).items():
        bond = world.get('bonds', {}).get(author, {})
        if any(bond.get(key) not in values for key, values in fields.items()):
            return False
    for ident, options in requirements.get('requires_scene_choices', {}).items():
        if _state(world)['choices'].get(ident, {}).get('option') not in options:
            return False
    return True


def _resolve(scene: dict, world: dict) -> dict:
    """Fige la question, les répliques et leurs effets au moment de la réception."""
    resolved = deepcopy(scene)
    for variant in scene.get('variants', []):
        if not _matches(variant, world):
            continue
        for key in ('question', 'grant_documents'):
            if key in variant: resolved[key] = deepcopy(variant[key])
        for option in resolved['options']:
            option.update(deepcopy(variant.get('options', {}).get(option['id'], {})))
    resolved.pop('variants', None)
    return resolved


def _grant_documents(career, world: dict, scene: dict) -> None:
    from .social import _message
    library = content().get('documents', {})
    for ident in scene.get('grant_documents', []):
        received = world.setdefault('documents', {})
        if ident in received: continue
        document = deepcopy(library[ident])
        document['id'] = ident
        document['sha256'] = hashlib.sha256(document['content'].encode('utf-8')).hexdigest()
        document['received_minute'] = world['minute']
        received[ident] = document
        author = document['author']
        body = (f"{document['title']} [{document['classification']}]\n"
                f"Copie locale : {document['path']}\n\n{document['content']}")
        key = 'scene:document:' + ident
        career.data['conversations'].setdefault(key, _message(
            key, author, document.get('channel', 'chordly'), author, body, world['minute'], document_id=ident))


def provision_files(state, data: dict) -> None:
    """Copies locales des pièces reçues. Ne réécrit pas un fichier modifié ou supprimé."""
    documents = data.get('social', {}).get('documents', {})
    if not documents: return
    provisioned = state.tool_data.setdefault('narrative_documents', [])
    for ident, document in documents.items():
        if ident in provisioned: continue
        state.terminal_files.setdefault(document['path'], document['content'])
        provisioned.append(ident)


def _eligible(career, scene: dict, world: dict) -> bool:
    if any(cid not in career.data['completed'] for cid in scene.get('requires_completed', [])):
        return False
    if scene.get('requires_any_completed') and not any(cid in career.data['completed'] for cid in scene['requires_any_completed']):
        return False
    if any(eid not in world['published'] for eid in scene.get('requires_published', [])):
        return False
    if scene.get('follows'):
        choice = _state(world)['choices'].get(scene['follows'])
        if not choice or choice['reply_id'] not in career.data['conversations']:
            return False
    return _matches(scene, world)


def prepare(career, world: dict, contacts: list[dict], profiles: dict) -> None:
    """Les PNJ écrivent les premiers. Un seul choix ouvert par conversation."""
    from .social import _message
    state = _state(world)
    unlocked = {(c['channel'], c['id']) for c in contacts}
    by_id = {s['id']: s for s in content()['scenes']}
    for peer, ident in list(state['active'].items()):
        scene = by_id.get(ident)
        if scene is None or profiles.get(scene['author'], {}).get('gone_after') in career.data['completed']:
            del state['active'][peer]
        else:
            state['resolved'].setdefault(ident, _resolve(scene, world))
    for scene in content()['scenes']:
        peer, ident = scene['peer'], scene['id']
        if (scene['channel'], peer) not in unlocked or ident in state['choices'] or peer in state['active']:
            continue
        if not _eligible(career, scene, world):
            continue
        if profiles.get(scene['author'], {}).get('gone_after') in career.data['completed']:
            continue
        if any(e['kind'] == 'chat' and e['target'] == peer for e in world['pending']):
            continue
        availability = profiles.get(scene['author'], {}).get('availability')
        if wait_until_available(world['minute'], availability):
            continue
        prompt_id = 'scene:' + ident
        resolved = state['resolved'].setdefault(ident, _resolve(scene, world))
        _grant_documents(career, world, resolved)
        career.data['conversations'].setdefault(prompt_id, _message(
            prompt_id, peer, scene['channel'], scene['author'],
            resolved['question'].replace('{handle}', career.data.get('handle') or 'toi'),
            world['minute'], scene_id=ident))
        state['active'][peer] = ident


def view(world: dict) -> list[dict]:
    """Le client reçoit les répliques, jamais les effets ni les réponses futures."""
    by_id = {s['id']: s for s in content()['scenes']}
    return [dict(id=scene['id'], peer=scene['peer'], channel=scene['channel'],
                 author=scene['author'], question=scene['question'],
                 options=[dict(id=o['id'], text=o['text']) for o in scene['options']])
            for ident in _state(world)['active'].values()
            if (scene := _state(world)['resolved'].get(ident, by_id.get(ident))) is not None]


def choose(career, channel: str, peer: str, scene_id: str, option_id: str, handle: str) -> None:
    """Une option est enregistrée une fois. Rejouer la même requête est sans effet."""
    from . import social
    world = social.prepare(career)
    state = _state(world)
    scene = next((s for s in content()['scenes'] if s['id'] == scene_id), None)
    if scene is None or scene['peer'] != peer or scene['channel'] != channel:
        raise ValueError('Cette réponse ne correspond pas à cette conversation.')
    if not any(c['id'] == peer and c['channel'] == channel for c in social.contacts(career)):
        raise ValueError('Ce personnage n’est pas encore disponible.')
    previous = state['choices'].get(scene_id)
    if previous:
        if previous['option'] == option_id:
            return
        raise ValueError('Cette scène a déjà reçu une autre réponse.')
    if state['active'].get(peer) != scene_id:
        raise ValueError('Cette question n’est plus en attente de réponse.')
    scene = state['resolved'].get(scene_id, scene)
    option = next((o for o in scene['options'] if o['id'] == option_id), None)
    if option is None:
        raise ValueError('Cette réponse ne fait pas partie des choix proposés.')
    _validate_effects(scene['author'], option.get('effects', {}))
    attachments = []
    for doc_id in option.get('transmit_documents', []):
        document = world.get('documents', {}).get(doc_id)
        if document is None:
            raise ValueError('La pièce à transmettre n’a pas encore été reçue.')
        attachments.append(deepcopy(document))
    ident = 'scene:answer:' + scene_id
    sent_text = option['text']
    for document in attachments:
        sent_text += f"\n\nPièce jointe : {document['title']} [{document['classification']}]\n{document['content']}"
    career.data['conversations'][ident] = social._message(
        ident, peer, channel, handle, sent_text, world['minute'], scene_id=scene_id, option_id=option_id)
    reply_id = social.schedule(career, kind='chat', target=peer, channel=channel,
                               author=scene['author'], text=option['reply'], delay=2, reply_to=ident)
    state['choices'][scene_id] = dict(option=option_id, minute=world['minute'], reply_id=reply_id)
    if attachments:
        world.setdefault('transmissions', {})[scene_id] = dict(
            recipient=scene['author'], option=option_id, minute=world['minute'], documents=attachments)
    # Valeurs catégorielles écrites dans les données. Aucun score d'affection.
    bond = world.setdefault('bonds', {}).setdefault(scene['author'], {})
    bond.update(deepcopy(option.get('effects', {})))
    del state['active'][peer]


def bonds(data: dict) -> dict:
    return deepcopy(data.get('social', {}).get('bonds', {}))
