"""Point d'entrée du moteur local et du paquet autonome."""
import argparse
from pathlib import Path
import os
import uvicorn
from api import main as api
app = api.app
from engine.career import Career


def acquire_profile_lock(folder: Path):
    """Un seul moteur peut écrire dans un dossier de sauvegarde donné."""
    folder.mkdir(parents=True, exist_ok=True)
    lock = (folder / '.engine.lock').open('a+')
    try:
        if os.name == 'nt':
            import msvcrt
            lock.seek(0)
            if not lock.read(1):
                lock.write('0')
                lock.flush()
            lock.seek(0)
            msvcrt.locking(lock.fileno(), msvcrt.LK_NBLCK, 1)
        else:
            import fcntl
            fcntl.flock(lock.fileno(), fcntl.LOCK_EX | fcntl.LOCK_NB)
    except OSError as exc:
        lock.close()
        raise RuntimeError('Un autre moteur utilise déjà cette sauvegarde. Ferme-le ou choisis un autre REDTEAM_SAVE_DIR.') from exc
    return lock


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--port', type=int, default=8001)
    args = parser.parse_args()
    try:
        lock = acquire_profile_lock(Career.default_path().parent)
        profile = Career()
        api._CAREER = profile
    except (ValueError, RuntimeError) as exc:
        parser.error(str(exc))
    try:
        uvicorn.run(app, host='127.0.0.1', port=args.port, log_level='warning')
    finally:
        lock.close()
