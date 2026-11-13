"""Opérations sur les fichiers du monde, partagés entre consoles et sauvegardés."""
import fnmatch
import hashlib
import posixpath
import shlex
from .virtual_shell import virtual_path


def directories(state):
    host = state.hosts.get(state.terminal_host)
    files = host.files if host else state.terminal_files
    key = host.id if host else 'operator'
    result = {'/', '/tmp'} | set(state.tool_data.get('vfs_dirs', {}).get(key, []))
    result |= {'/srv','/Tools','/Windows','/Windows/system32','/Users','/Users/'+state.terminal_user} if host and host.os.startswith('Windows') else ({'/home/'+state.terminal_user,'/srv','/etc','/root','/var','/usr','/usr/bin'} if host else {'/home','/home/operator','/home/operator/loot','/usr','/usr/bin','/opt','/etc'})
    for name in files:
        parent = posixpath.dirname(name)
        while parent not in result:
            result.add(parent)
            parent = posixpath.dirname(parent)
    return result


def writable(state, path):
    if state.terminal_host:
        return state.terminal_access == 'SYSTEM' or state.terminal_user == 'root' or path.startswith('/Users/'+state.terminal_user+'/') or path.startswith('/home/'+state.terminal_user+'/') or path.startswith('/tmp/')
    return path.startswith('/home/operator/') or path.startswith('/tmp/')


def audit(state, operation, path, before=None, after=None):
    if before != after:
        from .evidence import invalidate
        invalidate(state,path)
        if not state.terminal_host: state.tool_data.get("sqlite", {}).pop(path,None)
    def digest(text): return hashlib.sha256(text.encode()).hexdigest() if text is not None else None
    state.tool_data.setdefault('file_audit', []).append({'tick':state.tick,'console':state.active_terminal_id,'host':state.terminal_host or 'operator','user':state.terminal_user,'operation':operation,'path':path,'before':digest(before),'after':digest(after)})


