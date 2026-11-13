"""Progression 4 : actes séparés, variantes et conservation des acquis."""
from copy import deepcopy
from pathlib import Path

VERSION=4
TITLES={'act1_empreinte':'Une passation à vérifier','act1_service':'Un service, des permissions'}
VARIANTS={'tuto_p0','intro_transfer','act1_empreinte','act1_service'}


def current(data):return data.get('campaign_version',1)>=VERSION


def title(data,cid,original):
    return TITLES.get(cid,original) if current(data) and cid not in data.get('legacy_completed',[]) else original


def lock_reason(data,contract):
    if not current(data):return ''
    cid=contract['contract_id'];active=data.get('active') or {}
    if active.get('status')=='RUNNING' and (active.get('contract') or {}).get('contract_id')==cid and (active.get('contract') or {}).get('legacy_in_progress'):return ''
    if cid=='intro_hash' and cid not in data.get('completed',[]):return 'La découverte de Hashcat se fait désormais avec Cendre dans l’acte II.'
    if cid=='side_empreinte' and cid not in data.get('completed',[]):return 'Cet exercice est repris par Empreinte de secours dans les contrats de l’acte II.'
    return ''


def definitions(data,original):
    result=deepcopy(original)
    if not current(data):return result
    from .contracts import load_contract
    for cid in VARIANTS:
        if cid not in result or cid in data.get('legacy_completed',[]):continue
        result[cid]=load_contract(Path(__file__).parents[1]/'contracts/current'/f'{cid}.json')
    from .onboarding import CURRENT_STAGES
    for index,cid in enumerate(CURRENT_STAGES[:-1],1):
        if cid in result and cid not in data.get('legacy_completed',[]):
            label=result[cid]['bounty']['title'].split(' — ',1)[-1]
            result[cid]['bounty']['title']=f'{index:02} — {label}'
    if 'tuto_p0' in result and result['tuto_p0'].get('curriculum_version')==VERSION:
        # Réaffectation de la prime de l’exercice retiré, sans doubler un acquis.
        if 'intro_hash' not in data.get('completed',[]):
            result['tuto_p0']['reward']+=55
            result['tuto_p0']['reputation']+=5
    active=data.get('active') or {};contract=active.get('contract') or {}
    if active.get('status')=='RUNNING' and contract.get('legacy_in_progress'):
        cid=contract['contract_id']
        result[cid]=deepcopy(contract)
        result[cid]['definition_pinned']=True
    return result


def migrate(data):
    """Transformation pure : le stockage/rollback et les sessions restent à l’API."""
    result=deepcopy(data)
    if current(data) or data.get('classic_progression'):return result,False
    version=data.get('campaign_version',1)
    empty=not data.get('completed') and not data.get('active')
    from .onboarding import STAGES
    early=version==2 and not data.get('forum_invitation_accepted') and 'tuto_p0' not in data.get('completed',[]) and all(cid in STAGES for cid in data.get('completed',[]))
    if version!=3 and not empty and not early:return result,False
    result['campaign_version']=VERSION
    result['legacy_completed']=list(data.get('completed',[]))
    active=result.get('active') or {};contract=active.get('contract') or {}
    if active.get('status')=='RUNNING' and contract:
        contract['legacy_in_progress']=True
        contract['curriculum_version']=version
    result['curriculum_notice']='Pour la campagne, le prélude comporte désormais sept exercices. L’acte I privilégie les sources, les accès fournis et les permissions. Hashcat et les techniques avancées sont réservés à l’acte II. Le contrat en cours, les primes et les choix acquis sont conservés.'
    from .social import _message
    result.setdefault('conversations',{}).setdefault('curriculum:v4',_message('curriculum:v4','k0rvid','chordly','k0rvid',result['curriculum_notice'],result.get('social',{}).get('minute',0)))
    return result,True
