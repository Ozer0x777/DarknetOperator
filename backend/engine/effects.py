"""
Registre des effets utilisables dans le champ "effects" d'une ability.
Chaque effet est une fonction qui MUTE l'état : (state, ctx, **params) -> None.
Même logique que predicates.py : nouveau mécanisme = nouvelle fonction ici,
pas de nouveau code moteur par ability. Voir docs/02-ability-system-design.md.
"""
from __future__ import annotations

from .models import ActionContext, Credential, GameState


def mark_compromised(state: GameState, ctx: ActionContext, access_level: str = "USER") -> None:
    ctx.target.status = "COMPROMISED"
    ctx.target.compromised_by = ctx.actor
    ctx.target.access_level = access_level
    if ctx.params.get("kerberos_ticket") and ctx.target.is_domain_controller:
        compromise_domain(state, ctx)


def add_credential(
    state: GameState,
    ctx: ActionContext,
    username: str,
    cred_type: str,
    value_template: str = "sim-hash-{username}",
) -> None:
    import hashlib
    value = value_template.format(username=username)
    account = state.users.get(username)
    if cred_type == "PLAINTEXT" and account and account.password is not None: value = account.password
    if cred_type in {"NTLM_HASH", "KRBTGT_HASH"} and value_template == "sim-hash-{username}":
        if cred_type == "NTLM_HASH":
            from .ntlm import nt_hash
            value = nt_hash(account.password if account and account.password is not None else 'sim-password-' + username)
        else:
            value = hashlib.sha256(f"fictional:{ctx.target.id}:{username}".encode()).hexdigest()[:32]
    state.loot.append(
        Credential(
            type=cred_type,
            username=username,
            value=value,
            source_host=ctx.target.id,
        )
    )


def add_primary_user_credential(
    state: GameState,
    ctx: ActionContext,
    cred_type: str = "PLAINTEXT",
    value_template: str = "sim-pass-{username}",
) -> None:
    """Ajoute au butin l'identifiant de l'utilisateur attitré de la cible.
    Le nom vient du scénario, pas de l'ability : le même phishing marche partout."""
    if ctx.target.primary_user:
        add_credential(state, ctx, ctx.target.primary_user, cred_type, value_template)


def add_cached_credentials(
    state: GameState,
    ctx: ActionContext,
    cred_type: str = "NTLM_HASH",
    value_template: str = "sim-hash-{username}",
) -> None:
    """Ajoute au butin les identifiants des comptes en mémoire sur la cible
    (champ `cached_logons` du scénario)."""
    for username in ctx.target.cached_logons:
        add_credential(state, ctx, username, cred_type, value_template)


def reveal_network(state: GameState, ctx: ActionContext, prefix_octets: int = 3) -> None:
    """Scan réseau : révèle tous les hôtes du même sous-réseau que la cible
    (par défaut /24 = 3 premiers octets identiques) ainsi que leurs services."""
    prefix = ".".join(ctx.target.ip.split(".")[:prefix_octets]) + "."
    for host in state.hosts.values():
        if host.ip.startswith(prefix) and (ctx.params.get("scan_scope") != "host" or host.id == ctx.target.id):
            state.discovered.add(host.id)
            if ctx.params.get("discovery_only"):
                continue
            state.scanned.add(host.id)
            if ctx.params.get("scan_versions"):
                versions = state.tool_data.setdefault("recon", {}).setdefault("versions", [])
                if host.id not in versions: versions.append(host.id)
            ports = ctx.params.get("scan_ports") or [s.port for s in host.services]
            state.known_ports[host.id] = sorted(set(state.known_ports.get(host.id, [])) | set(ports))


