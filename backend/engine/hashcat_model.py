"""Mode NTLM/dictionnaire et potfile du laboratoire ; pas de processus Hashcat."""
from __future__ import annotations
import re
from .ntlm import nt_hash
from .shell_tools import path
from .mission_data import note_cracked

SAMPLE_WORDS = ['Password123!', 'Maintenance2026!', 'Morel2026!', 'Dumas2026!', 'Varenne2026!', 'Belin2026!', 'Valmont2026!', 'Bienvenue2026!']


PREMIUM_WORDS = SAMPLE_WORDS + ["Atelier2026!", "Planning2026!", "Boreal2026!", "Printemps2026!", "Automne2026!", "Bienvenue2025!"]


def prepare(state):
    state.terminal_files.setdefault('/usr/share/wordlists/rockyou.txt', '\n'.join(SAMPLE_WORDS)+'\n')
    if 'wordlist' in state.inventory:
        state.terminal_files.setdefault('/home/operator/wordlist.txt', '\n'.join(PREMIUM_WORDS)+'\n')


def parse(args, state):
    from .terminal import TerminalResult
    from .game_loop import QueuedAction
    prepare(state)
    mode,attack,show,operands = None,'0',False,[]
    i=0
    while i<len(args):
        value=args[i]
        if value in {'-m','-a'}:
            if i+1>=len(args):return TerminalResult(False,[f'hashcat: {value} requires an argument'])
            if value=='-m':mode=args[i+1]
            else:attack=args[i+1]
            i+=2;continue
        if value=='--show':show=True
        elif value.startswith('-'):return TerminalResult(False,[f'hashcat: option {value} non implémentée dans cette version'])
        else:operands.append(value)
        i+=1
    if mode=='13100':
        return parse_tgs(operands,show,state,attack)
    if mode!='1000' or attack!='0' or len(operands)!=(1 if show else 2):
        return TerminalResult(False,['usage: hashcat -m 1000 [-a 0] fichier_hash liste_de_mots | hashcat -m 1000 --show fichier_hash'])
    filename=path(state,operands[0])
    if filename not in state.terminal_files:return TerminalResult(False,[f'{operands[0]}: No such file or directory'])
    hashes=[line.strip().lower() for line in state.terminal_files[filename].splitlines() if line.strip()]
    if not hashes or any(not re.fullmatch(r'[a-f0-9]{32}',value) for value in hashes):return TerminalResult(False,['hashcat: No hashes loaded.'])
    pot=state.tool_data.setdefault('hashcat',{}).setdefault('pot',{})
    if show:
        note_cracked(state,[value for value in hashes if value in pot])
        return TerminalResult(True,[value+':'+pot[value] for value in hashes if value in pot])
    wordlist=path(state,operands[1])
    if wordlist not in state.terminal_files:return TerminalResult(False,[f'{operands[1]}: No such file or directory'])
    words=state.terminal_files[wordlist].splitlines()
    if len(words)>4096:return TerminalResult(False,['hashcat: ce laboratoire couvre des dictionnaires de 4096 entrées au maximum.'])
    candidates={nt_hash(word):word for word in words}
    matches={value:candidates[value] for value in hashes if value in candidates}
    matches.update({value:pot[value] for value in hashes if value in pot})
    credential=next((c for c in state.loot if c.type=='NTLM_HASH' and c.value.lower() in hashes),None)
    if 'red.crack_hash' not in state.available_abilities.get('red',[]):return TerminalResult(False,['hashcat: outil indisponible pour cette mission.'])
    target=state.hosts.get(credential.source_host) if credential else next((h for h in state.hosts.values() if h.id in state.discovered),None)
    if target is None:
        pot.update(matches)
        note_cracked(state,matches)
        complete=all(value in matches for value in hashes)
        return TerminalResult(complete,['Status...........: '+('Cracked' if complete else 'Exhausted'),*[value+':'+password for value,password in matches.items()]],exit_code=0 if complete else 1)
    return TerminalResult(True,['hashcat: traitement en attente…'],QueuedAction('red','red.crack_hash',target.id,
        credential.username if credential else None, 'NTLM_HASH' if credential else None, console_id=state.active_terminal_id,
        params={'hashes':hashes,'crack_matches':matches,'wordlist':wordlist}))


def parse_tgs(operands,show,state,attack):
    from .terminal import TerminalResult
    from .directory_tools import matches
    from .data_tools import fact
    if attack != '0' or len(operands) != (1 if show else 2):return TerminalResult(False,['usage: hashcat -m 13100 [-a 0] tickets wordlist | hashcat -m 13100 --show tickets'])
    if 'red.crack_hash' not in state.available_abilities.get('red',[]):return TerminalResult(False,['hashcat: outil indisponible pour cette mission.'])
    filename=path(state,operands[0])
    if filename not in state.terminal_files:return TerminalResult(False,['hashcat: No such file or directory'])
    hashes=[h.strip() for h in state.terminal_files[filename].splitlines() if h.strip()]
    if not hashes or any(not h.startswith('$krb5tgs$23$') for h in hashes):return TerminalResult(False,['hashcat: No hashes loaded.'])
    pot=state.tool_data.setdefault('hashcat',{}).setdefault('pot',{})
    if show:
        note_cracked(state,[h for h in hashes if h in pot])
        return TerminalResult(True,[h+':'+pot[h] for h in hashes if h in pot])
    words=state.terminal_files.get(path(state,operands[1]))
    if words is None:return TerminalResult(False,['hashcat: No such file or directory'])
    if len(words.splitlines())>4096:return TerminalResult(False,['hashcat: ce laboratoire couvre des dictionnaires de 4096 entrées au maximum.'])
    for value in hashes:
        for candidate in words.splitlines():
            if matches(value,candidate):pot[value]=candidate;break
    note_cracked(state,[value for value in hashes if value in pot])
    cracked=all(value in pot for value in hashes)
    if cracked:fact(state,'hashcat:tgs',file=filename)
    return TerminalResult(cracked,['Status...........: '+('Cracked' if cracked else 'Exhausted'),*[h+':'+pot[h] for h in hashes if h in pot]],exit_code=0 if cracked else 1)
