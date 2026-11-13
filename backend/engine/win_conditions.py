"""Conditions de fin d'une mission.

Un scénario déclare des `objectives` : la mission est réussie dès qu'ils sont
tous atteints, et échouée si le temps imparti s'écoule avant.

OBJECTIVES est un registre de conditions sur l'état du jeu. Il sert aux
objectifs de victoire et aux étapes du guide d'un contrat (engine/contracts.py).
Nouveau type = nouvelle fonction dans OBJECTIVES, jamais un cas particulier
dans check().
"""
from __future__ import annotations

from functools import lru_cache

from .models import GameState


def _domain_compromised(state: GameState) -> bool:
    return state.domain_compromised


def _host_compromised(state: GameState, host: str) -> bool:
    target = state.hosts.get(host)
    return target is not None and target.status == "COMPROMISED"


def _host_discovered(state: GameState, host: str) -> bool:
    return host in state.discovered


def _credential_owned(state: GameState, username: str, cred_type: str | None = None) -> bool:
    return state.find_credential(username, cred_type) is not None


def _file_exfiltrated(state: GameState, host: str, file: str) -> bool:
    return f"{host}:{file}" in state.exfiltrated


def _encrypted_ratio(state: GameState, percent: int) -> bool:
    return sum((h.encrypted or h.status == "ENCRYPTED") for h in state.hosts.values()) * 100 >= len(state.hosts) * percent


def _backups_destroyed(state: GameState, host: str) -> bool:
    return not state.hosts[host].backups


def _file_read(state, path, host='operator'):
    from .evidence import inspected
    return inspected(state,path,host)


def _session_on_host(state, host):
    return state.terminal_host == host or any(c.get('terminal_host') == host for c in state.terminals.values())


def _local_file_equals(state, path, value):
    return state.terminal_files.get(path, '').strip() == value


def _host_file_equals(state, host, path, value):
    return state.hosts[host].files.get(path, '').strip() == value


def _campaign_submitted(state, username):
    mapping = state.tool_data.get('campaign_contracts', {})
    return any(mapping.get(str(campaign['id'])) == state.conversation_id and any(row.get('email','').split('@')[0] == username and row.get('status') == 'Submitted Data' for row in campaign.get('results', [])) for campaign in state.tool_data.get('gophish', {}).get('campaigns', []))


def _hash_recovered(state, username):
    from .ntlm import nt_hash
    account = state.users.get(username)
    if account is None or not account.password: return False
    from .mission_data import cracked_in_mission
    digest = nt_hash(account.password)
    return state.tool_data.get('hashcat', {}).get('pot', {}).get(digest) == account.password and cracked_in_mission(state, digest)


def _investigation_step(state, step):
    return step in state.tool_data.get('investigation', {}).get('steps', [])


def _forum_read(state, thread):
    return thread in state.tool_data.get('investigation', {}).get('threads', [])


def _http_read(state, host, path):
    return host+':'+path in state.tool_data.get('read_http', [])


def _intact_download(state, host, file, inspected=False):
    content = state.hosts[host].files.get(file)
    return content is not None and _file_exfiltrated(state, host, file) and any(
        path.startswith('/home/operator/loot/') and value == content and (not inspected or _file_read(state,path))
        for path, value in state.terminal_files.items())


def _tool_fact(state, key):
    return key in state.tool_data.get('facts', {})


def _query_result(state, row, database=None, table=None, source=None, unordered=False):
    from .data_tools import canonical_dump
    from collections import Counter
    import json
    reference = (state.contract or {}).get('local_files', {}).get(source, state.terminal_files.get(source)) if source else None
    expected_script = canonical_dump(reference) if reference is not None else None
    for result in state.tool_data.get('queries', []):
        if table is not None and table not in result.get('tables', []): continue
        actual_database = result.get('database')
        if source:
            import hashlib
            if expected_script is None: continue
            if result.get('source_digest'):
                if result['source_digest'] != hashlib.sha256(expected_script.encode()).hexdigest(): continue
            elif state.tool_data.get('sqlite', {}).get(actual_database) != expected_script: continue
        elif database is not None and actual_database != database: continue
        for actual in result.get('rows', []):
            if actual == row: return True
            if unordered:
                expected = Counter(json.dumps(value,sort_keys=True) for value in row)
                found = Counter(json.dumps(value,sort_keys=True) for value in actual)
                if all(found[value] >= count for value,count in expected.items()): return True
    return False


def _decision_made(state, group):
    return group in state.tool_data.get("decisions", {})


def _export_matches(state, key, path, any_path=False, inspected=False):
    fact=state.tool_data.get('facts',{}).get(key,{})
    candidates = [name for name in state.terminal_files if name.startswith('/home/operator/loot/')] if any_path else [path]
    return bool(fact.get('content')) and any(state.terminal_files.get(name,'').strip()==fact['content'].strip() and (not inspected or _file_read(state,name)) for name in candidates)


