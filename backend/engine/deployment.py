"""Transferts d'artefacts virtuels. Aucun binaire ni fichier réel n'est exécuté."""
from __future__ import annotations
import posixpath
import re
import shlex
from .models import GameState, LogEvent
from .virtual_shell import virtual_path

TOOL_MARKERS = {name: f'REDTEAM-VIRTUAL-TOOL:{name}:1\n' for name in ('mimikatz', 'rclone', 'vesper', 'glasswing', 'sharphound', 'winpeas')}


def prepare(state: GameState) -> None:
    provisioned = state.tool_data.setdefault('provisioned_tools', [])
    state.terminal_files.setdefault('/home/operator/tools/linpeas.sh', 'VIRTUAL-SCRIPT:linpeas\n')
    for tool, marker in TOOL_MARKERS.items():
        if tool in {'vesper', 'glasswing'} and tool not in state.inventory: continue
        if tool not in provisioned:
            state.terminal_files.setdefault(f'/home/operator/tools/{tool}.exe', marker)
            provisioned.append(tool)
    if '__readme__' not in provisioned:
        state.terminal_files.setdefault('/home/operator/tools/README.txt',
            'OUTILS WINDOWS DU LABORATOIRE\nCes artefacts virtuels se transfèrent ; ils ne sont pas préinstallés sur les cibles.\n'
            'Sur le poste disposant d’OpenSSH : scp ~/tools/mimikatz.exe utilisateur@adresse:C:/Tools/mimikatz.exe\n'
            'Le mot de passe est demandé ensuite. Le dossier C:\\Tools existe sur les images du laboratoire.\n'
            'Sur un partage administratif : smbclient //adresse/C$ -U utilisateur%mot_de_passe -c "put /home/operator/tools/rclone.exe Tools/rclone.exe"\n'
            'Avec un hash NTLM : ajouter --pw-nt-hash et remplacer le mot de passe par le hash.\n'
            'Dans la session Windows : C:\\Tools\\mimikatz.exe ou C:\\Tools\\rclone.exe.\n'
            'Le répertoire C:\\Tools figure dans PATH sur les images du laboratoire.\n'
            'Les commandes Kali/Impacket se lancent dans une console locale séparée.\n')
        provisioned.append('__readme__')


def _accessible(state, host, port):
    return bool(host and host.id in state.discovered and host.status not in {'ISOLATED', 'ENCRYPTED'} and host.has_service('SSH' if port == 22 else 'SMB', port) and not state.is_blocked(host.id, port))


def _write(state, host, filename, content, user):
    if filename.startswith('/Tools/') and user not in host.admin_users: return False
    if not (filename.startswith('/Tools/') or filename.startswith('/tmp/') or filename.startswith('/Users/' + user + '/') or filename.startswith('/home/' + user + '/')):
        return False
    host.files[filename] = content
    state.logs.append(LogEvent('FILE-WRITE', host.id, state.tick, {'path': filename, 'user': user, 'source': 'file-transfer'}))
    return True


def finish_scp(state: GameState, password: str):
    from .terminal import TerminalResult
    pending = state.terminal_auth
    host = state.hosts.get(pending.get('host'))
    user = pending.get('username', '')
    if not _accessible(state, host, 22):
        state.terminal_auth = {}
        return TerminalResult(False, ['scp: Connection closed'])
    from .authentication import authenticate
    cred = authenticate(state, host, user, password)
    if not cred or (user not in host.admin_users and user != host.primary_user):
        pending['attempts'] += 1
        if pending['attempts'] >= 3:
            state.terminal_auth = {}
            return TerminalResult(False, ['Permission denied (publickey,password).'])
        return TerminalResult(False, ['Permission denied, please try again.', f"{user}@{host.ip}'s password:"])
    user = cred.username
    filename = pending['destination']
    content = state.terminal_files.get(pending['source'])
    state.terminal_auth = {}
    if content is None: return TerminalResult(False, ['scp: stat local: No such file or directory'])
    if not _write(state, host, filename, content, user):
        return TerminalResult(False, ['scp: dest open: Permission denied'])
    return TerminalResult(True, [f'{posixpath.basename(filename)} 100% {len(content.encode())} B'])


