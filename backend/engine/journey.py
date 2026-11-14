"""Prochaine piste publique et conséquences persistantes des dossiers."""
from .onboarding import STAGES
from .campaign import CHAPTERS, enabled

INTRO_TITLES = ['Prendre ses marques', 'Lire le réseau', 'Vérifier un accès', 'Récupérer un document', 'Comparer les sources', 'Préparer une campagne', 'Tester un dictionnaire', 'Lire une session Windows']


def view(data):
    if not enabled(data): return {}
    active = data.get('active') or {}
    contract = active.get('contract') or {}
    if active.get('status') == 'RUNNING':
        return dict(title='Dossier en cours - '+contract.get('bounty',{}).get('title', 'Mission sauvegardée'), detail='Reprends le dossier ouvert avec ce client. Le bouton Objectif te rappelle le but. Indice te donne une piste, sans toucher à la prime. Dans le terminal, help liste les commandes disponibles.', app='Chordly' if contract.get('channel','chordly') == 'chordly' else contract.get('channel','').capitalize(), peer=contract.get('client',{}).get('handle','k0rvid'), contract_id=contract.get('contract_id',''))
    if data.get('play_mode') == 'demo':
        from .onboarding import DEMO_STAGES, next_stage
        cid = next_stage(data)
        if cid:
            titles = dict(zip(DEMO_STAGES, ['Prendre ses marques', 'Lire le réseau', 'Comparer les sources', 'Le contretemps']))
            return dict(title=f'Démo · {DEMO_STAGES.index(cid)+1}/4 - {titles[cid]}', detail='Trois prises en main, puis un dossier ouvert. Rien à acheter, et les indices restent disponibles dans la conversation.', app='Chordly', peer='miette' if cid == 'dossier_contretemps' else 'k0rvid', contract_id=cid)
        choice = data.get('choices', {}).get('contretemps', '')
        route = 'le suivi web' if choice.startswith('web_') else 'le partage public'
        outcome = 'Cobalt a reçu la demande de correction.' if choice.endswith('_signaler') else 'Le client conserve les preuves en privé.'
        return dict(title='Démo terminée - une annonce corrigée dans ton dossier', detail='Tu as confronté une annonce aux faits par '+route+'. '+outcome+' Miette se souvient de ta vérification. Tes primes, tes preuves et tes décisions sont sauvegardées. Continue la campagne pour voir les autres outils, Ravelle et BreachBoard.', app='Chordly', peer='miette', action='continue_campaign')
    from .onboarding import stages
    from .curriculum import title as curriculum_title
    training=stages(data)[:-1]
    for index, cid in enumerate(training):
        if cid not in data['completed']:
            return dict(title=f'Prélude · {index+1}/{len(training)} - {INTRO_TITLES[STAGES.index(cid)]}', detail='La carte du dossier est sur Chordly. Les exercices sont payés une seule fois et il n’y a rien à acheter. Si tu bloques, demande aide au client.', app='Chordly', peer='k0rvid', contract_id=cid)
    if 'tuto_p0' not in data['completed']:
        return dict(title='Premier contrat - cabinet Ravelle', detail='k0rvid te confie un dossier complet sur Chordly. Si tu le réussis, BreachBoard et les fournisseurs s’ouvrent. Rien à acheter.', app='Chordly', peer='k0rvid', contract_id='tuto_p0')
    # Une première consultation du portefeuille ne doit pas retarder le chapitre suivant.
    for cid, title, peer, channel in CHAPTERS[1:]:
        if cid not in data['completed']:
            forum_offer = cid in {'act1_echantillon','act1_litige','act1_recommandation'}
            return dict(title='Prochaine piste - '+curriculum_title(data,cid,title), detail=('Consulte les propositions dans les MP de BreachBoard.' if forum_offer else 'Le dossier est disponible sur BreachBoard.' if cid == 'act1_partage' else 'Une proposition t’attend dans la conversation du client.') + ' Rien d’obligatoire à acheter pour l’acte I. Tes règlements sont dans ColdVault.', app='BreachBoard' if forum_offer or cid == 'act1_partage' else 'Chordly', peer=peer, contract_id=cid)
    if not data.get('forum_invitation_accepted'):
        return dict(title='Ta recommandation est prête', detail='Accepte l’invitation dans les MP de BreachBoard. Elle ne s’active pas toute seule.', app='BreachBoard', peer='bytewarden')
    from .act2 import journey as act2_journey
    next_act = act2_journey(data)
    if next_act: return next_act
    if 'grand_compte' in data['completed']:
        return dict(title='Parcours historique terminé', detail='Tes règlements et tes décisions sont conservés. L’acte II t’attend sur Telegrid : regarde la campagne ou la proposition de cendre. Les actes III et IV ne sont pas encore prêts.', app='BreachBoard', peer='spectre')
    if 'affiliation' in data['completed']:
        return dict(title='Préparer la passation XSX', detail='Va voir XSX, puis prends un passage SSH dans la boutique avant le grand compte. Un passage déjà utilisé pour ce dossier couvre aussi les nouvelles tentatives.', app='BreachBoard', peer='spectre', contract_id='grand_compte')
    if 'varenne' in data['completed']:
        return dict(title='Comparer les conditions d’affiliation', detail='Va voir le dossier d’affiliation sur Exployt. Vesper te laisse 30 % du règlement. Glasswing coûte 450 ₵ et te laisse 100 %. Le règlement dépend aussi des objectifs vérifiés.', app='BreachBoard', peer='relay', contract_id='affiliation')
    from .curriculum import current
    if current(data) and data.get('forum_invitation_accepted'):
        if data.get('route') not in {'tor','relay'}: return dict(title='Préparer l’accès à l’acte II',detail='Active le service gratuit NullVad puis sélectionne VPN + Tor. Les dossiers de l’acte II appliquent le forfait de route affiché. Pas besoin de GPU ni de dictionnaire payant.',app='Boutique',peer='cendre')
        return dict(title='Acte II - Une vieille passation',detail='Cendre te propose ton premier dossier sur Telegrid. Au programme de l’acte II : les empreintes, les droits étendus et les passages entre réseaux. Tu gardes ton portefeuille et tes relations.',app='Telegrid',peer='cendre',contract_id='act2_passation')
    if data.get('route') not in {'tor','relay'}:

        return dict(title='Préparer l’accès à Exployt', detail='Active le service gratuit NullVad dans la boutique puis sélectionne VPN + Tor. Prévois 50 ₵ pour le premier départ de Varenne.', app='Boutique', peer='relay')
    return dict(title='Explorer Exployt', detail='Lis les annonces et leurs conditions avant de dépenser quoi que ce soit. Chaque communauté a sa propre réputation.', app='BreachBoard', peer='relay')


