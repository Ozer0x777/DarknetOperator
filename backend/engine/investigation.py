"""Comptes rendus souples sur la forme, vérifiés sur les preuves du monde."""
import unicodedata
import re
from .win_conditions import objective_met

ALIASES = {
    'livraison': ['livre','livree','livres','livrees','transmis','transmise','transmises','remis','remise','remises'],
    'rapport': ['bilan','analyse'], 'preuve': ['constat','verification'],
    'publier': ['publication','publie'], 'mediation': ['arbitrage prive'],
    'dossier': ['lot'],
}


def normalized(text):
    text=text.translate(str.maketrans({'‑':'-','–':'-','—':'-','’':"'"}))
    return ' '.join(''.join(c for c in unicodedata.normalize('NFKD', text.casefold()) if not unicodedata.combining(c)).split())


def contains(words, token):
    alternatives=[normalized(token),*ALIASES.get(normalized(token),[])]
    return any(re.search(r'(?<!\w)'+re.escape(value).replace(r'\-',r'\s*-\s*')+r'(?!\w)',words) for value in alternatives)


def flags(state):
    return state.tool_data.setdefault('investigation', {}).setdefault('steps', [])


def observe_forum(state, thread_id):
    if not state.contract or thread_id not in state.contract.get('investigation_threads', []): return
    seen = state.tool_data.setdefault('investigation', {}).setdefault('threads', [])
    if thread_id not in seen: seen.append(thread_id)


def answer(state, text):
    if not state.contract: return None
    words=normalized(text)
    candidates=[step for step in state.contract.get('investigation_steps',[]) if all(contains(words,token) for token in step['tokens'])]
    if not candidates: return None
    groups={step.get('exclusive_group') for step in candidates if step.get('exclusive_group')}
    decisions=state.tool_data.setdefault('decisions',{})
    for group in groups:
        matching=[step for step in candidates if step.get('exclusive_group')==group]
        if len({step.get('choice', step['id']) for step in matching}) > 1:
            if group in decisions: return 'Ce choix a déjà été enregistré : '+decisions[group]
            return 'Tu évoques plusieurs décisions. Confirme une seule option avant de poursuivre. Aucun choix n’a été enregistré.'
    if '?' in text and re.match(r"^(?:dois|faut|comment|puis|est-ce|quelle|que choisir|j'hesite)\b",words):
        return 'Je ne prends pas une question pour une livraison ou une décision. Confirme ton compte rendu quand tu es prêt ; aucun choix n’a été enregistré.'
    intent=any(token in {'livraison','publier','mediation','signaler','discret','refuser','renegocier'} for step in candidates for token in step['tokens'])
    if intent and (re.search(r'\b(?:pas|sans|aucun)\s+(?:signaler|discret|refuser|renegocier)\b', words) or re.search(r'\b(?:pas(?: encore)?(?: de)?|sans|aucune?|rien(?: de)?)\s+(?:livr\w*|transm\w*|remis\w*|publi\w*|mediat\w*)',words) or re.search(r'\b(?:livr\w*|transm\w*|publi\w*)\s+pas\b',words) or 'pas encore' in words or re.search(r'\b(?:pas|non)\s+(?:termine\w*|valide\w*|pret\w*)',words)):
        return 'Ton message ne confirme pas encore la livraison ou la décision. Rien n’a été validé ; tu peux poursuivre tes vérifications.'
    # Si plusieurs voies sont nommées, une voie réellement prouvée prime sur une voie incomplète.
    ready=[step for step in candidates if all(objective_met(state,c) for c in step.get('requires',[]))]
    step=(ready or candidates)[0]
    if step['id'] in flags(state): return step['already']
    group=step.get('exclusive_group')
    if group and group in decisions: return 'Ce choix a déjà été enregistré : '+decisions[group]
    missing=[c for c in step.get('requires',[]) if not objective_met(state,c)]
    if missing:
        names={'file_read':'lecture du document à jour','forum_read':'lecture du fil de discussion','query_result':'vérification des données SQL fournies','table_export':'export complet et relu dans ~/loot','export_matches':'copie locale conforme et relue dans ~/loot','intact_download':'transfert du bon document et relecture','investigation_step':'validation de l’étape précédente'}
        def label(condition):
            if condition['type']!='tool_fact':
                return names.get(condition['type'],{'host_compromised':'accès à la cible vérifié','hash_recovered':'correspondance du mot de passe et de l’empreinte'}.get(condition['type'],'observation vérifiée du dossier'))
            key=condition.get('key','')
            labels={'smb:list:':'liste du partage observée','sqlmap:injection:':'paramètre de la cible vérifié','sqlmap:dump:':'export par la voie SQLmap observé','mysql:query:':'requête sur le service SQL distant observée','lab:checksec':'protections du binaire observées','lab:symbols':'symboles du binaire observés','lab:access':'session du laboratoire vérifiée','http:':'réponse du service web observée'}
            return next((value for prefix,value in labels.items() if key.startswith(prefix)),'observation vérifiée du dossier')
        labels=list(dict.fromkeys(label(c) for c in missing))
        return 'Il manque encore : '+', '.join(labels)+'. Demande un indice pour préciser la prochaine vérification.'
    if group: decisions[group]=step['id']
    flags(state).append(step['id'])
    state.discovered.update(step.get('discover', []))
    return step['response']


def help_text(state, detailed=False):
    if not state.contract: return None
    pending=[step for step in state.contract.get('investigation_steps',[]) if step['id'] not in flags(state) and step.get('exclusive_group') not in state.tool_data.get('decisions',{})]
    if not pending: return None
    # Ne pas proposer une phase ultérieure avant la validation du compte rendu précédent.
    eligible = [step for step in pending if all(objective_met(state, c) for c in step.get('requires', []) if c['type'] == 'investigation_step')]
    step=max(eligible or pending,key=lambda item: sum(objective_met(state,c) for c in item.get('requires',[])))
    from .guidance import progressive
    if all(objective_met(state, c) for c in step.get('requires', [])):
        group = step.get('exclusive_group')
        options = [item for item in pending if group and item.get('exclusive_group') == group and all(objective_met(state, c) for c in item.get('requires', []))] if group else [step]
        reports = ' ou '.join(dict.fromkeys('« '+' '.join(item['tokens'])+' »' for item in options))
        return 'Les preuves nécessaires à cette étape sont vérifiées. Confirme maintenant ton compte rendu : '+reports+'. Choisis une seule option ; aucune décision n’est prise à ta place.'
    for phase in step.get('help_stages', []):
        if not all(objective_met(state, c) for c in phase['requires']):
            key = state.contract['contract_id']+':investigation:'+step['id']+':'+phase['id']
            return progressive(state, key, phase['hints'], phase['hint'], detailed)
    return progressive(state,state.contract['contract_id']+':investigation:'+step['id'],step.get('hints',[]),step['hint'],detailed) or step['hint']
