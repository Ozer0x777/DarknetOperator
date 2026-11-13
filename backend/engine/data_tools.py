"""Clients SQL et SQLmap du monde virtuel. SQLite ne touche qu'à :memory:."""
import csv
import hashlib
from functools import lru_cache
import io
import json
import posixpath
import shlex
import sqlite3
from urllib.parse import urlsplit, parse_qs
from .shell_tools import path


def connect(script):
    db = sqlite3.connect(':memory:')
    db.setlimit(sqlite3.SQLITE_LIMIT_LENGTH, 2_000_000)
    db.setlimit(sqlite3.SQLITE_LIMIT_SQL_LENGTH, 200_000)
    db.setlimit(sqlite3.SQLITE_LIMIT_COLUMN, 128)
    db.set_progress_handler(lambda: 1, 200000)
    forbidden = {sqlite3.SQLITE_ATTACH, sqlite3.SQLITE_DETACH, sqlite3.SQLITE_PRAGMA}
    def authorize(action, arg1, arg2, *_):
        if action in forbidden or (action == sqlite3.SQLITE_FUNCTION and str(arg2).lower() in {'load_extension','readfile','writefile'}): return sqlite3.SQLITE_DENY
        return sqlite3.SQLITE_OK
    db.set_authorizer(authorize)
    try: db.executescript(script)
    except Exception:
        db.close()
        raise
    return db


@lru_cache(maxsize=32)
def canonical_dump(script):
    db=connect(script)
    try:
        db.set_authorizer(None)
        return '\n'.join(db.iterdump())+'\n'
    finally:db.close()


def query(script, statement, with_reads=False):
    db = connect(script)
    try:
        reads=[]
        def authorize(action,a,b,*_):
            if action==sqlite3.SQLITE_READ:reads.append(a)
            return sqlite3.SQLITE_OK if action in {sqlite3.SQLITE_SELECT,sqlite3.SQLITE_READ,sqlite3.SQLITE_FUNCTION,sqlite3.SQLITE_RECURSIVE} else sqlite3.SQLITE_DENY
        db.set_authorizer(authorize)
        cursor = db.execute(statement)
        rows = cursor.fetchmany(5001)
        if len(rows)>5000: raise ValueError('Result too large; add a WHERE or LIMIT clause (maximum 5000 rows).')
        result=([col[0] for col in cursor.description or []],rows)
        return (*result,sorted(set(reads))) if with_reads else result
    finally: db.close()


def csv_text(columns, rows):
    out=io.StringIO(); writer=csv.writer(out,lineterminator='\n')
    writer.writerow(columns); writer.writerows(rows)
    return out.getvalue()


def fact(state, key, **values):
    state.tool_data.setdefault('facts', {})[key] = values or {'ok':True}


def write(state, destination, content):
    from .virtual_files import writable, directories, audit
    if not writable(state,destination): raise ValueError(destination+': Permission denied')
    if posixpath.dirname(destination) not in directories(state): raise ValueError(destination+': No such directory')
    before=state.terminal_files.get(destination)
    state.terminal_files[destination]=content
    audit(state,'write',destination,before,content)


def parse(line,state,abilities):
    from .terminal import TerminalResult
    try:
        lexer=shlex.shlex(line,posix=True,punctuation_chars='<>');lexer.whitespace_split=True;words=list(lexer)
    except ValueError:return None
    if not words or words[0] not in {'sqlmap','sqlite3','mysql'}:return None
    if state.terminal_host:
        return TerminalResult(False,['Cet outil est installé dans Kali. Utilise une console locale.'])
    if state.terminal_foreground is not None:return TerminalResult(False,['Un processus occupe cette console.'])
    try:
        destination=None; source=None
        if '>' in words:
            at=words.index('>')
            if at!=len(words)-2:raise ValueError('Invalid redirection')
            destination=path(state,words[-1]);words=words[:at]
        if '<' in words:
            at=words.index('<')
            if at!=len(words)-2:raise ValueError('Invalid input redirection')
            source=path(state,words[-1]);words=words[:at]
        if words[0]=='sqlmap': result=sqlmap(words[1:],state)
        elif words[0]=='sqlite3':result=sqlite_cli(words[1:],state,source)
        else:
            result=mysql_cli(words[1:],state,destination)
            destination=None  # mysql écrit lui-même son fichier, y compris après l'invite de mot de passe
        if destination and not state.terminal_auth and result.ok:
            write(state,destination,'\n'.join(result.output)+ ('\n' if result.output else ''))
            result.output=[]
        return result
    except (ValueError,sqlite3.Error,KeyError,TypeError) as exc:
        return TerminalResult(False,[str(exc)],exit_code=1)


