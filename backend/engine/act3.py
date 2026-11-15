"""Douze dossiers Lenoir : droits, chemins réseau et copie d'audit."""
CHAPTERS = [
    ('act3_decouverte', 'Une machine qu’on ne voit pas'),
    ('act3_prestataire', 'La porte du prestataire'),
    ('act3_origine', 'Le réseau vu d’ici'),
    ('act3_chisel', 'Le retour est possible'),
    ('act3_proxychains', 'La même adresse, plusieurs chemins'),
    ('act3_winrm', 'Une console sans bureau'),
    ('act3_droits', 'Le réseau des droits'),
    ('act3_defender', 'Le fichier arrive, rien ne s’exécute'),
    ('act3_tamper', 'Administrateur ne suffit pas'),
    ('act3_second_pivot', 'Le second passage'),
    ('act3_repli', 'Le gardien se réveille'),
    ('act3_dossier', 'Le dossier qui ne devait pas sortir'),
]


def lock_reason(data, contract):
    if contract.get('act') != 3:
        return ''
    from .act2 import CHAPTERS as previous
    completed = data.get('completed', [])
    if not data.get('forum_invitation_accepted') or any(cid not in completed for cid, *_ in previous):
        return 'Termine les dix dossiers de l’acte II avant la passation Lenoir.'
    ids = [cid for cid, _ in CHAPTERS]
    cid = contract['contract_id']
    if cid in ids:
        for prior, title in CHAPTERS[:ids.index(cid)]:
            if prior not in completed:
                return 'Poursuis l’acte III : ' + title
    return ''


def journey(data):
    from .act2 import CHAPTERS as previous
    completed = data.get('completed', [])
    if not data.get('forum_invitation_accepted') or any(cid not in completed for cid, *_ in previous):
        return None
    for number, (cid, title) in enumerate(CHAPTERS, 1):
        if cid not in completed:
            return dict(title=f'Acte III · {number}/{len(CHAPTERS)} — {title}', detail='Découverte, droits, protections et chemins réseau. Traverse t’attend sur Telegrid ; documentation locale et indices disponibles.', app='Telegrid', peer='traverse', contract_id=cid)
    return dict(title='Acte III — dossiers terminés', detail='Tes douze constats sont conservés. Chordly reste accessible pour les échanges et les décisions de transmission.', app='Telegrid', peer='traverse')


def view(data):
    from .act2 import CHAPTERS as previous
    completed = data.get('completed', [])
    unlocked = bool(data.get('forum_invitation_accepted') and all(cid in completed for cid, *_ in previous))
    chapters = []
    for number, (cid, title) in enumerate(CHAPTERS, 1):
        ready = unlocked and all(prior in completed for prior, _ in CHAPTERS[:number-1])
        chapters.append(dict(id=cid, number=number, title=title, peer='traverse', channel='telegrid',
                             status='completed' if cid in completed else 'available' if ready else 'locked'))
    return dict(total=len(chapters), completed=sum(row['status']=='completed' for row in chapters),
                unlocked=unlocked, chapters=chapters, partial=False)


def settle(career, state):
    if state.contract['contract_id'] != 'act3_dossier':
        return
    from .win_conditions import objective_met
    requirements = state.contract['investigation_steps'][0]['requires']
    if not all(objective_met(state, requirement) for requirement in requirements):
        return
    import hashlib
    text = state.terminal_files['/home/operator/loot/lot-industriel.txt']
    from .social import prepare
    world = prepare(career)
    world.setdefault('documents', {})['lenoir-lot'] = dict(
        id='lenoir-lot', title='Lot industriel LN-RD-26', classification='confidentiel industriel',
        author=state.player_handle, channel='chordly', path='/home/operator/loot/lot-industriel.txt',
        content=text, sha256=hashlib.sha256(text.encode()).hexdigest(), received_minute=world['minute'])
