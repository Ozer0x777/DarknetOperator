"""Utilitaires de tests : commandes véritables du parseur, monde strictement virtuel."""
from engine import terminal, console_sessions
from engine.game_loop import load_all_abilities
import json
import shlex

ABILITIES = load_all_abilities()


def command(state, loop, line, console='main'):
    with console_sessions.using(state, console):
        result = terminal.parse(line, state, ABILITIES)
        assert result.ok, result.output
        if result.action: loop.submit(result.action)
    while loop._queue and state.status == 'RUNNING': loop.tick()
    return result


def phish(state, loop):
    if not state.tool_services.get('gophish', {}).get('running'):
        command(state, loop, 'gophish --config /opt/gophish/config.json', 'mail')
    command(state, loop, 'API_KEY=$(cat ~/gophish/api-key.txt)', 'api')
    command(state, loop, 'curl -k -H "Authorization: $API_KEY" -d @/home/operator/gophish/campaign.json https://127.0.0.1:3333/api/campaigns/', 'api')


def upload(state, loop, host, credential, tool='mimikatz'):
    identity = credential.username + '%' + credential.value
    args = ['smbclient', '//' + host.ip + '/C$', '-U', identity]
    if credential.type == 'NTLM_HASH': args.append('--pw-nt-hash')
    args += ['-c', f'put /home/operator/tools/{tool}.exe Tools/{tool}.exe']
    command(state, loop, shlex.join(args), 'deploy')