def sqlite_cli(args,state,source):
    from .terminal import TerminalResult
    if args==['--help']:return TerminalResult(True,['sqlite3 [-header] [-csv] database [SQL | .tables | .schema | .read file] ; sqlite3 database < dump.sql'])
    headers=False;mode='|';operands=[]
    for arg in args:
        if arg in {'-header','-headers'}:headers=True
        elif arg=='-csv':mode=','
        elif arg.startswith('-'):raise ValueError('sqlite3: unsupported option '+arg)
        else:operands.append(arg)
    if not 1<=len(operands)<=2:raise ValueError('usage: sqlite3 database "SQL" | sqlite3 database < dump.sql')
    filename=path(state,operands[0]); command=operands[1] if len(operands)>1 else ''
    dbs=state.tool_data.setdefault('sqlite',{})
    if command.startswith('.read '):source=path(state,command[6:].strip());command=''
    if source:
        if source not in state.terminal_files:raise ValueError(source+': No such file')
        script=state.terminal_files[source]
        with connect(script) as db:
            db.set_authorizer(None)
            canonical='\n'.join(db.iterdump())+'\n'
        db.close()
        write(state,filename,'SQLite format 3\x00VIRTUAL:'+filename)
        dbs[filename]=canonical
        state.tool_data.setdefault('read_files',[]).append('operator:'+source)
        fact(state,'sqlite:import:'+filename,source=source)
        return TerminalResult(True,[])
    if filename not in dbs or not state.terminal_files.get(filename,'').startswith('SQLite format 3\x00VIRTUAL:'):raise ValueError('Error: database not loaded; import a SQL dump with .read first')
    if command=='.tables':
        cols,rows=query(dbs[filename],"SELECT name FROM sqlite_master WHERE type='table' ORDER BY name")
        return TerminalResult(True,['  '.join(str(r[0]) for r in rows)])
    if command.startswith('.schema'):
        table=command[len('.schema'):].strip()
        if table and not table.replace('_','').isalnum():raise ValueError('Invalid table')
        statement="SELECT sql FROM sqlite_master WHERE type='table'"+(" AND name='"+table+"'" if table else '')
        _,rows=query(dbs[filename],statement)
        return TerminalResult(True,[str(r[0])+';' for r in rows])
    if not command:raise ValueError('Interactive SQLite shell is not implemented; supply a quoted query')
    columns,rows,tables=query(dbs[filename],command,with_reads=True)
    state.tool_data.setdefault('queries',[]).append({'database':filename,'sql':command,'columns':columns,'rows':[list(r) for r in rows],'tables':tables,'source_digest':hashlib.sha256(dbs[filename].encode()).hexdigest()})
    fact(state,'sqlite:query:'+filename)
    output=csv_text(columns,rows).rstrip('\n') if mode==',' else '\n'.join(([mode.join(columns)] if headers else [])+[mode.join('' if v is None else str(v) for v in row) for row in rows])
    return TerminalResult(True,[output] if output else [])


