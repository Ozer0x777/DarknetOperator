"""Découverte des exécutables et GoPhish/API entièrement dans le monde simulé."""
from __future__ import annotations
import json
import posixpath
import re
import shlex
from urllib.parse import urlsplit, parse_qs
from .models import GameState

BINARIES = {
    "scp": "/usr/bin/scp", "smbclient": "/usr/bin/smbclient",
    "nmap": "/usr/bin/nmap", "gophish": "/opt/gophish/gophish", "curl": "/usr/bin/curl",
    "ssh": "/usr/bin/ssh", "impacket-psexec": "/usr/bin/impacket-psexec",
    "impacket-secretsdump": "/usr/bin/impacket-secretsdump", "impacket-ticketer": "/usr/bin/impacket-ticketer",
    "impacket-lookupsid": "/usr/bin/impacket-lookupsid",
    "hashcat": "/usr/bin/hashcat", "rclone": "/usr/bin/rclone",
    "vesper": "/usr/bin/vesper", "glasswing": "/usr/bin/glasswing",
    "whoami": "/usr/bin/whoami", "hostname": "/usr/bin/hostname", "ip": "/usr/bin/ip",
    "host": "/usr/bin/host",
}
BINARIES.update({name: "/usr/bin/"+name for name in ("tar", "sqlmap", "sqlite3", "mysql", "nc", "gdb", "checksec", "python3", "grep", "head", "tail", "wc", "sort", "uniq", "cut", "sha256sum")})
BINARIES.update({name: "/usr/bin/"+name for name in ("ldapsearch", "impacket-GetUserSPNs", "groups", "sudo", "ss", "ps", "systemctl", "dpkg-query", "dpkg", "rpm", "pkexec", "getcap", "find", "stat", "gcc")})
BASE = "/home/operator/gophish"
API_KEY = "0123456789abcdef0123456789abcdef0123456789abcdef0123456789abcdef"


def path(state: GameState, value: str) -> str:
    if value == "~" or value.startswith("~/"):
        value = state.terminal_env.get("HOME", "/home/operator") + value[1:]
    return posixpath.normpath(value if value.startswith("/") else posixpath.join(state.terminal_cwd, value))


