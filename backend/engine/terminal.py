"""Terminal simulé : syntaxes des outils, sans interprétation par le système hôte."""
from __future__ import annotations

from dataclasses import dataclass, field

from .ability_engine import Ability
from .game_loop import QueuedAction
from .models import GameState

BUILTINS = {
    "help": "help [outil]      liste les commandes, ou détaille un outil",
    "hosts": "hosts             machines connues et services découverts",
    "loot": "loot              identifiants récupérés",
}


@dataclass
class TerminalResult:
    ok: bool
    output: list[str] = field(default_factory=list)
    action: QueuedAction | None = None
    open_url: str | None = None
    exit_code: int | None = None

    def __post_init__(self):
        if self.exit_code is not None: return
        self.exit_code = 0 if self.ok else 1
        if not self.ok and self.output:
            import re
            curl = re.match(r'curl: \((\d+)\)', self.output[0])
            if curl: self.exit_code = int(curl[1])
            elif self.output[0].startswith(('ssh:', 'Permission denied')): self.exit_code = 255


def parse(line: str, state: GameState, abilities: dict[str, Ability]) -> TerminalResult:
    if not state.terminal_auth:
        import re
        if re.match(r'^\s*(?:└─\$|\$\s|PS\s+[A-Za-z]:\\[^>]*>|[A-Za-z]:\\[^>]*>)',line):
            return TerminalResult(False,["L’invite de commande a été collée avec le texte. Copie uniquement la commande après $ ou >, puis Entrée."],exit_code=2)
    result = _parse(line, state, abilities)
    if result.ok and line.strip().split(' ',1)[0].casefold() in {'cat','type','get-content','gc'}:
        import shlex
        from .virtual_shell import virtual_path
        from .shell_tools import path as local_path
        files = state.hosts[state.terminal_host].files if state.terminal_host else state.terminal_files
        try: operands = shlex.split(line, posix=not bool(state.terminal_host))[1:]
        except ValueError: operands=[]
        read = state.tool_data.setdefault('read_files', [])
        for operand in operands:
            if operand.startswith('-'): continue
            resolved = virtual_path(operand.strip("\"'"),state.terminal_cwd) if state.terminal_host else local_path(state,operand)
            resolved = next((name for name in files if name.casefold()==resolved.casefold()),resolved) if state.terminal_host else resolved
            key = (state.terminal_host or 'operator')+':'+resolved
            if resolved in files and files[resolved] in result.output:
                from .evidence import read as record_read
                record_read(state,resolved)
    if result.action is None or result.action.params.get('gophish_campaign_id'):
        state.terminal_last_exit = result.exit_code
        from .powershell import ALIASES
        head = line.strip().split(' ',1)[0].casefold()
        unknown_ps = state.terminal_shell == 'powershell' and not result.ok and result.output and 'commande inconnue' in result.output[0]
        if not unknown_ps and (state.terminal_shell != 'powershell' or (head not in ALIASES and not head.startswith(('get-','set-','copy-','test-','write-','$')))):
            state.terminal_last_native_exit = result.exit_code
    return result


