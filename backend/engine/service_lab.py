"""Petit service vulnérable fictif, analysable dans le monde du jeu."""
import shlex
from .shell_tools import path
from .data_tools import fact


def parse(line,state,abilities):
    from .terminal import TerminalResult
    try:words=shlex.split(line)
    except ValueError:return None
    if not words or words[0] not in {'nc','checksec','gdb','python3'}:return None
    if state.terminal_host:return TerminalResult(False,['Utilise ces outils dans une console Kali locale.'])
    if state.terminal_foreground is not None:return TerminalResult(False,['Un processus occupe cette console.'])
    lab=state.environment.get('service_lab',{})
    if not lab:return TerminalResult(False,[words[0]+': aucun service ou binaire compatible dans ce dossier.'])
    tool,args=words[0],words[1:]
    if args==['--help']:return TerminalResult(True,[{'nc':'nc [-nv] host port','checksec':'checksec --file=binary','gdb':'gdb -q binary -ex "info functions" -ex quit','python3':'python3 script --host host --port port --offset bytes --ret address'}[tool]])
    binary=lab['binary'];host=state.hosts[lab['host']]
    if tool=='nc':
        operands=[a for a in args if not a.startswith('-')]
        if any(a.startswith('-') and a not in {'-n','-v','-nv','-vn'} for a in args) or len(operands)!=2:return TerminalResult(False,['usage: nc -nv host port'])
        if operands[0] not in {host.ip,host.hostname} or operands[1]!=str(lab['port']) or state.is_blocked(host.id,lab['port']):return TerminalResult(False,['nc: connection refused'])
        fact(state,'lab:banner')
        return TerminalResult(True,[f'Connection to {host.ip} {lab["port"]} port [tcp/*] succeeded!',lab['banner'],'Timeout waiting for a framed request; connection closed.'])
    if tool=='checksec':
        target=args[0].split('=',1)[1] if len(args)==1 and args[0].startswith('--file=') else (args[1] if len(args)==2 and args[0]=='--file' else '')
        if path(state,target)!=binary or binary not in state.terminal_files:return TerminalResult(False,['checksec: file not found or unsupported binary'])
        fact(state,'lab:checksec')
        return TerminalResult(True,['Arch: amd64-64-little','RELRO: Partial RELRO','Stack: No canary found','NX: NX enabled','PIE: No PIE (0x400000)'])
    if tool=='gdb':
        if args!=['-q',binary,'-ex','info functions','-ex','quit']:return TerminalResult(False,['Supported: gdb -q '+binary+' -ex "info functions" -ex quit'])
        fact(state,'lab:symbols')
        return TerminalResult(True,['Reading symbols from '+binary+'...', 'Non-debugging symbols:',f'{lab["ret"]:#018x}  maintenance_shell', '0x0000000000401220  handle_ticket'])
    if len(args)<1 or path(state,args[0])!=lab['script'] or lab['script'] not in state.terminal_files:return TerminalResult(False,['python3: ce terminal ne lance que les scripts de laboratoire fournis ; aucun interpréteur système.'])
    opts={};i=1
    while i<len(args):
        if args[i] not in {'--host','--port','--offset','--ret'} or i+1>=len(args):return TerminalResult(False,['Invalid laboratory script arguments'])
        opts[args[i]]=args[i+1];i+=2
    try:valid=opts['--host'] in {host.ip,host.hostname} and int(opts['--port'])==lab['port'] and int(opts['--offset'])==lab['offset'] and int(opts['--ret'],0)==lab['ret']
    except (KeyError,ValueError):valid=False
    if lab['binary'] not in state.terminal_files:return TerminalResult(False,['Laboratory binary missing'])
    if not any(service.port==lab['port'] for service in host.services):valid=False
    if not valid:return TerminalResult(False,['Connection opened; invalid frame or return address. Service closed the connection.'])
    if state.is_blocked(host.id,lab['port']):return TerminalResult(False,['Connection refused'])
    from .console_sessions import enter
    host.status,host.compromised_by,host.access_level='COMPROMISED','red','USER'
    fact(state,'lab:access')
    enter(state,host,lab['user'],'USER')
    return TerminalResult(True,['Maintenance handler reached.','Session opened as '+lab['user']+' (limited permissions).'])
