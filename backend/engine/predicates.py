"""
Registre des prédicats utilisables dans le champ "requires" d'une ability.
Chaque prédicat est une fonction pure : (state, ctx, **params) -> bool.
Ajouter un prédicat ici le rend disponible à TOUTE ability (existante ou future)
sans toucher au reste du moteur — voir docs/02-ability-system-design.md.
"""
from __future__ import annotations

from .models import ActionContext, GameState


def target_status_not(state: GameState, ctx: ActionContext, value: str) -> bool:
    return ctx.target.status != value


def target_status_is(state: GameState, ctx: ActionContext, value: str) -> bool:
    return ctx.target.status == value


def target_has_service(state: GameState, ctx: ActionContext, name: str, port: int) -> bool:
    return ctx.target.has_service(name, port)


def not_blocked_by_firewall(state: GameState, ctx: ActionContext, port: int) -> bool:
    return not state.is_blocked(ctx.target.id, port)


def actor_has_valid_credential(state: GameState, ctx: ActionContext) -> bool:
    return ctx.credential is not None and ctx.credential.valid


def credential_grants_admin_on_target(state: GameState, ctx: ActionContext) -> bool:
    from .authentication import current
    if not current(state, ctx.credential):
        return False
    if ctx.params.get("kerberos_ticket"):
        filename = ctx.params["kerberos_ticket"]
        ticket = state.tool_data.get("kerberos", {}).get(filename, {})
        return bool(ctx.target.is_domain_controller and ticket.get("username", "").casefold() == "administrator" and ticket.get("expires_minute", float('inf')) > state.environment.get("world_minute", 0) and ticket.get("domain") == state.domain.get("name") and ticket.get("source") == ctx.credential.value and ctx.credential.type == "KRBTGT_HASH")
    user = state.users.get(ctx.credential.username)
    return ctx.credential.username in ctx.target.admin_users and (not user or user.status == "ACTIVE")


def credential_has_dcsync_rights(state: GameState, ctx: ActionContext) -> bool:
    from .authentication import current
    if not current(state, ctx.credential):
        return False
    user = state.users.get(ctx.credential.username)
    return bool(user and user.has_dcsync_rights)


def credential_is_krbtgt_hash(state: GameState, ctx: ActionContext) -> bool:
    return ctx.credential is not None and ctx.credential.valid and ctx.credential.type == "KRBTGT_HASH"


def target_discovered(state: GameState, ctx: ActionContext) -> bool:
    """Brouillard de guerre : Red ne peut viser qu'un hôte qu'il a découvert."""
    return ctx.target.id in state.discovered


def target_has_primary_user(state: GameState, ctx: ActionContext) -> bool:
    """La machine a un utilisateur attitré (un serveur ne lit pas d'e-mails)."""
    return ctx.target.primary_user is not None


def target_compromised(state: GameState, ctx: ActionContext) -> bool:
    return ctx.target.compromised_by == "red" and ctx.target.status == "COMPROMISED"


def target_admin_access(state: GameState, ctx: ActionContext) -> bool:
    return target_compromised(state, ctx) and ctx.target.access_level == "SYSTEM"


def player_owns(state: GameState, ctx: ActionContext, item: str) -> bool:
    return item in state.inventory


def target_read_access(state: GameState, ctx: ActionContext) -> bool:
    if ctx.params.get('authenticated_share'):
        return credential_grants_admin_on_target(state, ctx) and ctx.target.status not in {'ISOLATED', 'ENCRYPTED'} and not state.is_blocked(ctx.target.id, 445)
    return target_compromised(state, ctx) and state.terminal_host == ctx.target.id


REGISTRY = {
    "target_system_session": lambda state, ctx: target_admin_access(state,ctx) and state.terminal_host==ctx.target.id and state.terminal_access=="SYSTEM",
    # Les empreintes viennent d'une commande hashcat (fichier d'empreintes + liste de mots).
    "crack_input_present": lambda state, ctx: bool(ctx.params.get("hashes")),
    "target_read_access": target_read_access,
    "target_is_domain_controller": lambda state, ctx: ctx.target.is_domain_controller,
    "target_compromised": target_compromised,
    "player_owns_any": lambda state, ctx, items: any(item in state.inventory for item in items),
    "target_admin_access": target_admin_access,
    "player_owns": player_owns,
    "target_status_not": target_status_not,
    "target_status_is": target_status_is,
    "target_has_service": target_has_service,
    "not_blocked_by_firewall": not_blocked_by_firewall,
    "actor_has_valid_credential": actor_has_valid_credential,
    "credential_grants_admin_on_target": credential_grants_admin_on_target,
    "credential_has_dcsync_rights": credential_has_dcsync_rights,
    "credential_is_krbtgt_hash": credential_is_krbtgt_hash,
    "target_discovered": target_discovered,
    "target_has_primary_user": target_has_primary_user,
}