def _parse(line: str, state: GameState, abilities: dict[str, Ability]) -> TerminalResult:
    from . import terminal_native, shell_tools, virtual_shell, deployment
    if state.terminal_host and state.hosts[state.terminal_host].status == "ISOLATED":
        from .console_sessions import disconnect
        disconnect(state)
        return TerminalResult(False, ["Connection closed by remote host."], exit_code=255)
    if not state.terminal_auth and state.terminal_shell == 'bash' and '$' in line:
        # Remplacement des variables en une seule passe, avant tout outil : mysql, grep, head…
        # reçoivent la valeur, et une valeur contenant elle-même un $ n'est pas remplacée à nouveau.
        shell_tools.prepare(state)  # les fichiers du poste doivent exister avant un $(cat fichier)
        try: line = shell_tools._expand(line, state)
        except ValueError as exc: return TerminalResult(False, [str(exc)])
    if not state.terminal_auth and state.terminal_host:
        import shlex
        try: software=shlex.split(line)[0].casefold()
        except (ValueError,IndexError): software=''
        installed=state.environment.get('systems',{}).get(state.terminal_host,{}).get('installed_tools')
        if installed is not None and (software in {'nmap','hashcat','ldapsearch','gcc','pkexec','curl','ssh','scp','getcap'} or software.startswith('impacket-')) and software not in installed:
            return TerminalResult(False,[software+': command not found'],exit_code=127)
    if not state.terminal_auth:
        from .tunnels import parse as parse_tunnel
        tunnel = parse_tunnel(line, state)
        if tunnel is not None: return tunnel
        from .archive_tools import parse as parse_archive
        archive_result = parse_archive(line,state)
        if archive_result is not None: return archive_result
        from .data_tools import parse as parse_data
        data_result = parse_data(line, state, abilities)
        if data_result is not None: return data_result
        from .service_lab import parse as parse_lab
        lab_result = parse_lab(line, state, abilities)
        if lab_result is not None: return lab_result
        from .text_commands import parse as parse_text
        text_result = parse_text(line, state, abilities)
        if text_result is not None: return text_result
        from .virtual_files import parse as parse_files
        file_result = parse_files(line, state, abilities)
        if file_result is not None: return file_result
        deployed = deployment.parse(line, state)
        if deployed is not None: return deployed
        missing = deployment.executable_error(state, line)
        if missing is not None: return missing
        if state.terminal_host:
            import re, ntpath
            token = re.match(r'^\s*(?:&\s+)?("[^"]+"|\S+)', line)
            if token:
                tool = ntpath.basename(token[1].strip('"')).lower().removesuffix('.exe')
                if tool in deployment.TOOL_MARKERS: line = tool + line[token.end():]
    from .directory_tools import parse as parse_directory
    directory = parse_directory(line, state)
    if directory is not None: return directory
    from .system_tools import parse as parse_system
    inventory = parse_system(line, state, abilities)
    if inventory is not None: return inventory
    windows = virtual_shell.parse(line, state, abilities)
    if windows is not None: return windows
    shell = shell_tools.parse(line, state, abilities)
    if shell is not None:
        return shell
    native = terminal_native.parse(line, state, abilities)
    if native is not None:
        return native
    tokens = line.strip().split()
    if not tokens:
        return TerminalResult(ok=True)

    head = tokens[0].lower()

    if head == "help":
        return terminal_native.help_result(tokens[1:], state, abilities)
    if head == "hosts":
        return _hosts(state)
    if head == "loot":
        return _loot(state)

    import difflib
    known=set(shell_tools.BINARIES)|{'cat','ls','pwd','cd','echo','head','tail','grep','sort','cut','sqlite3','mysql','help','whoami','hostname'}
    guesses=difflib.get_close_matches(head,sorted(known),n=1,cutoff=0.72)
    message=f"{tokens[0]}: commande inconnue - tape 'help'."
    if guesses:message+=" Voulais-tu écrire "+guesses[0]+" ?"
    if head in {'less','more'}:message=f"{head}: le pager interactif n’est pas simulé. Utilise cat ou head pour lire le fichier."
    windows = bool(state.terminal_host and state.hosts[state.terminal_host].os.startswith("Windows"))
    return TerminalResult(False, [message], exit_code=(1 if state.terminal_shell == "powershell" else 9009) if windows else 127)


def _hosts(state: GameState) -> TerminalResult:
    known = [h for h in state.hosts.values() if h.id in state.discovered]
    if not known:
        return TerminalResult(True, ["Aucune machine connue."])
    lines = []
    for h in sorted(known, key=lambda x: tuple(int(p) for p in x.ip.split("."))):
        if h.id in state.scanned:
            services = ", ".join(f"{s.name}/{s.port}" for s in h.services if h.id not in state.known_ports or s.port in state.known_ports[h.id]) or "aucun service exposé"
        else:
            services = "non scanné"
        mark = "  [compromis]" if h.compromised_by == "red" else ""
        lines.append(f"  {h.ip:<15} {h.hostname:<12} {services}{mark}")
    return TerminalResult(True, lines)


def _loot(state: GameState) -> TerminalResult:
    if not state.loot:
        return TerminalResult(True, ["Butin vide."])
    lines = []
    for c in state.loot:
        status = "" if c.valid else "  [invalidé]"
        lines.append(f"  {c.username:<12} {c.type:<12} (via {c.source_host}){status}")
    return TerminalResult(True, lines)
