"""Corrections de revue du moteur utilisé par le jeu Godot."""
import api.main as api
from engine import contracts
from engine.game_loop import GameLoop, load_all_abilities
from engine.models import Credential
from engine.win_conditions import condition_error, objective_met
from support import command, phish

ABILITIES = load_all_abilities()


def tutorial():
    state = contracts.start_contract(contracts.load_all_contracts()['tuto_p0'], 'Operator', known_ability_ids=set(ABILITIES))
    return state, GameLoop(state, ABILITIES)


def test_malformed_objectives_are_rejected_at_load_time():
    assert 'file' in condition_error({'type': 'file_exfiltrated', 'host': 'h'}, {'h'}, set())
    assert 'typo' in condition_error({'type': 'http_read', 'host': 'h', 'path': '/', 'typo': 1}, {'h'}, set())
    assert condition_error({'type': 'file_exfiltrated', 'host': 'h', 'file': '/a'}, {'h'}, set()) is None


def test_hash_recovered_is_false_for_an_account_without_password():
    state, _ = tutorial()
    state.users['m.leroux'].password = None
    assert objective_met(state, {'type': 'hash_recovered', 'username': 'm.leroux'}) is False
    assert objective_met(state, {'type': 'hash_recovered', 'username': 'absent'}) is False


def test_observation_check_reports_timeout_when_time_runs_out():
    state = contracts.start_contract(contracts.load_all_contracts()['intro_terminal'], 'Operator')
    state.tick = state.max_ticks
    api._resolve_observations(state)
    assert state.status == 'ENDED' and state.winner == 'BLUE' and state.end_reason == 'timeout'


def test_idle_ticks_do_not_rewrite_the_save():
    state, loop = tutorial()
    session = api.GameSession(id='g', loop=loop)
    writes = []
    original = api.Career.checkpoint
    api.Career.checkpoint = lambda self, s: writes.append(s.tick)
    try:
        api._checkpoint_if_changed(session)
        for _ in range(5):
            state.tick += 1
            api._checkpoint_if_changed(session)
        assert len(writes) == 1
        state.messages.append(state.messages[0])
        api._checkpoint_if_changed(session)
        assert len(writes) == 2
        session.saved_at -= api.CHECKPOINT_IDLE_SECONDS
        api._checkpoint_if_changed(session)
        assert len(writes) == 3
    finally:
        api.Career.checkpoint = original


def test_pass_the_hash_logon_is_flagged_but_password_logon_is_not():
    state, loop = tutorial()
    phish(state, loop)
    command(state, loop, 'impacket-psexec m.leroux:Password123!@10.20.0.21')
    assert next(l for l in state.logs if l.event_id == '4624').data['KeyLength'] == 128
    command(state, loop, 'exit')
    state.discovered.add('srv-fichiers')
    state.loot.append(Credential('NTLM_HASH', 'it.presta', 'ca61eb63ab385fa4039002a79909c534', 'poste-accueil'))
    command(state, loop, 'impacket-psexec -hashes :ca61eb63ab385fa4039002a79909c534 it.presta@10.20.0.10')
    hashed = [l for l in state.logs if l.event_id == '4624' and l.host_id == 'srv-fichiers']
    assert hashed and hashed[-1].data['KeyLength'] == 0
    from engine import siem
    assert siem._match_pass_the_hash(hashed[-1])
