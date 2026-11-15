"""Chisel, SOCKS et WinRM du monde simulé. Aucun socket réel n'est créé."""
from copy import deepcopy
import shlex
from urllib.parse import urlsplit
from .data_tools import fact


def service(state, pid):
    return next((s for s in state.tool_services.values() if s.get('pid') == pid), None)


def client_alive(state, client):
    if not client or not client.get('running'):
        return False
    server = service(state, client.get('server_pid'))
    host = state.hosts.get(client.get('jump'))
    return bool(server and server.get('running') and host and host.status not in {'ISOLATED', 'ENCRYPTED'}
                and not state.is_blocked(server.get('process_host') or 'operator', server['listen_port'], source=host.id)
                and (not server.get('process_host') or state.hosts[server['process_host']].status not in {'ISOLATED', 'ENCRYPTED'}))


def proxy_alive(state, pid):
    client = service(state, pid)
    return bool(client and client.get('kind') == 'chisel-client' and client.get('socks') and client_alive(state, client))


def route_alive(state, route):
    pids = route.get('chain', [route.get('pid')])
    if not pids:
        return False
    origin = 'operator'
    for pid in pids:
        if not proxy_alive(state, pid):
            return False
        client = service(state, pid)
        endpoint = listener_host(state, client)
        if endpoint and state.is_blocked(endpoint, client['listen_port'], source=origin):
            return False
        if endpoint is None and origin != 'operator':
            return False
        origin = client['jump']
    return True


def listener_host(state, item):
    server = service(state, item.get('server_pid')) if item.get('kind') == 'chisel-client' else None
    return server.get('process_host') if server else item.get('process_host')


def listener_busy(state, port, host_id=None):
    host = state.hosts.get(host_id)
    if host and any(item.port == port for item in host.services):
        return True
    for item in state.tool_services.values():
        if not item.get('running'):
            continue
        if listener_host(state, item) != host_id:
            continue
        if item.get('kind') == 'chisel-client':
            if item.get('listen_port') == port and client_alive(state, item):
                return True
        elif item.get('listen_port') == port:
            return True
        elif item.get('config'):
            for name in ('admin_server', 'phish_server'):
                address = item['config'].get(name, {}).get('listen_url', '')
                if address.rsplit(':', 1)[-1] == str(port):
                    return True
    return False


def start_process(state, kind, **values):
    pid = int(state.tool_data.get('next_pid', 3200))
    state.tool_data['next_pid'] = pid + 1
    item = dict(kind=kind, pid=pid, owner=state.active_terminal_id, running=True,
                process_host=state.terminal_host, **values)
    state.tool_services[kind + ':' + str(pid)] = item
    state.terminal_foreground = pid
    return item