def sqlmap(args,state):
    from .terminal import TerminalResult
    if args in [['--help'],['-h']]:return TerminalResult(True,['sqlmap -u URL [-p parameter] --batch [--dbs | -D database --tables | -D database -T table --columns | --dump] [-C columns] [--where=condition] [--output-dir=directory]'])
    opts={};flags=set();i=0
    valued={'-u','--url','-p','-D','-T','-C','--where','--output-dir','--cookie'}
    allowed={'--batch','--dbs','--tables','--columns','--dump'}
    while i<len(args):
        arg=args[i];name,sep,value=arg.partition('=')
        if name in valued:
            if not sep:
                i+=1
                if i>=len(args):raise ValueError('sqlmap: missing value for '+name)
                value=args[i]
            opts[name]=value
        elif arg in allowed:flags.add(arg)
        else:raise ValueError('sqlmap: unsupported option '+arg)
        i+=1
    url=opts.get('-u',opts.get('--url',''));target=urlsplit(url)
    host=state.find_host(target.hostname or '')
    if not host or host.id not in state.discovered:raise ValueError('sqlmap: target unknown; verify the address first')
    port=target.port or (443 if target.scheme=='https' else 80)
    if not state.reachable(host,port):raise ValueError('sqlmap: connection failed')
    surfaces=state.environment.get('sql_surfaces',{}).get(host.id,{})
    surface=surfaces.get(target.path)
    parameter=opts.get('-p',surface.get('parameter','') if surface else '')
    params=parse_qs(target.query)
    if not surface or not surface.get('vulnerable') or parameter!=surface['parameter'] or parameter not in params:
        return TerminalResult(False,["[WARNING] tested parameters do not appear to be injectable"],exit_code=1)
    if surface.get('cookie') and opts.get('--cookie')!=surface['cookie']:raise ValueError('sqlmap: authentication required')
    database=surface['database'];dbs=state.environment.get('databases',{})
    spec=dbs[database];tables=spec['tables'];visible=surface.get('tables',list(tables))
    fact(state,'sqlmap:injection:'+host.id,parameter=parameter,path=target.path)
    output=[f"Parameter: {parameter} (GET)","Type: boolean-based blind",f"back-end DBMS: {spec.get('engine','SQLite')}"]
    if '--dbs' in flags:return TerminalResult(True,output+['available databases [1]:','[*] '+database])
    chosen=opts.get('-D',database)
    if chosen!=database:raise ValueError('sqlmap: database access denied or database does not exist')
    if '--tables' in flags:return TerminalResult(True,output+[f'Database: {database}',*visible])
    table=opts.get('-T')
    if flags & {'--columns','--dump'}:
        if table not in visible or table not in tables:raise ValueError('sqlmap: table access denied or unknown table')
        schema=tables[table]
        if '--columns' in flags:return TerminalResult(True,output+[' | '.join(col) for col in schema['columns']])
        columns=opts.get('-C',','.join(c[0] for c in schema['columns'])).split(',')
        if any(c not in [x[0] for x in schema['columns']] for c in columns):raise ValueError('sqlmap: unknown column')
        script=database_script(spec)
        quote=lambda name:'"'+name.replace('"','""')+'"'
        statement='SELECT '+','.join(quote(c) for c in columns)+' FROM '+quote(table)
        if '--where' in opts:statement+=' WHERE '+opts['--where']
        names,rows=query(script,statement)
        folder=path(state,opts.get('--output-dir','/home/operator/.local/share/sqlmap/output'))
        if not folder.startswith('/home/operator/'):raise ValueError('sqlmap: output directory must be writable')
        destination=folder+'/'+host.ip+'/dump/'+database+'/'+table+'.csv'
        from .virtual_files import directories
        dirs=state.tool_data.setdefault('vfs_dirs',{}).setdefault('operator',[])
        parent=posixpath.dirname(destination)
        while parent not in directories(state):dirs.append(parent);parent=posixpath.dirname(parent)
        content=csv_text(names,rows);write(state,destination,content)
        fact(state,'sqlmap:dump:'+database+':'+table,path=destination,content=content)
        output += [f'Database: {database}',f'Table: {table}',f'[{len(rows)} entries]',*[' | '.join(str(v) for v in r) for r in rows[:15]],f"table dumped to CSV file '{destination}'"]
    return TerminalResult(True,output)


def database_script(spec):
    db=sqlite3.connect(':memory:')
    try:
        for name,table in spec['tables'].items():
            if not name.replace('_','').isalnum():raise ValueError('Invalid table name')
            columns=[]
            for col,kind in table['columns']:
                if not col.replace('_','').isalnum() or kind not in {'TEXT','INTEGER','REAL'}:raise ValueError('Invalid schema')
                columns.append('"'+col+'" '+kind)
            db.execute('CREATE TABLE "'+name+'" ('+','.join(columns)+')')
            db.executemany('INSERT INTO "'+name+'" VALUES ('+','.join('?' for _ in columns)+')',table['rows'])
        return '\n'.join(db.iterdump())+'\n'
    finally:db.close()


def mysql_cli(args,state,destination=None,password=None):
    """Exécute mysql ; avec une redirection, tout résultat va dans le fichier (une seule écriture)."""
    result=_mysql(args,state,destination,password)
    if destination and result.ok and not state.terminal_auth and result.output:
        write(state,destination,'\n'.join(result.output)+'\n')
        result.output=[]
    return result


