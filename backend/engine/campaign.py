"""Acte I : progression, choix persistants et invitation reçue sur le forum."""
CHAPTERS=[
 ('tuto_p0','Sous recommandation','k0rvid','chordly'),
 ('act1_partage','Une porte oubliée','k0rvid','chordly'),
 ('act1_echantillon','Échantillon gratuit','hexcache','chordly'),
 ('act1_boutique','Derrière la boutique','hexcache','chordly'),
 ('act1_portail','Le carnet d’adresses','0xvanta','chordly'),
 ('act1_empreinte','Le mot de passe de trop','0xvanta','chordly'),
 ('act1_service','Un service fragile','nullroute','chordly'),
 ('mauvaise_adresse','Mauvaise adresse','nullroute','chordly'),
 ('act1_litige','La réputation se paie','bytewarden','chordly'),
 ('act1_recommandation','Quelqu’un répond de toi','bytewarden','chordly')]


def enabled(data):return data.get('campaign_version',1)>=3

# Contrats de la première campagne : absents du forum tant que l'invitation de l'acte I n'est pas acceptée.
INVITATION_ONLY={'morel','rival','varenne','affiliation','grand_compte','offre_urgente'}


def hidden_from_board(data,contract_id):
    """Vrai si l'annonce ne doit pas encore apparaître sur le forum pour cette carrière."""
    from .curriculum import current
    if current(data) and contract_id=='side_empreinte' and contract_id not in data.get('completed',[]):return True
    return enabled(data) and not data.get('forum_invitation_accepted') and contract_id in INVITATION_ONLY


def lock_reason(data,contract):
    cid=contract['contract_id']
    ids=[c[0] for c in CHAPTERS]
    if cid in ids[1:] and (enabled(data) or cid!='mauvaise_adresse'):
        previous=ids[:ids.index(cid)]
        missing=next((i for i in previous if i not in data['completed']),None)
        if missing:
            from .curriculum import title as curriculum_title
            return 'Poursuis le chapitre précédent : '+curriculum_title(data,missing,next(c[1] for c in CHAPTERS if c[0]==missing))
    if enabled(data) and (contract.get('tier',0)>=2 or cid in {'morel','rival','offre_urgente'}) and not data.get('forum_invitation_accepted'):
        return 'Termine l’acte I et accepte ton invitation dans les MP de BreachBoard.'
    return ''


def summary(data):
    from .curriculum import title as curriculum_title
    completed=data['completed'];rows=[]
    for index,(cid,title,peer,channel) in enumerate(CHAPTERS,1):
        ready=all(c[0] in completed for c in CHAPTERS[:index-1])
        rows.append(dict(id=cid,number=index,title=curriculum_title(data,cid,title),peer=peer,channel=channel,status='completed' if cid in completed else ('available' if ready else 'locked')))
    return dict(completed=sum(r['status']=='completed' for r in rows),total=10,chapters=rows,
        invitation_accepted=bool(data.get('forum_invitation_accepted')),new_progression=enabled(data))


def settle(career,state):
    data=career.data
    data.setdefault('choices',{}).update(state.tool_data.get('decisions',{}))
    from .relationships import record as record_relationship
    record_relationship(career, state)
    from .act2 import settle as settle_act2
    settle_act2(career, state)
    if state.contract['contract_id'] == 'dossier_contretemps':
        from .relationships import trust_offer
        data['trust_offer'] = trust_offer(data) or ''
    if state.contract['contract_id']=='act1_litige':
        from . import social
        ident='act1-litige-resolution'
        if data.get('choices',{}).get('litige118')=='publication':
            posts=data.setdefault('forum_posts',{}).setdefault('act1-litige',[])
            if not any(post.get('id')==ident for post in posts):
                posts.append(social._post(ident,state.player_handle,'Comparaison vérifiée : AF-26-118 daté du 07/11/2026 ; AF-24-118 daté du 12/03/2024. Les deux livraisons sont différentes.',data.get('social',{}).get('minute',0)))
        else:
            data.setdefault('forum_messages',{}).setdefault(ident,dict(id=ident,forum='breachboard',author='bytewarden',subject='Médiation confidentielle — dossier 118',body='Tes preuves sont archivées en privé. Le vendeur doit corriger son annonce ; ton pseudo n’est pas publié dans le fil.',minute=data.get('social',{}).get('minute',0),read=False))
    if state.contract['contract_id']!='act1_recommandation':return
    if not all(cid in data['completed'] for cid,*_ in CHAPTERS):return
    messages=data.setdefault('forum_messages',{})
    privacy = 'Tu as choisi une publication documentée lors du litige 118.' if data.get('choices', {}).get('litige118') == 'publication' else 'Tu as choisi la médiation privée lors du litige 118 ; ta recommandation ne t’oblige pas à rendre cette intervention publique.'
    route = 'La livraison finale a été vérifiée par la voie SQLmap.' if data.get('choices', {}).get('finale') == 'finale_sqlmap' else 'La livraison finale a été vérifiée par le connecteur SQL limité.'
    messages.setdefault('act1-invitation',dict(id='act1-invitation',forum='breachboard',author='bytewarden',subject='Invitation — quelqu’un répond de toi',
        body='k0rvid, hexcache et nullroute ont confirmé tes livraisons. Ton dossier de litige est archivé. Tu as montré que tu sais vérifier une source et tenir un engagement. Je te propose une place sur Exployt. Accepte cette invitation ici ; configure ensuite une route Tor dans la boutique. Garde ton pseudo, on répond de toi. '+privacy+' '+route,
        minute=data.get('social',{}).get('minute',0),read=False,invitation='exployt'))


def accept(career,ident):
    message=career.data.get('forum_messages',{}).get(ident)
    if not message or message.get('invitation')!='exployt':raise ValueError('Invitation introuvable.')
    if not all(cid in career.data['completed'] for cid,*_ in CHAPTERS):raise ValueError('La recommandation n’est pas validée.')
    career.data['forum_invitation_accepted']=True
    career.data['tier']=max(2,career.data['tier'])
    message['accepted']=True;message['read']=True
    career.save()
