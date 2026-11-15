---
name: redteam-narrative
description: "Écrire ou réviser les personnages, conversations à choix, sujets du forum et arcs relationnels de Darknet Operator. Utiliser pour les changements narratifs du jeu ; les correctifs purement techniques ne nécessitent pas cette fiche."
---

# Narration de Darknet Operator

Les chemins ci-dessous sont relatifs à la racine du dépôt. Lire le canon utile
à la scène dans `docs/PERSONNAGES.md` et le fonctionnement livré dans
`docs/RELATIONS_NARRATIVES.md`. Recouper avec les données avant de prolonger un
arc : ces documents distinguent le jouable des propositions.

## Écrire dans le jeu existant

- `backend/data/social_world.json` : voix, biographies, sujets, événements et
  répliques libres. `backend/data/conversation_scenes.json` : questions et options.
- `backend/contracts/` et `backend/contracts/current/` : clients, briefs et
  réponses aux preuves. Vérifier les deux cursus avant de reprendre une consigne.
- `backend/engine/conversation_scenes.py` porte les décisions ; Godot affiche
  leurs textes et envoie leurs identifiants. Conserver cette séparation.

Une scène commence par une intention du PNJ : proposer, comprendre, se confier,
poser une limite ou obtenir quelque chose. Faire apparaître sa voix et ses
préoccupations, sans transformer tous les échanges en rappels de procédure.
Les détails du quotidien peuvent exister sans servir une demande de renseignement.

Dans le format présent, proposer trois réponses distinctes, avec une réponse
écrite du PNJ et une conséquence déclarée. Une reformulation polie de la même
phrase n'est pas une branche. Les préférences de travail sont mémorisées mais
ne modifient pas automatiquement la difficulté ni les indices techniques.

Pour les identifiants, conditions, effets et sauvegardes, conserver les invariants
vérifiés dans `backend/tests/test_conversation_scenes.py` : choix explicite,
idempotence, contexte du personnage et du canal, chronologie et limites privées.
Les futurs engagements et les confidences avec une vraie pièce demandent leur
propre scène ; un texte libre ne les crée pas à la place du joueur.

Respecter ce que chaque personnage a pu apprendre. Distinguer ses échanges
publics, ses MP et ce qui lui a effectivement été transmis. Ne pas faire d'une
intention de conception une mission ou une conséquence déjà disponible.
Les repères, syntaxes, références et preuves techniques restent exacts après
réécriture, même lorsque le ton devient plus naturel.

## Madame_TLS

Canon fixé par l'utilisateur : spécialiste CTI, OSINT et ingénierie sociale,
espionnage industriel et économique ; elle doit compromettre le joueur. Elle
n'est pas une experte système qui résout les commandes à la place de l'équipe.
Elle est sociable, sportive, très cultivée ; elle aime sortir, la musique,
la mode et les musées. Montrer des goûts et des points de vue, pas une liste
récitée de références ni une flatterie à chaque message.

La couverture publique et les informations d'auteur sont distinctes. Une
attirance peut compliquer sa mission sans l'annuler. Garder les liens
professionnel, amical et attiré possibles ; les relances suivent les choix
réels et les limites sur les informations. La révélation et le piège final
restent à construire tant qu'une branche jouable ne les livre pas.

## Vérification de la scène

Relire les répliques à voix haute et vérifier le moment où chacune apparaît.
Pour un changement de conditions, de branche ou de format, appliquer le skill
`redteam-game-qa` et ses contrôles ciblés. Une simple correction de ponctuation
n'impose pas de relancer tous les parcours du jeu.