@lru_cache(maxsize=64)
def _expected_export(spec_json, table, where, format):
    """Export attendu, calculé une fois par base/table/filtre : la vérification tourne à chaque tick."""
    import json
    from .data_tools import database_script,query,csv_text
    statement='SELECT * FROM "'+table.replace('"','""')+'"'+(' WHERE '+where if where else '')
    columns,rows=query(database_script(json.loads(spec_json)),statement)
    return csv_text(columns,rows) if format=='csv' else '\t'.join(columns)+'\n'+'\n'.join('\t'.join(str(v) for v in row) for row in rows)+'\n'


def _table_export(state, database, table, path, where=None, format='csv', any_path=False, inspected=False):
    import json
    spec=state.environment.get('databases',{}).get(database)
    if not spec or table not in spec['tables']:return False
    candidates = [name for name in state.terminal_files if name.startswith('/home/operator/loot/')] if any_path else [path]
    if not any(name in state.terminal_files for name in candidates): return False
    expected=_expected_export(json.dumps(spec,sort_keys=True),table,where,format)
    import csv,io
    delimiter = ',' if format=='csv' else '\t'
    expected_rows = list(csv.reader(io.StringIO(expected),delimiter=delimiter))
    header = expected_rows[0]
    for filename in candidates:
        if inspected and not _file_read(state,filename): continue
        try: actual_rows=list(csv.reader(io.StringIO(state.terminal_files.get(filename,'')),delimiter=delimiter))
        except csv.Error: continue
        if not actual_rows or len(actual_rows[0]) != len(header) or len(set(actual_rows[0])) != len(header) or set(actual_rows[0]) != set(header): continue
        order = [actual_rows[0].index(column) for column in header]
        if any(len(row)!=len(header) for row in actual_rows[1:]): continue
        rows = [[row[index] for index in order] for row in actual_rows[1:]]
        if sorted(rows)==sorted(expected_rows[1:]): return True
    return False


def _service_observed(state,host,port):
    return any(service['port']==port and service.get('state')=='open' for service in state.tool_data.get('recon',{}).get('observations',{}).get(host,{}).get('services',[]))


def _hashcat_match(state, source):
    from .ntlm import nt_hash
    expected=(state.contract or {}).get('local_files',{}).get(source,'').strip().lower()
    password=state.tool_data.get('hashcat',{}).get('pot',{}).get(expected)
    from .mission_data import cracked_in_mission
    return bool(expected and password and nt_hash(password)==expected and cracked_in_mission(state, expected))


def _ldap_entries(state, dns):
    observed=state.tool_data.get('facts',{}).get('ldap:search',{}).get('entries',[])
    return {v.casefold() for v in observed} == {v.casefold() for v in dns}


OBJECTIVES = {"ldap_entries": _ldap_entries, "hashcat_match": _hashcat_match,
    "service_observed": _service_observed,
    "table_export": _table_export,
    "decision_made": _decision_made,
    "tool_fact": _tool_fact, "query_result": _query_result, "export_matches": _export_matches,
    "investigation_step": _investigation_step, "forum_read": _forum_read,
    "http_read": _http_read, "intact_download": _intact_download,
    "campaign_submitted": _campaign_submitted, "hash_recovered": _hash_recovered,
    "file_read": _file_read, "session_on_host": _session_on_host,
    "local_file_equals": _local_file_equals, "host_file_equals": _host_file_equals,
    "file_exfiltrated": _file_exfiltrated,
    "encrypted_ratio": _encrypted_ratio,
    "backups_destroyed": _backups_destroyed,
    "domain_compromised": _domain_compromised,
    "host_compromised": _host_compromised,
    "host_discovered": _host_discovered,
    "credential_owned": _credential_owned,
}


def condition_error(condition: dict, host_ids: set[str], usernames: set[str]) -> str | None:
    """Message d'erreur si la condition est mal formée, None sinon.
    Utilisé par la validation des scénarios et des contrats."""
    kind = condition.get("type")
    if kind not in OBJECTIVES:
        return f"condition de type inconnu '{kind}' (types possibles : {', '.join(sorted(OBJECTIVES))})"
    if "host" in condition and condition["host"] not in host_ids:
        return f"la condition '{kind}' vise l'hôte inconnu '{condition['host']}'"
    if "username" in condition and condition["username"] not in usernames:
        return f"la condition '{kind}' vise l'utilisateur inconnu '{condition['username']}'"
    # Paramètres manquants ou inconnus : refusés au chargement, pas à chaque tick en jeu.
    import inspect
    params = {k: v for k, v in condition.items() if k != "type"}
    try:
        inspect.signature(OBJECTIVES[kind]).bind(None, **params)
    except TypeError as exc:
        return f"la condition '{kind}' a des paramètres invalides : {exc}"
    return None


def objective_met(state: GameState, objective: dict) -> bool:
    params = {k: v for k, v in objective.items() if k != "type"}
    return OBJECTIVES[objective["type"]](state, **params)


def check(state: GameState) -> str | None:
    """Renvoie "RED", "BLUE", ou None si la partie continue."""
    if state.status == "ENDED":
        return state.winner
    if state.objectives:
        if all(objective_met(state, o) for o in state.objectives):
            return "RED"
        if state.tick >= state.max_ticks:
            return "BLUE"  # mission ratée : délai dépassé
        return None

    # Sans objectif déclaré, rien ne peut être réussi : seule la fin du temps termine la mission.
    return "BLUE" if state.tick >= state.max_ticks else None
