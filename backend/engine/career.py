"""Profil solo persistant et boutique. Écritures atomiques avec sauvegarde précédente."""
from __future__ import annotations
import copy
from .onboarding import forum_unlocked
from .campaign import summary as campaign_summary
import json
import logging
import os
from pathlib import Path

_log = logging.getLogger(__name__)
_legacy_dir_warned = False

CATALOG = [
    {"id": "nullvad", "name": "NullVad — accès au service (50 ₵ / contrat)", "price": 0, "tier": 1},
    {"id": "wordlist", "name": "Liste de mots premium", "price": 150, "tier": 1},
    {"id": "gpu1", "name": "GPU niveau 1", "price": 400, "tier": 1},
    {"id": "gpu2", "name": "GPU niveau 2", "price": 1200, "tier": 2},
    {"id": "gpu3", "name": "GPU niveau 3", "price": 3000, "tier": 3},
    {"id": "relay", "name": "Accès SSH jetable", "price": 300, "tier": 3, "consumable": True},
    {"id": "vesper", "name": "Vesper — affiliation, part opérateur 30 %", "price": 0, "tier": 2},
    {"id": "glasswing", "name": "Glasswing — licence", "price": 450, "tier": 2},
]


def initial() -> dict:
    return {"version": 1, "money": 100, "reputation": 0, "tier": 0, "inventory": [],
            "completed": [], "settled": [], "conversations": {}, "forum_posts": {}, "route": "freeshield", "active": None}