def prepare(state: GameState) -> None:
    """Le laboratoire fournit un profil API et des ressources de démonstration, pas de vrais services."""
    from .deployment import prepare as prepare_tools
    prepare_tools(state)
    from .hashcat_model import prepare as prepare_hashcat
    prepare_hashcat(state)
    files = state.terminal_files
    if state.contract and (state.contract.get('contract_id') == 'tuto_p0' or state.contract.get('onboarding')):
        from pathlib import Path
        files['/home/operator/mission/lecons.txt'] = (Path(__file__).parents[1]/'data/tutorial_lessons.txt').read_text()
    seeded = state.tool_data.setdefault('provisioned_config_files', [])
    config = {"admin_server": {"listen_url": "127.0.0.1:3333", "use_tls": True}, "phish_server": {"listen_url": "0.0.0.0:80", "use_tls": False}, "db_name": "sqlite3", "db_path": "gophish.db"}
    if '/opt/gophish/config.json' not in seeded:
        files.setdefault("/opt/gophish/config.json", json.dumps(config, indent=2))
        seeded.append('/opt/gophish/config.json')
    if 'gophish-api' not in seeded:
        files.setdefault(BASE + "/api-key.txt", API_KEY + "\n")
        seeded.append('gophish-api')
    if 'gophish-admin' not in seeded:
        files.setdefault(BASE + "/admin.txt", "Compte du laboratoire préconfiguré :\nusername: admin\npassword: lab-admin-password\nInterface : https://127.0.0.1:3333\n")
        seeded.append('gophish-admin')
    previous_guide = files.get(BASE + "/README.txt", "")
    if "gophish-guide" not in seeded or previous_guide.startswith("Laboratoire de jeu : profil API et ressources préconfigurés."):
        files[BASE + "/README.txt"] = 'GUIDE GOPHISH — Une commande à la fois\nNe colle pas tout ce guide. Copie uniquement la commande de chaque étape,\npuis Entrée. Attends sa réponse avant de passer à la suivante.\nUne longue commande peut se replier visuellement sur plusieurs lignes.\n\nCONSOLE 1 — Démarrer le serveur\nCOMMANDE :\ngophish --config /opt/gophish/config.json\nATTENDU : Starting admin server at https://127.0.0.1:3333\nLaisse cette console ouverte et occupée. Ctrl+C arrêterait le serveur.\n\nOuvre CONSOLE 2 : Ctrl+Alt+T ou Fichier > Nouvelle fenêtre.\nLes étapes 1 à 4 se font dans cette même console.\n\n1 — Charger la clé API (aucune sortie : c\'est normal)\nCOMMANDE :\nAPI_KEY=$(cat ~/gophish/api-key.txt)\nATTENDU : l\'invite revient ; la variable existe dans cette console.\n\n2 — Vérifier les destinataires\nCOMMANDE :\ncurl -k -H "Authorization: $API_KEY" https://127.0.0.1:3333/api/groups/\nATTENDU : JSON du groupe Briefing et de son destinataire.\n\n3 — Lire le fichier de campagne (aucun envoi)\nCOMMANDE :\ncat ~/gophish/campaign.json\nATTENDU : JSON de la campagne Premier contrat.\n\n4 — Créer la campagne (une seule longue commande)\nCOMMANDE :\ncurl -k -H "Authorization: $API_KEY" -H "Content-Type: application/json" -d @/home/operator/gophish/campaign.json https://127.0.0.1:3333/api/campaigns/\nATTENDU : JSON avec id et statut Queued, puis résultat dans le terminal.\nDans le tutoriel, k0rvid confirme ensuite la récupération du compte.\nNe répète pas l\'envoi après cette confirmation.\n\nDÉPANNAGE\nFailed to connect : vérifie que GoPhish tourne dans la console 1.\nInvalid API key : refais l\'étape 1 dans la console utilisée pour curl.\nCommande mal collée : Ctrl+A dans la saisie, puis remplace-la.\nChaque nouvelle console a ses propres variables ; garde la même pour curl.\n\nInterface web optionnelle (commande séparée) :\nxdg-open https://127.0.0.1:3333\nCompte du laboratoire (commande séparée) :\ncat ~/gophish/admin.txt\n'
    if "gophish-guide" not in seeded: seeded.append("gophish-guide")
    data = state.tool_data.setdefault("gophish", {"groups": [], "templates": [{"id": 1, "name": "Briefing", "subject": "Document du cabinet", "text": "Exemple du laboratoire"}], "pages": [{"id": 1, "name": "Briefing", "html": "<p>Page fictive du laboratoire</p>", "capture_credentials": True, "capture_passwords": True}], "smtp": [{"id": 1, "name": "Lab", "host": "smtp.lab.invalid:25", "from_address": "contact@lab.invalid"}], "campaigns": [], "seed": None})
    for page in data["pages"]:
        if page.get("id") == 1 and page.get("name") == "Briefing" and "capture_passwords" not in page: page["capture_passwords"] = True
    seed = state.contract.get("contract_id") if state.contract else None
    if data.get("seed") != seed or not data["groups"]:
        targets = [{"email": h.primary_user + "@" + state.domain.get("name", "lab.invalid"), "first_name": h.primary_user, "last_name": "", "position": "Accueil"} for h in state.hosts.values() if h.id in state.discovered and h.primary_user]
        data["groups"] = [{"id": 1, "name": "Briefing", "targets": targets}]
        data["seed"] = seed
        payload = {"name": "Premier contrat", "template": {"name": "Briefing"}, "page": {"name": "Briefing"}, "smtp": {"name": "Lab"}, "groups": [{"name": "Briefing"}], "url": "http://landing.lab.invalid"}
        files[BASE + "/campaign.json"] = json.dumps(payload, indent=2)


