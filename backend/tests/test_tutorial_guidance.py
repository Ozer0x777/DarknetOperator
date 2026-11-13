"""Consignes complètes dans Chordly, DNS simulé de Ravelle et erreurs Impacket explicites."""
from pathlib import Path
from api.main import ABILITIES
from engine import contracts, terminal
from engine.contracts import load_contract

POST = 'curl -k -H "Authorization: $API_KEY" -H "Content-Type: application/json" -d @/home/operator/gophish/campaign.json https://127.0.0.1:3333/api/campaigns/'


def campaign():
    return contracts.start_contract(contracts.load_all_contracts()['intro_campaign'], 'NightShift')


def ravelle():
    return contracts.start_contract(load_contract(Path(__file__).parents[1] / 'contracts/current/tuto_p0.json'), 'NightShift')


def test_gophish_commands_are_given_in_chat_not_only_in_readme():
    s = campaign()
    brief = s.messages[0].text
    for command in ['gophish --config /opt/gophish/config.json', 'API_KEY=$(cat ~/gophish/api-key.txt)', POST]:
        assert '`' + command + '`' in brief
    assert 'README' not in brief


def test_detailed_help_repeats_every_gophish_command():
    s = campaign()
    for _ in range(3): contracts.player_message(s, 'chordly', 'aide')
    assert s.messages[-1].text.startswith('Rappel détaillé')
    assert POST in s.messages[-1].text and 'Ctrl+Alt+T' in s.messages[-1].text


def test_impacket_explains_an_unidentified_target():
    s = campaign()
    result = terminal.parse('impacket-psexec -hashes :00 it.presta@10.20.0.10', s, ABILITIES)
    assert not result.ok and 'non identifiée' in result.output[-1] and 'nmap' in result.output[-1]


def test_ravelle_site_has_public_ip_and_dns():
    s = ravelle()
    host = s.find_host('www.ravelle-associes.fr')
    assert host and not host.ip.startswith(('10.', '192.168.', '172.'))
    assert terminal.parse('host www.ravelle-associes.fr', s, ABILITIES).output == [f'www.ravelle-associes.fr has address {host.ip}']
    reverse = terminal.parse(f'host {host.ip}', s, ABILITIES)
    assert reverse.ok and reverse.output[0].endswith('domain name pointer www.ravelle-associes.fr.')
    missing = terminal.parse('host www.inconnu.fr', s, ABILITIES)
    assert not missing.ok and 'NXDOMAIN' in missing.output[0]
    page = terminal.parse('curl http://www.ravelle-associes.fr/mentions.txt', s, ABILITIES)
    assert page.ok and 'Ravelle' in page.output[0]


def test_ravelle_brief_explains_site_dns_and_delivery_phrase():
    brief = ravelle().messages[0].text
    assert '`host www.ravelle-associes.fr`' in brief and 'DNS' in brief and 'publique' in brief
    assert '`curl http://www.ravelle-associes.fr/`' in brief
    assert 'Quand tu as fini' in brief and '`livraison RAV-26-001`' in brief