def _mysql(args,state,destination=None,password=None):
    from .terminal import TerminalResult
    if args==['--help']:return TerminalResult(True,['mysql -h host -u user -p -D database -e "SELECT ..." [--batch]'])
    opts={};i=0
    while i<len(args):
        arg=args[i]
        if arg in {'-h','-u','-D','-e'}:
            i+=1
            if i>=len(args):raise ValueError('mysql: missing argument')
            opts[arg]=args[i]
        elif arg=='-p':opts['password_prompt']=True
        elif arg.startswith('--password='):opts['password']=arg.split('=',1)[1]
        elif arg.startswith('-p') and len(arg)>2:opts['password']=arg[2:]
        elif arg not in {'--batch','-B'}:raise ValueError('mysql: unsupported option '+arg)
        i+=1
    if not all(k in opts for k in ['-h','-u','-D','-e']):raise ValueError('usage: mysql -h host -u user -p -D database -e "SELECT ..."')
    host=state.find_host(opts['-h']);spec=state.environment.get('databases',{}).get(opts['-D'])
    if not host or not spec or spec.get('host')!=host.id or not state.reachable(host,3306):raise ValueError('ERROR 2003: Cannot connect to MySQL server')
    if opts.get('password_prompt') and password is None and 'password' not in opts:
        state.terminal_auth={'kind':'mysql','args':args,'destination':destination}
        return TerminalResult(True,['Enter password:'])
    secret=opts.get('password',password)
    grant=spec.get('accounts',{}).get(opts['-u'])
    if not grant or grant['password']!=secret:raise ValueError('ERROR 1045: Access denied for user')
    statement=opts['-e']
    import re
    clean=statement.strip().rstrip(';').strip()
    if clean.upper()=='SHOW TABLES':
        return TerminalResult(True,['Tables_in_'+opts['-D'],*grant.get('tables',[])])
    if clean.upper()=='SHOW DATABASES':return TerminalResult(True,['Database',opts['-D']])
    describe=re.fullmatch(r'(?:DESCRIBE|DESC|SHOW COLUMNS FROM)\s+([A-Za-z0-9_]+)',clean,re.I)
    if describe:
        table=describe[1]
        if table not in grant.get('tables',[]):raise ValueError('ERROR 1142: access denied for table')
        return TerminalResult(True,['Field\tType',*['\t'.join(c) for c in spec['tables'][table]['columns']]])
    columns,rows=query(database_script(spec),statement)
    # Vérifier les tables effectivement lues, y compris sous-requêtes et jointures.
    db=connect(database_script(spec))
    reads=[]
    def authorize(action,a,b,*_):
        if action==sqlite3.SQLITE_READ and a not in grant.get('tables',[]):return sqlite3.SQLITE_DENY
        if action==sqlite3.SQLITE_READ:reads.append(a)
        return sqlite3.SQLITE_OK if action in {sqlite3.SQLITE_SELECT,sqlite3.SQLITE_READ,sqlite3.SQLITE_FUNCTION,sqlite3.SQLITE_RECURSIVE} else sqlite3.SQLITE_DENY
    try:
        db.set_authorizer(authorize);db.execute(statement).fetchall()
    finally:db.close()
    output='\t'.join(columns)+'\n'+'\n'.join('\t'.join('' if v is None else str(v) for v in row) for row in rows)
    fact(state,'mysql:query:'+opts['-D'],columns=columns,rows=[list(r) for r in rows],tables=sorted(set(reads)))
    if destination:
        write(state,destination,output.rstrip('\n')+'\n')
        return TerminalResult(True,[])
    if '--batch' not in args and '-B' not in args:
        values=[[str(v) if v is not None else 'NULL' for v in row] for row in rows]
        widths=[max([len(c)]+[len(row[i]) for row in values]) for i,c in enumerate(columns)]
        border='+'+'+'.join('-'*(w+2) for w in widths)+'+'
        def render(row):return '| '+' | '.join(v.ljust(w) for v,w in zip(row,widths))+' |'
        return TerminalResult(True,[border,render(columns),border,*[render(row) for row in values],border,f'{len(rows)} rows in set'])
    return TerminalResult(True,[output.rstrip('\n')])


def finish_mysql(state,secret):
    from .terminal import TerminalResult
    pending=state.terminal_auth;state.terminal_auth={}
    try:return mysql_cli(pending['args'],state,pending.get('destination'),secret)
    except (ValueError,sqlite3.Error) as exc:return TerminalResult(False,[str(exc)])
