# Configuration Codex du projet

Le dépôt fournit deux skills dans `.agents/skills/` et un réglage local dans
`.codex/config.toml`. Ils concernent Darknet Operator, sans modifier les réglages
personnels ou globaux de Codex.

Le raisonnement est réglé sur `high` par défaut pour les branches narratives,
les sauvegardes et les changements transversaux. Le modèle reste celui choisi
dans l'application ou dans la configuration personnelle. Pour une petite
retouche, l'effort peut être réduit dans la session.

Les réglages locaux sont chargés par Codex lorsque le dépôt est approuvé.
Une session déjà ouverte peut conserver ses réglages ; les nouvelles sessions
qui chargent le projet utilisent sa configuration, sauf surcharge explicite.

## Skills disponibles

- `$redteam-narrative` : voix des personnages, scènes à choix, chronologie,
  limites privées et cohérence de Madame_TLS avec son expertise CTI/OSINT,
  son rôle d'espionne et ses goûts personnels.
- `$redteam-game-qa` : contrôles adaptés au changement, sauvegardes, interface,
  aperçus et parcours manuel. Il distingue les tests réussis d'une vraie partie
  avec affichage et d'un essai avec un débutant.

La sélection automatique des skills est conservée. Ils peuvent aussi être
invoqués explicitement dans une demande, par exemple :

```text
Utilise $redteam-narrative pour écrire une scène avec Madame_TLS au musée.
Utilise $redteam-game-qa pour vérifier cette scène et sa reprise après sauvegarde.
```

Les skills ne lancent pas de tâche planifiée. Un test joueur demande toujours
une personne qui joue et dont on observe les hésitations.
