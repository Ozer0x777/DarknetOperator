"""Vérifie les limites du projet : moteur local du client Godot, sans interface web."""
import asyncio
from pathlib import Path
from api.main import app

ROOT = Path(__file__).resolve().parents[2]


def test_engine_serves_only_the_godot_api():
    """Le prototype web est retiré : le moteur ne sert plus de page HTML."""
    paths = {getattr(route, "path", "") for route in app.routes}
    assert "/" not in paths and "/static" not in paths and "/red" not in paths
    assert not (ROOT / "frontend").exists()


def test_blue_actions_are_internal_only():
    import httpx
    from api.main import GAMES

    async def check():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            abilities = (await client.get("/api/abilities")).json()
            assert abilities and all(a["team"] == "red" for a in abilities)
            game = (await client.post("/api/games", json={"contract": "tuto_p0", "handle": "NullMoth"})).json()
            try:
                response = await client.post(f"/api/games/{game['id']}/action", json={
                    "team": "blue", "ability_id": "blue.isolate_host", "target_id": "poste-accueil",
                })
                assert response.status_code == 400
            finally:
                GAMES.pop(game["id"], None)
    asyncio.run(check())
