"""Commandes de base du shell Windows, sans appel au système hôte.

Les fichiers /srv historiques sont présentés sous C:\\Data pour conserver les
sauvegardes et les objectifs du moteur. /srv reste un alias de compatibilité.
"""
from __future__ import annotations
import ntpath
import posixpath
import re
from .models import GameState


def windows_path(value: str) -> str:
    if value.startswith('/srv'): return 'C:\\Data' + value[4:].replace('/', '\\')
    if value.startswith('/'): return 'C:\\' + value.lstrip('/').replace('/', '\\')
    return value


def virtual_path(value: str, cwd: str = '/srv') -> str:
    value = value.strip('"')
    if value.startswith('/'):
        return posixpath.normpath(value)
    current = windows_path(cwd)
    joined = ntpath.normpath(value if ntpath.isabs(value) else ntpath.join(current, value))
    if joined.lower() == 'c:\\data': return '/srv'
    if joined.lower().startswith('c:\\data\\'): return '/srv/' + joined[8:].replace('\\', '/')
    if joined.lower().startswith('c:\\'):
        parts = joined[3:].replace('\\', '/').split('/')
        parts[0] = {'tools':'Tools','users':'Users','windows':'Windows','tmp':'tmp'}.get(parts[0].casefold(),parts[0])
        if len(parts)>1 and parts[0]=='Windows' and parts[1].casefold()=='system32':parts[1]='system32'
        return '/'+'/'.join(parts)
    return joined


def parse(line: str, state: GameState, abilities=None):
    from .terminal import TerminalResult
    host = state.hosts.get(state.terminal_host)
    if not host or not host.os.startswith('Windows') or state.terminal_auth: return None
    if host.status == 'ISOLATED':
        from .console_sessions import disconnect
        disconnect(state)
        return TerminalResult(False, ['Connection closed by remote host.'])
    from . import powershell, console_sessions
    tool, _, argument = line.strip().partition(' ')
    tool = tool.lower().removesuffix('.exe')
    if tool in {'powershell', 'cmd'}:
        import shlex
        try: args = shlex.split(argument, posix=False)
        except ValueError: return TerminalResult(False, ['The string is missing the terminator.'])
        shell = 'powershell' if tool == 'powershell' else 'cmd'
        one_shot = args and args[0].casefold() in {'-command', '/c'}
        if one_shot:
            if len(args) < 2: return TerminalResult(False, ['Missing command.'])
            command = ' '.join(args[1:])
            if command[0:1] == command[-1:] and command[0:1] in {'"', "'"}: command = command[1:-1]
            console_sessions.switch_shell(state, shell)
            stack_depth = len(state.terminal_return_stack)
            from .terminal import parse as terminal_parse
            try: return terminal_parse(command, state, abilities or {})
            finally:
                if len(state.terminal_return_stack) >= stack_depth: console_sessions.leave(state)
        if any(a.casefold() not in {'-nologo','-noprofile'} for a in args):
            return TerminalResult(False, ['Unsupported shell option in this version.'])
        console_sessions.switch_shell(state, shell)
        return TerminalResult(True, ['Windows PowerShell 5.1'] if shell == 'powershell' else ['Microsoft Windows [Version 10.0]'])
    ps_result = powershell.parse(line, state)
    if ps_result is not None: return ps_result
    if tool in {'exit', 'logout'} and not argument:
        console_sessions.leave(state)
        return TerminalResult(True, ['Connection closed.'])
    if tool in {'nmap','ssh','scp','smbclient','curl','gophish','hashcat','export'} or tool.startswith('impacket-'):
        return TerminalResult(False, [f"'{tool}' n’est pas installé sur cette machine Windows. Utilise une console Kali locale."])
    if tool == 'echo' and state.terminal_shell != 'powershell':
        def expand(match): return str(state.terminal_last_exit) if match[1].upper() == 'ERRORLEVEL' else state.terminal_env.get(match[1].upper(), match[0])
        return TerminalResult(True, [re.sub(r'%([^%]+)%', expand, argument)])
    if tool in {'uname', 'id', 'ip', 'ls', 'll', 'rm', 'cp', 'mv'}:
        return TerminalResult(False, [f"'{tool}' n’est pas reconnu en tant que commande interne ou externe."])
    if tool in {'whoami','hostname','ver'} and argument:
        return TerminalResult(False, [f'{tool}: arguments non pris en charge dans cette version.'])
    if tool == 'whoami':
        identity = 'nt authority\\system' if state.terminal_access == 'SYSTEM' else state.terminal_env.get('USERDOMAIN', host.hostname).lower() + '\\' + state.terminal_user
        return TerminalResult(True, [identity])
    if tool == 'ver': return TerminalResult(True, [host.os + ' [Version 10.0]'])
    if tool == 'hostname': return TerminalResult(True, [host.hostname])
    if tool == 'ipconfig' and argument.lower() not in {'', '/all'}: return TerminalResult(False, ['ipconfig: option non prise en charge.'])
    if tool == 'ipconfig': return TerminalResult(True, ['Windows IP Configuration', 'Ethernet adapter Ethernet:', '   IPv4 Address. . . . . . . . . . . : ' + host.ip])
    if tool == 'cd' and not argument: return TerminalResult(True, [windows_path(state.terminal_cwd)])
    if tool in {'cd', 'dir', 'type'}:
        target = virtual_path(argument or '.', state.terminal_cwd)
        directories = powershell.directories(state)
        for filename in host.files:
            parent = posixpath.dirname(filename)
            while parent not in directories:
                directories.add(parent)
                if parent == '/': break
                parent = posixpath.dirname(parent)
        if tool == 'type':
            filename = next((p for p in host.files if p.casefold() == target.casefold()), None)
            if filename is None: return TerminalResult(False, ['Le fichier spécifié est introuvable.'])
            from .file_access import readable
            if not readable(state, filename): return TerminalResult(False, ['Accès refusé.'])
            return TerminalResult(True, [host.files[filename]])
        target = next((p for p in directories if p.casefold() == target.casefold()), target)
        if target not in directories: return TerminalResult(False, ['Le chemin d’accès spécifié est introuvable.'])
        if tool == 'cd':
            state.terminal_cwd = target
            return TerminalResult(True)
        names = sorted({p[len(target.rstrip('/') + '/'):].split('/')[0] for p in set(host.files) | directories if p != target and p.startswith(target.rstrip('/') + '/')})
        return TerminalResult(True, [' Répertoire de ' + windows_path(target), *names])
    if tool == 'mimikatz': return None
    if tool in {'ls', 'cat', 'pwd'}:
        return TerminalResult(False, [f"'{tool}' n’est pas reconnu. Dans cette session Windows, utilise dir, type ou cd."])
    return None
