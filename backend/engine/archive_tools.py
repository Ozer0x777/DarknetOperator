"""Archives tar virtuelles : liste et extraction dans les seuls fichiers du joueur."""
import json
import posixpath
import shlex
from .shell_tools import path
from .data_tools import write,fact


def parse(line,state):
    from .terminal import TerminalResult
    try:args=shlex.split(line)
    except ValueError:return None
    if not args or args[0]!='tar':return None
    if args==['tar','--help']:return TerminalResult(True,['tar -tf archive | tar -xf archive [-C directory]'])
    if state.terminal_foreground is not None:return TerminalResult(False,['Un processus occupe cette console.'])
    if state.terminal_host:return TerminalResult(False,['Utilise tar dans Kali pour les archives locales.'])
    if len(args)<3 or args[1] not in {'-tf','-xf','-xvf'}:return TerminalResult(False,['usage: tar -tf archive | tar -xf archive [-C directory]'])
    archive=path(state,args[2]);content=state.terminal_files.get(archive,'')
    if not content.startswith('VIRTUAL-TAR\n'):return TerminalResult(False,['tar: unsupported archive or file not found'])
    try:members=json.loads(content.split('\n',1)[1])
    except ValueError:return TerminalResult(False,['tar: invalid archive'])
    if not isinstance(members,dict):return TerminalResult(False,['tar: invalid archive'])
    if args[1]=='-tf':
        if len(args)!=3:return TerminalResult(False,['tar: unsupported option'])
        fact(state,'tar:list:'+archive)
        state.tool_data.setdefault('read_files',[]).append('operator:'+archive)
        return TerminalResult(True,sorted(members))
    if len(args)==3:folder=state.terminal_cwd
    elif len(args)==5 and args[3]=='-C':folder=path(state,args[4])
    else:return TerminalResult(False,['tar: invalid extraction arguments'])
    from .virtual_files import directories,writable
    if folder not in directories(state) or not writable(state,folder+'/'):return TerminalResult(False,['tar: target directory unavailable'])
    destinations={}
    for name,value in members.items():
        if not isinstance(name,str) or not isinstance(value,str):return TerminalResult(False,['tar: invalid member'])
        destination=posixpath.normpath(folder+'/'+name)
        if name.startswith('/') or destination==folder or not destination.startswith(folder.rstrip('/')+'/') or not writable(state,destination):return TerminalResult(False,['tar: unsafe member path'])
        destinations[destination]=value
    dirs=state.tool_data.setdefault('vfs_dirs',{}).setdefault('operator',[])
    for destination in destinations:
        parent=posixpath.dirname(destination)
        while parent not in directories(state):dirs.append(parent);parent=posixpath.dirname(parent)
    for destination,value in destinations.items():write(state,destination,value)
    fact(state,'tar:extract:'+archive)
    return TerminalResult(True,sorted(members) if args[1]=='-xvf' else [])