def _expand(line: str, state: GameState) -> str:
    result, i, quote = [], 0, ""
    while i < len(line):
        char = line[i]
        if char == "\\" and quote != "'" and i + 1 < len(line):
            result.append(line[i:i + 2]); i += 2; continue
        if char in "'\"" and (not quote or char == quote):
            quote = "" if quote else char
        if char == "$" and quote != "'":
            if line[i:i + 2] == "$?":
                result.append(str(state.terminal_last_exit)); i += 2; continue
            if line[i:i + 2] == "$(":
                end = line.find(")", i + 2)
                if end < 0: raise ValueError("shell: substitution de commande incomplète")
                command = shlex.split(line[i + 2:end])
                if len(command) != 2 or command[0] != "cat":
                    raise ValueError("shell: cette version prend en charge $(cat fichier)")
                filename = path(state, command[1])
                if filename not in state.terminal_files: raise ValueError(f"cat: {command[1]}: No such file or directory")
                result.append(state.terminal_files[filename].rstrip("\n")); i = end + 1; continue
            match = re.match(r"\$(?:\{([A-Za-z_][A-Za-z0-9_]*)\}|([A-Za-z_][A-Za-z0-9_]*))", line[i:])
            if match:
                result.append(state.terminal_env.get(match.group(1) or match.group(2), "")); i += len(match.group()); continue
        result.append(char); i += 1
    return "".join(result)


def parse(line: str, state: GameState, abilities):
    from .terminal import TerminalResult, parse as terminal_parse
    from .game_loop import QueuedAction
    if state.terminal_auth:
        return None
    prepare(state)
    if state.terminal_foreground is not None:
        return TerminalResult(False, ["Un processus occupe cette console. Ctrl+C pour l'arrêter, ou ouvre une autre console."])
    try:
        expanded = _expand(line, state)
        lexer=shlex.shlex(expanded,posix=True,punctuation_chars='<>')
        lexer.whitespace_split=True
        words=list(lexer)
    except ValueError as exc:
        return TerminalResult(False, [str(exc)])
    if not words: return None
    if expanded != line:
        return terminal_parse(expanded, state, abilities)
    assign = words[1:] if words[0] == "export" else words
    if len(assign) == 1 and re.match(r"^[A-Za-z_][A-Za-z0-9_]*=", assign[0]):
        name, value = assign[0].split("=", 1)
        state.terminal_env[name] = value
        return TerminalResult(True)
    for operator in (">", ">>"):
        if operator in words:
            index = words.index(operator)
            if index == 0 or index != len(words) - 2:
                return TerminalResult(False, ["shell: syntaxe de redirection non prise en charge"])
            result = terminal_parse(shlex.join(words[:index]), state, abilities)
            if result.ok:
                filename = path(state, words[-1])
                from .virtual_files import writable, directories, audit
                if not writable(state,filename): return TerminalResult(False,['shell: Permission denied'])
                if posixpath.dirname(filename) not in directories(state): return TerminalResult(False,['shell: No such file or directory'])
                files = state.hosts[state.terminal_host].files if state.terminal_host else state.terminal_files
                before = files.get(filename)
                content = "\n".join(result.output) + ("\n" if result.output else "")
                files[filename] = (before or "" if operator == ">>" else "") + content
                audit(state,'append' if operator == '>>' else 'write',filename,before,files[filename])
                result.output = []
            return result
    tool, args = words[0], words[1:]
    if tool == "xdg-open" and len(args) == 1:
        url = urlsplit(args[0])
        if url.hostname in {"localhost", "127.0.0.1"} and url.scheme in {"http", "https"}:
            return TerminalResult(True, open_url=args[0])
        return TerminalResult(False, ["xdg-open: cette URL n’est pas disponible dans le navigateur du jeu"] )
    if tool == "echo":
        return TerminalResult(True, [" ".join(args[1:] if args[:1] == ["-n"] else args)])
    if tool in {"which", "command"}:
        names = args[1:] if tool == "command" and args[:1] == ["-v"] else args
        if tool == "command" and args[:1] != ["-v"]: return None
        output = [BINARIES[n] if n in BINARIES else n for n in names if n in BINARIES or n in {"cd", "help", "export", "jobs"}]
        return TerminalResult(bool(output), output)
    if tool == "ls":
        directory = path(state, next((a for a in args if not a.startswith("-")), state.terminal_cwd))
        if directory in {"/usr/bin", "/bin"}: return TerminalResult(True, sorted(BINARIES))
        if directory == "/opt": return TerminalResult(True, ["gophish"])
        if directory == "/opt/gophish": return TerminalResult(True, ["config.json", "gophish"])
    if tool == "jobs":
        jobs = [s for s in state.tool_services.values() if s.get("running") and s.get("owner") == state.active_terminal_id]
        return TerminalResult(True, [f"[1]  Running   {s.get('kind', 'gophish')} ({s['pid']})" for s in jobs])
    if tool == "kill":
        value = args[-1] if args else ""
        if not value.isdigit(): return TerminalResult(False, ["usage: kill [-INT|-TERM] pid"])
        service = next((s for s in state.tool_services.values() if s.get("pid") == int(value) and s.get("running")), None)
        if not service: return TerminalResult(False, [f"kill: ({value}) - No such process"])
        service["running"] = False
        owner = service.get("owner")
        if owner in state.terminals: state.terminals[owner]["terminal_foreground"] = None
        if owner == state.active_terminal_id: state.terminal_foreground = None
        return TerminalResult(True)
    if tool in {"gophish", "./gophish", "/opt/gophish/gophish"}:
        return _gophish(args, state)
    if tool == "curl":
        return _curl(args, state, abilities)
    if tool == "host" and not state.terminal_host:
        return _host(args, state)
    if tool in {"vesper", "glasswing"}:
        if args in (["--help"], ["-h"]): return TerminalResult(True, [f"{tool} encrypt", "Programme fictif du jeu : agit sur la session distante courante."])
        if args != ["encrypt"]: return TerminalResult(False, [f"usage: {tool} encrypt"])
        if tool not in state.inventory: return TerminalResult(False, [f"{tool}: affiliation/licence absente de l'inventaire"])
        host = state.hosts.get(state.terminal_host)
        if not host: return TerminalResult(False, [f"{tool}: aucune session distante"])
        if state.terminal_access != "SYSTEM": return TerminalResult(False, [f"{tool}: Access is denied."])
        return TerminalResult(True, [f"{tool}: traitement en attente…"], QueuedAction("red", "red.encrypt", host.id, console_id=state.active_terminal_id))
    if tool.lower() in {"vssadmin", "vssadmin.exe"}:
        if [a.lower() for a in args] != ["delete", "shadows", "/all", "/quiet"]:
            return TerminalResult(False, ["usage: vssadmin delete shadows /all /quiet"])
        host = state.hosts.get(state.terminal_host)
        if not host: return TerminalResult(False, ["vssadmin: aucune session Windows distante"])
        if state.terminal_access != "SYSTEM": return TerminalResult(False, ["vssadmin: Access is denied."])
        return TerminalResult(True, [], QueuedAction("red", "red.destroy_backups", host.id, console_id=state.active_terminal_id))
    return None


