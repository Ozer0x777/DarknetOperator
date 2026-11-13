"""Réputation par communauté et règles d'accès partagées par l'API et le moteur."""
import json
from pathlib import Path

FORUMS = ('breachboard', 'exployt', 'xsx')


def scores(data):
    if 'forum_reputation' not in data:
        result = dict.fromkeys(FORUMS, 0)
        completed = set(data.get('completed', []))
        for path in (Path(__file__).parents[1] / 'contracts').glob('*.json'):
            if path.stem not in completed: continue
            contract = json.loads(path.read_text(encoding='utf-8'))
            forum = contract.get('bounty', {}).get('forum')
            if forum in result: result[forum] += int(contract.get('reputation', 0))
        # L'ancien score inexpliqué reste sur la communauté d'origine, jamais copié partout.
        result['breachboard'] += max(0, data.get('reputation', 0) - sum(result.values()))
        data['forum_reputation'] = result
    return data['forum_reputation']


def forum_reason(data, forum):
    from .onboarding import forum_unlocked
    from .campaign import enabled, CHAPTERS
    if forum not in FORUMS: return 'Forum inconnu.'
    if not forum_unlocked(data): return 'Termine le dossier Ravelle avec k0rvid pour recevoir ton accès à BreachBoard.'
    if enabled(data) and data.get('reputation', 0) < 40:
        return 'Il faut 40 points de confiance opérateur pour accéder aux communautés.'
    if forum == 'breachboard': return ''
    tier = 2 if forum == 'exployt' else 3
    if data.get('tier', 0) < tier: return f'Ce forum nécessite le palier {tier}.'
    if enabled(data):
        if not all(cid in data.get('completed', []) for cid, *_ in CHAPTERS): return 'Termine les dix chapitres de l’acte I.'
        if not data.get('forum_invitation_accepted'): return 'Accepte ton invitation dans les MP de BreachBoard.'
        origin = 'breachboard' if forum == 'exployt' else 'exployt'
        if scores(data)[origin] < 100: return f'Il faut 100 points de réputation sur {origin} pour cette recommandation.'
        if forum == 'xsx' and 'affiliation' not in data.get('completed', []): return 'La recommandation XSX se gagne en terminant le dossier d’affiliation.'
    if forum == 'exployt' and data.get('route') not in {'tor', 'relay'}: return 'Active une route Tor avant de rejoindre Exployt.'
    return ''


def shop_reason(data):
    from .campaign import enabled
    if data.get('tier', 0) < 1: return 'La boutique se débloque après le dossier Ravelle.'
    if enabled(data):
        if 'tuto_p0' not in data.get('completed', []): return 'Termine le dossier Ravelle avant de contacter les fournisseurs.'
        if data.get('reputation', 0) < 40: return 'La boutique demande 40 points de confiance opérateur.'
        if scores(data)['breachboard'] < 40: return 'La boutique demande 40 points de réputation sur BreachBoard.'
    return ''


def access(data):
    return {'shop': {'unlocked': not shop_reason(data), 'reason': shop_reason(data)},
            'forums': {forum: {'unlocked': not forum_reason(data, forum), 'reason': forum_reason(data, forum), 'reputation': scores(data)[forum]} for forum in FORUMS}}
