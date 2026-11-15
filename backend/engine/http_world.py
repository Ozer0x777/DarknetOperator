"""HTTP en mémoire : routes déclarées vers les fichiers des seuls hôtes du jeu."""
from urllib.parse import urlsplit, parse_qs


def request(state, url, method, include=False, fail=False, headers=None):
    from .terminal import TerminalResult
    try: target = urlsplit(url)
    except ValueError: return TerminalResult(False, ['curl: (3) URL rejected'])
    try: requested_port=target.port or (443 if target.scheme=='https' else 80)
    except ValueError:return TerminalResult(False,['curl: (3) URL rejected: invalid port'])
    from .tunnels import resolve
    forward=resolve(state,target.hostname,requested_port)
    if target.hostname in {'127.0.0.1', 'localhost'} and not forward:return None
    host = state.find_host(forward['destination'] if forward else (target.hostname or ''))
    routes = state.environment.get('http_routes', {}).get(host.id if host else '', {})
    if not routes: return None
    try: port = forward['destination_port'] if forward else requested_port
    except ValueError: return TerminalResult(False, ['curl: (3) URL rejected: invalid port'])
    if target.scheme not in {'http', 'https'} or not any(s.port == port for s in host.services) or state.is_blocked(host.id, port, forward['jump'] if forward else None) or host.status in {'ISOLATED', 'ENCRYPTED'}:
        return TerminalResult(False, ['curl: (7) Failed to connect to the service in the simulated network'])
    route = routes.get(target.path or '/')
    object_id = None
    if isinstance(route, dict):
        filename = route.get('file')
        object_id = parse_qs(target.query).get(route.get('parameter','id'),[''])[0]
        if 'objects' in route: filename = route['objects'].get(object_id)
        authenticated = not route.get('cookie') or (headers or {}).get('cookie') == route['cookie']
        permitted = not route.get('enforce_owner') or object_id in route.get('allowed_ids',[])
    else:
        filename = route
        authenticated = permitted = True
    status = 405 if method not in {'GET', 'HEAD'} else (401 if not authenticated else (403 if not permitted else (200 if filename in host.files else 404)))
    phrase = {200: 'OK', 401:'Unauthorized',403:'Forbidden',404: 'Not Found', 405: 'Method Not Allowed'}[status]
    if fail and status >= 400: return TerminalResult(False, [f'curl: (22) The requested URL returned error: {status}'], exit_code=22)
    lines = [f'HTTP/1.1 {status} {phrase}', 'Content-Type: text/plain; charset=utf-8', ''] if include or method == 'HEAD' else []
    if method != 'HEAD': lines.append(host.files[filename] if status == 200 else phrase+'\n')
    if status == 200:
        state.discovered.add(host.id)
        if method == 'GET':
            read = state.tool_data.setdefault('read_http', [])
            key = host.id+':'+(target.path or '/')
            if key not in read: read.append(key)
            from .data_tools import fact
            if forward: fact(state,'http:pivot:'+host.id,jump=forward['jump'],pid=forward['pid'])
            fact(state,'http:'+host.id+':'+(target.path or '/')+(':'+object_id if object_id is not None else ''),file=filename,content=host.files[filename], source=state.network_origin(), network_path=dict(state.terminal_network_path), isolated=[h.id for h in state.hosts.values() if h.status == "ISOLATED"])
    return TerminalResult(True, lines, stdout="\n".join(lines))
