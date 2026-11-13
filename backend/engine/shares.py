"""Partages SMB nommés ; le partage administratif C$ conserve son modèle existant."""
import posixpath
import shlex
from .data_tools import fact, write


def parse(args,state):
    from .terminal import TerminalResult
    if not args:return None
    listing=args[0]=='-L'
    if not listing and (not args[0].startswith('//') or '/' not in args[0][2:]):return None
    if not listing and args[0].split('/',3)[-1].casefold()=='c$':return None
    try:
        ref=args[1] if listing else args[0][2:].split('/',1)[0]
        host=state.find_host(ref)
        if not host or host.id not in state.discovered or not host.has_service('SMB',445) or state.is_blocked(host.id,445):raise ValueError('NT_STATUS_CONNECTION_REFUSED')
        shares=state.environment.get('shares',{}).get(host.id,{})
        username='guest';secret=None
        i=2 if listing else 1; command=None
        while i<len(args):
            if args[i]=='-N':i+=1;continue
            if args[i] in {'-U','-c'} and i+1<len(args):
                if args[i]=='-U':username,secret=args[i+1].split('%',1)
                else:command=args[i+1]
                i+=2;continue
            raise ValueError('smbclient: unsupported argument '+args[i])
        def permitted(spec):
            if username=='guest':return '*' in spec.get('users',[])
            from .authentication import authenticate
            return bool(authenticate(state,host,username,secret)) and username in spec.get('users',[])
        if listing:return TerminalResult(True,['Sharename       Type',*[(name+'       Disk') for name,spec in shares.items() if permitted(spec)]])
        share=args[0][2:].split('/',1)[1]
        if share not in shares:raise ValueError('NT_STATUS_BAD_NETWORK_NAME')
        spec=shares[share]
        if not permitted(spec):raise ValueError('NT_STATUS_ACCESS_DENIED')
        operation=shlex.split(command or '')
        if not operation:raise ValueError('Use -c "ls" or -c "get file destination"')
        root=spec['path'].rstrip('/')
        relative=operation[1] if len(operation)>1 else '.'
        source=posixpath.normpath(root+'/'+relative.replace('\\','/'))
        if source!=root and not source.startswith(root+'/'):raise ValueError('NT_STATUS_ACCESS_DENIED')
        if operation[0]=='ls' and len(operation)<=2:
            fact(state,'smb:list:'+host.id+':'+share)
            return TerminalResult(True,[name[len(root)+1:] for name in sorted(host.files) if name.startswith(source.rstrip('/')+'/')])
        if operation[0]!='get' or len(operation)!=3:raise ValueError('Read-only share: supported operation is get source destination')
        if source not in host.files:raise ValueError('NT_STATUS_OBJECT_NAME_NOT_FOUND')
        from .file_access import readable
        if not readable(state,source,username,host):raise ValueError('NT_STATUS_ACCESS_DENIED')
        if 'red.exfiltrate' not in state.available_abilities.get('red',[]):raise ValueError('Transfers unavailable for this contract')
        from .shell_tools import path
        destination=path(state,operation[2]);write(state,destination,host.files[source])
        state.exfiltrated[host.id+':'+source]=host.files[source]
        fact(state,'smb:get:'+host.id+':'+source,path=destination)
        return TerminalResult(True,[f'getting file {relative} as {destination}'])
    except (ValueError,IndexError) as exc:return TerminalResult(False,[str(exc)])
