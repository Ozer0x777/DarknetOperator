"""Vérifie les assertions ET les erreurs Godot qui n'affectent pas toujours son code de sortie.

Tous les contrôles sont lancés, même après un échec ; un résumé final liste ceux
qui ont échoué, et le code de sortie est non nul s'il y en a au moins un.
"""
from pathlib import Path
import os
import shutil
import subprocess
import sys
import time

root=Path(__file__).resolve().parents[1]
godot=os.environ.get('GODOT') or shutil.which('godot') or shutil.which('godot4')
if not godot:
    raise SystemExit('Godot 4 est requis pour les tests d’interface.')
python=str(root/'backend/.venv/bin/python')
VALIDATIONS=['validation_suite.py','act1_validation.py','journey_validation.py','first_hour_validation.py','mission_review_validation.py',
             'save_review_validation.py','demo_validation.py','act2_validation.py','curriculum_validation.py','tls_arc_validation.py','act3_validation.py']
GODOT_TESTS=['tests/test_audio.gd','tests/test_music_player.gd','tests/test_main_menu.gd','tests/test_desktop.gd','tests/test_window_input.gd',
             'tests/test_menu_over_windows.gd','tests/test_console_restore.gd','tests/test_review_fixes.gd','tests/test_terminal_input.gd',
             'tests/test_social_life.gd','tests/test_forum_community.gd','tests/test_social_layout.gd','tests/test_social_workflow.gd','tests/test_dialogue_choices.gd','tests/test_tls_arc.gd','tests/test_progression_wallet.gd',
             'tests/test_journey.gd','tests/test_demo.gd','tests/test_act2.gd','tests/test_act3.gd','tests/test_first_hour.gd','tests/test_tool_forms.gd',
             'tests/test_scenario_replays.gd','tests/test_act1_replays.gd']
# Les rejeux complets prennent environ deux minutes sur une machine chargée.
LONG={'tests/test_scenario_replays.gd':300,'tests/test_act1_replays.gd':300,'tests/test_tls_arc.gd':120}
failures=[]
started=time.monotonic()

# Les validations produisent build/validation, lu ensuite par les rejeux Godot.
for script in VALIDATIONS:
    result=subprocess.run([python,str(root/'backend'/script),str(root/'build/validation')],cwd=root)
    if result.returncode: failures.append(f'{script} (code {result.returncode})')

for script in GODOT_TESTS:
    timeout=LONG.get(script,45)
    try:
        result=subprocess.run([godot,'--headless','--path',str(root/'game'),'--script',script,'--','--offline-test'],
            text=True,capture_output=True,timeout=timeout)
    except subprocess.TimeoutExpired as error:
        for value in [error.stdout,error.stderr]:
            if value: print(value.decode(errors='replace') if isinstance(value,bytes) else value)
        failures.append(f'{script} (plus de {timeout} s)')
        continue
    sys.stdout.write(result.stdout)
    sys.stderr.write(result.stderr)
    if result.returncode or 'SCRIPT ERROR:' in result.stderr or 'ERROR:' in result.stderr:
        failures.append(f'{script} (code {result.returncode or 1})')

total=len(VALIDATIONS)+len(GODOT_TESTS)
print(f'\n=== {total-len(failures)}/{total} contrôles réussis en {round(time.monotonic()-started)} s ===')
for failure in failures: print('ÉCHEC : '+failure)
raise SystemExit(1 if failures else 0)
