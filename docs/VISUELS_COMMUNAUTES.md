# Navigateur et communautés

Le navigateur simulé adopte les conventions de Firefox : onglets fermables,
nouvel onglet, historique par onglet, retour/avance, rechargement, barre d’adresse,
favoris et menu. Ctrl+L sélectionne l’adresse ; Ctrl+T ouvre un onglet.
Il affiche les sites du jeu, sans moteur web généraliste.

Les forums possèdent des rubriques, fils, réponses, compteurs de vues, dates,
rangs, réputation et avatars. Les pseudos sont fictifs : k0rvid, nullroute,
0xvanta, hexcache, miette et sable. Les trois portraits anime représentent des
personnages adultes originaux. Les communautés ne reproduisent pas des comptes réels.

Chordly reprend une organisation de messagerie inspirée de Discord ; Telegrid et
Sessyon gardent leurs palettes distinctes. Les brouillons sont conservés par contact.
Un accusé d’envoi ne doit pas effacer le brouillon d’une autre conversation.
Les dossiers privés possèdent une carte pour accepter ou reprendre la mission.

Références de conventions : [barres d’outils Firefox](https://support.mozilla.org/en-US/kb/customize-firefox-controls-buttons-and-toolbars)
et [messagerie Discord](https://support.discord.com/hc/en-us/sections/115000458672-Messaging-and-Chat).
Ces interfaces restent des créations du jeu, pas les applications officielles.

Les aperçus de composition se trouvent dans `build/ui-previews/index.html`.
Ce sont des exports de scène, pas des captures GPU du jeu lancé.

## Fenêtres compactes et rédaction

Les fenêtres des forums et des trois messageries peuvent être réduites jusqu’à
600 × 420 px. Les contrôles de composition sont vérifiés dans un bureau de
1280 × 720 px, avec des fenêtres de 600 et 1040 px de large.

Sous 880 px, le forum présente le profil en tête du message (avatar de 40 px),
les compteurs sous le titre des sujets et une navigation qui revient à la ligne.
En disposition large, le profil occupe une colonne de 148 px avec un portrait de
72 px ; les listes utilisent des portraits de 44 px (40 px en mode compact). Des badges distinguent
les annonces épinglées, les sujets verrouillés et les contrats.

Sous 760 px, la messagerie donne priorité à la conversation. Le bouton de menu
permet de retrouver les contacts ; le bouton d’information ouvre le profil.
La colonne de profil remplace celle des contacts lorsque la largeur manque.
Les messages d’un même auteur espacés de cinq minutes au plus sont regroupés,
avec une séparation lors d’un changement de jour. Telegrid et Sessyon limitent
la largeur des bulles ; Chordly conserve sa présentation en flux.

Dans les messageries : **Entrée** envoie, **Maj+Entrée** ajoute une ligne.
Le champ grandit jusqu’à cinq lignes environ, puis défile. Le compteur indique
la limite de 2 000 caractères ; un texte trop long reste modifiable et ne part pas.
Dans le forum : **Entrée** ajoute une ligne, **Ctrl+Entrée** publie.
Une citation s’ajoute au brouillon existant et amène la rédaction dans la zone
visible. Les citations publiées sont distinguées par un fond et une bordure.
Les brouillons restent en mémoire par sujet ; curseur, sélection et recherche
sont conservés lors d’une reconstruction de la vue.

Les icônes d’action partagent le même dessin ; les boutons ont un état de focus
clavier visible et les champs reprennent la couleur d’accent de leur application.

Vérification : `python3 scripts/check_ui.py`, dont
`game/tests/test_social_layout.gd` pour les dispositions et la saisie réelle au
clavier. `python3 scripts/preview_ui.py` ajoute les vues compactes 31 à 39 à la
galerie de composition. Pour enregistrer le rendu natif lorsqu’un affichage est
accessible :

```bash
godot --path game --script tests/test_social_layout.gd -- --offline-test --capture
```

Les captures sont écrites dans `build/social-layout/`. Le mode headless ne
produit pas de capture du rendu natif.


## Lecture, publication et brouillons durables

Les conversations remontent selon leur dernière activité datée ; le chargement
ultérieur d’une archive ancienne ne remplace pas l’aperçu récent. La recherche
par contact porte aussi sur le texte complet de son dernier message.

Dans une conversation, la recherche indique le résultat courant et le nombre
de messages correspondants. Les flèches et Entrée/Maj+Entrée permettent de passer
au résultat suivant/précédent ; Échap ferme la recherche. Le résultat actif est
encadré. Les cartes de dossiers et l’indicateur de saisie restent hors de cette
liste de résultats.

Un nouveau message reçu pendant la lecture des anciens échanges est signalé
sans déplacer le défilement. Le bouton « Nouveaux messages ↓ » rejoint la fin et
quitte une éventuelle recherche. Les identifiants évitent les doublons de signal.

Le forum bloque les publications concurrentes d’une même réponse, y compris après
actualisation de la page. Un accusé est associé à son sujet : une erreur conserve
le texte et autorise une nouvelle tentative ; une réussite efface seulement la
réponse envoyée et affiche sa confirmation.

Les brouillons des forums et messageries sont enregistrés après une courte pause
de saisie et à la fermeture du bureau. Ils sont conservés dans `user://drafts`,
avec des fichiers séparés par pseudo et service, écriture temporaire et copie
précédente. Ils sont locaux au client, indépendants des points de sauvegarde du
monde : charger une ancienne partie ne rembobine pas un texte en préparation.
Une erreur d’écriture est signalée et laisse le texte dans le compositeur.

Les tests hors ligne n’utilisent pas les brouillons du joueur. La vérification
`test_social_workflow.gd` injecte un dossier temporaire pour éprouver les reprises,
la récupération de fichier et les erreurs d’envoi. Les vues 40 à 43 de la galerie
montrent la recherche, l’arrivée d’un message et les états de publication.

## Passe de finition des espaces sociaux

Un thème commun limité aux messageries et forums harmonise les polices, les
séparateurs, l’interligne et les barres de défilement. Chaque service conserve
sa palette. Les listes de conversations présentent un avatar centré, une heure
alignée et un compteur de non-lus ; la conversation sélectionnée est signalée
par une bordure latérale. Les liens vers le forum ont une carte distincte.
Les profils de contact défilent pour rester accessibles en petite fenêtre.

Les forums utilisent des en-têtes plus compacts, des compteurs centrés et des
profils d’auteur moins encombrants. Les avatars compacts gardent leurs proportions.
Le texte des messages est affiché en 15 px avec un interligne plus confortable ;
les lignes successives d’une citation partagent un seul encadré.

Validation de cette passe : 48 contrôles de composition/rédaction, 32 de flux
persistants, 40 de vie sociale et 61 du bureau, sans échec. Les aperçus sociaux
larges et compacts ont été examinés. Le lancement graphique réel reste à valider
sur une machine avec affichage ; les aperçus ne remplacent pas une capture GPU.

La version 0.4.5 ajoute les accès Console / Objectif / Indice dans le dossier,
les notifications regroupées et le suivi du défilement lors du redimensionnement.
Voir [REVUE_PREMIERS_PAS.md](REVUE_PREMIERS_PAS.md) pour la portée des vérifications.