def forge_ticket(state: GameState, ctx: ActionContext) -> None:
    username = ctx.params.get("ticket_user", "administrator")
    filename = f"/home/operator/{username}.ccache"
    state.terminal_files[filename] = "Fichier ccache virtuel du laboratoire — aucune clé réelle."
    state.tool_data.setdefault("kerberos", {})[filename] = {"username": username, "domain": state.domain.get("name"), "source": ctx.credential.value if ctx.credential else None, "expires_minute": state.environment.get("world_minute", 0) + ctx.params.get("ticket_hours", 87600) * 60}


def compromise_domain(state: GameState, ctx: ActionContext) -> None:
    state.domain_compromised = True
    ctx.target.status = "COMPROMISED"
    ctx.target.compromised_by = ctx.actor
    for user in state.users.values():
        if user.is_domain_admin:
            user.status = "ACTIVE"  # pas de changement réel, juste explicite


# Gestes de la défense automatique : blue_ai les appelle directement, aucun fichier
# d'ability ne les déclare. Ils ne figurent donc pas dans REGISTRY.
def isolate_host(state: GameState, ctx: ActionContext) -> None:
    ctx.target.status = "ISOLATED"
    ctx.target.isolated_at_tick = ctx.tick


def disable_user(state: GameState, ctx: ActionContext) -> None:
    if ctx.user is None:
        return
    ctx.user.status = "DISABLED"
    # Invalide tous les credentials déjà volés pour cet utilisateur : Red ne
    # peut plus les réutiliser une fois le compte désactivé (containment réel).
    for cred in state.loot:
        if cred.username == ctx.user.username:
            cred.valid = False


def exfiltrate_files(state: GameState, ctx: ActionContext) -> None:
    for name, content in ctx.target.files.items():
        if 'files' in ctx.params and name not in ctx.params['files']: continue
        state.exfiltrated[f"{ctx.target.id}:{name}"] = content
        if ctx.params.get('download_destination'):
            path=ctx.params['download_destination']
            if state.terminal_files.get(path) != content:
                from .evidence import invalidate
                invalidate(state,path,'operator')
            state.terminal_files[path] = content


def encrypt_host(state: GameState, ctx: ActionContext) -> None:
    if not ctx.target.encrypted:
        import hashlib
        for filename, content in list(ctx.target.files.items()):
            if filename.startswith('/srv/'):
                ctx.target.files[filename] = '[Données chiffrées dans le laboratoire]\n' + hashlib.sha256(content.encode()).hexdigest()
    ctx.target.status = "ENCRYPTED"
    ctx.target.encrypted = True


def destroy_backups(state: GameState, ctx: ActionContext) -> None:
    ctx.target.backups = False


def crack_credential(state: GameState, ctx: ActionContext) -> None:
    # Seules les correspondances trouvées par hashcat dans une liste de mots comptent :
    # aucun mot de passe n'est révélé sans dictionnaire.
    matches = ctx.params.get('crack_matches') or {}
    state.tool_data.setdefault('hashcat', {}).setdefault('pot', {}).update(matches)
    from .mission_data import note_cracked
    note_cracked(state, matches)
    for credential in list(state.loot):
        if credential.type != 'NTLM_HASH' or credential.value.lower() not in matches: continue
        password = matches[credential.value.lower()]
        if any(c.username == credential.username and c.type == 'PLAINTEXT' and c.value == password for c in state.loot): continue
        account = state.users.get(credential.username)
        state.loot.append(Credential('PLAINTEXT', credential.username, password, credential.source_host, credential.valid and (not account or account.status == 'ACTIVE')))


REGISTRY = {
    "forge_ticket": forge_ticket,
    "exfiltrate_files": exfiltrate_files,
    "encrypt_host": encrypt_host,
    "destroy_backups": destroy_backups,
    "crack_credential": crack_credential,
    "mark_compromised": mark_compromised,
    "reveal_network": reveal_network,
    "add_credential": add_credential,
    "add_primary_user_credential": add_primary_user_credential,
    "add_cached_credentials": add_cached_credentials,
    "compromise_domain": compromise_domain,
}
