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
    if target in data.get('completed', []): detail = 'La prime de confiance a été réglée ; une reprise ne la verse pas à nouveau.'
    return {
        'miette': dict(label='Confiance établie', detail='Tu as vérifié les sources avant de conclure. '+('Tu as demandé une correction.' if correction else 'Tu as respecté la remise confidentielle.')),
        'k0rvid': dict(label='Garant de tes preuves' if correction else 'Discrétion reconnue', detail='La décision sur CT-26-071 est conservée dans ta carrière.'),
        'bytewarden' if correction else 'hexcache': dict(label='Correction documentée' if correction else 'Partenaire discret', detail=detail),
    }


MILESTONES = {
    'k0rvid': ('act1_partage', 'Livraisons vérifiées', 'Tu distingues un accès invité, une archive et la pièce à livrer.'),
    'hexcache': ('act1_boutique', 'Périmètre respecté', 'Ton travail sur Pivoine permet de te recommander à 0xvanta.'),
    '0xvanta': ('act1_empreinte', 'Vérifications fiables', 'Tu as distingué une empreinte, une authentification et une copie relue.'),
    'nullroute': ('mauvaise_adresse', 'Contradiction acceptée', 'Tu as corrigé mon attribution à partir des sources ; je préfère cela à une livraison sur la mauvaise cible.'),
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
    return relations


def record(career, state):
    """Retours de relation réservés à la première réussite ; ids stables à la reprise."""
    if career.data.get('campaign_version', 1) < 3: return
    from . import social
    cid = state.contract['contract_id']
    reactions = {
        'act1_partage': ('k0rvid', 'La bonne référence est reçue. Après Ravelle, tu as montré que tu sais aussi choisir la version à livrer. Je transmets cette recommandation ; les prochains clients te laisseront davantage choisir les vérifications.'),
        'act1_boutique': ('hexcache', 'Tu as vérifié mon échantillon avant de travailler sur Pivoine, puis livré dans le périmètre demandé. J’en parle à 0xvanta : il faudra distinguer les droits annoncés des droits réellement observés.'),
        'act1_empreinte': ('0xvanta', 'La passation seule ne suffisait pas : tu as vérifié l’accès et relu la copie. Je confirme ton travail à nullroute. Son laboratoire introduit une notion nouvelle ; demande-lui les repères au besoin.'),
        'mauvaise_adresse': ('nullroute', 'Mon tableau était faux. Tu as corrigé l’attribution avant la récupération : c’est une raison de te faire confiance. La prochaine fois, je distinguerai mieux une adresse reprise d’une ancienne note et une cible confirmée.'),
    }
    if cid == 'act1_litige':
        public = career.data.get('choices', {}).get('litige118') == 'publication'
        reactions[cid] = ('bytewarden', ('Tu as choisi de rendre les deux pièces publiques. Je retiens la comparaison vérifiable, pas seulement la prise de parole.' if public else 'Tu as choisi la médiation privée avec les mêmes preuves. Je respecte cette limite ; ton intervention reste hors du fil public.') + ' La recommandation finale tiendra compte de cette décision, sans exiger une nouvelle prise de position.')
    from .curriculum import current
    if cid=='act1_empreinte' and current(career.data) and cid not in career.data.get('legacy_completed',[]):
        reactions[cid]=('0xvanta','La passation seule ne suffisait pas : tu as vérifié l’accès et relu la copie. Je confirme ton travail à nullroute. Son dossier portera sur un service et un compte limité ; aucune exploitation binaire n’est attendue.')
    if current(career.data) and cid not in career.data.get('legacy_completed',[]):
        reactions.update({
            'act1_portail':('0xvanta','Tu as comparé les droits annoncés à ce que la session permettait réellement de lire. Pour la passation suivante, je fournis le compte : l’enjeu sera de vérifier sa validité et la pièce courante, pas de chercher un autre accès.'),
            'act1_service':('nullroute','La configuration et le compte SQL racontent la même chose : un accès de lecture limité aux tickets. Tu as livré dans ce périmètre. Pour le prochain dossier, je te transmets mon tableau d’adresses ; recoupe-le, une note de ma part peut aussi être fausse.')})
    if cid not in reactions: return
    peer, text = reactions[cid]
    ident = 'relationship:'+cid
    minute = social.prepare(career)['minute']
    career.data.setdefault('conversations', {}).setdefault(ident, social._message(ident, peer, 'chordly', peer, text, minute))


def _continuity(data, definitions):
    completed = data.get('completed', [])
    notes = {}
    if 'act1_partage' in completed:
        notes['act1_echantillon'] = 'k0rvid m’a confirmé ta livraison de Nacre. Ici, j’attends surtout que tu vérifies ma propre annonce ; une recommandation ne remplace pas les données.'
    if 'act1_boutique' in completed:
        notes['act1_portail'] = 'hexcache confirme ta livraison de Pivoine. Je te laisse choisir la comparaison utile ; n’étends pas la collecte au-delà du document demandé.'
    if 'act1_empreinte' in completed:
        notes['act1_service'] = '0xvanta confirme que tu as vérifié la passation. Mon dossier introduit un binaire : je fournis les repères et un script, puis tu contrôleras les droits obtenus.'
    if 'mauvaise_adresse' in completed:
        notes['act1_litige'] = 'nullroute a reconnu la correction de son tableau. Ici aussi, ton client ou ton vendeur peut se tromper ; ma décision reposera sur les pièces datées.'
    choice = data.get('choices', {}).get('litige118')
    if choice:
        notes['act1_recommandation'] = ('Ta publication du litige 118 reste dans le fil public.' if choice == 'publication' else 'Ton intervention sur le litige 118 reste en médiation privée ; tu n’as pas à la publier pour obtenir ma recommandation.') + ' Pour ce dernier dossier, une seule voie suffit et les deux règlent la même prime.'
    decision = data.get('choices', {}).get('act2_garant')
    if decision:
        notes['act2_binome'] = ('Tu as refusé la promesse de domaine administrateur.' if decision.startswith('refus') else 'Tu as renégocié une délégation de lecture.') + ' Notre binôme s’en tient aux droits vérifiés ; les deux voies règlent la même prime.'
    from .curriculum import current
    if current(data) and 'act1_empreinte' in completed:
        notes['act1_service']='0xvanta confirme ta vérification de passation. Mon dossier porte sur un service et un compte SQL limité ; aucun exploit binaire ni accès root n’est demandé.'
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
                title = definitions[demo_id]['bounty']['title'].split(' — ', 1)[-1]
                definitions[demo_id]['bounty']['title'] = f'Démo {index}/4 — {title}'
    if not decision: return definitions
    correction = decision.endswith('_signaler')
    cid = trust_offer(data)
    contract = definitions.get(cid)
    if contract and not contract.get('definition_pinned'):
        note = ('Ta correction de CT-26-071 était documentée.' if correction else 'Tu as respecté la confidentialité de CT-26-071.') + ' Une prime de confiance de 30 ₵ est incluse dans ce règlement, une seule fois.'
        contract['reward'] += 30
        for key in ('intro', 'brief'): contract[key] = contract.get(key, '') + '\n\n' + note
        contract['bounty']['body'] += '\n' + note
    return definitions
