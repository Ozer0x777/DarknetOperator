# Revue des premiers pas - 0.4.5

## Portée réelle

La session graphique a été tentée : Godot ne peut accéder ni à X11 ni à Wayland
dans cet environnement. Aucun temps de jeu humain de 30–60 minutes n’a donc été
mesuré. La revue porte sur les consignes, les commandes et états réels du moteur,
les contrôles Godot, puis les aperçus géométriques de l’interface.

Le parcours novice couvre les huit exercices et Ravelle : une erreur volontaire
par dossier, deux demandes d’indice, une sauvegarde rechargée avant la reprise,
puis la réussite par les commandes du terminal. Il termine à 740 ₵ et ouvre la
première communauté. Les erreurs et demandes d’aide ne paient rien et ne sautent
aucun objectif.

## Frictions corrigées

| Observation | Correction |
|---|---|
| Retrouver le terminal ou le but impose un détour par les menus/historique. | Barre du dossier dans la conversation : Console, Objectif et Indice. |
| Demander de l’aide pendant la rédaction risque de remplacer le brouillon. | La demande d’indice utilise le dossier actif et laisse le texte et la sélection intacts. |
| Les grandes consignes arrivent automatiquement en un seul bloc. | Résumé automatique court ; indices écrits de plus en plus précis, puis rappel détaillé à la demande. |
| « Indice » ou « rappel détaillé » ne sont pas reconnus comme une demande d’aide. | Ces formulations, « guide complet » et « aide complète » sont traitées immédiatement. |
| Les étapes d’aide pourraient être héritées du dossier précédent. | Les compteurs sont isolés par dossier et étape ; une vraie reprise conserve l’aide déjà demandée. |
| Une nouvelle partie peut recevoir deux accueils similaires. | Le message synthétique ancien n’est plus ajouté aux nouvelles carrières. |
| L’ouverture des archives peut ressembler à une rafale de nouveaux messages. | Première synchronisation silencieuse ; ensuite, regroupement par application et intervalle de huit secondes. |
| Une notification ouvre seulement l’application. | Le clic rejoint la conversation concernée ou les MP du forum, sans lire un autre fil à la place. |
| Un objectif court réserve inutilement une grande zone. | Hauteur adaptée au texte, avec défilement pour les objectifs longs. |
| Réduire la fenêtre peut cacher les dernières réponses. | Suivi du bas lors du redimensionnement si le joueur lisait les derniers messages ; la lecture des anciens reste respectée. |

Sur Ravelle, les trois messages de progression automatiques passent respectivement
de 3 288 à 203, de 2 136 à 216 et de 847 à 188 caractères. Les explications complètes
restent disponibles. Les premiers indices s’appuient seulement sur l’étape déjà
atteinte : ils ne révèlent pas d’identifiant futur. Le bouton Console ouvre un
terminal ; il n’exécute aucune action de mission à la place du joueur.

## Vérification

- `backend/tests/test_first_hour.py` : aide, absence de révélation prématurée,
  sauvegarde/reprise, objectif public et parcours avec erreurs.
- `backend/first_hour_validation.py` : neuf dossiers, neuf erreurs, dix-huit
  indices et neuf sauvegardes rechargées, sans modifier les profils personnels.
- `game/tests/test_first_hour.gd` : petites fenêtres, actions du dossier,
  conservation des brouillons, redimensionnement et notifications.
- Les parcours de campagne existants restent exécutés par `scripts/check_ui.py`.

Les vues 53–55 de la galerie montrent le dossier compact et la notification
regroupée. Ce sont des aperçus de composition, pas des captures du jeu rendu par
le GPU. La fluidité perçue, le confort de lecture pendant une vraie heure et le
volume des sons restent à éprouver dans une session manuelle sur Linux.
