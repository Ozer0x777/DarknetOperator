"""Acte II : dossiers séquentiels, contacts et bilan persistant."""
CHAPTERS=[
 ('act2_passation','Une vieille passation','cendre'),('act2_compte','Un compte ne suffit pas','cendre'),
 ('act2_polkit','Une machine mal entretenue','cendre'),('act2_reseau','Derrière le serveur','traverse'),
 ('act2_pivot','Le passage étroit','traverse'),('act2_annuaire','Le réseau du prestataire','iris'),
 ('act2_service','Un service trop privilégié','iris'),('act2_lateral','Changer de machine','quartz'),
 ('act2_garant','La passation douteuse','relay'),('act2_binome','Premier travail en binôme','quartz')]


def lock_reason(data,contract):
    if contract.get('act')!=2:return ''
    if not data.get('forum_invitation_accepted'):return 'Accepte la recommandation de l’acte I avant ce dossier.'
    cid=contract['contract_id'];ids=[row[0] for row in CHAPTERS]
    if cid in ids:
        missing=next((i for i in ids[:ids.index(cid)] if i not in data['completed']),None)
        if missing:return 'Poursuis l’acte II : '+next(row[1] for row in CHAPTERS if row[0]==missing)
    return ''


def view(data):
    done=data.get('completed',[]);unlocked=bool(data.get('forum_invitation_accepted'));rows=[]
    for n,(cid,title,peer) in enumerate(CHAPTERS,1):
        ready=unlocked and all(row[0] in done for row in CHAPTERS[:n-1])
        rows.append(dict(id=cid,number=n,title=title,peer=peer,channel='telegrid',status='completed' if cid in done else ('available' if ready else 'locked')))
    return dict(total=len(rows),completed=sum(r['status']=='completed' for r in rows),chapters=rows,unlocked=unlocked)


def journey(data):
    if not data.get('forum_invitation_accepted') or not data.get('act2_started'):return None
    next_row=next((r for r in view(data)['chapters'] if r['status']!='completed'),None)
    if not next_row:return dict(title='Acte II terminé - la passation tient',detail='Tes preuves et tes choix sont conservés. Les actes III et IV ne sont pas encore prêts. En attendant, tu peux faire les contrats facultatifs et lire les discussions.',app='Telegrid',peer='quartz')
    return dict(title='Acte II · '+str(next_row['number'])+'/10 - '+next_row['title'],detail='Le dossier t’attend sur Telegrid. Le résultat dépend de tes commandes, de tes observations et des droits que tu obtiens. Les indices ne retirent rien à la prime.',app='Telegrid',peer=next_row['peer'],contract_id=next_row['id'])


def settle(career,state):
    if state.contract.get('act')!=2:return
    from . import social
    cid=state.contract['contract_id'];peer=state.contract['client']['handle'];choice=career.data.get('choices',{})
    lines={
      'act2_passation':'Une correspondance hors ligne, ça prouve pas encore un accès. Vérifie le compte sur la machine de la passation.',
      'act2_compte':'L’accès est limité, et ta livraison reste dedans. Le prochain dossier parle de versions et de correctifs.',
      'act2_polkit':'Tu as fait la différence entre l’image vulnérable et l’image corrigée. Traverse va maintenant regarder ce que cette machine voit du réseau.',
      'act2_reseau':'Tu as trouvé le réseau interne. Il va falloir un passage précis. Connaître une IP, ça rend pas son service joignable.',
      'act2_pivot':'Le passage est vérifié. Iris regarde l’annuaire du prestataire. Elle te demandera de pas confondre la collecte du graphe et les droits réels.',
      'act2_annuaire':'Collecte reçue. Un lien dans le graphe, c’est une piste à vérifier. C’est pas un accès que t’as déjà.',
      'act2_service':'L’empreinte correspond. Quartz t’attend pour vérifier où ce compte peut vraiment ouvrir une session.',
      'act2_lateral':'Copie reçue. Relay a une passation à comparer avec tes observations. Prends pas la promesse du vendeur pour une preuve.',
      'act2_garant':('Tu as refusé la passation annoncée comme illimitée.' if choice.get('act2_garant','').startswith('refus') else 'Tu as négocié une passation limitée et vérifiable.')+' Quartz conserve cette décision pour la finale.',
      'act2_binome':'La passation est close. '+('Tu as livré par le passage HTTP interne.' if choice.get('act2_binome')=='binome_pivot' else 'Tu as livré par les droits SMB vérifiés.')+' Le partenaire reçoit les preuves du seul lot demandé.'}
    if cid not in lines:return
    minute=social.prepare(career)['minute'];ident='act2:outcome:'+cid
    career.data.setdefault('conversations',{}).setdefault(ident,social._message(ident,peer,'telegrid',peer,lines[cid],minute))
