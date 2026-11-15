"""Relations tirées des décisions de carrière, stables après une reprise."""
from copy import deepcopy


def trust_offer(data):
    decision = data.get('choices', {}).get('contretemps', '')
    if not decision: return None
    candidates = ['act1_recommandation'] if decision.endswith('_signaler') else ['act1_echantillon', 'act1_boutique', 'act1_recommandation']
    # The first offer designated at resolution stays fixed, even after it is paid.
    assigned = data.get('trust_offer')
    if assigned is not None: return assigned or None
    return next((cid for cid in candidates if cid not in data.get('completed', [])), None)


def _contretemps(data):
    decision = data.get('choices', {}).get('contretemps', '')
    if not decision: return {}
    correction = decision.endswith('_signaler')
    target = trust_offer(data)
    titles = {'act1_recommandation': 'la recommandation finale', 'act1_echantillon': 'Échantillon gratuit', 'act1_boutique': 'Derrière la boutique'}
    detail = ('Prime de confiance de 30 ₵ incluse dans '+titles[target]+'.') if target else 'Les règlements déjà effectués restent inchangés.'
    if target in data.get('completed', []): detail = 'La prime de confiance est déjà réglée. Rejouer le dossier ne la verse pas une deuxième fois.'
    return {
        'miette': dict(label='Confiance établie', detail='Tu as vérifié les sources avant de conclure. '+('Tu as demandé une correction.' if correction else 'Tu as respecté la remise confidentielle.')),
        'k0rvid': dict(label='Garant de tes preuves' if correction else 'Discrétion reconnue', detail='La décision sur CT-26-071 est conservée dans ta carrière.'),
        'bytewarden' if correction else 'hexcache': dict(label='Correction documentée' if correction else 'Partenaire discret', detail=detail),
    }


MILESTONES = {
    'k0rvid': ('act1_partage', 'Livraisons vérifiées', 'Tu sais faire la différence entre un accès invité, une archive et la pièce à livrer.'),
    'hexcache': ('act1_boutique', 'Périmètre respecté', 'Vu ton travail sur Pivoine, je t’ai recommandé à 0xvanta.'),
    '0xvanta': ('act1_empreinte', 'Vérifications fiables', 'Tu as distingué une empreinte, une authentification et une copie relue.'),
    'nullroute': ('mauvaise_adresse', 'Contradiction acceptée', 'Tu as corrigé mon attribution avec les sources. Je préfère ça à une livraison sur la mauvaise cible.'),
}


def view(data):
    completed = data.get('completed', [])
    relations = {peer: dict(label=label, detail=detail) for peer, (cid, label, detail) in MILESTONES.items() if cid in completed}
    from .curriculum import current
    if current(data) and '0xvanta' in relations and 'act1_empreinte' not in data.get('legacy_completed',[]): relations['0xvanta']['detail']='Tu as vérifié une passation de lecture, l’accès et la copie courante.'
    relations.update(_contretemps(data))
    for peer,cid,label,detail in [
        ('cendre','act2_polkit','Versions recoupées','Tu as distingué l’image vulnérable de celle corrigée.'),
        ('traverse','act2_pivot','Passage vérifié','Tu as vérifié le service depuis la bonne origine réseau.'),
        ('iris','act2_annuaire','Collecte traçable','Tu as relié les objets collectés à leurs relations sans inventer un accès.'),
        ('quartz','act2_binome','Partenaire confirmé','La passation finale et son périmètre sont conservés.')]:
        if cid in completed: relations[peer] = dict(label=label,detail=detail)
    decision = data.get('choices', {}).get('litige118')
    if decision:
        public = decision == 'publication'
        previous = relations.get('bytewarden', {}).get('detail', '')
        relations['bytewarden'] = dict(label='Preuves publiques assumées' if public else 'Médiation de confiance', detail=('Tu as choisi une résolution publique fondée sur les deux pièces.' if public else 'Tu as confié les deux pièces à la modération sans publier ton intervention.') + (' '+previous if previous else ''))
    from .conversation_scenes import bonds
    labels = {'professionnel': 'Lien professionnel choisi', 'amitie': 'Lien amical choisi',
              'attirance': 'Attirance partagée', 'rivalite_amicale': 'Rivalité amicale',
              'reserve': 'Distance préservée', 'dialogue': 'Dialogue ouvert', 'exigeant': 'Franchise assumée',
              'humour': 'Complicité', 'complicite': 'Complicité'}
    for peer, bond in bonds(data).items():
        relation = relations.setdefault(peer, dict(label='Premiers échanges', detail='Tes réponses de conversation sont conservées.'))
        relation['bond'] = bond
        if bond.get('stance') in labels:
            previous_detail = relation['detail'] if peer in relations and relation['label'] != 'Premiers échanges' else ''
            relation.update(label=labels[bond['stance']], detail='Tu as choisi la nature de ce lien. Tu pourras la préciser lors des prochaines conversations.' + (' ' + previous_detail if previous_detail else ''))
    return relations