def _host(args, state):
    """Résolution DNS du monde simulé : nom → adresse, ou adresse → nom (PTR)."""
    from .terminal import TerminalResult
    if len(args) != 1 or args[0].startswith("-"):
        return TerminalResult(False, ["Usage: host nom_ou_adresse"], exit_code=1)
    name = args[0].rstrip(".")
    if re.fullmatch(r"\d{1,3}(\.\d{1,3}){3}", name):
        host = next((h for h in state.hosts.values() if h.ip == name), None)
        names = state.dns_names(host.id) if host else []
        arpa = ".".join(reversed(name.split("."))) + ".in-addr.arpa"
        if not names: return TerminalResult(False, [f"Host {arpa} not found: 3(NXDOMAIN)"], exit_code=1)
        return TerminalResult(True, [f"{arpa} domain name pointer {names[0]}."])
    target = {n.lower(): h for n, h in state.environment.get("dns", {}).items()}.get(name.lower())
    host = state.hosts.get(target) if target else None
    if not host: return TerminalResult(False, [f"Host {name} not found: 3(NXDOMAIN)"], exit_code=1)
    return TerminalResult(True, [f"{name} has address {host.ip}"])


def _gophish(args, state):
    from .terminal import TerminalResult
    if args in (["--help"], ["-h"]):
        return TerminalResult(True, ["usage: gophish [<flags>]", "  --config=./config.json    Location of config.json.", "  --disable-mailer         Disable the mailer.", "  --mode=all               all, admin or phish", "Guide du laboratoire : cat ~/gophish/README.txt"])
    background = bool(args and args[-1] == "&")
    if background: args = args[:-1]
    config_path, mode, disabled, i = "/opt/gophish/config.json", "all", False, 0
    while i < len(args):
        arg = args[i]
        if arg in {"--config", "--mode"} and i + 1 < len(args):
            if arg == "--config": config_path = path(state, args[i + 1])
            else: mode = args[i + 1]
            i += 2; continue
        if arg.startswith("--config="): config_path = path(state, arg.split("=", 1)[1])
        elif arg.startswith("--mode="): mode = arg.split("=", 1)[1]
        elif arg == "--disable-mailer": disabled = True
        else: return TerminalResult(False, [f"gophish: unknown flag or argument {arg}"])
        i += 1
    if mode not in {"all", "admin", "phish"}: return TerminalResult(False, ["gophish: invalid mode"])
    if state.terminal_host: return TerminalResult(False, ["gophish: exécutable installé sur le poste local, pas dans cette session distante"])
    if state.tool_services.get("gophish", {}).get("running"):
        return TerminalResult(False, ["listen tcp 127.0.0.1:3333: bind: address already in use"])
    try:
        config = json.loads(state.terminal_files[config_path])
        listen = config["admin_server"]["listen_url"]
        phish = config["phish_server"]["listen_url"]
        for address in (listen, phish):
            if not isinstance(address, str) or not address.rsplit(":", 1)[-1].isdigit() or not 1 <= int(address.rsplit(":", 1)[-1]) <= 65535:
                raise ValueError("invalid listen address")
    except (KeyError, ValueError, TypeError): return TerminalResult(False, [f"gophish: cannot load config {config_path}"])
    pid = int(state.tool_data.get("next_pid", 3200)); state.tool_data["next_pid"] = pid + 1
    state.tool_services["gophish"] = {"running": True, "pid": pid, "owner": state.active_terminal_id, "mode": mode, "disable_mailer": disabled, "config": config}
    if not background: state.terminal_foreground = pid
    lines = [f"[1] {pid}"] if background else []
    if mode in {"all", "admin"}: lines.append(f"Starting admin server at {'https' if config['admin_server'].get('use_tls') else 'http'}://{listen}")
    if mode in {"all", "phish"}: lines.append(f"Starting phishing server at http://{phish}")
    return TerminalResult(True, lines)


