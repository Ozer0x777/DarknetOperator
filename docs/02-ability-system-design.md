> Conception du moteur hérité. Les mentions du blueprint sont historiques ;
> la référence actuelle du jeu solo est `03-red-progression.md`.

# Système d'abilities déclaratif

## Le problème que ça résout

Dans le blueprint (§5.3/5.4), chaque action Red/Blue est une fonction Python avec son
propre bloc prérequis/effet (`resolve_psexec`, `resolve_blue_action`, …). Ça marche pour
une poignée d'actions, mais le blueprint prévoit ~14 actions Red + ~14 Blue, répliquées
différemment selon 6 scénarios. Avec du code ad hoc par action, ajouter du contenu =
toucher le moteur à chaque fois, et le moteur grossit indéfiniment.

**MITRE CALDERA** (cité en inspiration dans le blueprint, §B) résout exactement ce
problème : les capacités offensives sont décrites en YAML (*abilities*), séparées du
code qui les exécute. On reprend ce principe, en plus simple.

## Le format

Une ability = un fichier JSON. Le moteur ne connaît que deux registres de fonctions :
des **prédicats** (vérifient un prérequis) et des **effets** (modifient l'état). Une
ability ne fait que combiner des prédicats et des effets déjà connus du moteur - elle
n'a pas de code propre.

```json
{
  "id": "red.psexec_lateral",
  "team": "red",
  "name": "psexec.py",
  "requires": [
    {"type": "target_status_not", "value": "ISOLATED"},
    {"type": "target_has_service", "name": "SMB", "port": 445},
    {"type": "credential_grants_admin_on_target"},
    {"type": "not_blocked_by_firewall", "port": 445}
  ],
  "noise": 75,
  "effects": [
    {"type": "mark_compromised", "access_level": "SYSTEM"}
  ],
  "artifacts": [
    {"event_id": "4624", "data": {"LogonType": 3, "LogonProcessName": "NtLmSsp", "KeyLength": 0}},
    {"event_id": "4688", "data": {"NewProcess": "psexesvc.exe", "ParentProcess": "services.exe"}},
    {"event_id": "7045", "data": {"ServiceName": "PSEXESVC"}}
  ]
}
```

**Pour ajouter une action Red/Blue : un nouveau fichier JSON, zéro ligne de moteur**,
à condition que les prédicats/effets dont elle a besoin existent déjà. C'est la même
logique que le blueprint applique déjà aux scénarios (§12, config JSON) - on l'étend
aux actions elles-mêmes.

## Ce qui reste du code (volontairement)

Les prédicats et les effets, eux, sont du code Python normal (pas de petit langage
d'expression maison - trop de risque de sur-ingénierie pour la taille du projet).
Chaque prédicat/effet est une fonction pure, petite, testable isolément :

```python
def target_has_service(state, ctx, name, port):
    return any(s.name == name and s.port == port for s in ctx.target.services)
```

Quand une nouvelle *mécanique* apparaît (pas juste une nouvelle action, un vrai nouveau
concept - ex. "Credential Guard bloque le dump LSASS"), on ajoute un prédicat une fois,
et toutes les abilities existantes et futures peuvent s'en servir.

## Ce que ça donne pour les 6 scénarios du blueprint

Un scénario reste un fichier JSON décrivant hosts/users/credentials/droits (déjà prévu
au §12 du blueprint). La différence : les *actions disponibles* ne sont plus codées en
dur dans le moteur mais listées par ID dans la config du scénario. "Ransomware Cascade"
et "The Silent Insider" peuvent partager 90% des mêmes abilities (`psexec_lateral`,
`mimikatz_dump`, `dcsync`…) et ne diverger que sur la topologie et 2-3 abilities propres
au scénario (ex. `ransomware_deploy`, `supply_chain_backdoor`).

## Implémentation

Voir `backend/engine/` :
- `models.py` - état d'une mission en mémoire.
- `predicates.py` / `effects.py` - les deux registres.
- `ability_engine.py` - charge les JSON, résout un outil contre l'état courant.
- `siem.py` - règles de corrélation, même logique déclarative appliquée aux logs.
- `blue_ai.py` - défense automatique de la cible (isolement, désactivation de compte) ;
  le joueur ne pilote aucune action de défense.
- `../abilities/red/*.json` - les dix outils du joueur, lancés depuis le terminal.
- `../scenarios/*.json` - un scénario par contrat.
- `../tests/fixtures/reseau_ad.json` - réseau de test à trois machines, hors du jeu.
