"""Contextes de shell isolés ; fichiers locaux et monde partagés entre consoles."""
from contextlib import contextmanager
from copy import deepcopy
from .models import GameState

FIELDS = ("terminal_host", "terminal_user", "terminal_access", "terminal_shell", "terminal_last_exit", "terminal_last_native_exit", "terminal_return_stack", "terminal_auth", "terminal_cwd", "terminal_env", "terminal_foreground")


def initial() -> dict:
    return {"terminal_host": None, "terminal_user": "operator", "terminal_access": "USER", "terminal_shell": "bash", "terminal_last_exit": 0, "terminal_last_native_exit": 0, "terminal_return_stack": [], "terminal_auth": {},
            "terminal_cwd": "/home/operator", "terminal_env": {"HOME": "/home/operator", "PATH": "/usr/bin:/bin:/opt/gophish"},
            "terminal_foreground": None}


@contextmanager
def using(state: GameState, console_id: str):
    previous = {key: deepcopy(getattr(state, key)) for key in FIELDS}
    previous_id = state.active_terminal_id
    if console_id not in state.terminals:
        state.terminals[console_id] = deepcopy(previous) if console_id == "main" else initial()
    context = state.terminals[console_id]
    context["terminal_env"] = {**(initial()["terminal_env"] if context.get("terminal_host") is None else {}), **context.get("terminal_env", {})}
    for key in FIELDS:
        setattr(state, key, deepcopy(context.get(key, initial()[key])))
    state.active_terminal_id = console_id
    try:
        yield
    finally:
        state.terminals[console_id] = {key: deepcopy(getattr(state, key)) for key in FIELDS}
        if console_id != "main":
            for key, value in state.terminals.get("main", previous).items():
                setattr(state, key, value)
        state.active_terminal_id = previous_id


def summary(state: GameState, context: dict, console_id: str = "main") -> dict:
    host = state.hosts.get(context.get("terminal_host"))
    from .virtual_shell import windows_path
    auth = context.get("terminal_auth", {})
    auth_host = state.hosts.get(auth.get("host"))
    auth_prompt = "Enter password:" if auth.get("kind") == "mysql" else "Password:" if auth.get("kind") == "impacket" else f"{auth.get('username', '')}@{auth_host.ip if auth_host else 'host'}'s password:"
    return {"shell": context.get("terminal_shell", "cmd") if host and host.os.startswith("Windows") and context.get("terminal_shell") != "bash" else ("cmd" if host and host.os.startswith("Windows") else "bash"), "display_cwd": windows_path(context.get("terminal_cwd", "/srv")) if host and host.os.startswith("Windows") else context.get("terminal_cwd", "/home/operator"), "user": context.get("terminal_user", "operator"), "cwd": context.get("terminal_cwd", "/home/operator"),
            "hostname": host.hostname if host else "kali", "password_prompt": bool(auth), "password_label": auth_prompt if auth else "", "last_exit": context.get("terminal_last_exit", 0),
            "foreground": context.get("terminal_foreground"), "pending": sum(1 for a in state.pending_actions if a.get("console_id", "main") == console_id and not a.get("params", {}).get("gophish_campaign_id"))}


def public_contexts(state: GameState) -> dict:
    result = {key: summary(state, context, key) for key, context in state.terminals.items()}
    result.setdefault("main", summary(state, {key: getattr(state, key) for key in FIELDS}))
    return result


def interrupt(state: GameState) -> list[str]:
    state.terminal_auth = {}
    pid = state.terminal_foreground
    state.terminal_foreground = None
    if pid is not None:
        for service in state.tool_services.values():
            if service.get("pid") == pid:
                service["running"] = False
        return ["^C", "CTRL+C Received... Gracefully shutting down servers"]
    return ["^C"]


TRANSCRIPT_LIMIT = 600


def transcript(state: GameState, console_id: str) -> list[str]:
    """Texte affiché dans une console, sauvegardé avec la partie pour la reprise."""
    return state.tool_data.setdefault("terminal_transcripts", {}).setdefault(console_id, [])


def record(state: GameState, console_id: str, lines) -> None:
    log = transcript(state, console_id)
    for line in lines:
        log.extend(str(line).split("\n"))
    del log[:-TRANSCRIPT_LIMIT]


def echo(context: dict, line: str) -> list[str]:
    """Même mise en forme que l'invite Godot ; un mot de passe saisi n'est jamais conservé."""
    if context.get("password_prompt"):
        return [context.get("password_label") or "Password:"]
    if context.get("shell") in ("cmd", "powershell"):
        return ["", ("PS " if context.get("shell") == "powershell" else "") + str(context.get("display_cwd", "C:\\")) + "> " + line]
    cwd = str(context.get("cwd", "~")).replace("/home/operator", "~")
    return ["", f"┌──({context.get('user', 'operator')}㉿{context.get('hostname', 'kali')})-[{cwd}]", "└─$ " + line]


def close(state: GameState, console_id: str) -> None:
    for service in state.tool_services.values():
        if service.get("owner") == console_id:
            service["running"] = False
    state.terminals.pop(console_id, None)
    state.tool_data.get("terminal_transcripts", {}).pop(console_id, None)
    if console_id == "main":
        for key, value in initial().items(): setattr(state, key, value)


SESSION_FIELDS = ("terminal_host", "terminal_user", "terminal_access", "terminal_shell", "terminal_cwd", "terminal_env", "terminal_last_exit", "terminal_last_native_exit")


def enter(state: GameState, host, user: str, access: str) -> None:
    state.terminal_return_stack.append({key: deepcopy(getattr(state, key)) for key in SESSION_FIELDS})
    state.terminal_host, state.terminal_user, state.terminal_access = host.id, user, access
    windows = host.os.startswith("Windows")
    state.terminal_shell = "cmd" if windows else "bash"
    state.terminal_cwd = "/Windows/system32" if windows and access == "SYSTEM" else ("/Users/" + user if windows else ("/root" if user == "root" else "/home/"+user))
    state.terminal_env = {"PATH": "C:\\Windows\\system32;C:\\Windows;C:\\Tools", "USERNAME": "SYSTEM" if access == "SYSTEM" else user, "COMPUTERNAME": host.hostname, "USERDOMAIN": state.domain.get("name", host.hostname).split(".")[0].upper()} if windows else {"HOME": "/root" if user == "root" else "/home/"+user, "PATH": "/usr/bin:/bin"}
    state.terminal_last_exit = state.terminal_last_native_exit = 0
    state.terminal_auth = {}


def leave(state: GameState) -> None:
    if state.terminal_return_stack:
        previous = state.terminal_return_stack.pop()
        for key in SESSION_FIELDS: setattr(state, key, deepcopy(previous[key]))
    else:
        for key, value in initial().items(): setattr(state, key, deepcopy(value))


def switch_shell(state: GameState, shell: str) -> None:
    state.terminal_return_stack.append({key: deepcopy(getattr(state, key)) for key in SESSION_FIELDS})
    state.terminal_shell = shell


def disconnect(state: GameState) -> None:
    """Quitte aussi les shells imbriqués du même hôte, puis restaure le parent."""
    host_id = state.terminal_host
    while state.terminal_host == host_id:
        leave(state)
        if state.terminal_host is None:
            break
    state.terminal_auth = {}
