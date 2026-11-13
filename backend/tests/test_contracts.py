"""
Contrats et guide du contact (docs/03-red-progression.md §9, étape 1 bis) :
contracts/tuto_p0.json, messages Chordly, issue du contrat, API forum.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest
import httpx

from api.main import app
from support import command, phish, upload
from engine import contracts, terminal
from engine.contracts import ContractValidationError
from engine.game_loop import GameLoop, load_all_abilities
from engine.persistence import state_from_dict, state_to_dict

ROOT = Path(__file__).parent.parent
CONTRACT_PATH = ROOT / "contracts" / "tuto_p0.json"
ABILITIES = load_all_abilities()


def tuto_contract():
    return contracts.load_contract(CONTRACT_PATH, known_ability_ids=set(ABILITIES))


def start(handle="NullMoth"):
    state = contracts.start_contract(tuto_contract(), handle, known_ability_ids=set(ABILITIES))
    return state, GameLoop(state, ABILITIES)


def play(line, state, loop, console='main'):
    return command(state, loop, line, console)



def texts(state):
    return [m.text for m in state.messages]


# ---------------------------------------------------------------------------
# Chargement et validation
# ---------------------------------------------------------------------------

def test_all_contracts_load():
    loaded = contracts.load_all_contracts(known_ability_ids=set(ABILITIES))
    assert "tuto_p0" in loaded


def _write(tmp_path, mutate):
    data = json.loads(CONTRACT_PATH.read_text())
    mutate(data)
    path = tmp_path / "contract.json"
    path.write_text(json.dumps(data))
    return path


@pytest.mark.parametrize("mutate, match", [
    (lambda d: d.update(channel="whatsapp"), "messagerie inconnue"),
    (lambda d: d.update(scenario="nulle_part"), "scénario introuvable"),
    (lambda d: d.pop("brief"), "champs manquants"),
    (lambda d: d["guide"].append({"when": {"type": "host_discovered", "host": "ghost"}, "message": "x"}),
     "ghost"),
    (lambda d: d["guide"].append({"when": {"type": "credential_owned", "username": "fantome"}, "message": "x"}),
     "fantome"),
    (lambda d: d["guide"].append({"when": {"type": "pirater_tout"}, "message": "x"}), "inconnu"),
    (lambda d: d["guide"].append({"when": {"type": "host_discovered", "host": "srv-fichiers"}}),
     "pas de message"),
])
def test_invalid_contracts_are_rejected(tmp_path, mutate, match):
    with pytest.raises(ContractValidationError, match=match):
        contracts.load_contract(_write(tmp_path, mutate))


# ---------------------------------------------------------------------------
# Guide du contact
# ---------------------------------------------------------------------------

def test_contract_starts_with_the_brief_addressed_to_the_player():
    state, _ = start("NullMoth")
    assert len(state.messages) == 1
    first = state.messages[0]
    assert first.channel == "chordly"
    assert first.sender == "k0rvid"
    assert first.tick == 0
    assert "NullMoth" in first.text and "{handle}" not in first.text


def test_each_step_sends_the_next_message_then_the_payment():
    state, loop = start()

    play("nmap 10.20.0.0/24", state, loop)
    assert len(state.messages) == 2 and "GoPhish" in state.messages[-1].text

    phish(state, loop)
    assert len(state.messages) == 3 and "compte collecté" in state.messages[-1].text

    upload(state, loop, state.hosts['poste-accueil'], state.find_credential('m.leroux', 'PLAINTEXT'))
    play("impacket-psexec m.leroux:Password123!@10.20.0.21", state, loop)
    play('mimikatz "privilege::debug" "sekurlsa::logonpasswords" exit', state, loop)
    assert len(state.messages) == 4 and "prestataire" in state.messages[-1].text

    play(f"impacket-psexec -hashes :{state.find_credential('it.presta', 'NTLM_HASH').value} it.presta@10.20.0.10", state, loop, "server")
    assert state.contract_outcome == "SUCCESS"
    assert "300 ₵" in state.messages[-1].text
    assert len(state.messages) == 5


def test_no_message_when_nothing_progresses():
    state, loop = start()
    for _ in range(3):
        loop.tick()
    assert len(state.messages) == 1


def test_skipped_steps_only_send_the_most_advanced_message():
    """Phishing avant le scan : le contact ne commente pas le scan après coup."""
    state, loop = start()
    phish(state, loop)
    assert len(state.messages) == 2
    assert "compte collecté" in state.messages[-1].text
    assert state.guide_index == 2
    play("nmap 10.20.0.0/24", state, loop)
    assert len(state.messages) == 2  # l'étape « scan » est déjà dépassée


def test_timeout_fails_the_contract_with_a_single_message():
    state, loop = start()
    for _ in range(state.max_ticks + 5):
        loop.tick()
    assert state.contract_outcome == "FAILED"
    assert texts(state)[-1].startswith("Trop long")
    assert len(state.messages) == 2


def test_contract_progress_survives_save_and_reload():
    state, loop = start()
    play("nmap 10.20.0.0/24", state, loop)
    restored = state_from_dict(json.loads(json.dumps(state_to_dict(state))))
    assert texts(restored) == texts(state)
    assert restored.guide_index == state.guide_index
    assert restored.player_handle == "NullMoth"
    assert restored.contract["contract_id"] == "tuto_p0"

    # La partie rechargée continue le guide là où il s'était arrêté.
    loop2 = GameLoop(restored, ABILITIES)
    phish(restored, loop2)
    assert "compte collecté" in restored.messages[-1].text


# ---------------------------------------------------------------------------
# API : forum, inscription, partie sous contrat
# ---------------------------------------------------------------------------

@pytest.fixture
def anyio_backend():
    return "asyncio"


@pytest.fixture
async def client():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://test", follow_redirects=True) as client:
        yield client


@pytest.mark.anyio
async def test_api_lists_bounties_without_leaking_the_guide(client):
    bounties = (await client.get("/api/contracts", params={"forum": "breachboard"})).json()
    tuto = next(b for b in bounties if b["contract_id"] == "tuto_p0")
    assert "300 ₵" in tuto["body"]
    assert "guide" not in tuto and "brief" not in tuto
    assert "BreachBoard" in tuto["intro"]


@pytest.mark.anyio
async def test_api_suggests_distinct_handles(client):
    handles = (await client.get("/api/handles", params={"count": 4, "seed": 1})).json()["handles"]
    assert len(set(handles)) == 4
    assert handles == (await client.get("/api/handles", params={"count": 4, "seed": 1})).json()["handles"]


@pytest.mark.anyio
async def test_api_creates_a_contract_game(client):
    resp = await client.post("/api/games", json={"contract": "tuto_p0", "handle": "NullMoth"})
    assert resp.status_code == 200
    state = resp.json()["state"]
    assert state["contract"]["client"] == "k0rvid"
    assert state["contract"]["debrief_hints"] == []
    assert state["discovered"] == ["poste-accueil"]
    assert len(state["messages"]) == 1
    assert state["objectives"] == [{"type": "host_compromised", "host": "srv-fichiers", "met": False}]


@pytest.mark.anyio
@pytest.mark.parametrize("handle", [None, "", "ab", "<script>", "un pseudo avec espaces"])
async def test_api_rejects_invalid_handles(client, handle):
    resp = await client.post("/api/games", json={"contract": "tuto_p0", "handle": handle})
    assert resp.status_code == 400


@pytest.mark.anyio
async def test_api_unknown_contract_is_404(client):
    resp = await client.post("/api/games", json={"contract": "nope", "handle": "NullMoth"})
    assert resp.status_code == 404
