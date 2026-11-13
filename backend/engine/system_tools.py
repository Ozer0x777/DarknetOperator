"""Inventaire système des machines virtuelles ; aucun appel au système hôte."""
import posixpath
import shlex
from .data_tools import fact
from .file_access import readable


def describe(state):
    host=state.hosts.get(state.terminal_host)
    configured=state.environment.get('systems',{}).get(host.id if host else 'operator',{})
    windows=bool(host and host.os.startswith('Windows'))
    defaults=dict(os=host.os if host else 'Kali GNU/Linux',kernel='6.8.0',arch='x86_64',uid=1000,gid=1000,groups=[state.terminal_user],packages={},services={},processes=[],routes=[],dns='10.20.0.1',files={},sudo=[],hotfixes=[],privileges=[])
    defaults.update(configured)
    if windows and state.terminal_access=='SYSTEM':defaults.update(groups=['NT AUTHORITY\\SYSTEM','BUILTIN\\Administrators'],privileges=['SeDebugPrivilege Enabled','SeImpersonatePrivilege Enabled','SeChangeNotifyPrivilege Enabled'])
    if state.terminal_user=='root':defaults.update(uid=0,gid=0,groups=['root'],sudo=['(ALL : ALL) ALL'])
    return host,windows,defaults


def parse(line,state,abilities=None):
    from .terminal import TerminalResult
    if state.terminal_auth or state.terminal_foreground is not None:return None
    host,windows,spec=describe(state)
    try:words=shlex.split(line,posix=not windows)
    except ValueError:return None
    words=[w.strip('"') for w in words]
    if not words:return None
    tool=words[0].lower().removesuffix('.exe');args=words[1:];lower=[a.casefold() for a in args]
    hostid=host.id if host else 'operator';user=state.terminal_user
    def ok(lines,key=None):
        fact(state,'system:'+hostid+':'+(key or tool),user=user,access=state.terminal_access)
        return TerminalResult(True,lines)
    def fail(text):return TerminalResult(False,[text])
    if (tool=='bash' and not windows and len(args)==1) or (tool=='winpeas' and windows and not args):
        from .shell_tools import path
        filename=path(state,args[0]) if tool=='bash' else None
        files=host.files if host else state.terminal_files
        if tool=='bash' and files.get(filename)!='VIRTUAL-SCRIPT:linpeas\n':return None
        return ok(['System: '+spec['os'], 'Version: '+(spec.get('build','10.0') if windows else spec['kernel']), 'User: '+user, 'Groups: '+', '.join(spec['groups']), 'Packages / Hotfixes:', *([n+' '+v for n,v in spec['packages'].items()] if not windows else spec['hotfixes']), 'Services:', *[n+' '+v for n,v in spec['services'].items()], 'Review package fixes, permissions and service configuration before choosing a technique.'], 'inventory')
    if tool=='whoami' and windows:
        identity='nt authority\\system' if state.terminal_access=='SYSTEM' else state.terminal_env.get('USERDOMAIN',host.hostname).lower()+'\\'+user
        if not args:return ok([identity])
        if any(a not in {'/all','/user','/groups','/priv'} for a in lower):return fail('ERROR: Invalid argument/option. Type WHOAMI /? for usage.')
        output=[]
        if '/all' in lower or '/user' in lower:output+=['USER INFORMATION',identity+'  '+state.domain.get('sid','S-1-5-21-0')+'-1101']
        if '/all' in lower or '/groups' in lower:output+=['GROUP INFORMATION',*spec['groups']]
        if '/all' in lower or '/priv' in lower:output+=['PRIVILEGES INFORMATION',*spec['privileges']]
        return ok(output)
    if tool in {'id','groups','uname'} and not windows:
        if tool=='id':
            if args:return fail('id: only current identity is available in this image')
            return ok([f"uid={spec['uid']}({user}) gid={spec['gid']}({user}) groups="+', '.join(f'{spec["gid"] if n==0 else 100+n}({g})' for n,g in enumerate(spec['groups']))])
        if tool=='groups' and not args:return ok([' '.join(spec['groups'])])
        if tool=='uname' and args in ([],['-a'],['-r'],['-m'],['-s']):
            value={'-r':spec['kernel'],'-m':spec['arch'],'-s':'Linux'}.get(args[0] if args else '-s',f"Linux {host.hostname if host else 'redteam'} {spec['kernel']} #1 SMP {spec['arch']} GNU/Linux")
            return ok([value])
        return None
    if tool=='sudo' and not windows:
        if args!=['-l']:return fail('sudo: only permission listing is installed in this image; use sudo -l')
        if spec['sudo']:return ok([f'User {user} may run the following commands:',*spec['sudo']])
        result=ok([f'Sorry, user {user} may not run sudo on {host.hostname if host else "redteam"}.'])
        result.ok=False;result.exit_code=1
        return result
    if tool=='ip' and not windows and args in (['route'],['route','show']):
        return ok(spec['routes'] or [f'{host.ip.rsplit(".",1)[0] if host else "10.10.14"}.0/24 dev eth0 proto kernel scope link'])
    if tool in {'ss','netstat'} and not windows and args in (['-lntp'],['-lnt'],['-tulpn']):
        lines=['State  Local Address:Port  Process',*[f'LISTEN 0.0.0.0:{s.port} {s.name}' for s in (host.services if host else [])]]
        if not host:
            for service in state.tool_services.values():
                if not service.get('running'):continue
                if service.get('kind')=='ssh-forward':lines.append(f'LISTEN 127.0.0.1:{service["listen_port"]} ssh pid={service["pid"]}')
                elif 'config' in service:
                    for name in ('admin_server','phish_server'):
                        if name=='admin_server' and service.get('mode')=='phish':continue
                        if name=='phish_server' and service.get('mode')=='admin':continue
                        address=service['config'].get(name,{}).get('listen_url')
                        if address:lines.append(f'LISTEN {address} gophish pid={service["pid"]}')
        return ok(lines)
    if tool=='ps' and not windows and args in (['aux'],['-ef']):
        tools=[f'{user} {s["pid"]} '+('ssh -N -L '+str(s['listen_port'])+':'+s['destination']+':'+str(s['destination_port']) if s.get('kind')=='ssh-forward' else 'gophish') for s in state.tool_services.values() if not host and s.get('running')]
        return ok(['USER PID COMMAND',*spec['processes'],*tools])
    if tool=='systemctl' and not windows:
        if args in ([],['list-units'],['list-units','--type=service']):return ok([name+'.service '+value for name,value in spec['services'].items()])
        if len(args)==2 and args[0]=='status':
            name=args[1].removesuffix('.service');status=spec['services'].get(name)
            return ok([name+'.service', 'Active: '+status]) if status else fail('Unit '+args[1]+' could not be found.')
        return fail('systemctl: invalid arguments for this image')
    if tool in {'dpkg-query','dpkg','rpm'} and not windows:
        packages=spec['packages']
        if tool=='dpkg-query' and args and args[0]=='-W':
            fmt='${Package}\t${Version}\n';names=[];i=1
            while i<len(args):
                if args[i].startswith('-f='):fmt=args[i][3:]
                elif args[i]=='-f' and i+1<len(args):i+=1;fmt=args[i]
                elif args[i].startswith('-'):return fail('dpkg-query: unknown option '+args[i])
                else:names.append(args[i])
                i+=1
            names=names or list(packages)
            if any(n not in packages for n in names):return fail('dpkg-query: no packages found matching '+','.join(names))
            return ok([fmt.replace('${Package}',n).replace('${Version}',packages[n]).replace('\\n','').replace('\\t','\t') for n in names])
        if tool=='dpkg' and len(args)==2 and args[0] in {'-s','--status','-l'}:
            name=args[1]
            return ok([f'Package: {name}', 'Status: install ok installed', 'Version: '+packages[name]]) if name in packages else fail('dpkg-query: package is not installed')
        if tool=='rpm' and len(args)==2 and args[0]=='-q':return ok([args[1]+'-'+packages[args[1]]]) if args[1] in packages else fail('package '+args[1]+' is not installed')
        return fail(tool+': invalid arguments')
    if tool=='pkexec' and not windows:
        if args==['--version']:return ok(['pkexec version '+spec.get('polkit_version','0.105')])
        return fail('Error executing command as another user: Not authorized')
    if tool=='getcap' and not windows and args==['-r','/']:
        return ok([p+' '+m['capabilities'] for p,m in spec['files'].items() if m.get('capabilities')])
    if tool=='find' and not windows and args and args[0]=='/' and '-perm' in args:
        if args[args.index('-perm')+1:] not in (['-4000'],['-4000','-type','f']):return None
        return ok([p for p,m in spec['files'].items() if m.get('suid')])
    if tool=='stat' and not windows and len(args)==1:
        from .shell_tools import path
        filename=path(state,args[0]);files=host.files if host else state.terminal_files
        if filename not in files:return fail('stat: cannot stat '+args[0]+': No such file or directory')
        m=spec['files'].get(filename,{})
        if not readable(state,filename):return fail('stat: Permission denied')
        return ok([f'File: {filename}',f'Size: {len(files[filename].encode())}',f'Access: ({m.get("mode","0644")}) Uid: ({m.get("owner","root")}) Gid: ({m.get("group","root")})'])
    if windows:
        if tool=='ver' and not args:return ok(['Microsoft Windows [Version '+spec.get('build','10.0')+']'])
        if tool=='systeminfo' and not args:return ok(['Host Name: '+host.hostname,'OS Name: '+host.os,'OS Version: '+spec.get('build','10.0.20348'), 'Domain: '+state.domain.get('name','WORKGROUP'),'Hotfix(s): '+', '.join(spec['hotfixes'])])
        if tool=='route' and lower==['print']:return ok(['IPv4 Route Table',*spec['routes']])
        if tool=='netstat' and lower in (['-ano'],['-an']):return ok(['Proto Local Address State',*[f'TCP 0.0.0.0:{s.port} LISTENING' for s in host.services]])
        if tool=='tasklist' and not args:return ok(['Image Name PID',*spec['processes']])
        if tool=='sc' and lower and lower[0]=='query':return ok([name+': '+value for name,value in spec['services'].items() if len(lower)==1 or name.casefold()==lower[1]])
        if tool=='get-hotfix' and not args and state.terminal_shell=='powershell':return ok(['Source Description HotFixID',*[host.hostname+' Security Update '+v for v in spec['hotfixes']]])
        if tool=='get-ciminstance' and lower in (['win32_operatingsystem'],['-classname','win32_operatingsystem']) and state.terminal_shell=='powershell':return ok(['Caption: '+host.os,'Version: '+spec.get('build','10.0.20348')])
        if tool in {'icacls','get-acl'} and len(args)==1:
            from .virtual_shell import virtual_path
            filename=virtual_path(args[0],state.terminal_cwd)
            if filename not in host.files:return fail('The system cannot find the file specified.')
            if not readable(state,filename):return fail('Access is denied.')
            return ok([args[0]+' '+spec['files'].get(filename,{}).get('acl','NT AUTHORITY\\SYSTEM:(F) '+user+':(R)')])
        if tool=='net' and lower in (['user','/domain'],['group','/domain'],['localgroup','administrators']):
            directory=state.environment.get('directory',{})
            values=[u.username for u in state.users.values()] if lower[0]=='user' else (host.admin_users if lower[0]=='localgroup' else directory.get('groups',[]))
            return ok(values+['The command completed successfully.'])
    # Seuls les artefacts fournis par le laboratoire sont compilés/interprétés.
    if not windows and tool=='gcc' and host and len(args)==3 and args[1]=='-o':
        from .shell_tools import path
        from .virtual_files import writable
        source=path(state,args[0]);dest=path(state,args[2])
        if host.files.get(source)!='VIRTUAL-SOURCE:CVE-2021-4034\n':return fail('gcc: source is not a compilable image artifact')
        if not writable(state,dest):return fail('gcc: Permission denied')
        host.files[dest]='VIRTUAL-ELF:CVE-2021-4034\n';fact(state,'polkit:compiled',path=dest)
        return ok([])
    if not windows and host and (tool.startswith('./') or tool.startswith('/')):
        from .shell_tools import path
        target=path(state,words[0])
        if host.files.get(target)=='VIRTUAL-ELF:CVE-2021-4034\n' and not args:
            if not spec.get('polkit_vulnerable') or not spec['files'].get('/usr/bin/pkexec',{}).get('suid'):return fail('pkexec: exploit conditions not satisfied on this patched image')
            from .console_sessions import enter
            enter(state,host,'root','ROOT');host.access_level='ROOT';host.compromised_by='red';host.status='COMPROMISED'
            fact(state,'polkit:root',host=host.id)
            return TerminalResult(True,['#'])
    return None
