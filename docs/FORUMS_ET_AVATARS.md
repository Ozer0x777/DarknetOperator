# Forums, avatars et bannières

Les forums conservent leurs trois identités : BreachBoard, communauté ouverte et
entraide ; Exployt, retours techniques et opérateurs confirmés ; XSX, conditions
et passations privées. Les règles d'accès de la carrière restent appliquées.

## Lecture et échanges

Les 37 sujets écrits sont répartis par catégories, avec tri par dernière activité,
date d'ouverture ou nombre de réponses. La recherche s'applique à la liste
sélectionnée. Un filtre montre les sujets non lus ; ouvrir un sujet n'est jamais
empêché par les filtres de la liste, notamment lors d'un retour d'historique.

Les six nouvelles discussions comportent 29 réponses entre habitués : réparation
de matériel, surprises au musée, petites victoires du quotidien, origine des
tests réseau, relecture d'une passation et correction d'un message public.
Madame_TLS parle de culture avec les autres membres. Ces échanges ne révèlent
pas sa mission cachée et ne modifient pas les relations choisies par le joueur.

Les réponses, participants, derniers auteurs et vues proviennent des données du
jeu. Les compteurs de vues initiaux représentent l'archive écrite ; les ouvertures
réelles du joueur s'y ajoutent. Aucun nombre de visiteurs prétendument connectés
n'est inventé. Les réponses automatiques restent écrites et limitées à un retour
par personnage et sujet selon les règles existantes.

## Marqueurs de lecture

`social.forum_seen` conserve l'identifiant du dernier message vu dans chaque
sujet. La lecture suit les identifiants et détecte donc aussi deux messages
arrivés à la même minute. Un rafraîchissement du sujet ouvert met à jour ce
marqueur sans augmenter les vues. Sans changement, il ne réécrit pas la carrière. La publication de sa propre
réponse la marque lue ; la réponse suivante d’un personnage réactive le repère.

Les anciennes contributions sans identifiant reçoivent un identifiant stable
lors de leur préparation. Texte, auteur et ordre sont conservés. Les nouveaux
messages initiaux utilisent leurs identifiants éditoriaux habituels. Les accès
aux forums et les conditions de lecture d'enquête restent vérifiés par l'API.

## Direction visuelle

Les dix-huit personnages et le compte client temporaire disposent chacun d'un
avatar. Leurs portraits reprennent la direction du fond orbital : anime SF des
années 1990, contours encrés, ombres mates, grain discret et palette prune,
olive, menthe et corail. Les anciens portraits de k0rvid, miette et sable sont
conservés comme ressources historiques ; leurs nouvelles versions gardent leurs
traits distinctifs.

Les avatars sont des illustrations de profil choisies par les personnages,
pas des preuves de leur apparence réelle dans le récit. Les groupes et les
pseudos inconnus conservent un monogramme.

| Contexte | Taille affichée |
|---|---:|
| Auteur d'un message de forum en fenêtre large | 200 × 200 px |
| Fiche de profil | 200 × 200 px |
| Auteur d'un message de forum en fenêtre compacte | 56 × 56 px |
| Listes de sujets | 40 ou 44 px |
| Dernier auteur dans une liste large | 28 px |
| Messageries | Miniatures adaptées au contexte, avec masque circulaire |

Les trois bannières sont des scènes distinctes avec chacune un personnage
féminin adulte : atelier radio sur BreachBoard, cockpit et relais sur Exployt,
galerie d'observation sur XSX. Titres et profil connecté sont superposés en
interface ; le personnage reste visible et le nom du compte ouvre sa fiche.

Les PNG originaux ne sont pas retouchés par un script. Les paramètres d'import
Godot limitent les textures des avatars à 200 pixels et celles des bannières à
2048 pixels, sans modifier les sources. Les manifestes des répertoires
`game/assets/avatars/` et `game/assets/forums/` consignent les prompts exacts,
références, dimensions, mode de génération et empreintes des ressources livrées.

## Contrôles

- Tests moteur : lecture, reprise, nouveau message à la même minute, absence
  d'écriture répétée et conservation des contributions du joueur.
- `game/tests/test_forum_community.gd` : présence des portraits et bannières,
  changement de profil, monogramme de secours, tailles affichées de 200 pixels,
  catégories, tri, non lus, brouillons et format compact.
- Les tests sociaux existants conservent les contrôles de citations, sujets
  verrouillés, brouillons, navigation et disposition des messageries.
- Les vues 34–35 et 72–78 de `scripts/preview_ui.py` permettent d'inspecter les
  forums, les fiches et les trois bannières. Ce sont des aperçus tirés de la
  géométrie Godot ; ils ne remplacent pas un essai graphique natif.

## Résultat de la vérification du 15 novembre 2026

- 462 tests moteur réussis, dont les marqueurs de lecture et les anciennes
  contributions sans identifiant.
- 35/35 contrôles complets de parcours et de client Godot réussis.
- 59 assertions dédiées aux forums et avatars réussies après les dernières
  retouches de disposition.
- Neuf aperçus de composition produits ; index compact, portraits de profil et
  trois bannières inspectés. Le recadrage des textures d’atlas est reproduit par
  l’outil d’aperçu.
- Fichiers, empreintes et paramètres d’import des 19 avatars et 3 bannières
  vérifiés.
- Aucun `SCRIPT ERROR:` ou `ERROR:` dans le contrôle complet. Un avertissement
  de quatre objets non libérés reste présent à la fermeture d’un processus
  Godot. Pas de partie avec un testeur ni de validation graphique native.


Madame_TLS utilise désormais `madame-tls-orbital-v2.png` : portrait blond aux
yeux bleus et boucles triangulaires roses, inspiré de la référence illustrée
fournie par l’utilisateur. Source carrée plein cadre, sans cercle dessiné ;
import et affichage large 200 × 200, miniatures adaptées aux autres vues.
L’ancienne version est conservée. Le prompt imagegen intégré et les empreintes
figurent dans le manifeste des avatars.
