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


def test_only_red_abilities_and_no_direct_action_route_are_exposed():
    """Le joueur agit par le terminal ; la défense est interne au moteur."""
    import httpx

    async def check():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test") as client:
            abilities = (await client.get("/api/abilities")).json()
            assert abilities and all(a["team"] == "red" for a in abilities)
    asyncio.run(check())
    paths = {getattr(route, "path", "") for route in app.routes}
    assert "/api/games/{game_id}/action" not in paths and "/api/scenarios" not in paths
