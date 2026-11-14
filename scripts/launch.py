"""Lance le moteur local et le bureau Godot, puis ferme uniquement ses processus."""
from pathlib import Path
import argparse
import os
import shutil
import socket
import subprocess
import sys
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]


def main():
    parser = argparse.ArgumentParser(description='RedTeamSimulator - bureau natif')
    parser.add_argument('--editor', action='store_true', help='ouvrir le projet dans Godot')
    parser.add_argument('--port', type=int, default=0, help='port local du moteur (automatique par défaut)')
    args = parser.parse_args()
    godot = os.environ.get('GODOT') or shutil.which('godot') or shutil.which('godot4')
    python = ROOT / 'backend/.venv' / ('Scripts/python.exe' if os.name == 'nt' else 'bin/python')
    if not godot:
        parser.error('Godot 4 est absent. Installe Godot ou définis GODOT avec son chemin.')
    if args.editor:
        return subprocess.call([godot, '--editor', '--path', str(ROOT/'game')])
    if not python.exists():
        parser.error('Environnement moteur absent. Suivre README.md pour installer backend/.venv.')
    port = args.port
    if not 0 <= port <= 65535:
        parser.error('Le port doit être compris entre 0 et 65535.')
    if not port:
        try:
            with socket.socket() as probe:
                probe.bind(('127.0.0.1', 0))
                port = probe.getsockname()[1]
        except OSError as exc:
            parser.error(f'Les connexions locales sont indisponibles dans cet environnement : {exc}')
    command = [str(python), str(ROOT/'backend/desktop_server.py'), '--port', str(port)]
    service = subprocess.Popen(command, cwd=ROOT/'backend')
    client = None
    try:
        url = f'http://127.0.0.1:{port}'
        for _ in range(100):
            if service.poll() is not None:
                raise RuntimeError('Le moteur local s’est arrêté au lancement.')
            try:
                with urllib.request.urlopen(url+'/api/health', timeout=.25) as response:
                    if response.status == 200:
                        break
            except OSError:
                time.sleep(.1)
        else:
            raise RuntimeError('Le moteur local ne répond pas après dix secondes.')
        client = subprocess.Popen([godot, '--path', str(ROOT/'game'), '--', '--api='+url], cwd=ROOT)
        return client.wait()
    except (KeyboardInterrupt, RuntimeError) as exc:
        print(str(exc), file=sys.stderr)
        return 1
    finally:
        for process in [client, service]:
            if process is not None and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


if __name__ == '__main__':
    raise SystemExit(main())