def _curl(args, state, abilities):
    from .terminal import TerminalResult
    normalized=[];destination=None;i=0
    while i<len(args):
        arg=args[i]
        name,separator,value=arg.partition('=')
        if name in {'-o','--output'} or (arg.startswith('-o') and not arg.startswith('--') and len(arg)>2):
            if destination is not None:return TerminalResult(False,['curl: une seule destination de sortie est prise en charge.'])
            if arg.startswith('-o') and len(arg)>2 and not arg.startswith('--'):value=arg[2:]
            elif not separator:
                i+=1
                if i>=len(args):return TerminalResult(False,['curl: --output requires parameter'])
                value=args[i]
            destination=path(state,value)
        elif name=='--url':
            if not separator:
                i+=1
                if i>=len(args):return TerminalResult(False,['curl: --url requires parameter'])
                value=args[i]
            normalized.append(value)
        elif separator and name in {'--header','--request','--data','--data-binary'}:normalized.extend([name,value])
        else:normalized.append(arg)
        i+=1
    if destination:
        from .virtual_files import writable,directories
        if not writable(state,destination):return TerminalResult(False,['curl: (23) Permission denied'],exit_code=23)
        if posixpath.dirname(destination) not in directories(state):return TerminalResult(False,['curl: (23) No such directory'],exit_code=23)
    result=_curl_request(normalized,state,abilities)
    if destination and result.ok:
        from .virtual_files import audit
        content='\n'.join(result.output)
        content+=('\n' if content and not content.endswith('\n') else '')
        files=state.hosts[state.terminal_host].files if state.terminal_host else state.terminal_files
        before=files.get(destination)
        files[destination]=content
        audit(state,'write',destination,before,content)
        result.output=[]
    return result


