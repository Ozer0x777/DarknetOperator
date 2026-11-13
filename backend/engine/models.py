"""
État du jeu en mémoire pour le MVP — pas de DB (voir README.md).
Les noms des champs restent proches du modèle SQLAlchemy-style du blueprint
(§4.2) pour que le passage à une vraie persistance plus tard soit direct.
"""
from __future__ import annotations

import random
from dataclasses import dataclass, field


@dataclass
class Service:
    name: str
    port: int
    version: str = ""


@dataclass
class Host:
    id: str
    hostname: str
    ip: str
    status: str = "HEALTHY"          # HEALTHY | COMPROMISED | ISOLATED | ENCRYPTED
    services: list[Service] = field(default_factory=list)
    edr_agent: bool = False
    # Rights model simplifié : qui a les droits admin / DCSync sur ce host.
    admin_users: list[str] = field(default_factory=list)
    compromised_by: str | None = None
    isolated_at_tick: int | None = None
    # Qui utilise ce poste au quotidien (destinataire d'un phishing), et quels
    # comptes ont laissé des identifiants en mémoire (récupérables par mimikatz).
    is_domain_controller: bool = False
    access_level: str = "NONE"
    files: dict[str, str] = field(default_factory=dict)
    backups: bool = True
    primary_user: str | None = None
    cached_logons: list[str] = field(default_factory=list)

    encrypted: bool = False
    os: str = "Windows Server 2022"
    role: str = ""
    phishing: dict = field(default_factory=dict)

    def has_service(self, name: str, port: int) -> bool:
        return any(s.name == name and s.port == port for s in self.services)


@dataclass
class User:
    username: str
    status: str = "ACTIVE"           # ACTIVE | DISABLED
    is_domain_admin: bool = False
    has_dcsync_rights: bool = False
    password: str | None = None


@dataclass
class Credential:
    """Un credential dans le "loot box" de Red (§8.6 du blueprint)."""
    type: str                        # NTLM_HASH | KRBTGT_HASH | PLAINTEXT
    username: str
    value: str
    source_host: str
    valid: bool = True


@dataclass
class LogEvent:
    event_id: str
    host_id: str
    tick: int
    data: dict


@dataclass
class Alert:
    id: int
    title: str
    severity: str
    rule_id: str
    host_id: str
    attack_tick: int
    detected_tick: int
    status: str = "NEW"              # NEW | ACK


@dataclass
class ActionResult:
    success: bool
    message: str
    noise: int = 0
    reason: str | None = None


@dataclass
class ActionContext:
    """Ce dont un prédicat/effet a besoin pour juger une action."""
    actor: str                       # "red" | "blue"
    target: Host
    tick: int
    credential: Credential | None = None
    user: User | None = None         # pour les actions Blue (disable_user…)
    params: dict = field(default_factory=dict)


@dataclass
class Player:
    """Un joueur ayant rejoint la partie — §7.1/§8.1 du blueprint, réduit à
    team + role (structure héritée du moteur initial). Le token sert de clé d'auth légère :
    pas de mot de passe, juste un secret opaque renvoyé au join."""
    token: str
    name: str
    team: str          # "red" | "blue" | "spectator"
    role: str


@dataclass
class HistoryEntry:
    """Une ligne de narration — alimente le flux temps réel de l'UI."""
    tick: int
    team: str
    message: str
    success: bool
    reason: str | None = None
    console_id: str = "main"
    exit_code: int | None = None


@dataclass
class Message:
    """Un message reçu par le joueur sur une messagerie (Chordly, Telegrid…)."""
    tick: int
    channel: str                     # "chordly" | "telegrid" | "sessyon"
    sender: str
    text: str
    time: str = ""


