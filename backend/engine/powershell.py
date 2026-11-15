"""Sous-ensemble explicite de PowerShell 5.1 pour les images Windows du jeu."""
from __future__ import annotations
import posixpath
import re
import shlex
from .virtual_shell import virtual_path, windows_path
from .models import GameState

ALIASES = {'ls':'get-childitem', 'dir':'get-childitem', 'gci':'get-childitem', 'cat':'get-content', 'type':'get-content', 'gc':'get-content',
           'cd':'set-location', 'chdir':'set-location', 'sl':'set-location', 'pwd':'get-location', 'gl':'get-location', 'cp':'copy-item', 'copy':'copy-item', 'echo':'write-output', 'ps':'get-process'}


def _words(line):
    # shlex sert seulement au découpage. Aucun code PowerShell n'est évalué.
    return [word[1:-1] if len(word) >= 2 and word[0] == word[-1] and word[0] in "\"'" else word for word in shlex.split(line, posix=False)]


def directories(state):
    from .virtual_files import directories as shared_directories
    return shared_directories(state)


def parse(line: str, state: GameState):
    from .terminal import TerminalResult
    from .console_sessions import leave
    host = state.hosts.get(state.terminal_host)
    if not host or state.terminal_shell != 'powershell': return None
    try: words = _words(line)
    except ValueError: return TerminalResult(False, ['ParserError: The string is missing the terminator.'])
    if not words: return TerminalResult(True)
    command = ALIASES.get(words[0].casefold(), words[0].casefold())
    args = words[1:]
    from .endpoint_tools import parse as parse_endpoint
    endpoint = parse_endpoint(command, args, state)
    if endpoint is not None: return endpoint
    if command == 'exit' and not args:
        leave(state)
        return TerminalResult(True)
    if command == '$?' and not args: return TerminalResult(True, ['True' if state.terminal_last_exit == 0 else 'False'])
    if command == '$lastexitcode' and not args: return TerminalResult(True, [str(state.terminal_last_native_exit)])
    if command == '$psversiontable': return TerminalResult(True, ['Name                           Value', '----                           -----', 'PSVersion                      5.1', 'PSEdition                      Desktop'])
    match = re.fullmatch(r'\$env:([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(["\'])(.*)\2', line.strip())
    if match:
        state.terminal_env[match[1].upper()] = match[3]
        return TerminalResult(True)
    if command.startswith('$env:') and not args: return TerminalResult(True, [state.terminal_env.get(command[5:].upper(), '')])
    if command == 'write-output':
        return TerminalResult(True, [re.sub(r'\$env:([\w]+)', lambda m: state.terminal_env.get(m[1].upper(), ''), ' '.join(args), flags=re.I)])
    if command in {'get-help', 'get-command'}:
        names = ['Get-MpComputerStatus', 'Get-MpPreference', 'Set-MpPreference', 'Get-WinEvent', 'Get-ChildItem', 'Get-Content', 'Set-Location', 'Get-Location', 'Test-Path', 'Copy-Item', 'Get-Process', 'Get-Service', 'Write-Output', 'Test-NetConnection', 'Get-HotFix', 'Get-CimInstance', 'Get-Acl']
        if len(args) != 1: return TerminalResult(False, [f'{command} : Specify one command name.'])
        found = next((name for name in names if name.casefold() == ALIASES.get(args[0].casefold(), args[0].casefold())), None)
        if not found: return TerminalResult(False, ['Get-Command : The term is not recognized as the name of a cmdlet.'])
        return TerminalResult(True, ['NAME', '    ' + found, '    Commande du sous-ensemble PowerShell du laboratoire.'])
    if command == 'test-netconnection':
        if len(args) != 3 or args[1].casefold() != '-port' or not args[2].isdigit() or not 1 <= int(args[2]) <= 65535:
            return TerminalResult(False, ['Test-NetConnection : Expected ComputerName -Port 1..65535.'])
        target = state.find_host(args[0])
        port = int(args[2])
        reachable = bool(target and target.status not in {'ISOLATED', 'ENCRYPTED'} and any(s.port == port for s in target.services) and not state.is_blocked(target.id, port))
        return TerminalResult(True, [f'ComputerName     : {args[0]}', f'RemotePort       : {port}', f'TcpTestSucceeded : {str(reachable)}'])
    if command == 'get-location' and not args:
        return TerminalResult(True, ['Path', '----', windows_path(state.terminal_cwd)])
    if command in {'get-childitem','get-content','set-location','test-path','copy-item'}:
        operands, flags, i = [], {}, 0
        while i < len(args):
            value = args[i]
            key = value.casefold()
            if key in {'-path','-literalpath','-destination','-filter'}:
                if i + 1 >= len(args): return TerminalResult(False, [f'{command} : Missing an argument for parameter {value}.'])
                flags[key] = args[i + 1]; i += 2; continue
            if key in {'-raw','-name','-file','-directory','-force'}:
                flags[key] = True; i += 1; continue
            if value.startswith('-'): return TerminalResult(False, [f'{command} : A parameter cannot be found that matches parameter name {value}.'])
            operands.append(value); i += 1
        allowed = {
            'get-childitem': {'-path','-literalpath','-filter','-name','-file','-directory','-force'},
            'get-content': {'-path','-literalpath','-raw'}, 'set-location': {'-path','-literalpath'},
            'test-path': {'-path','-literalpath'}, 'copy-item': {'-path','-literalpath','-destination','-force'},
        }[command]
        if set(flags) - allowed or ('-path' in flags and '-literalpath' in flags):
            return TerminalResult(False, [f'{command} : Parameter set cannot be resolved using the specified named parameters.'])
        maximum = (2 if command == 'copy-item' else 1) - int('-path' in flags or '-literalpath' in flags) - int('-destination' in flags)
        if len(operands) > maximum:
            return TerminalResult(False, [f'{command} : A positional parameter cannot be found that accepts argument {operands[-1]}.'])
        source = flags.get('-literalpath', flags.get('-path', operands[0] if operands else '.'))
        path = virtual_path(source, state.terminal_cwd)
        folders = directories(state)
        target = next((p for p in set(host.files) | folders if p.casefold() == path.casefold()), None)
        if command == 'test-path': return TerminalResult(True, ['True' if target is not None else 'False'])
        if target is None: return TerminalResult(False, [f"{command} : Cannot find path '{source}' because it does not exist."])
        if command == 'set-location':
            if target not in folders: return TerminalResult(False, ['Set-Location : Cannot find path because it is not a directory.'])
            state.terminal_cwd = target
            return TerminalResult(True)
        if command == 'get-content':
            from .file_access import readable
            if target not in host.files or not readable(state, target): return TerminalResult(False, ['Get-Content : Access to the path is denied.'])
            return TerminalResult(True, [host.files[target]])
        if command == 'copy-item':
            destination = flags.get('-destination', operands[1] if len(operands) > 1 else None)
            if not destination: return TerminalResult(False, ['Copy-Item : A destination is required in this version.'])
            if target not in host.files: return TerminalResult(False, ['Copy-Item : Recursive directory copying is not implemented.'])
            from .file_access import readable
            if not readable(state, target): return TerminalResult(False, ['Copy-Item : Access to the path is denied.'])
            dest = virtual_path(destination, state.terminal_cwd)
            if dest in folders: dest = posixpath.join(dest, posixpath.basename(target))
            if posixpath.dirname(dest) not in folders: return TerminalResult(False, ['Copy-Item : Could not find a part of the path.'])
            if state.terminal_access != 'SYSTEM' and not dest.startswith('/Users/' + state.terminal_user + '/'):
                return TerminalResult(False, ['Copy-Item : Access to the path is denied.'])
            if host.files.get(dest) != host.files[target]:
                from .evidence import invalidate
                invalidate(state,dest,host.id)
            host.files[dest] = host.files[target]
            return TerminalResult(True)
        import fnmatch
        entries = sorted(p for p in set(host.files) | folders if posixpath.dirname(p) == target and p != target)
        if '-filter' in flags: entries = [p for p in entries if fnmatch.fnmatch(posixpath.basename(p).casefold(), flags['-filter'].casefold())]
        if '-file' in flags: entries = [p for p in entries if p in host.files]
        if '-directory' in flags: entries = [p for p in entries if p in folders]
        if '-name' in flags: return TerminalResult(True, [posixpath.basename(p) for p in entries])
        lines = ['    Directory: ' + windows_path(target), '', 'Mode          Length Name', '----          ------ ----']
        for p in entries:
            lines.append(f"{'d-----' if p in folders else '-a----'} {len(host.files.get(p, '').encode()):>12} {posixpath.basename(p)}")
        return TerminalResult(True, lines)
    if command == 'get-process':
        if args: return TerminalResult(False, ['Get-Process : This version supports the unfiltered process list.'])
        lines = ['Id   ProcessName', '--   -----------', '4    System']
        if host.edr_agent: lines.append('840  LabEndpoint')
        if host.has_service('SSH', 22): lines.append('920  sshd')
        if state.terminal_access == 'SYSTEM': lines.append('1340 cmd')
        lines.append('1480 powershell')
        return TerminalResult(True, lines)
    if command == 'get-service':
        selected = None
        if args:
            if len(args) != 2 or args[0].casefold() != '-name': return TerminalResult(False, ['Get-Service : This version supports -Name service.'])
            selected = args[1].casefold()
        names = {'SMB':'LanmanServer','SSH':'sshd','LDAP':'NTDS','Kerberos':'Kdc'}
        services = [names.get(s.name,s.name) for s in host.services]
        if host.edr_agent: services.append("LabEndpoint")
        if selected is not None: services = [s for s in services if s.casefold() == selected]
        if not services and selected: return TerminalResult(False, ['Get-Service : Cannot find any service with the specified name.'])
        return TerminalResult(True, ['Status   Name', '------   ----', *['Running  ' + service for service in services]])
    return None
