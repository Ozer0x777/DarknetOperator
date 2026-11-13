"""Complétion de la console : exécutables, fichiers virtuels et hôtes découverts."""
from __future__ import annotations
import posixpath
import re
from . import shell_tools
from .models import GameState

FLAGS = {
    "sqlmap": ["-u", "-p", "--batch", "--dbs", "-D", "--tables", "-T", "--columns", "--dump", "-C", "--where=", "--output-dir="],
    "sqlite3": ["-csv", "-header", "--help"], "mysql": ["-h", "-u", "-p", "-D", "-e", "--batch"],
    "grep": ["-i", "-n", "-v", "-c", "-r", "-E", "-F", "-e", "--help"],
    "head": ["-n"], "tail": ["-n"], "wc": ["-l", "-w", "-c"],
    "sort": ["-r", "-u", "-n"], "uniq": ["-c"], "cut": ["-d", "-f"],
    "gophish": ["--help", "--config", "--disable-mailer", "--mode"],
    "nmap": ["-sV", "-sS", "-sT", "-sn", "-Pn", "-p", "-n", "-T4", "--help"],
    "curl": ["--help", "--insecure", "--header", "--data", "--data-binary", "--request", "--include", "--fail", "--silent"],
    "hashcat": ["--help", "-m"],
}


def complete(state: GameState, line: str, caret: int) -> dict:
    caret = min(max(0, caret), len(line))
    before = line[:caret]
    match = re.search(r"[^\s]*$", before)
    start = match.start() if match else caret
    prefix = before[start:]
    quote = prefix[:1] if prefix[:1] in {'"', "'"} else ""
    if quote:
        start += 1
        prefix = prefix[1:]
    earlier = before[:start].strip().split()
    command = earlier[0] if earlier else ""
    commands = sorted(set(shell_tools.BINARIES) | {"cd", "ls", "cat", "pwd", "help", "hosts", "loot", "clear", "exit", "export", "echo", "jobs", "kill", "xdg-open"})
    candidates: set[str] = set()
    host = state.hosts.get(state.terminal_host)
    if state.terminal_auth or state.terminal_foreground is not None or (host and host.status == "ISOLATED"):
        return _result(line, caret, start, [], quote)
    if host and host.os.startswith("Windows"):
        return _windows_result(state, line, caret, start, prefix, earlier, quote)
    if not earlier:
        candidates.update(name for name in commands if name.startswith(prefix))
    elif command == "help":
        candidates.update(name for name in commands + ["mimikatz", "vssadmin", "psexec", "secretsdump", "ticketer"] if name.startswith(prefix))
    elif prefix.startswith("-") and command in FLAGS:
        candidates.update(flag for flag in FLAGS[command] if flag.startswith(prefix))
    else:
        files = host.files if host else state.terminal_files
        directories = {"/", "/home", "/home/operator", "/tmp", "/srv"}
        names = set(files)
        if not host:
            names.update(shell_tools.BINARIES.values())
        for filename in list(names):
            directory = posixpath.dirname(filename)
            while directory and directory not in directories:
                directories.add(directory)
                if directory == "/": break
                directory = posixpath.dirname(directory)
        raw_directory, basename = posixpath.split(prefix)
        parent = shell_tools.path(state, raw_directory or ".")
        for filename in names | directories:
            if filename == parent or posixpath.dirname(filename) != parent:
                continue
            name = posixpath.basename(filename)
            if not name.startswith(basename) or (name.startswith(".") and not basename.startswith(".")):
                continue
            if command == "cd" and filename not in directories:
                continue
            candidate = (raw_directory.rstrip("/") + "/" if raw_directory else "") + name
            if filename in directories: candidate += "/"
            candidates.add(candidate)
        if command in {"nmap", "ssh", "impacket-psexec", "psexec.py", "impacket-secretsdump", "secretsdump.py"}:
            auth, separator, host_prefix = prefix.rpartition("@")
            search = host_prefix if separator else prefix
            for target in state.hosts.values():
                if target.id not in state.discovered: continue
                for value in [target.ip, target.hostname, target.hostname + "." + state.domain.get("name", "lab.invalid")]:
                    if value.lower().startswith(search.lower()): candidates.add((auth + "@" if separator else "") + value)
        if command in {"curl", "xdg-open"}:
            for value in ["https://127.0.0.1:3333/", "https://127.0.0.1:3333/api/campaigns/", "https://127.0.0.1:3333/api/groups/"]:
                if value.startswith(prefix): candidates.add(value)
    return _result(line, caret, start, sorted(candidates)[:100], quote)


def _result(line: str, caret: int, start: int, candidates: list[str], quote: str) -> dict:
    import os
    replacement = os.path.commonprefix(candidates) if candidates else line[start:caret]
    if len(candidates) == 1 and not replacement.endswith(("/", "\\")):
        replacement += quote + " "
    return {"source_line": line, "source_caret": caret, "replace_start": start, "replace_end": caret,
            "line": line[:start] + replacement + line[caret:], "caret": start + len(replacement),
            "candidates": candidates, "quote": quote}


def _windows_result(state, line, caret, start, prefix, earlier, quote):
    from .virtual_shell import virtual_path
    import ntpath
    host = state.hosts[state.terminal_host]
    candidates = []
    if not earlier:
        commands = ['whoami', 'hostname', 'ver', 'ipconfig', 'powershell', 'cmd', 'cd', 'dir', 'type', 'exit', 'mimikatz', 'vssadmin', 'rclone', 'vesper', 'glasswing', 'help', 'systeminfo', 'route', 'netstat', 'tasklist', 'sc.exe', 'icacls', 'net', 'sharphound.exe']
        if state.terminal_shell == 'powershell':
            commands += ['Get-ChildItem', 'Get-Content', 'Set-Location', 'Get-Location', 'Copy-Item', 'Test-Path', 'Get-Process', 'Get-Service', 'Get-Help', 'Get-Command', 'Write-Output', 'Get-HotFix', 'Get-CimInstance', 'Get-Acl', 'ls', 'cat', 'pwd']
        commands = [name for name in commands if name not in shell_tools.deployment_tools() or '/Tools/' + name + '.exe' in host.files]
        candidates = [name for name in commands if name.casefold().startswith(prefix.casefold())]
    elif earlier[0].casefold() in {'type', 'dir', 'cd', 'rclone', 'get-childitem', 'get-content', 'set-location', 'test-path', 'copy-item', 'ls', 'cat'}:
        raw_parent, basename = ntpath.split(prefix)
        parent = virtual_path(raw_parent or '.', state.terminal_cwd)
        from .powershell import directories as windows_directories
        directories = windows_directories(state)
        for filename in host.files:
            directory = posixpath.dirname(filename)
            while directory not in directories:
                directories.add(directory)
                if directory == '/': break
                directory = posixpath.dirname(directory)
        for filename in set(host.files) | directories:
            if posixpath.dirname(filename).casefold() != parent.casefold() or filename.casefold() == parent.casefold(): continue
            name = posixpath.basename(filename)
            if not name.casefold().startswith(basename.casefold()): continue
            if earlier[0].casefold() == 'cd' and filename not in directories: continue
            candidate = (raw_parent.rstrip('\\') + '\\' if raw_parent else '') + name
            if filename in directories: candidate += '\\'
            candidates.append(candidate)
    return _result(line, caret, start, sorted(candidates), quote)
