"""Robustesse du terminal : une ligne mal formée donne un message, jamais une exception.

Le test rejoue des variantes abîmées des commandes citées dans les contrats (jetons retirés,
guillemets ouverts, options tronquées, adresses impossibles) sur le poste Kali, dans une session
distante et sous PowerShell. Côté joueur, une exception ici serait une erreur 500 de l'API."""
import json
import random
import re

from engine import completion, console_sessions, contracts, shell_tools, terminal
from engine.game_loop import GameLoop, load_all_abilities
from engine.powershell import ALIASES

ABILITIES = load_all_abilities()
LINES = 8000
HEADS = sorted(set(shell_tools.BINARIES) | set(ALIASES) | {'cat', 'ls', 'pwd', 'cd', 'echo', 'export', 'help', 'hosts', 'loot', 'whoami', 'hostname', 'exit', 'type', 'dir',
    'mimikatz', 'hashcat', 'impacket-secretsdump', 'impacket-ticketer', 'Get-Content', 'Get-Service', 'Get-ChildItem', 'Set-Location', 'less'})
JUNK = ['', ' ', '"', "'", '`', '$', '$(', ')', '|', '&&', ';', '>', '>>', '<', '*', '~', '..', '/', '\\', '-', '--', '=', '@', '%', '#', '{', '[', '-1', '0', '99999999999999999999',
        '::', ':', '\t', '\x00', 'é', 'A' * 300, '../../etc/passwd', 'C:\\', '//', '$HOME', '$?', '${X', '$(cat ~/x)', '-U', '-U %', '-p', '-p 70000', '-hashes', '-hashes :',
        'user@', '@host', 'a:b@', '/24', '/33', '10.0.0.999', '1.2.3', '::1', 'http://', 'http://[', '-d', '-d @', '-H', '-X', '-c', '-c "', '-o', '-m x', '-L', '-N', '-k']


def _mutate(rng, line, words):
    tokens = line.split(' ')
    for _ in range(rng.choice((0, 1, 1, 2, 3))):
        op, pos = rng.randrange(8), rng.randrange(len(tokens) + 1)
        last = min(pos, len(tokens) - 1)
        if op == 0 and tokens: tokens.pop(last)
        elif op == 1: tokens.insert(pos, rng.choice(JUNK))
        elif op == 2: tokens.insert(pos, rng.choice(words))
        elif op == 3 and tokens: tokens[last] = rng.choice(JUNK)
        elif op == 4 and tokens: tokens[last] = tokens[last][:rng.randrange(len(tokens[last]) + 1)]
        elif op == 5: tokens.insert(0, rng.choice(HEADS))
        elif op == 6 and tokens: tokens[0] = rng.choice(HEADS)
        elif op == 7: rng.shuffle(tokens)
    return ' '.join(tokens)


def _line(rng, seeds, words):
    kind = rng.randrange(10)
    if kind < 5 and seeds: return _mutate(rng, rng.choice(seeds), words)
    if kind < 8: return ' '.join([rng.choice(HEADS)] + [rng.choice(JUNK + words) for _ in range(rng.randrange(5))])
    return ''.join(rng.choice(JUNK + HEADS + words) for _ in range(rng.randrange(1, 6)))


def _session(rng, state):
    """Une fois sur quatre, la console se trouve dans une session distante, parfois sous PowerShell."""
    roll, hosts = rng.randrange(8), list(state.hosts.values())
    if roll > 1 or not hosts: return
    host = rng.choice(hosts)
    user = next(iter(host.admin_users), None) or next(iter(state.users), 'user')
    with console_sessions.using(state, 'main'):
        host.status, host.compromised_by, host.access_level = 'COMPROMISED', 'red', 'SYSTEM'
        console_sessions.enter(state, host, user, rng.choice(('USER', 'SYSTEM')))
        if roll == 1 and host.os.startswith('Windows'): console_sessions.switch_shell(state, 'powershell')


def test_malformed_lines_never_raise():
    rng, every, done = random.Random(20261114), contracts.load_all_contracts(), 0
    while done < LINES:
        cid = rng.choice(sorted(every))
        state = contracts.start_contract(every[cid], 'Operator', rng_seed=rng.randrange(10**6), known_ability_ids=set(ABILITIES))
        shell_tools.prepare(state)
        loop = GameLoop(state, ABILITIES)
        text = json.dumps(every[cid], ensure_ascii=False)
        seeds = [m.replace('\\"', '"').replace('\\\\', '\\') for m in re.findall(r'`([^`]{2,200})`', text)]
        words = sorted({w for h in state.hosts.values() for w in (h.ip, h.hostname, f'//{h.ip}/C$', f'{h.ip}/24', *list(h.files)[:6])} | set(list(state.users)[:6]) | set(list(state.terminal_files)[:10]))
        _session(rng, state)
        for _ in range(rng.randrange(20, 60)):
            done += 1
            line, console = _line(rng, seeds, words), rng.choice(('main', 'main', 'c2'))
            try:
                with console_sessions.using(state, console):
                    result = terminal.parse(line, state, ABILITIES)
                    if result.action:
                        try: loop.submit(result.action)
                        except RuntimeError: pass  # file d'actions pleine : refus attendu
                assert isinstance(result.output, list) and all(isinstance(row, str) for row in result.output)
                for _ in range(rng.randrange(4)):
                    if state.status == 'RUNNING': loop.tick()
                with console_sessions.using(state, console):
                    completion.complete(state, line, rng.randrange(len(line) + 1))
                console_sessions.public_contexts(state)
            except Exception as exc:
                raise AssertionError(f'{cid} : la ligne {line!r} a levé {type(exc).__name__}: {exc}') from exc
            if state.status != 'RUNNING': break


def test_spn_request_with_a_malformed_identity_is_refused():
    """Trouvé par le test ci-dessus : « http://[ » contient « / » et « : », mais pas dans le bon ordre."""
    state = contracts.start_contract(contracts.load_all_contracts()['act2_service'], 'Operator', known_ability_ids=set(ABILITIES))
    result = terminal.parse('impacket-GetUserSPNs http://[', state, ABILITIES)
    assert not result.ok and 'expected domain/username:password' in result.output[0]


def test_hosts_listing_sorts_ipv6_addresses():
    state = contracts.start_contract(contracts.load_all_contracts()['tuto_p0'], 'Operator', known_ability_ids=set(ABILITIES))
    state.discovered |= set(state.hosts)
    next(iter(state.hosts.values())).ip = 'fd00::10'
    assert terminal.parse('hosts', state, ABILITIES).ok