def parse(line, state, abilities):
    from .terminal import TerminalResult
    windows = bool(state.terminal_host and state.hosts[state.terminal_host].os.startswith('Windows'))
    ps = windows and state.terminal_shell == 'powershell'
    try:
        words = shlex.split(line,posix=not windows)
        if windows: words = [v[1:-1] if len(v)>1 and v[0]==v[-1] and v[0] in '\"\'' else v for v in words]
    except ValueError: return None  # Le parseur du shell affiche l'erreur.
    if not words: return None
    head,args = words[0].casefold(),words[1:]
    if not windows and head == 'll':
        from .terminal import parse as dispatch
        return dispatch(shlex.join(['ls','-la',*args]),state,abilities)
    mapping = {'rm':'delete','rmdir':'rmdir','mkdir':'mkdir','touch':'touch','cp':'copy','mv':'move'} if not windows else ({'rm':'delete','del':'delete','erase':'delete','remove-item':'delete','mkdir':'mkdir','new-item':'mkdir','set-content':'write','add-content':'append'} if ps else {'del':'delete','erase':'delete','copy':'copy','move':'move','md':'mkdir','mkdir':'mkdir','rd':'rmdir','rmdir':'rmdir'})
    if windows and head in {'echo', 'write-output'} and any(v in args for v in ('>', '>>')):
        at = next(i for i,v in enumerate(args) if v in {'>', '>>'})
        if at != len(args)-2 or any(v in {'>', '>>'} for v in args[at+1:]): return TerminalResult(False,['Redirection : syntaxe non couverte.'])
        import re
        text = ' '.join(args[:at])
        text = re.sub(r'%([^%]+)%',lambda m:state.terminal_env.get(m[1].upper(),m[0]),text) if not ps else text
        head,args = 'add-content' if args[at]=='>>' else 'set-content',[args[-1],text]
        mapping[head] = 'append' if head=='add-content' else 'write'
    if head not in mapping: return None
    op = mapping[head]
    files = state.hosts[state.terminal_host].files if state.terminal_host else state.terminal_files
    dirs = directories(state)
    state.tool_data.setdefault("vfs_dirs", {}).setdefault(state.terminal_host or "operator", sorted(dirs))
    def resolve(value):
        value = virtual_path(value,state.terminal_cwd) if windows else posixpath.normpath((state.terminal_env.get('HOME','/home/operator')+value[1:]) if value=='~' or value.startswith('~/') else (value if value.startswith('/') else posixpath.join(state.terminal_cwd,value)))
        return next((p for p in set(files)|dirs if p.casefold()==value.casefold()),value) if windows else value
    operands=[]; recursive=False; force=False; i=0
    while i<len(args):
        arg=args[i]; lower=arg.casefold()
        if (not windows and arg in {'-r','-R','-f','-rf','-fr'}) or (windows and lower in {'/s','/q','-recurse','-force'}):
            recursive |= arg in {'-r','-R','-rf','-fr'} or lower in {'/s','-recurse'}
            force |= arg in {'-f','-rf','-fr'} or lower in {'/q','-force'}
        elif ps and lower in {'-path','-literalpath','-value'}:
            if i+1>=len(args): return TerminalResult(False,[head+': argument manquant.'])
            i+=1; operands.append(args[i])
        elif ps and lower=='-itemtype':
            if i+1>=len(args) or args[i+1].casefold()!='directory': return TerminalResult(False,['New-Item : seul -ItemType Directory est couvert.'])
            i+=1
        elif arg.startswith('-') or (windows and arg.startswith('/')):
            return TerminalResult(False,[head+': option non prise en charge.'])
        else: operands.append(arg)
        i+=1
    expected=2 if op in {'copy','move','write','append'} else 1
    if len(operands)!=expected: return TerminalResult(False,[head+': nombre d’arguments incorrect ; une opération à la fois.'])
    target=resolve(operands[0])
    if op=='mkdir':
        if target in dirs or target in files: return TerminalResult(False,[head+': le chemin existe déjà.'])
        if posixpath.dirname(target) not in dirs: return TerminalResult(False,[head+': dossier parent introuvable.'])
        if not writable(state,target): return TerminalResult(False,[head+': accès refusé.'])
        key=state.terminal_host or 'operator'
        state.tool_data.setdefault('vfs_dirs',{}).setdefault(key,[]).append(target)
        audit(state,'mkdir',target)
    elif op in {'touch','write','append','copy','move'}:
        destination=resolve(operands[1]) if op in {'copy','move'} else target
        from .file_access import readable
        if op in {'copy','move'} and not readable(state,target): return TerminalResult(False,[head+': Permission denied'])
        if op in {'copy','move'} and target not in files: return TerminalResult(False,[head+': fichier source introuvable (copie récursive non couverte).'])
        if op in {'copy','move'} and destination in dirs: destination=posixpath.join(destination,posixpath.basename(target))
        if destination in dirs: return TerminalResult(False,[head+': le chemin est un dossier.'])
        if posixpath.dirname(destination) not in dirs: return TerminalResult(False,[head+': dossier parent introuvable.'])
        if not writable(state,destination) or (op=='move' and not writable(state,target)): return TerminalResult(False,[head+': accès refusé.'])
        sqlite_script = state.tool_data.get("sqlite", {}).get(target) if not state.terminal_host and op in {"copy","move"} else None
        before=files.get(destination)
        content=files[target] if op in {'copy','move'} else ((before or '') if op in {'touch','append'} else '')
        if op in {'write','append'}: content+=operands[1]+'\n'
        files[destination]=content
        audit(state,op,destination,before,content)
        if op=='move' and target!=destination:
            old=files.pop(target);audit(state,'delete',target,old)
        if sqlite_script is not None: state.tool_data.setdefault('sqlite',{})[destination]=sqlite_script
    else:
        parent,pattern=posixpath.split(target)
        matches=[p for p in files if posixpath.dirname(p)==parent and fnmatch.fnmatchcase(posixpath.basename(p).casefold() if windows else posixpath.basename(p),pattern.casefold() if windows else pattern)]
        if target in dirs:
            if windows and head in {'del','erase'}: return TerminalResult(False,[head+': indique un fichier ou un motif ; suppression de dossier via rmdir.'])
            children=[p for p in files if p.startswith(target.rstrip('/')+'/')]
            childdirs=[p for p in dirs if p.startswith(target.rstrip('/')+'/')]
            if op=='delete' and not recursive: return TerminalResult(False,[head+': est un dossier ; option récursive requise.'])
            if op=='rmdir' and (children or childdirs) and not recursive: return TerminalResult(False,[head+': dossier non vide.'])
            matches=children
        elif op=='rmdir': return TerminalResult(False,[head+': dossier introuvable.'])
        if not matches and target not in dirs and not force: return TerminalResult(False,[head+': fichier introuvable.'])
        if not writable(state,target) or any(not writable(state,p) for p in matches): return TerminalResult(False,[head+': accès refusé.'])
        for name in matches:
            old=files.pop(name);audit(state,'delete',name,old)
        if target in dirs:
            key=state.terminal_host or 'operator'
            kept=[p for p in dirs if p!=target and not p.startswith(target.rstrip('/')+'/')]
            state.tool_data.setdefault('vfs_dirs',{})[key]=kept
            audit(state,'rmdir',target)
    return TerminalResult(True)