def _curl_request(args, state, abilities):
    from .terminal import TerminalResult
    if args in (["--help"], ["-h"]):
        return TerminalResult(True, ["Usage: curl [options...] <url>", " -k, --insecure        Allow insecure server connections", " -H, --header <header> Pass custom header(s)", " -d, --data <data>     HTTP POST data (or @file)", " -X, --request <method> HTTP method", " -i, --include        Include response headers", " -o, --output <file>  Save the response in a local file", " -f, --fail           Fail on HTTP error", "Laboratoire GoPhish : cat ~/gophish/README.txt"])
    from .game_loop import QueuedAction
    headers, method, body, url, i = {}, "GET", None, None, 0
    show_headers, fail = False, False
    while i < len(args):
        arg = args[i]
        if arg.startswith("-") and not arg.startswith("--") and len(arg) > 2 and set(arg[1:]) <= set("ksSfi"):
            show_headers = show_headers or "i" in arg
            fail = fail or "f" in arg
            i += 1
            continue
        if arg in {"-k", "--insecure", "-s", "--silent", "-S", "-sS", "-ks", "-sk", "-ksS"}: pass
        elif arg in {"-i", "--include"}: show_headers = True
        elif arg in {"-f", "--fail"}: fail = True
        elif arg in {"-X", "--request", "-H", "--header", "-d", "--data", "--data-binary"}:
            if i + 1 >= len(args): return TerminalResult(False, [f"curl: option {arg}: requires parameter"])
            i += 1; value = args[i]
            if arg in {"-X", "--request"}: method = value.upper()
            elif arg in {"-H", "--header"}:
                key, _, value = value.partition(":"); headers[key.strip().lower()] = value.strip()
            else:
                if value.startswith("@"):
                    filename = path(state, value[1:])
                    if filename not in state.terminal_files: return TerminalResult(False, ["curl: (26) Failed to open/read local data from file"])
                    body = state.terminal_files[filename]
                else: body = value
                if method == "GET": method = "POST"
        elif arg.startswith("-"): return TerminalResult(False, [f"curl: option {arg}: non implémentée dans cette version"])
        elif url is None: url = arg
        else: return TerminalResult(False, ["curl: cette version traite une URL par commande"])
        i += 1
    if not url: return TerminalResult(False, ["curl: no URL specified"])
    from .http_world import request as world_request
    world_result = world_request(state, url, method, show_headers, fail, headers)
    if world_result is not None: return world_result
    target = urlsplit(url)
    service = state.tool_services.get("gophish", {})
    config = service.get("config", {}).get("admin_server", {})
    address = config.get("listen_url", "127.0.0.1:3333")
    try: port = target.port
    except ValueError: return TerminalResult(False, ["curl: (3) URL rejected: invalid port"])
    expected_scheme = "https" if config.get("use_tls", True) else "http"
    if target.hostname not in {"localhost", "127.0.0.1"} or port != int(address.rsplit(":", 1)[-1]) or not service.get("running") or service.get("mode") == "phish":
        return TerminalResult(False, ["curl: (7) Failed to connect to the service in the simulated network"])
    if target.scheme != expected_scheme: return TerminalResult(False, ["curl: (35) SSL connect error (protocol does not match server)"])
    key = headers.get("authorization") or parse_qs(target.query).get("api_key", [""])[0]
    status, payload, action = 200, None, None
    if key != API_KEY: status, payload = 401, {"message": "Invalid API key", "success": False, "data": ""}
    else:
        endpoint = target.path.strip("/").split("/")
        data = state.tool_data["gophish"]
        if len(endpoint) < 2 or endpoint[0] != "api" or endpoint[1] not in {"groups", "templates", "pages", "smtp", "campaigns"}:
            status, payload = 404, {"message": "Not found", "success": False, "data": ""}
        else:
            kind = endpoint[1]; collection = data[kind]
            if method == "GET":
                if len(endpoint) == 2: payload = collection
                else:
                    record = next((r for r in collection if str(r["id"]) == endpoint[2]), None)
                    if record is None: status, payload = 404, {"message": "Not found", "success": False, "data": ""}
                    elif len(endpoint) == 4 and endpoint[3] == "results": payload = {k: record.get(k) for k in ("id", "name", "status", "results", "timeline")}
                    else: payload = record
            elif method == "POST":
                try:
                    payload = json.loads(body or "")
                    if not isinstance(payload, dict) or not isinstance(payload.get("name"), str) or not payload["name"].strip(): raise ValueError("name is required")
                    payload = dict(payload)
                    if kind == "campaigns":
                        if "red.phishing_initial_access" not in state.available_abilities.get("red", []): raise ValueError("Campaigns are unavailable for this contract")
                        for key_, resource in [("template", "templates"), ("page", "pages"), ("smtp", "smtp")]:
                            if not any(r["name"] == payload.get(key_, {}).get("name") for r in data[resource]): raise ValueError(f"Unknown {key_}")
                        names = [group["name"] for group in payload["groups"]]
                        groups = [g for g in data["groups"] if g["name"] in names]
                        if len(groups) != len(set(names)): raise ValueError("Unknown group")
                        emails = {t["email"] for g in groups for t in g.get("targets", [])}
                        hosts = [h for h in state.hosts.values() if h.id in state.discovered and h.primary_user and h.primary_user + "@" + state.domain.get("name", "lab.invalid") in emails]
                        if len(hosts) != 1: raise ValueError("This version requires one known recipient per campaign")
                        if not payload.get("url"): raise ValueError("url is required")
                        payload.update(status="Queued", results=[{"id": "sim-1", "email": next(iter(emails)), "status": "Email Sent"}], timeline=[])
                        if not service.get("disable_mailer") and service.get("mode") == "all":
                            template = next(r for r in data['templates'] if r['name'] == payload['template']['name'])
                            page = next(r for r in data['pages'] if r['name'] == payload['page']['name'])
                            smtp = next(r for r in data['smtp'] if r['name'] == payload['smtp']['name'])
                            blocked = any(term.casefold() in template.get('subject', '').casefold() for term in hosts[0].phishing.get('blocked_subjects', []))
                            action = QueuedAction("red", "red.phishing_initial_access", hosts[0].id, console_id=state.active_terminal_id, params={
                                "gophish_campaign_id": max([c["id"] for c in collection] or [0]) + 1,
                                "mail_filtered": blocked, "capture_passwords": bool(page.get('capture_credentials') and page.get('capture_passwords')),
                                "smtp_available": smtp.get('host') == 'smtp.lab.invalid:25'})
                    payload["id"] = max([c["id"] for c in collection] or [0]) + 1
                    if kind == 'campaigns': state.tool_data.setdefault('campaign_contracts', {})[str(payload['id'])] = state.conversation_id
                    collection.append(payload); status = 201
                except (ValueError, KeyError, TypeError, AttributeError) as exc:
                    status, payload = 400, {"message": str(exc), "success": False, "data": ""}
            else: status, payload = 405, {"message": "Method not implemented", "success": False, "data": ""}
    if fail and status >= 400: return TerminalResult(False, [f"curl: (22) The requested URL returned error: {status}"])
    output = ([f"HTTP/1.1 {status}", "Content-Type: application/json", ""] if show_headers else []) + [json.dumps(payload, ensure_ascii=False, indent=2)]
    return TerminalResult(True, output, action)


