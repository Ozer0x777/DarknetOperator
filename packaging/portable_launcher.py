"""Lance la distribution Linux portable avec ses propres exécutables."""
from pathlib import Path
import argparse
import asyncio
import json
import os
import signal
import socket
import subprocess
import sys
import tempfile
import time
import urllib.request

ROOT = Path(__file__).resolve().parent
RUNTIME = ROOT / 'runtime'


def command(program, *arguments):
    return [str(RUNTIME/'ld-linux-x86-64.so.2'), '--library-path', str(RUNTIME/'lib'), str(program), *map(str, arguments)]


def python_command(*arguments):
    return command(RUNTIME/'python/bin/python3', '-s', *arguments)


def check_result(process, label):
    print(process.stdout, end='')
    if process.stderr:
        print(process.stderr, end='', file=sys.stderr)
    if process.returncode or 'SCRIPT ERROR:' in process.stderr or 'ERROR:' in process.stderr:
        raise RuntimeError(f'{label} a échoué (code {process.returncode}).')


async def check_wallet(output):
    import httpx
    from api import main as api
    from engine.career import Career
    from engine.onboarding import STAGES
    previous = api._CAREER
    profile = Career(output/'wallet-check.json')
    profile.data.update(campaign_version=3, handle='PackageCheck', money=1000)
    api._CAREER = profile
    try:
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api.app),base_url='http://test') as client:
            assert (await client.get('/api/shop')).status_code == 403
            assert (await client.get('/api/contracts')).json() == []
            profile.data.update(completed=list(STAGES), tier=1, reputation=40, money=1000, forum_reputation={'breachboard':40,'exployt':0,'xsx':0})
            result = await client.post('/api/shop/buy',json={'item':'gpu1'})
            assert result.status_code == 200 and not result.json()['paid']
            request = result.json()['wallet']['pending']['id']
            assert profile.data['money'] == 1000
            assert (await client.post('/api/wallet/device',json={'action':'approve','request_id':request})).status_code == 400
            for action in ('connect','unlock'):
                assert (await client.post('/api/wallet/device',json={'action':action})).status_code == 200
            result = await client.post('/api/wallet/device',json={'action':'approve','request_id':request})
            assert result.status_code == 200 and result.json()['balance'] == 600
            assert (await client.post('/api/wallet/device',json={'action':'approve','request_id':request})).status_code == 400
            assert profile.data['money'] == 600 and profile.data['inventory'].count('gpu1') == 1
        print('Accès verrouillés et ColdVault : confirmation obligatoire et débit unique validés en mémoire.')
    finally:
        api._CAREER = previous


def self_test():
    # Ces parcours utilisent des profils temporaires et l’API en mémoire, sans port.
    sys.path.insert(0, str(ROOT/'engine'))
    from validation_suite import qualify
    from act1_validation import main as qualify_act1
    from journey_validation import qualify as qualify_journey
    from first_hour_validation import qualify as qualify_first_hour
    from mission_review_validation import qualify as qualify_alternatives
    from save_review_validation import qualify as qualify_sensitive_saves
    from demo_validation import qualify as qualify_demo
    from act2_validation import qualify as qualify_act2
    from curriculum_validation import qualify as qualify_curriculum
    with tempfile.TemporaryDirectory(prefix='darknet-operator-verification-') as folder:
        output = Path(folder)
        os.environ['RVB_SAVE_DIR'] = str(output/'career')
        os.environ['XDG_DATA_HOME'] = str(output/'client')
        asyncio.run(qualify(output))
        asyncio.run(qualify_act1(output))
        asyncio.run(qualify_journey(output))
        asyncio.run(qualify_first_hour(output))
        asyncio.run(qualify_alternatives(output))
        asyncio.run(qualify_sensitive_saves(output))
        asyncio.run(qualify_demo(output))
        asyncio.run(qualify_act2(output))
        asyncio.run(qualify_curriculum(output))
        asyncio.run(check_wallet(output))
        print('Moteur embarqué : campagnes, données et reprises validées en mémoire.')
        for script in ('tests/test_audio.gd', 'tests/test_music_player.gd', 'tests/test_main_menu.gd', 'tests/test_desktop.gd', 'tests/test_social_layout.gd', 'tests/test_social_workflow.gd', 'tests/test_progression_wallet.gd', 'tests/test_journey.gd', 'tests/test_demo.gd', 'tests/test_act2.gd', 'tests/test_first_hour.gd'):
            result = subprocess.run(command(RUNTIME/'godot', '--headless', '--path', ROOT/'game', '--script', script, '--', '--offline-test'),
                                    cwd=ROOT, text=True, capture_output=True, timeout=60)
            check_result(result, script)
    print('Vérification hors réseau réussie. Elle ne valide pas une session graphique ni l’ouverture des ports locaux.')
    return 0


def main():
    parser = argparse.ArgumentParser(description='Darknet Operator — Linux portable x86_64')
    parser.add_argument('--self-test', action='store_true', help='vérifier le contenu embarqué sans modifier les sauvegardes du joueur')
    parser.add_argument('--headless', action='store_true', help='démarrage sans affichage, pour diagnostic')
    parser.add_argument('--smoke-test', action='store_true', help='ouvrir le menu pendant cinq secondes, puis arrêter le paquet')
    args = parser.parse_args()
    if args.self_test:
        return self_test()
    try:
        with socket.socket() as probe:
            probe.bind(('127.0.0.1', 0))
            port = probe.getsockname()[1]
    except OSError as exc:
        raise RuntimeError('Les connexions locales sont bloquées. Le jeu doit pouvoir ouvrir un port sur 127.0.0.1. ' + str(exc)) from exc
    service = None
    client = None
    def interrupted(_number, _frame):
        raise KeyboardInterrupt
    signal.signal(signal.SIGTERM, interrupted)
    try:
        service = subprocess.Popen(python_command(ROOT/'engine/desktop_server.py', '--port', port), cwd=ROOT/'engine')
        url = f'http://127.0.0.1:{port}'
        opener = urllib.request.build_opener(urllib.request.ProxyHandler({}))
        for _ in range(100):
            if service.poll() is not None:
                raise RuntimeError('Le moteur s’est arrêté au démarrage. Consulte le message précédent.')
            try:
                with opener.open(url+'/api/health', timeout=.25) as response:
                    if response.status == 200: break
            except OSError:
                time.sleep(.1)
        else:
            raise RuntimeError('Le moteur local ne répond pas après dix secondes.')
        flags = ['--headless'] if args.headless else []
        if args.smoke_test: flags += ['--quit-after', '300', '--max-fps', '60']
        client = subprocess.Popen(command(RUNTIME/'godot', *flags, '--path', ROOT/'game', '--', '--api='+url), cwd=ROOT)
        if args.smoke_test:
            try:
                return client.wait(timeout=20)
            except subprocess.TimeoutExpired as exc:
                raise RuntimeError('Le test de lancement a dépassé vingt secondes.') from exc
        return client.wait()
    finally:
        for process in (client, service):
            if process is not None and process.poll() is None:
                process.terminate()
                try:
                    process.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    process.kill()
                    process.wait()


if __name__ == '__main__':
    try:
        raise SystemExit(main())
    except KeyboardInterrupt:
        raise SystemExit(130)
    except (RuntimeError, OSError, subprocess.TimeoutExpired) as error:
        print('Darknet Operator : ' + str(error), file=sys.stderr)
        raise SystemExit(1)
