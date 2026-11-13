"""Indices écrits et progressifs, limités à l'étape déjà atteinte."""
def progressive(state, key, hints, full, detailed=False):
    if not hints: return None
    requests=state.tool_data.setdefault('guidance_requests',{})
    level=requests.get(key,0)
    if detailed or level >= len(hints):
        requests[key]=len(hints)
        return 'Rappel détaillé de cette étape :\n'+full
    requests[key]=level+1
    return f'Indice {level+1}/{len(hints)} : '+hints[level]+'\nDemande un autre indice si nécessaire ; le rappel détaillé vient ensuite.'


def hint(state, *, detailed=False):
    contract=state.contract
    guide=contract.get('guide',[])
    previous=state.guide_index-1
    current=guide[previous] if 0 <= previous < len(guide) else contract
    return progressive(state,contract['contract_id']+':guide:'+str(previous),current.get('hints',[]),current.get('message',contract['brief']),detailed)