def record(career, state, game_id, first_success):
    from . import social
    data = career.data
    if not enabled(data): return
    cid = state.contract['contract_id']
    ident = 'outcome:' + (state.conversation_id or game_id)
    events = data.setdefault('career_events', [])
    if any(event['id'] == ident for event in events): return
    success = state.contract_outcome == 'SUCCESS'
    if not success: state.payout = 0
    failures = sum(event['contract'] == cid and event['outcome'] != 'SUCCESS' for event in events)
    event = dict(id=ident, contract=cid, outcome=state.contract_outcome, payout=state.payout, minute=social.prepare(career)['minute'])
    events.append(event)
    peer = state.contract['client']['handle']
    channel = state.contract['channel']
    if success:
        if first_success and cid == 'tuto_p0':
            posts = data.setdefault('forum_posts', {}).setdefault('introductions', [])
            review_id = 'review:tuto_p0'
            if not any(post.get('id') == review_id for post in posts):
                posts.append(social._post(review_id, peer, f"Je confirme une première livraison vérifiée de {state.player_handle}. Son accès à la communauté est ouvert. Les détails du dossier restent privés.", event['minute']))
        if not first_success: text = 'Ce dossier est déjà réglé. Le rejouer ne rapporte ni prime ni réputation, et tes choix de carrière ne changent pas.'
        else:
            forum = state.contract.get('bounty',{}).get('forum','breachboard')
            gain = state.contract.get('reputation',0)
            text = f"Dossier vérifié : {state.payout} ₵ crédités dans ColdVault. Réputation {forum} : +{gain}."
            if cid == 'dossier_contretemps':
                decision = data.get('choices', {}).get('contretemps', '')
                text += ' Le report au 12 novembre est confirmé. '+('Cobalt corrige son annonce après ton signalement, et bytewarden en tiendra compte pour la recommandation finale.' if decision.endswith('_signaler') else 'Je garde les preuves en privé. Hexcache apprécie la discrétion, il s’en souviendra pour sa prochaine proposition.')
            if cid == 'intro_terminal': text += ' Première lecture terminée. La prochaine carte te fait découvrir le réseau. Prends le temps de relire tes résultats.'
            elif cid == 'tuto_p0': text += ' Je réponds de ton premier travail. BreachBoard et les fournisseurs te sont ouverts. Le règlement est dans ColdVault, et tu peux continuer l’acte I avec le matériel de départ.'
            if any(alert.severity == 'CRITICAL' for alert in state.alerts): text += ' La livraison est acceptée, mais il y a des alertes critiques dans le rapport. Relis la chronologie avant le prochain dossier.'
            if cid == 'act1_litige': text += ' Ta décision est conservée : ' + ('les preuves ont été publiées dans le fil.' if data.get('choices',{}).get('litige118') == 'publication' else 'les preuves restent dans la médiation privée.')
    else:
        text = 'Dossier interrompu : aucune prime ni réputation ajoutée. ' + ('Relis le rapport et demande aide avant de retenter.' if failures == 0 else 'Ça fait plusieurs tentatives. Vérifie une observation à la fois et demande un indice au client.')
        text += ' Tu gardes les accès déjà obtenus. Une route déjà payée pour ce dossier reste couverte.'
    step = view({**data, 'active': None})
    if step and success: text += ' Prochaine piste : ' + step['title'] + ' (' + step['app'] + ').'
    # Retour immédiat du client, stable entre rafraîchissements et reprises.
    data.setdefault('conversations',{}).setdefault(ident, social._message(ident, peer, channel, peer, text, event['minute']))
