from pathlib import Path
from engine import terminal, console_sessions
from engine.game_loop import load_all_abilities
from engine.scenario_loader import load_scenario
from engine.persistence import state_to_dict,state_from_dict

ABILITIES=load_all_abilities()
def fresh(): return load_scenario(Path(__file__).parents[1]/'scenarios/tuto_p0.json')
def run(state,line): return terminal.parse(line,state,ABILITIES)


def test_linux_files_shared_between_consoles_and_saved():
    state=fresh()
    with console_sessions.using(state,'one'):
        assert run(state,'mkdir ~/notes').ok
        assert run(state,'echo preuve > ~/notes/rapport.txt').ok
        assert run(state,'cp ~/notes/rapport.txt ~/notes/copie.txt').ok
    restored=state_from_dict(state_to_dict(state))
    with console_sessions.using(restored,'two'):
        assert run(restored,'cat ~/notes/copie.txt').output==['preuve\n']
        assert run(restored,'mv ~/notes/copie.txt ~/notes/final.txt').ok
        assert 'rapport.txt' in '\n'.join(run(restored,'ll ~/notes').output)
        assert not run(restored,'rmdir ~/notes').ok
        assert run(restored,'rm -r ~/notes').ok
        assert not run(restored,'cat ~/notes/rapport.txt').ok
    assert any(e['operation']=='delete' for e in restored.tool_data['file_audit'])


def test_writes_respect_permissions_and_do_not_recreate_deleted_tools():
    state=fresh()
    run(state,'ls')  # Initialisation des outils fournis.
    assert run(state,'rm ~/tools/mimikatz.exe').ok
    run(state,'ls')
    assert '/home/operator/tools/mimikatz.exe' not in state.terminal_files
    assert not run(state,'echo test > /etc/shadow').ok
    assert not run(state,'rm -rf /').ok


def test_windows_deletion_redirection_and_powershell_aliases():
    state=fresh()
    console_sessions.enter(state,state.hosts['poste-accueil'],'m.leroux','USER')
    assert run(state,r'echo debut > C:\Users\m.leroux\note.txt').ok
    assert run(state,r'type C:\Users\m.leroux\note.txt').output==['debut\n']
    assert not run(state,r'echo interdit > C:\Windows\system32\note.txt').ok
    assert run(state,r'copy C:\Users\m.leroux\note.txt C:\Users\m.leroux\copie.txt').ok
    assert run(state,r'del C:\Users\m.leroux\copie.txt').ok
    assert not run(state,'rm note.txt').ok  # cmd n'est pas Bash.
    run(state,'powershell')
    assert run(state,r'Set-Content -Path C:\Users\m.leroux\note.txt -Value "nouveau"').ok
    assert run(state,r'Get-Content C:\Users\m.leroux\note.txt').output==['nouveau\n']
    assert run(state,r'Remove-Item C:\Users\m.leroux\note.txt').ok
    assert run(state,r'Test-Path C:\Users\m.leroux\note.txt').output==['False']
    assert len(state.tool_data['file_audit']) >= 5