@dataclass
class GameState:
    hosts: dict[str, Host]
    users: dict[str, User]
    loot: list[Credential] = field(default_factory=list)
    logs: list[LogEvent] = field(default_factory=list)
    alerts: list[Alert] = field(default_factory=list)
    history: list[HistoryEntry] = field(default_factory=list)
    firewall_blocks: set[tuple[str, int]] = field(default_factory=set)  # (host_id, port)
    domain_compromised: bool = False
    tick: int = 0
    max_ticks: int = 60
    status: str = "RUNNING"           # RUNNING | ENDED
    winner: str | None = None         # "RED" | "BLUE" | None
    score: dict[str, int] = field(default_factory=lambda: {"red": 0, "blue": 0})
    cooldowns: dict[str, int] = field(default_factory=dict)  # ability_id -> tick dispo
    rng: random.Random = field(default_factory=random.Random)
    next_alert_seq: int = 1           # entier simple, pas itertools.count : sérialisable tel quel
    scenario_name: str = ""
    available_abilities: dict[str, list[str]] = field(default_factory=dict)
    players: dict[str, Player] = field(default_factory=dict)  # token -> Player
    # Brouillard de guerre (docs/03-red-progression.md §8) : ce que Red connaît.
    # discovered = hôtes dont Red connaît l'existence (nom + IP) ;
    # scanned = hôtes dont Red connaît aussi les services ouverts.
    discovered: set[str] = field(default_factory=set)
    scanned: set[str] = field(default_factory=set)
    # Objectifs déclarés par le scénario (voir win_conditions.OBJECTIVES).
    # Vide = mode d'origine (compromission du domaine ou score).
    objectives: list[dict] = field(default_factory=list)
    # Contrat en cours (engine/contracts.py). None = partie libre, sans client.
    contract: dict | None = None
    player_handle: str | None = None
    messages: list[Message] = field(default_factory=list)
    conversation_id: str = ""
    guidance_enabled: bool = True
    guide_index: int = 0              # prochaine étape du guide à déclencher
    contract_outcome: str | None = None  # None (en cours) | "SUCCESS" | "FAILED"

    trace: dict = field(default_factory=dict)
    defender: dict = field(default_factory=dict)
    inventory: list[str] = field(default_factory=list)
    exfiltrated: dict[str, str] = field(default_factory=dict)
    end_reason: str | None = None
    payout: int = 0
    terminal_host: str | None = None
    terminal_user: str = "operator"
    terminal_access: str = "USER"
    terminal_shell: str = "bash"
    terminal_last_exit: int = 0
    terminal_last_native_exit: int = 0
    terminal_return_stack: list[dict] = field(default_factory=list)
    terminal_auth: dict = field(default_factory=dict)
    terminal_cwd: str = "/home/operator"
    terminal_files: dict[str, str] = field(default_factory=dict)
    terminals: dict[str, dict] = field(default_factory=dict)
    terminal_env: dict[str, str] = field(default_factory=dict)
    terminal_foreground: int | None = None
    active_terminal_id: str = "main"
    tool_services: dict = field(default_factory=dict)
    tool_data: dict = field(default_factory=dict)
    pending_actions: list[dict] = field(default_factory=list)
    known_ports: dict[str, list[int]] = field(default_factory=dict)
    domain: dict = field(default_factory=dict)
    environment: dict = field(default_factory=dict)

    def find_credential(self, username: str, type_: str | None = None) -> Credential | None:
        for cred in reversed(self.loot):  # le plus récent d'abord
            if cred.username == username and cred.valid and (type_ is None or cred.type == type_):
                return cred
        return None

    def find_host(self, ref: str) -> Host | None:
        """Retrouve un hôte par hostname, FQDN (insensibles à la casse) ou IP."""
        ref_l = ref.lower().rstrip(".")
        for host in self.hosts.values():
            if ref_l in (host.hostname.lower(), host.ip, host.hostname.lower()+"."+self.domain.get("name", "").lower()):
                return host
        # Noms publics déclarés par le scénario (DNS simulé) : nom → identifiant d'hôte.
        target = {name.lower(): host_id for name, host_id in self.environment.get("dns", {}).items()}.get(ref_l)
        return self.hosts.get(target) if target else None

    def dns_names(self, host_id: str) -> list[str]:
        """Noms DNS publics qui pointent vers cet hôte, dans l'ordre du scénario."""
        return [name for name, target in self.environment.get("dns", {}).items() if target == host_id]

    def is_blocked(self, host_id: str, port: int, source: str | None = None) -> bool:
        if (host_id, port) in self.firewall_blocks:
            return True
        source = source or self.terminal_host or "operator"
        for rule in self.environment.get("network_rules", []):
            if rule["target"] == host_id and rule["port"] == port and rule["source"] in {source, "*"}:
                return rule["action"] == "deny"
        return False

    def next_alert_id(self) -> int:
        value = self.next_alert_seq
        self.next_alert_seq += 1
        return value

    def is_on_cooldown(self, ability_id: str, tick: int) -> bool:
        """Évalué contre le tick DE L'ACTION (ctx.tick), pas self.tick : les
        deux coïncident dans GameLoop mais pas forcément si resolve() est
        appelé directement (tests, scripts)."""
        return tick < self.cooldowns.get(ability_id, 0)
