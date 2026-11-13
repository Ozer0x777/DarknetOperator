"""Traçage du joueur à travers sa route fictive, déterministe via state.rng."""
from .models import GameState

ROUTES = {
    "direct": [],
    "freeshield": [{"id": "freeshield", "name": "FreeShield", "resistance": 15}],
    "nullvad": [{"id": "nullvad", "name": "NullVad", "resistance": 25}],
    "tor": [{"id": "nullvad", "name": "NullVad", "resistance": 25}, {"id": "tor", "name": "Tor", "resistance": 40}],
    "relay": [{"id": "tor", "name": "Tor", "resistance": 40}, {"id": "relay", "name": "Relais SSH", "resistance": 35}],
}


def configure(state: GameState, route: str) -> None:
    import copy
    state.trace = {"enabled": bool(state.defender.get("enabled", False)), "nodes": copy.deepcopy(ROUTES[route]),
                   "progress": 0, "investigating": False, "burned": [], "events": []}


def advance(state: GameState) -> None:
    trace = state.trace
    if not trace.get("enabled") or state.status != "RUNNING":
        return
    seen = set(trace.get("processed_alerts", []))
    severe = [a for a in state.alerts if a.severity in {"HIGH", "CRITICAL"} and a.id not in seen]
    trace["processed_alerts"] = list(seen | {a.id for a in severe})
    if not severe:
        return
    trace["investigating"] = True
    pressure = sum(4 if a.severity == "CRITICAL" else 2 for a in severe)
    trace["progress"] += pressure
    nodes = trace["nodes"]
    used = trace.get("used", 0) + pressure
    while nodes:
        node = nodes[-1]
        if node["id"] == "freeshield" and node.get("checked") is not True:
            node["checked"] = True
            if state.rng.random() < .35:
                used = max(used, node["resistance"])
                trace["events"].append({"tick": state.tick, "message": "FreeShield a livré ses journaux."})
        if used < node["resistance"]:
            break
        used -= node["resistance"]
        trace["burned"].append(nodes.pop()["id"])
        trace["events"].append({"tick": state.tick, "message": f"Intermédiaire atteint : {node['name']}."})
        if node["id"] == "relay":
            # Le relais absorbe le reste de ce tour et protège le joueur.
            used = 0
            break
    trace["used"] = used
    if not nodes:
        if not trace.get("exposed"):
            trace["events"].append({"tick": state.tick, "message": "Route exposée : la mission continue. Consulte les alertes dans le rapport."})
        trace["exposed"] = True


def summary(state: GameState) -> dict:
    trace = state.trace
    nodes = trace.get("nodes", [])
    return {"enabled": trace.get("enabled", False), "route": ["Joueur"] + [n["name"] for n in nodes] + ["Cible"],
            "progress": trace.get("progress", 0), "capacity": sum(n["resistance"] for n in nodes) + trace.get("progress", 0) - trace.get("used", 0),
            "investigating": trace.get("investigating", False), "burned": trace.get("burned", [])}