def parse(line, state, abilities):
    from .terminal import TerminalResult
    if state.terminal_auth or state.terminal_foreground is not None:
        return None
    try:
        words = shlex.split(line)
    except ValueError:
        return None
    if not words:
        return None
    tool, args = words[0], words[1:]
    if tool not in {'chisel', 'proxychains', 'proxychains4', 'evil-winrm'}:
        return None
    def fail(message):
        return TerminalResult(False, [message])
    if args in (['--help'], ['-h']):
        return TerminalResult(True, [HELP[tool]])
    if tool == 'chisel':
        if args == ['--version']:
            return TerminalResult(True, ['chisel — sous-ensemble simulé, syntaxe de référence 1.10'])
        if args[:1] == ['server']:
            if state.terminal_host and 'chisel' not in state.environment.get('systems', {}).get(state.terminal_host, {}).get('installed_tools', []):
                return fail('chisel: command not found')
            remaining = args[1:]
            if '--reverse' not in remaining:
                return fail('chisel: cette tranche couvre server --reverse --port PORT.')
            remaining = [a for a in remaining if a != '--reverse']
            if len(remaining) != 2 or remaining[0] not in {'--port', '-p'} or not valid_port(remaining[1]):
                return fail('Usage : chisel server --reverse --port PORT')
            port = int(remaining[1])
            if listener_busy(state, port, state.terminal_host):
                return fail('chisel: bind: address already in use')
            item = start_process(state, 'chisel-server', listen_port=port)
            return TerminalResult(True, [f"server: Reverse tunnelling enabled; Listening on http://0.0.0.0:{port} (pid={item['pid']})"])
        if args[:1] != ['client'] or len(args) != 3 or not state.terminal_host:
            return fail('Usage couvert : chisel client http://SERVEUR:PORT R:PORT:socks ou R:PORT:HOTE:PORT')
        installed = state.environment.get('systems', {}).get(state.terminal_host, {}).get('installed_tools', [])
        if 'chisel' not in installed:
            return fail('chisel: command not found')
        try:
            url = urlsplit(args[1]); port = url.port or 80
        except ValueError:
            return fail('chisel: invalid server address')
        server_host = None if url.hostname == state.environment.get('operator_ip', '10.10.14.2') else state.find_host(url.hostname or '')
        if url.scheme != 'http' or (server_host is None and url.hostname != state.environment.get('operator_ip', '10.10.14.2')) or url.path not in {'', '/'} or url.query or url.username:
            return fail('chisel: adresse serveur non couverte ou inaccessible dans ce laboratoire.')
        server = next((s for s in state.tool_services.values() if s.get('kind') == 'chisel-server' and s.get('running') and s['listen_port'] == port and s.get('process_host') == (server_host.id if server_host else None)), None)
        if not server or (server_host and server_host.status in {'ISOLATED', 'ENCRYPTED'}) or state.is_blocked(server_host.id if server_host else 'operator', port, source=state.terminal_host):
            return fail('chisel: connection failed: server unreachable')
        binding = args[2].split(':')
        if binding[:1] != ['R'] or len(binding) not in {3, 4} or not valid_port(binding[1]):
            return fail('chisel: remote invalide ; attendu R:PORT:socks ou R:PORT:HOTE:PORT')
        socks = len(binding) == 3 and binding[2] == 'socks'
        if not socks and (len(binding) != 4 or not valid_port(binding[3]) or not state.find_host(binding[2])):
            return fail('chisel: destination ou port non couvert')
        listen_port = int(binding[1])
        if listener_busy(state, listen_port, server.get('process_host')):
            return fail('chisel: bind: address already in use')
        item = start_process(state, 'chisel-client', jump=state.terminal_host, server_pid=server['pid'],
                             listen_port=listen_port, socks=socks, destination=None if socks else binding[2],
                             destination_port=None if socks else int(binding[3]))
        fact(state, 'chisel:connected', jump=state.terminal_host, pid=item['pid'])
        return TerminalResult(True, [f"client: Connected; reverse listener 0.0.0.0:{listen_port} (pid={item['pid']})"])
    if tool in {'proxychains', 'proxychains4'}:
        if state.terminal_host or len(args) < 3 or args[0] != '-f':
            return fail('Usage couvert : proxychains4 -f CONFIG COMMANDE [ARGUMENTS] depuis Kali')
        from .shell_tools import path
        config = state.terminal_files.get(path(state, args[1]))
        if config is None:
            return fail('proxychains: configuration file not found')
        entries = [row.split('#', 1)[0].strip() for row in config.splitlines()]
        entries = [row for row in entries if row]
        if len(entries) < 3 or entries[:2] != ['strict_chain', '[ProxyList]']:
            return fail('proxychains: configuration attendue strict_chain puis [ProxyList] et SOCKS5.')
        clients = []
        origin = 'operator'
        for entry in entries[2:]:
            fields = entry.split()
            if len(fields) != 3 or fields[0] != 'socks5' or not valid_port(fields[2]):
                return fail('proxychains: entrée SOCKS5 invalide')
            if origin != 'operator' and fields[1] in {'127.0.0.1', 'localhost'}:
                return fail('proxychains: utilise l’adresse du relais distant pour le second proxy.')
            endpoint = None if fields[1] in {'127.0.0.1', 'localhost'} and origin == 'operator' else state.find_host(fields[1])
            if endpoint is None and fields[1] not in {'127.0.0.1', 'localhost'}:
                return fail('proxychains: proxy inconnu')
            if endpoint and state.is_blocked(endpoint.id, int(fields[2]), source=origin):
                return fail('proxychains: proxy unreachable')
            client = next((item for item in state.tool_services.values()
                if item.get('listen_port') == int(fields[2]) and proxy_alive(state, item.get('pid'))
                and service(state, item.get('server_pid')).get('process_host') == (endpoint.id if endpoint else None)), None)
            if not client:
                return fail('proxychains: SOCKS proxy connection refused')
            clients.append(client)
            origin = client['jump']
        command = args[2:]
        if command[0] not in {'nmap', 'curl', 'evil-winrm', 'ldapsearch'}:
            return fail('proxychains: client non couvert ; nmap TCP, curl, ldapsearch et evil-winrm sont disponibles.')
        if command[0] == 'nmap' and (not {'-sT', '-Pn', '-n'} <= set(command) or any(a in command for a in ['-sS', '-sU', '-sn'])):
            return fail('proxychains: le chemin SOCKS transporte TCP ; utilise nmap -sT -Pn -n, sans sondes brutes.')
        if command[0] == 'ldapsearch' and '-W' in command:
            return fail('proxychains: le prompt LDAP n’est pas couvert ; utilise -w SECRET dans ce laboratoire.')
        previous = deepcopy(state.terminal_network_path)
        previous_host = state.terminal_host
        route = {'pid': client['pid'], 'jump': client['jump'], 'chain': [item['pid'] for item in clients]}
        state.terminal_network_path = route
        from .terminal import parse as parse_terminal
        try:
            result = parse_terminal(shlex.join(command), state, abilities)
            if result.action:
                result.action.params['network_path'] = route
            if state.terminal_host != previous_host:
                state.terminal_return_stack[-1]['terminal_network_path'] = previous
            else:
                state.terminal_network_path = previous
            if result.ok:
                fact(state, 'proxychains:used', jump=client['jump'], pid=client['pid'])
                if len(clients) > 1:
                    fact(state, 'proxychains:multi', chain=route['chain'])
            return result
        except Exception:
            state.terminal_network_path = previous
            raise
    # WinRM : authentification, appartenance autorisée et transport distincts.
    if state.terminal_host:
        return fail('evil-winrm: lance le client depuis Kali.')
    values = {}; ssl = False; i = 0
    while i < len(args):
        if args[i] == '-S':
            ssl = True; i += 1; continue
        if args[i] not in {'-i', '-u', '-p', '-P', '-H'} or i + 1 >= len(args) or args[i] in values:
            return fail('evil-winrm: arguments non couverts ; consulte evil-winrm -h')
        values[args[i]] = args[i + 1]; i += 2
    if not {'-i', '-u'} <= values.keys() or ('-p' in values) == ('-H' in values):
        return fail('evil-winrm: -i, -u et un secret (-p ou -H) sont requis dans cette tranche.')
    port_text = values.get('-P', '5986' if ssl else '5985')
    if not valid_port(port_text):
        return fail('evil-winrm: invalid port')
    host = state.find_host(values['-i'])
    if not host or not host.os.startswith('Windows') or not state.reachable(host, int(port_text)):
        return fail('evil-winrm: WinRM connection failed')
    spec = state.environment.get('winrm', {}).get(host.id, {})
    if spec.get('tls', False) != ssl or int(port_text) != spec.get('port', 5986 if ssl else 5985):
        return fail('evil-winrm: endpoint transport mismatch')
    from .authentication import authenticate
    state.discovered.add(host.id)
    credential = authenticate(state, host, values['-u'], values.get('-p', values.get('-H')), 'PLAINTEXT' if '-p' in values else 'NTLM_HASH')
    if credential and credential.username not in spec.get('users', []):
        fact(state, 'winrm:denied:' + host.id, user=credential.username)
    if not credential or credential.username not in spec.get('users', []):
        return fail('evil-winrm: WinRMAuthorizationError')
    from .console_sessions import enter
    enter(state, host, credential.username, 'ADMIN' if credential.username in host.admin_users else 'USER')
    state.terminal_shell = 'powershell'
    if host.status == 'HEALTHY':
        host.status, host.compromised_by, host.access_level = 'COMPROMISED', 'red', state.terminal_access
    from .models import LogEvent
    state.logs.append(LogEvent('4624', host.id, state.tick, {'TargetUserName': credential.username, 'LogonType': 3, 'AuthenticationPackageName': 'NTLM', 'LogonProcessName': 'NtLmSsp', 'KeyLength': 128 if '-p' in values else 0}))
    fact(state, 'winrm:session:' + host.id, user=credential.username, port=int(port_text), proxy=deepcopy(state.terminal_network_path))
    return TerminalResult(True, ['Evil-WinRM — session PowerShell du laboratoire', f'{credential.username}@{host.hostname}'])


def valid_port(value):
    return isinstance(value, str) and value.isdigit() and 1 <= int(value) <= 65535


HELP = {
    'chisel': 'Chisel (sous-ensemble simulé) : server --reverse --port PORT ; client http://SERVEUR:PORT R:PORT:socks ou R:PORT:HOTE:PORT. Une console par processus ; Ctrl+C ou kill coupe le passage. Les autres modes sont hors couverture.',
    'proxychains4': 'proxychains4 -f CONFIG {nmap -sT -Pn -n ...|curl URL|ldapsearch ...|evil-winrm ...}. Configuration : strict_chain, [ProxyList], puis socks5 ADRESSE PORT pour chaque passage. TCP uniquement ; chaîne stricte de proxies SOCKS5. LDAP avec -w ; invite -W hors couverture.',
    'evil-winrm': 'evil-winrm -i HOTE -u UTILISATEUR {-p SECRET|-H EMPREINTE} [-S] [-P PORT]. Vérifie le réseau, le transport et les utilisateurs autorisés. Une session réussie ne donne pas SYSTEM. Les autres options ne sont pas couvertes.',
}
HELP['proxychains'] = HELP['proxychains4']
