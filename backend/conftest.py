import sys
from pathlib import Path

# Permet de lancer pytest depuis n'importe quel répertoire tout en gardant
# `import engine...` fonctionnel (comme l'API).
sys.path.insert(0, str(Path(__file__).parent))


import pytest

@pytest.fixture(autouse=True)
def isolated_career(tmp_path, monkeypatch):
    """Les tests ne lisent ni ne modifient les sauvegardes du joueur."""
    monkeypatch.setenv("REDTEAM_SAVE_DIR", str(tmp_path / "saves"))
    import api.main as api
    api._CAREER = None
    api._WORKSPACE = None
    api.GAMES.clear()
    yield
    api._CAREER = None
    api._WORKSPACE = None
    api.GAMES.clear()
