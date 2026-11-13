"""Début de campagne par contact privé ; compatibilité avec les carrières existantes."""
STAGES = ['intro_terminal','intro_recon','intro_login','intro_transfer','intro_evidence','intro_campaign','intro_hash','intro_windows','tuto_p0']


def enabled(data): return data.get('campaign_version', 1) >= 2

def forum_unlocked(data): return not enabled(data) or 'tuto_p0' in data.get('completed', [])

CURRENT_STAGES = [cid for cid in STAGES if cid != 'intro_hash']

DEMO_STAGES = ['intro_terminal', 'intro_recon', 'intro_evidence', 'dossier_contretemps']


def stages(data):
    if data.get('play_mode') == 'demo': return DEMO_STAGES
    from .curriculum import current
    return CURRENT_STAGES if current(data) else STAGES


def next_stage(data):
    active=data.get('active') or {};contract=active.get('contract') or {}
    if active.get('status')=='RUNNING' and contract.get('legacy_in_progress') and contract.get('onboarding'): return contract['contract_id']
    return next((name for name in stages(data) if name not in data.get('completed', [])), None)


def lock_reason(data, contract):
    if not enabled(data): return ''
    from .curriculum import lock_reason as curriculum_lock
    reason=curriculum_lock(data,contract)
    if reason:return reason
    if data.get('play_mode') == 'demo':
        cid = contract['contract_id']
        if cid not in DEMO_STAGES or (cid not in data.get('completed', []) and cid != next_stage(data)):
            return 'Poursuis le parcours de démo proposé sur Chordly.'
        return ''
    if contract['contract_id'] == 'dossier_contretemps' and 'act1_partage' not in data.get('completed', []):
        return 'Le dossier facultatif arrive après Une porte oubliée.'
    if forum_unlocked(data): return ''
    if contract['contract_id'] != next_stage(data): return 'Termine le dossier proposé par k0rvid sur Chordly.'
    return ''