def parse(line: str, state: GameState):
    from .terminal import TerminalResult
    from .game_loop import QueuedAction
    from .shell_tools import path
    prepare(state)
    try: words = shlex.split(line)
    except ValueError: return None
    if not words or words[0] not in {'scp', 'smbclient'}: return None
    tool, args = words[0], words[1:]
    if state.terminal_host:
        return TerminalResult(False, [f'{tool}: lance ce client depuis une console Kali locale.'])
    if tool == 'smbclient':
        from .shares import parse as share_parse
        shared = share_parse(args,state)
        if shared is not None: return shared
    if tool == 'scp':
        if len(args)==2 and '@' in args[0]:
            match=re.fullmatch(r'([^@:]+)@([^:]+):(.+)',args[0])
            if not match:return TerminalResult(False,['scp: invalid source'])
            user,ref,source=match.groups();host=state.find_host(ref)
            if not _accessible(state,host,22):return TerminalResult(False,['scp: connection refused'])
            from .shell_tools import path
            source=posixpath.normpath(source) if not host.os.startswith('Windows') else virtual_path(source)
            state.terminal_auth=dict(kind='scp_download',username=user,host=host.id,source=source,destination=path(state,args[1]),attempts=0)
            return TerminalResult(True,[f"{user}@{host.ip}'s password:"])
        if len(args) != 2 or '@' not in args[1]:
            return TerminalResult(False, ['usage: scp source utilisateur@cible:chemin'])
        match = re.fullmatch(r'([^@:]+)@([^:]+):(.+)', args[1])
        if not match: return TerminalResult(False, ['scp: invalid target'])
        user, ref, destination = match.groups()
        host = state.find_host(ref)
        if not _accessible(state, host, 22): return TerminalResult(False, ['ssh: connect to host: Connection refused'])
        source = path(state, args[0])
        if source not in state.terminal_files: return TerminalResult(False, ['scp: stat local: No such file or directory'])
        state.terminal_auth = dict(kind='scp', username=user, host=host.id, source=source, destination=virtual_path(destination), attempts=0)
        return TerminalResult(True, [f"{user}@{host.ip}'s password:"])
    if len(args) < 5 or not args[0].startswith('//') or '-U' not in args or '-c' not in args:
        return TerminalResult(False, ['usage: smbclient //cible/C$ -U utilisateur%secret [--pw-nt-hash] -c "put source destination | get source destination | ls"'])
    try:
        identity, command = args[args.index('-U') + 1], args[args.index('-c') + 1]
        if any(a not in {args[0], '-U', identity, '-c', command, '--pw-nt-hash'} for a in args): raise ValueError
        ref, share = args[0][2:].split('/', 1)
        user, secret = identity.split('%', 1)
        if '/' in user:
            domain, user = user.split('/', 1)
            if domain.casefold() not in {state.domain.get('name', '').casefold(), state.domain.get('name', '').split('.')[0].casefold()}: raise ValueError
        operation = shlex.split(command)
    except (IndexError, ValueError): return TerminalResult(False, ['smbclient: invalid arguments'])
    host = state.find_host(ref)
    if not _accessible(state, host, 445): return TerminalResult(False, ['do_connect: Connection to server failed (NT_STATUS_CONNECTION_REFUSED)'])
    from .authentication import authenticate
    cred = authenticate(state, host, user, secret, 'NTLM_HASH' if '--pw-nt-hash' in args else 'PLAINTEXT')
    if cred is None: return TerminalResult(False, ['session setup failed: NT_STATUS_LOGON_FAILURE'])
    user = cred.username
    if share.casefold() != 'c$' or user not in host.admin_users:
        return TerminalResult(False, ['tree connect failed: NT_STATUS_ACCESS_DENIED'])
    if operation == ['ls']:
        return TerminalResult(True, [name.lstrip('/').replace('/', '\\') for name in sorted(host.files)])
    if len(operation) != 3 or operation[0] not in {'put', 'get'}:
        return TerminalResult(False, ['smbclient: this version supports ls, put source destination, get source destination'])
    if operation[0] == 'put':
        source = path(state, operation[1])
        filename = virtual_path('C:/' + operation[2].replace('\\', '/').lstrip('/'))
        if source not in state.terminal_files: return TerminalResult(False, ['Error opening local file: No such file or directory'])
        if not _write(state, host, filename, state.terminal_files[source], user):
            return TerminalResult(False, ['NT_STATUS_ACCESS_DENIED opening remote file'])
        return TerminalResult(True, [f'putting file {source} as {operation[2]}'])
    source = virtual_path('C:/' + operation[1].replace('\\', '/').lstrip('/'))
    filename = next((p for p in host.files if p.casefold() == source.casefold()), None)
    if filename is None: return TerminalResult(False, ['NT_STATUS_OBJECT_NAME_NOT_FOUND opening remote file'])
    if 'red.exfiltrate' not in state.available_abilities.get('red', []):
        return TerminalResult(False, ['Ce contrat ne prévoit pas de transfert documentaire.'])
    destination = path(state, operation[2])
    return TerminalResult(True, [f'getting file {operation[1]}'], QueuedAction('red.exfiltrate', host.id, user, cred.type,
        console_id=state.active_terminal_id, params={'files': [filename], 'download_destination': destination, 'authenticated_share': True, 'credential_value':cred.value}))