def conversation_reply(data, peer, text):
    """Rappelle une décision réellement prise, dans la voix du personnage.

    Les libellés de la fiche relation restent à l'interface. Une conversation
    ne doit pas sonner comme une lecture de cette fiche.
    """
    from .dialogue import intent
    topic = intent(text)
    if topic not in {'trust', 'dispute', 'unknown'}:
        return None
    if topic == 'unknown' and 'af-26-118' not in text.casefold():
        return None
    choices = data.get('choices', {})
    decision = choices.get('contretemps', '')
    if peer == 'miette' and decision and topic == 'trust':
        return ('Je repense à Cobalt. Tu as vérifié avant de demander la correction. '
                'J’aurais aimé avoir ce réflexe sans ton aide.' if decision.endswith('_signaler') else
                'Pour Cobalt, tu as tenu la remise en privé. Je sais pourquoi on l’a fait. '
                'Je me demande encore si on aurait dû prévenir les autres, ça ne veut pas dire que je t’en veux.')
    if peer == 'bytewarden' and choices.get('litige118'):
        return ('Sur le 118, tu as publié les deux pièces. Ça m’a mis dans une position difficile, '
                'mais je ne vais pas te demander de regretter une comparaison juste.'
                if choices['litige118'] == 'publication' else
                'Tu m’as confié les pièces du 118 sans les publier. Je garde cette intervention privée. '
                'Ta recommandation ne dépend pas de changer ce choix.')
    if peer == 'nullroute' and 'mauvaise_adresse' in data.get('completed', []):
        return 'Mon tableau Aquila était faux. Tu l’as dit avant de livrer sur la mauvaise cible. Ça m’a vexé sur le moment. Je préfère ça à quelqu’un qui me laisse me planter.'
    return None


def record(career, state):
    """Retours de relation réservés à la première réussite ; ids stables à la reprise."""
    if career.data.get('campaign_version', 1) < 3: return
    from . import social
    cid = state.contract['contract_id']
    reactions = {
        'act1_partage': ('k0rvid', 'Bien reçu, c’est la bonne référence. Après Ravelle, t’as montré que tu sais aussi choisir quelle version livrer. Je fais passer le mot : les prochains clients te laisseront plus de liberté sur les vérifications.'),
        'act1_boutique': ('hexcache', 'Tu as vérifié mon échantillon avant de toucher à Pivoine, et tu as livré sans sortir du périmètre. J’en parle à 0xvanta. Avec lui, fais bien la différence entre les droits qu’on t’annonce et ceux que tu constates.'),
        'act1_empreinte': ('0xvanta', 'La passation suffisait pas. T’as vérifié l’accès et relu la copie, c’est ce qu’il fallait. Je confirme à nullroute. Son laboratoire amène une notion nouvelle, demande-lui les repères si besoin.'),
        'mauvaise_adresse': ('nullroute', 'Mon tableau était faux. Tu as corrigé l’attribution avant de récupérer quoi que ce soit, et ça c’est une raison de te faire confiance. La prochaine fois je séparerai mieux une adresse reprise d’une vieille note et une cible confirmée.'),
    }
    if cid == 'act1_litige':
        public = career.data.get('choices', {}).get('litige118') == 'publication'
        reactions[cid] = ('bytewarden', ('Tu as rendu les deux pièces publiques. Ce que je retiens, c’est que ta comparaison se vérifie.' if public else 'Tu as choisi la médiation privée, avec les mêmes preuves. Je respecte ça, ton intervention reste hors du fil public.') + ' J’en tiendrai compte dans la recommandation finale, sans te redemander de prendre position.')
    from .curriculum import current
    if cid=='act1_empreinte' and current(career.data) and cid not in career.data.get('legacy_completed',[]):
        reactions[cid]=('0xvanta','La passation suffisait pas. T’as vérifié l’accès et relu la copie, c’est ce qu’il fallait. Je confirme à nullroute. Son dossier porte sur un service et un compte limité, aucune exploitation binaire à prévoir.')
    if current(career.data) and cid not in career.data.get('legacy_completed',[]):
        reactions.update({
            'act1_portail':('0xvanta','T’as comparé les droits annoncés avec ce que la session laissait vraiment lire. Bien. Pour la passation suivante je fournis le compte. À toi de vérifier qu’il est valide et de trouver la pièce courante. Pas besoin de chercher un autre accès.'),
            'act1_service':('nullroute','La configuration et le compte SQL disent la même chose : un accès en lecture, limité aux tickets. Tu as livré sans en sortir. Pour le prochain dossier je t’envoie mon tableau d’adresses. Recoupe-le, mes notes peuvent être fausses aussi.')})
    if cid not in reactions: return
    peer, text = reactions[cid]
    ident = 'relationship:'+cid
    minute = social.prepare(career)['minute']
    career.data.setdefault('conversations', {}).setdefault(ident, social._message(ident, peer, 'chordly', peer, text, minute))