class Career:
    @staticmethod
    def default_path() -> Path:
        import sys
        default_root = Path.home() / ".local/share"
        if os.name == "nt": default_root = Path(os.environ.get("LOCALAPPDATA", Path.home() / "AppData/Local"))
        elif sys.platform == "darwin": default_root = Path.home() / "Library/Application Support"
        folder = os.environ.get("REDTEAM_SAVE_DIR")
        if not folder and os.environ.get("RVB_SAVE_DIR"):
            # Ancien nom de la variable : toujours honoré, sinon la carrière du joueur
            # semblerait perdue et une partie d'essai écrirait dans la vraie.
            global _legacy_dir_warned
            folder = os.environ["RVB_SAVE_DIR"]
            if not _legacy_dir_warned:
                _legacy_dir_warned = True
                _log.warning("RVB_SAVE_DIR est l'ancien nom de REDTEAM_SAVE_DIR : il reste pris en compte, mais renomme la variable.")
        return Path(folder or default_root / "RedTeamSimulator") / "career.json"

    def __init__(self, path: Path | None = None):
        self.path = path or self.default_path()
        self.data = initial()
        self.recovered = False
        self.needs_recovery = False
        previous = self.path.with_suffix('.previous')
        if self.path.exists() or previous.exists():
            from .save_store import validate_profile, atomic_json, SaveStore
            try:
                self.data.update(validate_profile(json.loads(self.path.read_text(encoding='utf-8'))))
            except (ValueError, OSError) as exc:
                try:
                    restored = validate_profile(json.loads(previous.read_text(encoding='utf-8')))
                except (ValueError, OSError):
                    if not any(row['valid'] for row in SaveStore(self.path).list()):
                        raise ValueError(f"Sauvegarde illisible : {self.path}. Aucun emplacement valide trouvé.") from exc
                    self.needs_recovery = True
                    return  # Le menu peut charger un emplacement sans écraser le fichier abîmé.
                if self.path.exists():
                    import shutil, time
                    shutil.copy2(self.path, self.path.with_name('career.corrupt-'+str(time.time_ns())+'.json'))
                atomic_json(self.path, restored)
                self.data.update(restored)
                self.recovered = True

    def save(self) -> None:
        if self.needs_recovery: raise ValueError('Charge un emplacement valide ou crée une nouvelle partie avant de sauvegarder.')
        from . import community, wallet
        community.scores(self.data)
        wallet.ensure(self.data)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        tmp = self.path.with_suffix(".tmp")
        with tmp.open("w", encoding="utf-8") as f:
            json.dump(self.data, f, ensure_ascii=False, indent=2)
            f.flush()
            os.fsync(f.fileno())
        if self.path.exists():
            import shutil
            shutil.copy2(self.path, self.path.with_suffix(".previous"))
        tmp.replace(self.path)

    def wallet_session(self):
        if not hasattr(self, '_wallet_session'):
            self.reset_wallet_session()
        return self._wallet_session

    def reset_wallet_session(self):
        self._wallet_session = {'connected': False, 'unlocked': False, 'pending': None}

    def wallet_action(self, action, request_id=None):
        from . import wallet
        session = self.wallet_session()
        if action == 'connect': session['connected'] = True
        elif action == 'unlock':
            if not session['connected']: raise ValueError('Connecte le portefeuille matériel simulé.')
            session['unlocked'] = True
        elif action == 'disconnect':
            self.reset_wallet_session()
        elif action == 'cancel': session['pending'] = None
        elif action == 'approve':
            pending = session['pending']
            if not pending or pending['id'] != request_id: raise ValueError('Demande de paiement absente ou déjà traitée.')
            if not session['connected'] or not session['unlocked']: raise ValueError('Connecte et déverrouille ColdVault avant de confirmer sur l’appareil.')
            if self.purchase_item(pending['item'])['price'] != pending['amount']:
                raise ValueError("Le prix a changé. Annule cette demande et prépare un nouveau paiement.")
            self.buy(pending['item'])
            session['pending'] = None
        else: raise ValueError('Action de portefeuille inconnue.')
        return wallet.view(self)

    def request_purchase(self, item_id):
        import uuid
        from .wallet import view
        item = self.purchase_item(item_id)
        if item['price'] == 0:
            self.buy(item_id)
            return {'paid': True, 'profile': self.view()}
        session = self.wallet_session()
        if session['pending']:
            if session['pending']['item'] != item_id: raise ValueError('Confirme ou annule le paiement déjà en attente dans ColdVault.')
        else:
            session['pending'] = {'id': uuid.uuid4().hex, 'item': item_id, 'label': item['name'], 'amount': item['price'], 'recipient': 'Fournisseurs — services et matériel'}
        return {'paid': False, 'wallet': view(self)}

    def view(self) -> dict:
        from . import community, wallet, journey
        from .relationships import view as relationships
        from .act2 import view as act2_summary
        access = community.access(self.data)
        wallet.ensure(self.data)
        active = self.data.get("active") or {}
        running = active.get("status") == "RUNNING"
        contract = active.get("contract") or {}
        active_contract = None
        if running:
            active_contract = {"contract_id": contract.get("contract_id"),
                "title": contract.get("bounty", {}).get("title", active.get("scenario_name", "Mission sauvegardée")),
                "tick": active.get("tick", 0), "max_ticks": active.get("max_ticks", 0)}
        return {**copy.deepcopy({k: v for k, v in self.data.items() if k not in {"active", "settled", "conversations", "forum_posts", "workspace", "social"}}),
            "forum_counts": {key: len(posts) for key, posts in self.data.get("forum_posts", {}).items()},
            "act2": act2_summary(self.data), "relationships": relationships(self.data), "has_active": running, "active_contract": active_contract, "recovery_required": self.needs_recovery, "forum_unlocked": forum_unlocked(self.data), "campaign": campaign_summary(self.data), "access": access, "wallet": wallet.view(self), "journey": journey.view(self.data)}

    def lock_reason(self, contract: dict) -> str:
        from .onboarding import lock_reason
        reason = lock_reason(self.data,contract)
        if reason: return reason
        from .campaign import lock_reason as campaign_lock, enabled as act1_enabled
        from .act2 import lock_reason as act2_lock
        reason = act2_lock(self.data,contract)
        if reason: return reason
        reason = campaign_lock(self.data,contract)
        if reason: return reason
        if contract.get('bounty', {}).get('forum') in {'exployt', 'xsx'}:
            from .community import forum_reason
            reason = forum_reason(self.data, contract['bounty']['forum'])
            if reason: return reason
        legacy_requirements = [] if act1_enabled(self.data) and contract["contract_id"]=="mauvaise_adresse" else contract.get("required_completed", [])
        if any(cid not in self.data["completed"] for cid in legacy_requirements):
            return "Termine d’abord : " + ", ".join(contract["required_completed"])
        if contract["tier"] > self.data["tier"]:
            return f"Nécessite le palier {contract['tier']}"
        if self.data["reputation"] < contract.get("required_rep", 0):
            return f"Nécessite {contract['required_rep']} points de confiance opérateur"
        if contract.get("required_any") and not any(i in self.data["inventory"] for i in contract["required_any"]):
            return "Nécessite une affiliation ou une licence (boutique)"
        for item in contract.get("required_items", []):
            if item not in self.data["inventory"]:
                return f"Nécessite {item} (boutique)"
        return ""

    def purchase_item(self, item_id: str) -> dict:
        item = next((i for i in CATALOG if i["id"] == item_id), None)
        if item is None:
            raise ValueError("Article inconnu.")
        if item["tier"] > self.data["tier"]:
            raise ValueError("Palier insuffisant.")
        from .community import shop_reason
        reason = shop_reason(self.data)
        if reason: raise ValueError(reason)
        if item_id in self.data["inventory"] and not item.get("consumable"):
            raise ValueError("Article déjà acquis.")
        from . import economy
        reason = economy.item_reason(self.data, item)
        if reason: raise ValueError(reason)
        return {**item, "price": economy.price(self.data, item)}

    def buy(self, item_id: str) -> dict:
        from . import wallet
        import uuid
        item = self.purchase_item(item_id)
        wallet.ensure(self.data)
        before = copy.deepcopy(self.data)
        self.data["money"] -= item["price"]
        if item['price']: wallet.record(self.data, 'purchase:'+uuid.uuid4().hex, 'purchase', -item['price'], item['name'], 'shop')
        self.data["inventory"].append(item_id)
        try: self.save()
        except (OSError, ValueError):
            self.data = before
            raise
        return self.view()

    def select_route(self, route: str) -> None:
        if route not in {"direct", "freeshield", "nullvad", "tor", "relay"}:
            raise ValueError("Route inconnue.")
        if route in {"nullvad", "tor"} and "nullvad" not in self.data["inventory"]:
            raise ValueError("Active NullVad dans la boutique.")
        if route == "tor" and self.data["tier"] < 2:
            raise ValueError("Tor est débloqué au palier 2.")
        if route == "relay" and (self.data["tier"] < 3 or ("relay" not in self.data["inventory"] and not any(p.endswith(":relay") for p in self.data.get("route_passes", [])))):
            raise ValueError("Achète un accès SSH au palier 3.")
        self.data["route"] = route
        self.save()

    def prepare(self, contract: dict, state) -> None:
        from . import trace
        reason = self.lock_reason(contract)
        if reason:
            raise ValueError(reason)
        if self.data["active"] and self.data["active"].get("status") == "RUNNING":
            raise ValueError("Une mission est déjà en cours. Reprends-la ou déconnecte-toi.")
        from . import wallet
        wallet.ensure(self.data)
        self.select_route(self.data["route"])
        if contract.get("require_route") and self.data["route"] != contract["require_route"]:
            raise ValueError(f"Ce contrat nécessite la route {contract['require_route']}.")
        if contract["tier"] > 0 and not contract.get("side_job"):
            route = self.data["route"]
            passes = self.data.setdefault("route_passes", [])
            key = contract['contract_id'] + (':vpn' if route in {'nullvad', 'tor'} else ':relay')
            if route in {'nullvad', 'tor', 'relay'} and key not in passes:
                cost = 50 if route in {'nullvad', 'tor'} else 0
                if cost > self.data["money"]: raise ValueError("Il faut 50 ₵ pour le premier départ de ce dossier par cette route.")
                if route == 'relay' and 'relay' not in self.data['inventory']: raise ValueError("Achète un passage SSH pour ce nouveau dossier.")
                self.data["money"] -= cost
                if cost: wallet.record(self.data, 'route:'+__import__('uuid').uuid4().hex, 'route', -cost, 'Route de mission — '+contract['contract_id'], 'route')
                if route == 'relay': self.data['inventory'].remove('relay')
                passes.append(key)
        if contract.get("act") == 2: self.data["act2_started"] = True
        self.data["handle"] = state.player_handle
        state.inventory = list(self.data["inventory"])
        from . import social
        state.environment["world_minute"] = social.prepare(self)["minute"]
        for message in state.messages: message.time = social.stamp(state.environment["world_minute"])
        if contract["tier"] == 3:
            from .models import Credential
            host = next(iter(state.hosts.values()))
            host.status, host.compromised_by, host.access_level = "COMPROMISED", "red", "SYSTEM"
            account = next(iter(host.cached_logons), host.admin_users[0])
            if account not in host.admin_users: host.admin_users.append(account)
            relay_password = state.users[account].password or "sim-relay-access"
            state.loot.append(Credential("PLAINTEXT", account, relay_password, host.id))
            from . import console_sessions
            with console_sessions.using(state, "main"):
                console_sessions.enter(state, host, account, "SYSTEM")
            state.terminal_files["/home/operator/mission/acces.txt"] = f"Passation vérifiée — laboratoire\nMachine : {host.hostname} ({host.ip})\nCompte : {account}\nMot de passe : {relay_password}\nAccès : session de maintenance administrateur déjà ouverte.\nLimite : le compte peut être désactivé ; les droits des autres machines restent à vérifier.\n"
        trace.configure(state, self.data["route"])
        self.checkpoint(state)

    def replace(self, data: dict) -> None:
        """Remplace toute la carrière et l'écrit ; en cas d'échec, l'ancienne est rétablie en mémoire."""
        old_data, old_recovery = self.data, self.needs_recovery
        self.data, self.needs_recovery = data, False
        try: self.save()
        except (OSError, ValueError):
            self.data, self.needs_recovery = old_data, old_recovery
            raise

    def checkpoint(self, state) -> None:
        from .persistence import state_to_dict
        if not state.conversation_id:
            import uuid
            state.conversation_id = uuid.uuid4().hex
        archive = self.data.setdefault("conversations", {})
        for i, message in enumerate(state.messages):
            key = f"{state.conversation_id}:{i}"
            archive[key] = {**archive.get(key, {}), "id": key, "peer": state.contract["client"]["handle"] if state.contract else message.sender,
                "channel": message.channel, "sender": message.sender, "text": message.text, "tick": message.tick, "time": message.time}
        self.data["active"] = state_to_dict(state)
        if state.status == "ENDED":
            # Mission terminée : le bureau reprend le poste Kali tel qu'il est maintenant, pour que
            # les fichiers de la mission y soient visibles et que le prochain contrat parte de là.
            from .mission_data import desk_after
            self.data["workspace"] = desk_after(state)
            self.data["workspace_mission"] = state.conversation_id
            self.data["workspace_revision"] = self.data.get("workspace_revision", 0) + 1
        self.save()
        # L'autosauvegarde est un filet de sécurité : son échec (dossier non inscriptible,
        # emplacement verrouillé) ne doit ni annuler la sauvegarde réussie ni arrêter la partie.
        from .save_store import SaveStore
        try: SaveStore(self.path).autosave(self.data)
        except (OSError, ValueError) as exc:
            _log.warning("Autosauvegarde impossible : %s", exc)

    def settle(self, game_id: str, state) -> None:
        contract = state.contract
        if not contract or not state.contract_outcome or game_id in self.data["settled"]:
            return
        from . import community, wallet
        community.scores(self.data)
        wallet.ensure(self.data)
        first_success = contract["contract_id"] not in self.data["completed"]
        self.data["settled"].append(game_id)
        if state.contract_outcome == "SUCCESS":
            reward = contract["reward"] if first_success else 0
            if any(o.get("type") == "encrypted_ratio" for o in state.objectives):
                # Sauvegardes et exfiltration modulent le règlement dans ce modèle de jeu.
                data_hosts = [h for h in state.hosts.values() if any(name.startswith("/srv/") for name in h.files)]
                if any(h.backups for h in data_hosts):
                    reward = reward * 35 // 100
                if state.exfiltrated:
                    reward = reward * 115 // 100
            if contract.get("affiliation") and "glasswing" not in state.inventory:
                reward = reward * 30 // 100
            if first_success and contract.get("bonus") and not any(a.severity == "CRITICAL" for a in state.alerts):
                reward += contract["reward"] // 2
            state.payout = reward
            self.data["money"] += reward
            if reward: wallet.record(self.data, 'reward:'+game_id, 'reward', reward, contract.get('bounty', {}).get('title', contract['contract_id']), contract.get('bounty', {}).get('forum', 'private'))
            if contract["contract_id"] not in self.data["completed"]:
                self.data["completed"].append(contract["contract_id"])
                gain = contract.get('reputation', 0)
                self.data["reputation"] += gain
                forum = contract.get('bounty', {}).get('forum')
                if forum in community.FORUMS:
                    self.data['forum_reputation'][forum] += gain
                    if gain: self.data.setdefault('reputation_events', []).append({'id': game_id, 'contract': contract['contract_id'], 'forum': forum, 'amount': gain})
                self.data["tier"] = max(self.data["tier"], contract.get("unlocks_tier", self.data["tier"]))
        if state.contract_outcome == "SUCCESS" and first_success and contract.get('legacy_in_progress'):
            historical=self.data.setdefault('legacy_completed',[])
            if contract['contract_id'] not in historical: historical.append(contract['contract_id'])
        if state.contract_outcome == "SUCCESS" and first_success:
            from .campaign import settle as settle_campaign
            settle_campaign(self,state)
        from . import journey
        journey.record(self, state, game_id, first_success)
        self.checkpoint(state)
