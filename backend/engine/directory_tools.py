"""Annuaire et collecte du domaine fictif, sans LDAP ni Kerberos extérieurs."""
import fnmatch
import hashlib
import hmac
import json
import re
import shlex
from urllib.parse import urlsplit
from .data_tools import fact,write
from .authentication import authenticate
from .ntlm import nt_hash


def rc4(key,data):
    s=list(range(256));j=0
    for i in range(256):j=(j+s[i]+key[i%len(key)])%256;s[i],s[j]=s[j],s[i]
    i=j=0;out=bytearray()
    for b in data:
        i=(i+1)%256;j=(j+s[i])%256;s[i],s[j]=s[j],s[i];out.append(b^s[(s[i]+s[j])%256])
    return bytes(out)


def ticket(password,user,domain,spn,seed):
    # RC4-HMAC, EncTicketPart key usage 2 (RFC 4757). Le corps reste fictif.
    key=hmac.new(bytes.fromhex(nt_hash(password)),(2).to_bytes(4,'little'),hashlib.md5).digest()
    def der(tag,data):
        length=len(data)
        encoded=bytes([length]) if length<128 else bytes([0x80+(length.bit_length()+7)//8])+length.to_bytes((length.bit_length()+7)//8,'big')
        return bytes([tag])+encoded+data
    integer=lambda n:der(2,bytes([n]))
    string=lambda value:der(27,value.encode())
    seq=lambda value:der(48,value)
    ctx=lambda n,value:der(160+n,value)
    principal=seq(ctx(0,integer(1))+ctx(1,seq(string('audit'))))
    session_key=seq(ctx(0,integer(23))+ctx(1,der(4,hashlib.sha256(seed.encode()).digest()[:16])))
    transited=seq(ctx(0,integer(0))+ctx(1,der(4,b'')))
    fields=ctx(0,der(3,b'\x00\x00\x00\x00\x00'))+ctx(1,session_key)+ctx(2,string(domain.upper()))+ctx(3,principal)+ctx(4,transited)+ctx(5,der(24,b'20261112100000Z'))+ctx(7,der(24,b'20261112110000Z'))
    body=hashlib.sha256(seed.encode()).digest()[:8]+der(99,seq(fields))
    checksum=hmac.new(key,body,hashlib.md5).digest();cipher=rc4(hmac.new(key,checksum,hashlib.md5).digest(),body)
    return f'$krb5tgs$23$*{user}${domain}${spn}*${checksum.hex()}${cipher.hex()}'


def matches(value,password):
    try:
        _,kind,etype,identity,domain,spn,checksum,cipher=value.split('$')
        if kind!='krb5tgs' or etype!='23':return False
        checksum=bytes.fromhex(checksum);cipher=bytes.fromhex(cipher)
        key=hmac.new(bytes.fromhex(nt_hash(password)),(2).to_bytes(4,'little'),hashlib.md5).digest()
        body=rc4(hmac.new(key,checksum,hashlib.md5).digest(),cipher)
        return hmac.compare_digest(checksum,hmac.new(key,body,hashlib.md5).digest())
    except (ValueError,TypeError):return False


def ldap_filter(text):
    """Filtres LDAP composés &, |, !, égalité et présence, sans eval."""
    if len(text)>4096:raise ValueError('Bad search filter')
    def read(i,depth=0):
        if depth>32 or i>=len(text) or text[i]!='(':raise ValueError('Bad search filter')
        i+=1
        if i<len(text) and text[i] in '&|!':
            op=text[i];i+=1;nodes=[]
            while i<len(text) and text[i]=='(':
                child,i=read(i,depth+1);nodes.append(child)
            if i>=len(text) or text[i]!=')' or not nodes or (op=='!' and len(nodes)!=1):raise ValueError('Bad search filter')
            def test(entry):
                values=[n(entry) for n in nodes]
                return all(values) if op=='&' else (any(values) if op=='|' else not values[0])
            return test,i+1
        end=text.find(')',i)
        if end<0 or '=' not in text[i:end]:raise ValueError('Bad search filter')
        attr,value=text[i:end].split('=',1)
        if not re.fullmatch(r'[\w.-]+',attr):raise ValueError('Bad search filter')
        pattern='';j=0
        while j<len(value):
            if value[j]=='\\' and j+2<len(value) and re.fullmatch(r'[0-9a-fA-F]{2}',value[j+1:j+3]):
                pattern+=re.escape(chr(int(value[j+1:j+3],16)));j+=3
            else:
                pattern+='.*' if value[j]=='*' else re.escape(value[j]);j+=1
        def test(entry):
            values=next((v for k,v in entry.items() if k.casefold()==attr.casefold()),[])
            values=values if isinstance(values,list) else [values]
            return bool(values) if value=='*' else any(re.fullmatch(pattern,str(v),flags=re.I) for v in values)
        return test,end+1
    parsed,end=read(0)
    if end!=len(text):raise ValueError('Bad search filter')
    return parsed


def finish(state,password):
    pending=state.terminal_auth;state.terminal_auth={}
    return ldap(state,pending['args'],password)


def ldap(state,args,password=None):
    from .terminal import TerminalResult
    options={};attrs=[];i=0
    while i<len(args):
        arg=args[i]
        if arg in {'-x','-LLL','-LL','-L'}:options[arg]=True
        elif arg=='-W':options[arg]=True
        elif arg in {'-H','-D','-w','-b','-s'} and i+1<len(args):i+=1;options[arg]=args[i]
        elif arg.startswith('-'):return TerminalResult(False,['ldapsearch: unrecognized option '+arg])
        else:attrs.append(arg)
        i+=1
    directory=state.environment.get('directory',{})
    try:url=urlsplit(options.get('-H','ldap://'+directory.get('host','')));port=url.port or (636 if url.scheme=='ldaps' else 389)
    except ValueError:return TerminalResult(False,['ldapsearch: invalid URI'])
    dc=state.find_host(url.hostname or '')
    if not dc or not directory or state.is_blocked(dc.id,port) or not any(s.port==port for s in dc.services):return TerminalResult(False,["ldap_sasl_bind(SIMPLE): Can't contact LDAP server (-1)"])
    dn=options.get('-D','');user=next((entry.get('sAMAccountName','') for entry in directory['entries'] if entry.get('dn','').casefold()==dn.casefold()),dn.split('@')[0].split('\\')[-1])
    if options.get('-W') and password is None:
        state.terminal_auth={'kind':'ldap','args':args};return TerminalResult(True,['Enter LDAP Password:'])
    base=options.get('-b','');scope=options.get('-s','sub')
    domain_users={str(e.get('sAMAccountName','')).casefold() for e in directory['entries'] if 'user' in e.get('objectClass',[])}
    correct_upn='@' not in dn or dn.rsplit('@',1)[1].casefold()==state.domain['name'].casefold()
    if not dn and base and not directory.get('anonymous'):return TerminalResult(False,['ldap_bind: Inappropriate authentication (48)'])
    if dn and (not correct_upn or user.casefold() not in domain_users or not authenticate(state,dc,user,password if password is not None else options.get('-w',''))):return TerminalResult(False,['ldap_bind: Invalid credentials (49)'])
    if scope not in {'base','one','sub'}:return TerminalResult(False,['ldapsearch: invalid scope'])
    if not base:
        fact(state,'ldap:rootdse')
        requested=[a.casefold() for a in attrs if not a.startswith('(')]
        values={'namingContexts':directory['base'],'defaultNamingContext':directory['base'],'supportedLDAPVersion':'3','dnsHostName':dc.hostname.lower()+'.'+state.domain['name']}
        return TerminalResult(True,['dn:',*[key+': '+value for key,value in values.items() if not requested or '*' in requested or key.casefold() in requested]])
    if not any(str(e['dn']).casefold()==base.casefold() for e in directory['entries']) and base.casefold()!=directory['base'].casefold():return TerminalResult(False,['ldap_search_ext: No such object (32)'])
    expression=next((a for a in attrs if a.startswith('(')),'(objectClass=*)');attributes=[a for a in attrs if a!=expression]
    try:predicate=ldap_filter(expression)
    except ValueError as exc:return TerminalResult(False,[str(exc)])
    lines=[];visible=[]
    for entry in directory['entries']:
        name=entry['dn'];suffix=name.casefold().endswith(','+base.casefold())
        in_scope=name.casefold()==base.casefold() if scope=='base' else (suffix and name.count(',')==base.count(',')+1 if scope=='one' else suffix or name.casefold()==base.casefold())
        if not in_scope or not predicate(entry):continue
        visible.append(name);lines+=['dn: '+name]
        for key,value in entry.items():
            if key=='dn' or (attributes and '*' not in attributes and key.casefold() not in [a.casefold() for a in attributes]):continue
            for v in value if isinstance(value,list) else [value]:lines.append(key+': '+str(v))
        lines.append('')
    fact(state,'ldap:search',entries=visible,base=base,filter=expression)
    return TerminalResult(True,lines)


def parse(line,state):
    from .terminal import TerminalResult
    if state.terminal_auth or state.terminal_foreground is not None:return None
    try:words=shlex.split(line,posix=not bool(state.terminal_host and state.hosts[state.terminal_host].os.startswith('Windows')))
    except ValueError:return None
    if not words:return None
    words=[w.strip('"') for w in words];tool=words[0].casefold().removesuffix('.exe');args=words[1:]
    if tool=='ldapsearch':
        if state.terminal_host and state.hosts[state.terminal_host].os.startswith('Windows'):return TerminalResult(False,['ldapsearch is not installed on this machine.'])
        return ldap(state,args)
    if tool in {'impacket-getuserspns','getuserspns.py'}:
        if state.terminal_host:return TerminalResult(False,['GetUserSPNs: run the client from the local Kali console.'])
        options={};identity=None;i=0
        while i<len(args):
            a=args[i]
            if a=='-request':options[a]=True
            elif a in {'-dc-ip','-outputfile','-request-user'} and i+1<len(args):i+=1;options[a]=args[i]
            elif not a.startswith('-') and identity is None:identity=a
            else:return TerminalResult(False,['GetUserSPNs: unrecognized argument '+a])
            i+=1
        directory=state.environment.get('directory',{});dc=state.find_host(options.get('-dc-ip',directory.get('host','')))
        if not identity or '/' not in identity or ':' not in identity:return TerminalResult(False,['GetUserSPNs: expected domain/username:password'])
        domain,account=identity.split('/',1);user,secret=account.split(':',1)
        domain_users={str(e.get('sAMAccountName','')).casefold() for e in directory.get('entries',[]) if 'user' in e.get('objectClass',[])}
        if not dc or user.casefold() not in domain_users or domain.casefold()!=state.domain.get('name','').casefold() or state.is_blocked(dc.id,389) or not authenticate(state,dc,user,secret):return TerminalResult(False,['LDAP SessionError: invalid credentials or server unavailable'])
        services=[s for s in directory.get('spns',[]) if state.users.get(s['user']) and state.users[s['user']].status=='ACTIVE' and (not options.get('-request-user') or s['user']==options['-request-user'])]
        lines=['ServicePrincipalName Name MemberOf',*[s['spn']+' '+s['user']+' '+s.get('group','') for s in services]]
        if options.get('-request'):
            if state.is_blocked(dc.id,88) or not any(s.port==88 for s in dc.services):return TerminalResult(False,['Kerberos SessionError: KDC unreachable'])
            if any(s.get('etype',23)!=23 for s in services):return TerminalResult(False,['KDC encryption type is outside the RC4 image coverage; no ticket was exported.'])
            hashes=[ticket(state.users[s['user']].password,s['user'],domain,s['spn'],state.scenario_name+s['spn']) for s in services if s.get('etype',23)==23]
            if options.get('-outputfile'):
                from .shell_tools import path
                try:write(state,path(state,options['-outputfile']),'\n'.join(hashes)+'\n')
                except ValueError as exc:return TerminalResult(False,[str(exc)])
            else:lines+=hashes
            fact(state,'kerberos:tgs',users=[s['user'] for s in services])
        else:fact(state,'kerberos:spns',users=[s['user'] for s in services])
        return TerminalResult(True,lines)
    if tool=='sharphound':
        host=state.hosts.get(state.terminal_host);directory=state.environment.get('directory',{})
        if not host or not host.os.startswith('Windows') or not directory:return TerminalResult(False,['SharpHound requires a Windows domain context.'])
        account=state.users.get(state.terminal_user)
        if not account or account.status!='ACTIVE' or state.terminal_user not in {e.get('sAMAccountName') for e in directory['entries']}:return TerminalResult(False,['SharpHound: domain authentication failed'])
        options={};i=0
        while i<len(args):
            a=args[i].casefold()
            if a in {'--collectionmethods','-c','--domain','-d','--outputdirectory','--zipfilename'} and i+1<len(args):i+=1;options[a]=args[i]
            else:return TerminalResult(False,['SharpHound: unrecognized option '+args[i]])
            i+=1
        methods=options.get('--collectionmethods',options.get('-c','Default')).split(',')
        if any(m.casefold() not in {'default','group','objectprops','acl','session','localadmin','trusts','container','all'} for m in methods):return TerminalResult(False,['SharpHound: invalid collection method'])
        domain=options.get('--domain',options.get('-d',state.domain['name']))
        if domain.casefold()!=state.domain['name'].casefold():return TerminalResult(False,['SharpHound: unable to resolve domain'])
        dc=state.find_host(directory['host'])
        if not dc or state.is_blocked(dc.id,389):return TerminalResult(False,['SharpHound: LDAP server unreachable'])
        from .virtual_shell import virtual_path
        output=virtual_path(options.get('--outputdirectory',state.terminal_cwd),state.terminal_cwd)
        filename=options.get('--zipfilename','collection.zip')
        if '/' in filename or '\\' in filename or not filename.lower().endswith('.zip'):return TerminalResult(False,['SharpHound: invalid zip filename'])
        nodes=[{'ObjectIdentifier':e['objectSid'],'Properties':{'name':e.get('sAMAccountName',e.get('cn','')).upper()+'@'+domain.upper(),'domain':domain.upper()},'DN':e['dn']} for e in directory['entries'] if e.get('objectSid')]
        methods_lower={m.casefold() for m in methods}
        include_groups=bool(methods_lower & {'group','default','all'})
        include_acl=bool(methods_lower & {'acl','default','all'})
        entries=directory['entries'];by_dn={e['dn'].casefold():e for e in entries}
        members={}
        for kind in ('users','groups','computers'):
            objects=[]
            for entry in entries:
                classes=[c.casefold() for c in entry.get('objectClass',[])]
                actual='groups' if 'group' in classes else ('computers' if 'computer' in classes else 'users')
                if actual!=kind or not entry.get('objectSid'):continue
                obj=dict(ObjectIdentifier=entry['objectSid'],Properties=dict(domain=domain.upper(),name=(entry.get('sAMAccountName') or entry.get('cn','')).upper()+'@'+domain.upper(),enabled=True),Aces=[],IsACLProtected=False)
                if kind=='groups':
                    obj['Members']=[dict(ObjectIdentifier=by_dn[dn.casefold()]['objectSid'],ObjectType='User') for dn in entry.get('member',[]) if include_groups and dn.casefold() in by_dn]
                if include_acl:
                    obj['Aces']=[dict(PrincipalSID=e['source'],PrincipalType='User',RightName=e['type'],IsInherited=False) for e in directory.get('edges',[]) if e['target']==entry['objectSid'] and e['type']!='AdminTo']
                objects.append(obj)
            members[kind+'.json']=json.dumps(dict(data=objects,meta=dict(count=len(objects),type=kind,version=6)))

        from .file_access import readable
        from .virtual_files import writable
        destination=output+'/'+filename
        if not writable(state,destination):return TerminalResult(False,['SharpHound: access denied to output directory'])
        host.files[destination]='VIRTUAL-ZIP\n'+json.dumps(members,ensure_ascii=False)
        fact(state,'sharphound:collection',host=host.id,path=destination,nodes=len(nodes),digest=hashlib.sha256(host.files[destination].encode()).hexdigest())
        return TerminalResult(True,['SharpHound collection completed', 'Output: '+options.get('--outputdirectory',state.terminal_cwd)+'\\'+filename])
    return None
