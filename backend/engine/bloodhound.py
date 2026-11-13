"""Import et analyse des seules collectes virtuelles du scénario actif."""
import hashlib
import json
from .data_tools import fact


def view(state):
    files=[p for p,v in state.terminal_files.items() if p.startswith('/home/operator/loot/') and v.startswith('VIRTUAL-ZIP\n')]
    graph=state.tool_data.get('bloodhound',{})
    return dict(files=files,nodes=graph.get('nodes',[]),edges=graph.get('edges',[]),source=graph.get('source',''),collected_for=graph.get('contract_id',''),stale=bool(graph and graph.get('contract_id')!=(state.contract or {}).get('contract_id')))


def import_archive(state,path):
    if not path.startswith('/home/operator/loot/'):raise ValueError('Récupère la collecte dans ~/loot avant de l’importer.')
    raw=state.terminal_files.get(path,'')
    expected=state.tool_data.get('facts',{}).get('sharphound:collection',{}).get('digest')
    if not raw.startswith('VIRTUAL-ZIP\n') or not expected or hashlib.sha256(raw.encode()).hexdigest()!=expected:raise ValueError('Cette archive ne correspond pas à la collecte observée dans ce dossier.')
    try:
        members=json.loads(raw.split('\n',1)[1]);nodes=[];edges=[]
        for filename,contents in members.items():
            doc=json.loads(contents);kind=doc['meta']['type']
            if kind not in {'users','groups','computers'} or doc['meta']['count']!=len(doc['data']):raise ValueError('Format de collecte invalide.')
            for obj in doc['data']:
                ident=obj['ObjectIdentifier'];nodes.append(dict(id=ident,name=obj['Properties']['name'],kind=kind))
                for member in obj.get('Members',[]):edges.append(dict(source=member['ObjectIdentifier'],target=ident,type='MemberOf'))
                for ace in obj.get('Aces',[]):edges.append(dict(source=ace['PrincipalSID'],target=ident,type=ace['RightName']))
    except (ValueError,KeyError,TypeError,AttributeError) as exc:raise ValueError('Collecte JSON invalide.') from exc
    state.tool_data['bloodhound']=dict(source=path,nodes=nodes,edges=edges,digest=expected,contract_id=(state.contract or {}).get('contract_id',''))
    fact(state,'bloodhound:import',nodes=len(nodes),edges=len(edges))
    return view(state)
