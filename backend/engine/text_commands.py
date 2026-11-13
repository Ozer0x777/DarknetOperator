"""Filtres textuels du terminal virtuel ; jamais de shell ni de fichier hôte."""
import fnmatch
import hashlib
import posixpath
import re
import shlex

TOOLS = {'grep', 'head', 'tail', 'wc', 'sort', 'uniq', 'cut', 'sha256sum'}


def parse(line, state, abilities):
    from .terminal import TerminalResult
    if state.terminal_host and state.hosts[state.terminal_host].os.startswith('Windows'): return None
    try:
        lexer = shlex.shlex(line, posix=True, punctuation_chars='|><')
        lexer.whitespace_split = True
        words = list(lexer)
    except ValueError: return None
    if not words or (words[0] not in TOOLS and not (words[0] == 'cat' and ('|' in words or any(arg in {'-n','-b','--number','--number-nonblank'} for arg in words[1:])))): return None
    if state.terminal_foreground is not None: return TerminalResult(False, ['Un processus occupe cette console. Ouvre une autre console.'])
    if not state.terminal_host:
        from .shell_tools import prepare
        prepare(state)
    files = state.hosts[state.terminal_host].files if state.terminal_host else state.terminal_files
    def resolve(value):
        if value == '~' or value.startswith('~/'): value = state.terminal_env.get('HOME', '/home/operator')+value[1:]
        return posixpath.normpath(value if value.startswith('/') else posixpath.join(state.terminal_cwd, value))
    def read(names, recursive=False):
        rows = []
        for name in names:
            pattern = resolve(name)
            paths = sorted(p for p in files if fnmatch.fnmatchcase(p, pattern) or (recursive and p.startswith(pattern.rstrip('/')+'/')))
            if not paths: raise ValueError(f'{name}: No such file or directory')
            for path in paths:
                from .file_access import readable
                if not readable(state,path): raise ValueError(f'{name}: Permission denied')
                if '\x00' in files[path]: raise ValueError(f'{name}: binary data is not supported by these text filters')
                rows.append((path, files[path]))
                from .evidence import read as record_read
                record_read(state,path)
        return rows
    destination = None; append = False
    if '>' in words or '>>' in words:
        at = next(i for i,w in enumerate(words) if w in {'>', '>>'})
        if at != len(words)-2: return TerminalResult(False, ['Redirection : une destination finale est requise.'], exit_code=2)
        destination = resolve(words[-1]); append = words[at] == '>>'; words = words[:at]
        from .virtual_files import writable, directories
        if posixpath.dirname(destination) not in directories(state): return TerminalResult(False, [destination+': No such file or directory'])
        if not writable(state, destination): return TerminalResult(False, [destination+': Permission denied'])
    groups = [[]]
    for word in words:
        if word == '|': groups.append([])
        else: groups[-1].append(word)
    stream = None; code = 0
    try:
        for group in groups:
            if not group or group[0] not in TOOLS | {'cat'}: raise ValueError('Pipe : filtre non pris en charge.')
            tool, args = group[0], group[1:]
            if args == ['--help']:
                stream = {'grep':'grep [-invcrEF] [-e motif] [--] motif fichier...','cut':'cut -d séparateur -f champs fichier...','sha256sum':'sha256sum fichier...', 'wc':'wc [-lwc] fichier...'}.get(tool, tool+' [-n nombre] fichier...')+'\n'
                continue
            recursive = False; options = set(); operands = []; pattern = None; count = 10; delim = '\t'; fields = None; i = 0
            while i < len(args):
                arg = args[i]
                if tool == 'cat' and arg in {'--number','--number-nonblank'}: arg = '-n' if arg == '--number' else '-b'
                if arg == '--': operands += args[i+1:]; break
                if tool == 'grep' and arg == '-e':
                    i += 1
                    if i >= len(args): raise ValueError('grep: missing pattern')
                    pattern = args[i]
                elif tool in {'head','tail'} and (arg == '-n' or arg.startswith('-n')):
                    value = arg[2:]
                    if not value:
                        i += 1
                        if i >= len(args): raise ValueError(tool+': missing line count')
                        value = args[i]
                    if not value.isdigit(): raise ValueError(tool+': invalid line count')
                    count = int(value)
                elif tool == 'cut' and arg[:2] in {'-d','-f'}:
                    opt = arg[1]; value = arg[2:]
                    if not value:
                        i += 1
                        if i >= len(args): raise ValueError('cut: option requires an argument')
                        value = args[i]
                    if opt == 'd':
                        if len(value) != 1: raise ValueError('cut: delimiter must be a single character')
                        delim = value
                    else: fields = value
                elif arg.startswith('-') and arg != '-':
                    allowed = {'grep':'invcrREF', 'wc':'lwc', 'sort':'run', 'uniq':'c', 'cat':'nb'}.get(tool, '')
                    if not arg[1:] or any(c not in allowed for c in arg[1:]): raise ValueError(tool+': unsupported option '+arg)
                    options.update(arg[1:]); recursive = bool(options & {'r','R'}) if tool == 'grep' else False
                else: operands.append(arg)
                i += 1
            if tool == 'grep' and pattern is None:
                if not operands: raise ValueError('grep: missing pattern')
                pattern = operands.pop(0)
            sources = read(operands, recursive) if operands else ([('', stream)] if stream is not None else [])
            if not sources: raise ValueError(tool+': un fichier ou un pipe est requis')
            data = ''.join(value for _,value in sources)
            lines = data.splitlines()
            code = 0
            if tool == 'cat':
                if options & {'n','b'}:
                    numbered=[];number=0
                    for value in lines:
                        if 'b' not in options or value.strip():
                            number+=1;numbered.append(f'{number:6}\t'+value)
                        else:numbered.append(value)
                    stream='\n'.join(numbered)+('\n' if data.endswith('\n') else '')
                else:stream = data
            elif tool == 'grep':
                # BRE de base ou ERE : sous-ensemble explicite, sans expressions Python avancées.
                if len(pattern) > 256 or '(?' in pattern or re.search(r'[+*?}]\s*[+*?{]|\)[+*?{]', pattern): raise ValueError('grep: expression non prise en charge')
                expression = pattern if 'E' in options else re.sub(r'(?<!\\)([+?|(){}])', r'\\\1', pattern)
                if 'F' not in options: matcher = re.compile(expression, re.I if 'i' in options else 0)
                output = []; matches = 0
                for name,content in sources:
                    selected = []
                    for number, value in enumerate(content.splitlines(),1):
                        hit = (pattern.casefold() in value.casefold() if 'i' in options else pattern in value) if 'F' in options else bool(matcher.search(value))
                        if hit != ('v' in options): selected.append((number,value))
                    matches += len(selected)
                    prefix = name+':' if len(sources)>1 or recursive else ''
                    if 'c' in options: output.append(prefix+str(len(selected)))
                    else: output.extend(prefix+(str(n)+':' if 'n' in options else '')+v for n,v in selected)
                stream = '\n'.join(output)+('\n' if output else ''); code = 0 if matches else 1
            elif tool in {'head','tail'}:
                if len(sources)>1: raise ValueError(tool+': plusieurs fichiers ne sont pas encore pris en charge')
                chosen = lines[:count] if tool == 'head' else (lines[-count:] if count else [])
                stream = '\n'.join(chosen)+('\n' if chosen else '')
            elif tool == 'cut':
                if not fields or not re.fullmatch(r'\d+(?:-\d+)?(?:,\d+(?:-\d+)?)*',fields): raise ValueError('cut: use positive fields such as 1,3 or 2-4')
                selected = set()
                for span in fields.split(','):
                    bounds = [int(v) for v in span.split('-')]; lo,hi = bounds[0],bounds[-1]
                    if lo < 1 or hi < lo or hi>4096: raise ValueError('cut: invalid field range')
                    selected.update(range(lo-1,hi))
                stream = '\n'.join(delim.join(v for j,v in enumerate(row.split(delim)) if j in selected) if delim in row else row for row in lines)+ ('\n' if lines else '')
            elif tool == 'sort':
                if 'n' in options:
                    def numeric(value):
                        m = re.match(r'\s*([+-]?\d+(?:\.\d+)?)',value)
                        return float(m[1]) if m else 0
                    lines.sort(key=numeric, reverse='r' in options)
                else: lines.sort(reverse='r' in options)
                if 'u' in options: lines = list(dict.fromkeys(lines))
                stream = '\n'.join(lines)+ ('\n' if lines else '')
            elif tool == 'uniq':
                output = []; previous = None; total = 0
                for value in lines+[None]:
                    if value != previous and total:
                        output.append((f'{total:7} ' if 'c' in options else '')+previous); total = 0
                    previous = value; total += 1
                stream = '\n'.join(output)+ ('\n' if output else '')
            elif tool == 'wc':
                flags = [c for c in 'lwc' if c in options] or list('lwc')
                output = []; totals = [0,0,0]
                for name,value in sources:
                    counts = [value.count('\n'),len(value.split()),len(value.encode())]
                    totals = [a+b for a,b in zip(totals,counts)]
                    output.append(' '.join(str(counts['lwc'.index(c)]) for c in flags)+(' '+name if name else ''))
                if len(sources)>1: output.append(' '.join(str(totals['lwc'.index(c)]) for c in flags)+' total')
                stream = '\n'.join(output)+'\n'
            elif tool == 'sha256sum':
                stream = ''.join(hashlib.sha256(value.encode()).hexdigest()+'  '+(name or '-')+'\n' for name,value in sources)
        if destination:
            from .virtual_files import audit
            before = files.get(destination)
            files[destination] = (before or '' if append else '')+stream
            audit(state, 'append' if append else 'write', destination, before, files[destination])
            return TerminalResult(code == 0, [], exit_code=code)
        return TerminalResult(code == 0, [stream] if stream else [], exit_code=code)
    except (ValueError, re.error) as exc:
        return TerminalResult(False, [str(exc)], exit_code=2)
