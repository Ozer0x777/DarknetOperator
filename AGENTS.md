# RedTeamSimulator

Jeu solo Red Team : faux bureau, forum BreachBoard, messagerie Chordly, contrats et terminal simulé.

- Réponses, documentation et messages de jeu en français.
- Ce dépôt est indépendant du projet voisin. Ne pas ajouter d'import, de lien
  symbolique ou de dépendance de fichiers vers celui-ci.
- Lanceur : `./run.sh` (client Godot et moteur local). Le prototype web a été retiré le 13 novembre 2026.
- Tests moteur : `backend/.venv/bin/python -m pytest -q backend/tests`.
- Test Godot : `python3 scripts/check_ui.py` (détecte aussi les erreurs de script Godot).
- Revue de composition : `python3 scripts/preview_ui.py`.
- Les composants du bureau sont dans `game/scripts/ui/`, leurs ressources et licences dans `game/assets/`.
- Conserver la séparation moteur / API / interface.
- Les actions décrites sont résolues dans le monde simulé.
- Cible du terminal : syntaxe authentique des outils et sorties cohérentes avec
  le monde simulé. Le parseur simplifié actuel est une limite du prototype.
- Les mécanismes Blue servent au défenseur et au débriefing du jeu solo.

- Architecture : Godot 4 standard/GDScript typé pour le client ; moteur Python local.
- État réel du plan : `docs/ROADMAP.md` ; fidélité terminal : `docs/COMMANDES.md`.
- Ne pas annoncer un paquet Steam ou une commande comme validé sans test correspondant.

- Les outils se pilotent en CLI ; une GUI n’est ajoutée que pour reproduire celle du logiciel réel (GoPhish, futurs C2). Aucun bouton générique ne remplace les commandes.
- Chaque console doit isoler cwd, connexion, variables, auth, sorties et historique. Les fichiers locaux sont partagés.
