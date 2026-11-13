"""Protections observables, preuves contradictoires et limites du débriefing."""
from pathlib import Path
import json
import pytest
from engine import ability_engine, console_sessions, social, terminal
from engine.career import Career
from engine.game_loop import GameLoop, QueuedAction, load_all_abilities
from engine.models import ActionContext, Credential
from engine.persistence import state_from_dict, state_to_dict
from engine.scenario_loader import load_scenario, ScenarioValidationError
from engine.security import incident_summary

ROOT = Path(__file__).parents[1]
ABILITIES = load_all_abilities()


def scenario():
    return load_scenario(ROOT/'scenarios/varenne.json', known_ability_ids=set(ABILITIES))


def test_network_policy_depends_on_console_origin_and_survives_save():
    state = scenario()
    assert state.is_blocked('poste-compta', 445)
    with console_sessions.using(state, 'inside'):
        console_sessions.enter(state, state.hosts['poste-accueil'], 'p.varenne', 'SYSTEM')
        console_sessions.switch_shell(state, 'powershell')
        result = terminal.parse('Test-NetConnection VAR-COMPTA -Port 445', state, ABILITIES)
        assert result.ok and 'TcpTestSucceeded : True' in result.output
    assert state.is_blocked('poste-compta', 445)
    restored = state_from_dict(state_to_dict(state))
    with console_sessions.using(restored, 'inside'):
        assert not restored.is_blocked('poste-compta', 445)
    # Un filtrage global prime sur l'exception liée à l'origine.
    restored.environment['network_rules'].insert(0, {'target': 'poste-compta', 'port': 445, 'source': '*', 'action': 'deny'})
    with console_sessions.using(restored, 'inside'):
        assert restored.is_blocked('poste-compta', 445)


def test_edr_blocks_repeatably_without_effect_and_audits_other_hosts():
    state = scenario()
    state.discovered.update(state.hosts)
    host = state.hosts['poste-compta']
    user = host.admin_users[0]
    cred = Credential('PLAINTEXT', user, state.users[user].password, host.id)
    with console_sessions.using(state, 'inside'):
        console_sessions.enter(state, state.hosts['poste-accueil'], 'p.varenne', 'SYSTEM')
        for _ in range(3):
            result = ability_engine.resolve(ABILITIES['red.psexec_lateral'], state, ActionContext('red', host, state.tick, credential=cred))
            assert not result.success and result.reason == 'blocked_by_edr'
            assert host.compromised_by is None
    host = state.hosts['srv-fichiers']
    result = ability_engine.resolve(ABILITIES['red.psexec_lateral'], state, ActionContext('red', host, state.tick, credential=cred))
    assert result.success and host.compromised_by == 'red'
    assert any(log.event_id == 'EDR-POLICY' and log.data['disposition'] == 'audit' for log in state.logs)


def test_documents_allow_discarding_stale_address_and_inspecting_protection():
    state = scenario()
    console_sessions.enter(state, state.hosts['poste-accueil'], 'p.varenne', 'SYSTEM')
    console_sessions.switch_shell(state, 'powershell')
    old = terminal.parse('Get-Content C:\\Users\\Public\\Documents\\Support\\inventaire-2024.txt', state, ABILITIES)
    new = terminal.parse('Get-Content C:\\Users\\Public\\Documents\\Support\\migration-2026.txt', state, ABILITIES)
    assert old.ok and '.99' in '\n'.join(old.output)
    assert new.ok and state.hosts['srv-fichiers'].ip in '\n'.join(new.output)
    assert 'LabEndpoint' in '\n'.join(terminal.parse('Get-Service -Name LabEndpoint', state, ABILITIES).output)
    assert 'maintenance supervisée' in '\n'.join(terminal.parse('Get-Content C:\\ProgramData\\LabEndpoint\\policy.txt', state, ABILITIES).output)


def test_invalid_network_policy_rejected_before_game(tmp_path):
    data = json.loads((ROOT/'scenarios/varenne.json').read_text())
    data['environment']['network_rules'][0]['target'] = 'missing'
    path = tmp_path/'bad.json'; path.write_text(json.dumps(data))
    with pytest.raises(ScenarioValidationError, match='Règle réseau'): load_scenario(path)


def test_failed_critical_action_on_isolated_target_keeps_mission_running():
    state = scenario()
    state.discovered.update(state.hosts)
    state.hosts['srv-fichiers'].status = 'ISOLATED'
    state.loot.append(Credential('KRBTGT_HASH', 'krbtgt', 'a'*32, 'srv-fichiers'))
    loop = GameLoop(state, ABILITIES)
    loop.submit(QueuedAction('red', 'red.golden_ticket', 'srv-fichiers', 'krbtgt', 'KRBTGT_HASH'))
    loop.tick()
    assert state.status == 'RUNNING' and state.winner is None
    assert not state.history[0].success


def test_aftermath_reports_observed_effects_without_claiming_victim_payment():
    state = scenario()
    state.hosts['srv-fichiers'].encrypted = True
    state.hosts['srv-fichiers'].backups = False
    state.exfiltrated['srv-fichiers:/srv/archive.zip'] = 'archive fictive'
    report = incident_summary(state)
    assert report['encrypted_hosts'] == ['VAR-DC-FS01']
    assert len(report['exfiltrated_files']) == 1
    assert any('sauvegardes externes' in note for note in report['notes'])
    assert any('paiement' in note for note in report['notes'])
    assert 'victim_paid' not in report


def test_forum_dispute_and_contextual_reply_persist(tmp_path):
    career = Career(tmp_path/'career.json')
    social.prepare(career)
    assert 'seller-dispute' in {t['id'] for t in social.view(career)['threads']}
    assert 'incident-aftermath' not in {t['id'] for t in social.view(career)['threads']}
    social.queue_chat(career, 'chordly', 'miette', 'Operator', 'Une rançon signifie un paiement ?')
    career.save(); career = Career(career.path)
    social.advance(career, 5)
    assert any('ne prouve pas un paiement' in m['text'] for m in career.data['conversations'].values())
    count = len(career.data['forum_posts']['seller-dispute'])
    social.advance(career, 40)
    assert len(career.data['forum_posts']['seller-dispute']) == count + 1
    social.advance(career, 40)
    assert len(career.data['forum_posts']['seller-dispute']) == count + 1


def test_filtered_scan_does_not_publish_unobserved_server_version():
    from engine.terminal_native import output
    from api.serializers import serialize_state
    state = scenario()
    state.discovered.add('poste-compta'); state.scanned.add('poste-compta')
    host = state.hosts['poste-compta']
    result = output('red.recon_scan', state, ActionContext('red', host, state.tick, params={'scan_scope':'host', 'scan_ports':[445], 'scan_versions':True}))
    assert 'filtered' in result and 'Microsoft Windows SMB' not in result
    public = next(h for h in serialize_state(state)['hosts'] if h['id'] == host.id)
    assert public['services'][0]['state'] == 'filtered'
    assert public['services'][0]['version'] == ''
    assert public['edr_agent'] is None