def _continuity(data, definitions):
    completed = data.get('completed', [])
    notes = {}
    if 'act1_partage' in completed:
        notes['act1_echantillon'] = 'k0rvid m’a confirmé ta livraison de Nacre. Ici j’attends surtout que tu vérifies ma propre annonce. Une recommandation, ça remplace pas les données.'
    if 'act1_boutique' in completed:
        notes['act1_portail'] = 'hexcache confirme ta livraison de Pivoine. Je te laisse choisir la comparaison utile. Ne collecte rien au-delà du document demandé.'
    if 'act1_empreinte' in completed:
        notes['act1_service'] = '0xvanta confirme que tu as vérifié la passation. Mon dossier contient un binaire. Je fournis les repères et un script, ensuite tu contrôles les droits obtenus.'
    if 'mauvaise_adresse' in completed:
        notes['act1_litige'] = 'nullroute a reconnu que tu avais corrigé son tableau. Ici aussi ton client ou ton vendeur peut se tromper. Je déciderai sur les pièces datées.'
    choice = data.get('choices', {}).get('litige118')
    if choice:
        notes['act1_recommandation'] = ('Ta publication du litige 118 reste dans le fil public.' if choice == 'publication' else 'Ton intervention sur le litige 118 reste en médiation privée. T’as pas à la publier pour avoir ma recommandation.') + ' Pour ce dernier dossier une seule voie suffit, et les deux paient la même prime.'
    decision = data.get('choices', {}).get('act2_garant')
    if decision:
        notes['act2_binome'] = ('Tu as refusé la promesse de domaine administrateur.' if decision.startswith('refus') else 'Tu as renégocié une délégation de lecture.') + ' Notre binôme s’en tient aux droits vérifiés. Les deux voies paient la même prime.'
    from .curriculum import current
    if current(data) and 'act1_empreinte' in completed:
        notes['act1_service']='0xvanta confirme ta vérification de passation. Mon dossier porte sur un service et un compte SQL limité. Je demande ni exploit binaire ni accès root.'
    for cid, note in notes.items():
        if cid not in definitions or definitions[cid].get('definition_pinned'): continue
        for key in ('intro', 'brief'): definitions[cid][key] = definitions[cid].get(key, '')+'\n\n'+note
    return definitions


def offers(data, definitions):
    definitions = _continuity(data, deepcopy(definitions))
    decision = data.get('choices', {}).get('contretemps', '')
    if data.get('play_mode') == 'demo':
        from .onboarding import DEMO_STAGES
        for index, demo_id in enumerate(DEMO_STAGES, 1):
            if demo_id in definitions:
                title = definitions[demo_id]['bounty']['title'].split(' - ', 1)[-1]
                definitions[demo_id]['bounty']['title'] = f'Démo {index}/4 - {title}'
    if not decision: return definitions
    correction = decision.endswith('_signaler')
    cid = trust_offer(data)
    contract = definitions.get(cid)
    if contract and not contract.get('definition_pinned'):
        note = ('Ta correction de CT-26-071 était documentée.' if correction else 'Tu as respecté la confidentialité de CT-26-071.') + ' J’ajoute une prime de confiance de 30 ₵ à ce règlement, une seule fois.'
        contract['reward'] += 30
        for key in ('intro', 'brief'): contract[key] = contract.get(key, '') + '\n\n' + note
        contract['bounty']['body'] += '\n' + note
    return definitions
