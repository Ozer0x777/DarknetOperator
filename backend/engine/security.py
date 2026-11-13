"""Politiques explicites du laboratoire : réseau et protection des hôtes."""
from .models import ActionResult, Alert, LogEvent


def inspect_action(state, ability, ctx):
    if not ctx.target.edr_agent:
        return None
    policy = state.environment.get('endpoint_policies', {}).get(ctx.target.id)
    if policy is None:
        return None
    disposition = policy.get('actions', {}).get(ability.id)
    if disposition not in {'audit', 'block'}:
        return None
    data = {'action': ability.id, 'disposition': disposition, 'policy': policy.get('name', 'Protection locale')}
    state.logs.append(LogEvent('EDR-POLICY', ctx.target.id, state.tick, data))
    state.alerts.append(Alert(state.next_alert_id(), f"{data['policy']} : {'exécution bloquée' if disposition == 'block' else 'activité observée'}", 'MEDIUM', 'ENDPOINT-POLICY', ctx.target.id, state.tick, state.tick))
    if disposition == 'block':
        return ActionResult(False, f"Exécution refusée sur {ctx.target.hostname} par la politique de protection locale ({data['policy']}). La mission continue ; vérifier le périmètre et les autres services autorisés.", reason='blocked_by_edr')
    return None


def incident_summary(state):
    encrypted = [h for h in state.hosts.values() if h.encrypted]
    destroyed = [h for h in state.hosts.values() if not h.backups]
    return {
        'encrypted_hosts': [h.hostname for h in encrypted],
        'exfiltrated_files': sorted(state.exfiltrated),
        'local_snapshots_removed': [h.hostname for h in destroyed],
        'notes': [
            'Une copie exfiltrée prouve un transfert, pas une publication ni une vente.',
            'La suppression des instantanés locaux ne prouve pas la disparition des sauvegardes externes.',
            'La présence de chiffrement ne prouve ni un arrêt total de l’entreprise ni le paiement d’une rançon.',
            'Le règlement du contrat est un mécanisme de jeu distinct du paiement éventuel par une victime.',
        ] if encrypted or state.exfiltrated or destroyed else [],
    }