def executable_error(state: GameState, line: str):
    """Contrôle la présence de l'artefact, y compris avec un chemin explicite."""
    from .terminal import TerminalResult
    import ntpath
    host = state.hosts.get(state.terminal_host)
    if not host: return None
    match = re.match(r'^\s*(?:&\s+)?("[^"]+"|\S+)', line)
    if not match: return None
    token = match.group(1).strip('"')
    tool = ntpath.basename(token).lower().removesuffix('.exe')
    if tool not in TOOL_MARKERS: return None
    filename = virtual_path(token, state.terminal_cwd) if ('\\' in token or '/' in token or ':' in token) else '/Tools/' + tool + '.exe'
    value = next((v for p, v in host.files.items() if p.casefold() == filename.casefold()), None)
    if value is None:
        return TerminalResult(False, [f"'{token}' n’est pas reconnu : le fichier doit être transféré dans C:\\Tools. Guide local : cat ~/tools/README.txt."])
    if value != TOOL_MARKERS[tool]: return TerminalResult(False, ['Le fichier n’est pas un artefact exécutable reconnu par ce laboratoire.'])
    from .endpoint_tools import artifact_blocked
    if artifact_blocked(state, tool):
        return TerminalResult(False, ['Cette exécution a été bloquée par Microsoft Defender Antivirus. Consulte le journal Operational.'])
    return None


def finish_download(state,password):
    from .terminal import TerminalResult
    from .authentication import authenticate
    from .file_access import readable
    from .data_tools import write
    pending=state.terminal_auth;state.terminal_auth={}
    host=state.hosts.get(pending['host']);user=pending['username'];source=pending['source']
    if not _accessible(state,host,22):return TerminalResult(False,['scp: connection closed'])
    credential=authenticate(state,host,user,password)
    if not credential or user not in host.admin_users+[host.primary_user]:return TerminalResult(False,['Permission denied (publickey,password).'])
    if not readable(state,source,user,host):return TerminalResult(False,['scp: Permission denied'])
    if source not in host.files:return TerminalResult(False,['scp: No such file'])
    try:write(state,pending['destination'],host.files[source])
    except ValueError as exc:return TerminalResult(False,[str(exc)])
    state.exfiltrated[host.id+':'+source]=host.files[source]
    return TerminalResult(True,[source+' 100%'])
