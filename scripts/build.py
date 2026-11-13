"""Prépare un paquet natif Godot + moteur autonome, sur le système cible."""
from pathlib import Path
import argparse
import importlib.util
import os
import shutil
import subprocess
import sys

ROOT=Path(__file__).resolve().parents[1]

def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('platform',choices=['linux','windows'])
    args=parser.parse_args()
    if (args.platform=='windows') != (os.name=='nt'):
        parser.error('Construire le moteur autonome sur le système cible (Windows pour Windows, Linux pour Linux).')
    godot=os.environ.get('GODOT') or shutil.which('godot') or shutil.which('godot4')
    if not godot:
        parser.error('Godot 4 et ses modèles d’export sont nécessaires.')
    if importlib.util.find_spec('PyInstaller') is None:
        parser.error('Installer packaging/requirements.txt dans l’environnement moteur puis relancer ce script avec son Python.')
    output=ROOT/'build'/args.platform
    output.mkdir(parents=True,exist_ok=True)
    engine_command=[sys.executable,'-m','PyInstaller','--noconfirm','--clean','--onedir','--name','redteam-engine',
        '--distpath',str(output/'engine'),'--workpath',str(ROOT/'build/pyinstaller-work'),
        '--specpath',str(ROOT/'build'),'--paths',str(ROOT/'backend')]
    for folder in ['abilities','scenarios','contracts','data']:
        engine_command+=['--add-data',f'{ROOT / "backend" / folder}{os.pathsep}{folder}']
    engine_command += ['--collect-all','uvicorn',str(ROOT/'backend/desktop_server.py')]
    subprocess.run(engine_command,cwd=ROOT,check=True)
    target=output/('RedTeamSimulator.exe' if args.platform=='windows' else 'RedTeamSimulator.x86_64')
    subprocess.run([godot,'--headless','--path',str(ROOT/'game'),'--export-release',args.platform.title(),str(target)],check=True)
    shutil.copy2(ROOT/'packaging/README-player.txt',output/'README.txt')
    print(f'Paquet prêt à tester : {output}')

if __name__=='__main__':
    main()
