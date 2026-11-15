"""Redirection locale OpenSSH en mémoire, liée au processus de sa console."""
import shlex
from .data_tools import fact


def resolve(state,address,port):
    if address not in {'127.0.0.1','localhost'}:return None
    from .network_tools import client_alive
    for item in state.tool_services.values():
        if item.get('listen_port') != port:
            continue
        if item.get('kind') == 'ssh-forward' and item.get('running') and state.reachable(state.hosts.get(item['jump']), 22, source='operator'):
            return item
        if item.get('kind') == 'chisel-client' and not item.get('socks') and client_alive(state, item) and not next((s.get('process_host') for s in state.tool_services.values() if s.get('pid') == item.get('server_pid')), None):
            return item
    return None



def parse(line,state):
    from .terminal import TerminalResult
    if state.terminal_auth or state.terminal_foreground is not None or state.terminal_host:return None
    try:words=shlex.split(line)
    except ValueError:return None
    if not words or words[0]!='ssh' or '-L' not in words:return None
    args=words[1:];identity=None;binding=None;no_command=False;i=0
    while i<len(args):
        a=args[i]
        if a=='-N':no_command=True
        elif a=='-L' and i+1<len(args):i+=1;binding=args[i]
        elif a=='-o' and i+1<len(args) and args[i+1]=='ExitOnForwardFailure=yes':i+=1
        elif not a.startswith('-') and identity is None:identity=a
        else:return TerminalResult(False,['ssh: invalid forwarding arguments'])
        i+=1
    if not no_command or not identity or '@' not in identity or not binding:return TerminalResult(False,['usage: ssh -N -L [127.0.0.1:]port:host:hostport user@jump'])
    parts=binding.split(':')
    if len(parts)==4 and parts[0] in {'127.0.0.1','localhost'}:parts=parts[1:]
    if len(parts)!=3 or not parts[0].isdigit() or not parts[2].isdigit() or not all(1<=int(parts[n])<=65535 for n in [0,2]):return TerminalResult(False,['Bad local forwarding specification'])
    user,ref=identity.rsplit('@',1);jump=state.find_host(ref)
    if not jump or jump.id not in state.discovered or not state.reachable(jump,22):return TerminalResult(False,['ssh: connect to host: Connection refused'])
    from .network_tools import listener_busy
    if listener_busy(state,int(parts[0])):return TerminalResult(False,['bind [127.0.0.1]: Address already in use'])
    state.terminal_auth=dict(kind='ssh-forward',username=user,host=jump.id,attempts=0,listen_port=int(parts[0]),destination=parts[1],destination_port=int(parts[2]))
    return TerminalResult(True,[f"{user}@{jump.ip}'s password:"])


def finish(state,password):
    from .terminal import TerminalResult
    from .authentication import authenticate
    pending=state.terminal_auth;host=state.hosts.get(pending['host'])
    credential=authenticate(state,host,pending['username'],password)
    if not credential or (credential.username!=host.primary_user and credential.username not in host.admin_users) or not state.reachable(host,22):
        pending['attempts']+=1
        if pending['attempts']>=3:state.terminal_auth={}
        return TerminalResult(False,['Permission denied (publickey,password).'])
    pid=int(state.tool_data.get('next_pid',3200));state.tool_data['next_pid']=pid+1
    state.tool_services['ssh:'+str(pid)]=dict(kind='ssh-forward',running=True,pid=pid,owner=state.active_terminal_id,jump=host.id,listen_port=pending['listen_port'],destination=pending['destination'],destination_port=pending['destination_port'])
    state.terminal_foreground=pid;state.terminal_auth={}
    fact(state,'ssh:forward',jump=host.id,port=pending['listen_port'])
    return TerminalResult(True,[])
