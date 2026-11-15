---
name: redteam-game-qa
description: "Vérifier une modification ou une version de Darknet Operator : moteur Python, parcours, sauvegardes, conversations et interface Godot. Utiliser pour un bilan de qualité ou les contrôles nécessaires à une modification ; ne pas imposer la suite complète à chaque retouche éditoriale."
---

# Vérification de Darknet Operator

Lire `AGENTS.md` et le statut Git avant les vérifications. Les commandes sont
lancées depuis la racine du dépôt. Les limites connues sont dans
`docs/ROADMAP.md`, `docs/COMMANDES.md` et `docs/RELATIONS_NARRATIVES.md`.

## Choisir les contrôles selon le changement

| Changement | Vérification utile |
|---|---|
| Réplique, bio ou sujet seulement | Relecture, références et conditions de publication ; tests du contenu concerné si nécessaire |
| Choix, relation ou chronologie | `backend/tests/test_conversation_scenes.py`, `test_dialogue.py`, `test_story_events.py` et `test_world_life.py` selon le périmètre |
| Moteur, API, économie ou sauvegarde | Tests ciblés puis `backend/.venv/bin/python -m pytest -q backend/tests` |
| Messagerie ou saisie des choix | Test Godot `tests/test_dialogue_choices.gd` et flux sociaux concernés |
| Modification transversale ou bilan de version | `python3 scripts/check_ui.py` : validations de parcours puis contrôles et rejeux Godot |
| Composition d'écran | `python3 scripts/preview_ui.py --only NOM_DE_VUE` puis inspection des images produites |

Le test ciblé Godot se lance avec `godot --headless --path game --script
 tests/test_dialogue_choices.gd -- --offline-test` (sur une seule ligne).
Adapter l'exécutable si le projet utilise `godot4` ou `GODOT`.

`check_ui.py` écrit des corpus dans `build/validation`. Deux validations qui
réécrivent le même corpus doivent être séquentielles. Le contrôle complet peut
prendre plusieurs minutes. Lire son résumé final et les journaux : un code de
sortie Godot nul ne suffit pas en présence de `SCRIPT ERROR:` ou `ERROR:`.
Distinguer un défaut du jeu d'une restriction d'environnement, notamment les
journaux `user://` bloqués par le bac à sable.

## Parcours manuel pour une tranche de jeu

Pour vérifier le jeu sans toucher à une carrière existante, lancer `./run.sh`
avec un répertoire temporaire fourni par `REDTEAM_SAVE_DIR`. Conserver ce
répertoire tant que la reprise doit être examinée.

Vérifier une question reçue, ses trois réponses, la réponse du PNJ et une
reprise après fermeture. Essayer aussi un changement de contact pendant
l'envoi, un brouillon conservé et la fenêtre compacte. Pour une branche de
Madame_TLS, vérifier le lien choisi et la limite sur les informations, puis
une relance ultérieure cohérente. Les commandes et preuves de mission restent
accessibles pendant les échanges personnels.

Un essai avec un débutant dure idéalement 30 à 45 minutes : relever les moments
où il hésite, demande une explication ou ignore un message, sans le guider à
chaque étape. Ce test mesure la compréhension et le rythme ; une suite headless
ne le remplace pas. Si aucun testeur ou affichage natif n'a été utilisé,
indiquer cette limite dans le bilan.

## Bilan

Rapporter les contrôles réellement exécutés, leurs résultats et les limites
restantes. Distinguer assertions réussies, avertissements à la fermeture,
inspection des aperçus et partie manuelle. Ne qualifier ni un paquet ni Steam
sur la seule base des tests du moteur. Préserver les modifications de l'utilisateur.