def finish_campaign(state, ctx, result):
    campaign_id = ctx.params.get("gophish_campaign_id")
    if not campaign_id: return
    for campaign in state.tool_data.get("gophish", {}).get("campaigns", []):
        if campaign["id"] != campaign_id: continue
        human_outcome = result.reason in {"recipient_ignored", "recipient_reported", "capture_disabled", "mail_filtered"}
        campaign["status"] = "In progress" if result.success else ("Completed" if human_outcome else "Error")
        status = {"recipient_reported": "Email Reported", "recipient_ignored": "Email Opened", "capture_disabled": "Clicked Link", "mail_filtered": "Error"}.get(result.reason, "Submitted Data" if result.success else "Error")
        for recipient in campaign["results"]: recipient["status"] = status
        campaign["timeline"].append({"time": state.tick, "message": status, "details": result.message})


def advance_campaigns(state: GameState) -> None:
    for action in state.pending_actions:
        cid = action.get("params", {}).get("gophish_campaign_id")
        if not cid or not state.tool_services.get("gophish", {}).get("running"): continue
        campaign = next((c for c in state.tool_data.get("gophish", {}).get("campaigns", []) if c["id"] == cid), None)
        if not campaign: continue
        created = action["params"].get("created_tick", state.tick)
        message = "Email Opened" if state.tick >= created + max(1, (action["ready_tick"] - created) // 2) else "Email Sent"
        if not any(e["message"] == "Email Sent" for e in campaign["timeline"]):
            campaign["timeline"].append({"time": state.tick, "message": "Email Sent"})
        if message == "Email Opened" and not any(e["message"] == message for e in campaign["timeline"]):
            campaign["timeline"].append({"time": state.tick, "message": message})
        campaign["status"] = "In progress"
        for recipient in campaign["results"]: recipient["status"] = message


def deployment_tools():
    from .deployment import TOOL_MARKERS
    return TOOL_MARKERS
