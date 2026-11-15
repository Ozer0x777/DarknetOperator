# Darknet Operator

Jeu solo pour PC : bureau natif inspiré de Kali/Xfce, terminal, contrats,
progression et rapport des détections sur les cibles. Version de développement **0.6.1-dev.1**.

Le projet RedVsBlue reste indépendant dans son propre dossier.

## Jouer depuis les sources

Prérequis : **Godot 4 standard**, Python 3 et les dépendances du moteur.
L'environnement Python est déjà préparé sur cette machine.

```bash
cd DarknetOperator
./run.sh
```

Le lanceur démarre le moteur sur un port local libre, attend qu'il soit prêt,
ouvre le bureau Godot, puis ferme ses processus à la sortie du jeu. Pour ouvrir
le projet dans l'éditeur : `./run.sh --editor`.

Installation sur une autre machine :

```bash
python3 -m venv backend/.venv
backend/.venv/bin/python -m pip install -r backend/requirements.txt
```

Sous Windows, utiliser `backend\.venv\Scripts\python.exe` pour les commandes
Python de l'environnement, puis `python scripts/launch.py` pour lancer le jeu.

## Contenu jouable

- Bureau Kali/Xfce : panneau compact, quatre espaces de travail, barre des tâches,
  menu de recherche, fenêtres déplaçables, réduction, maximisation et restauration.
- Douze applications : terminal, trois messageries, navigateur de forums, réseau,
  gestionnaire de fichiers, boutique, portefeuille matériel ColdVault, outils, rapport et paramètres.
- Chordly (présentation Discord), Telegrid (présentation Telegram) et Sessyon
  (présentation Session) : conversations triées par activité, recherche avec
  navigation des résultats, messages, rédaction multiligne, non-lus et brouillons locaux persistants.
- Forums BreachBoard, Exployt et XSX : navigation, catégories, sujets, profils,
  citations et réponses persistantes. Accès avancés selon le palier et la route.
- Acte I : exercices privés, dix chapitres et contrats facultatifs ; acte II : dix missions et six dossiers facultatifs ; acte III : douze missions Lenoir/Aster.
- Profil sauvegardé, argent, réputation, achats, GPU, listes de mots et passages
  de palier par contrat. Sauvegarde et reprise de la mission en cours.
- Routes FreeShield, NullVad, Tor et relais SSH ; exposition de la route sans arrestation automatique.
- Sécurité des cibles : confinement temporaire, rétablissement des comptes et délai compensé ; aucun rôle Blue Team jouable.
- Exfiltration, sauvegardes et chiffrement représentés dans l'état du monde.
- Débriefing avec historique, alertes, événements et déroulement du traçage.

Les premiers exercices arrivent dans Chordly ; BreachBoard se débloque au fil du prélude. Le tutoriel se poursuit sur BreachBoard. Les messages arrivent dans la messagerie du
client ; les objectifs et la route sont dans le centre d’opération **Outils**.
Les actions se pilotent depuis les consoles. **Outils** est désormais un catalogue,
pas un panneau de boutons d'attaque. GoPhish possède sa propre interface web,
reproduite en complément de son API en ligne de commande.
**F11** change le mode d'affichage ; **Ctrl+Alt+T** ouvre le terminal ; les flèches
haut et bas parcourent l'historique. **Super+E** ouvre les fichiers, **Super+W** le
navigateur, **Super+D** affiche le bureau, **Alt+Tab** change de fenêtre et
**Ctrl+Alt+←/→** change d'espace de travail.

## Voir les interfaces

La [galerie locale](build/ui-previews/index.html) présente les vues de composition :
bureau, menu, trois messageries, index et sujets de forum, terminal, ainsi que
les dispositions compactes de 600 px et la rédaction multiligne. Elles sont
reconstruites depuis la géométrie de la scène Godot et ne sont pas des captures GPU.

Pour les régénérer : `python3 scripts/preview_ui.py`. Les SVG sont autonomes ;
la conversion PNG utilise `rsvg-convert` lorsqu'il est installé. Les ressources
visuelles et leurs licences sont décrites dans [game/assets/CREDITS.md](game/assets/CREDITS.md).

## Plusieurs consoles et découverte des outils

Chaque clic sur le lanceur Terminal, **Ctrl+Alt+T** ou **Ctrl+Shift+N** dans une
console ouvre une nouvelle fenêtre. Le menu **Fichier → Nouvelle fenêtre** fait
la même chose. Historique, sortie, répertoire, variables, connexion distante et
invite de mot de passe sont indépendants ; le système de fichiers local est partagé.
Les commandes de base et l'inventaire sont utilisables avant d'accepter un contrat.

```bash
ls /usr/bin
which gophish
gophish --help
```

GoPhish :

```bash
# Console 1 : laisser le serveur au premier plan.
gophish --config /opt/gophish/config.json
# Console 2 : guide du laboratoire et API.
cat ~/gophish/README.txt
# Interface web du véritable type de logiciel, reproduite dans le navigateur du jeu.
xdg-open https://127.0.0.1:3333
cat ~/gophish/admin.txt
```

Le profil de laboratoire contient des ressources et un compte déjà configurés.
Ils sont propres au jeu : ce ne sont pas les identifiants par défaut de GoPhish.
**Ctrl+C** interrompt le processus de la console courante ; **Ctrl+Shift+C** copie
la sélection. Fermer une console interrompt ses actions en attente et son serveur.

## Terminal

`help` et `help outil` décrivent la syntaxe actuellement reconnue. Les commandes
agissent sur les hôtes, les sessions et les fichiers virtuels du jeu. Les options
non implémentées produisent une erreur explicite.

La reproduction complète de chaque outil réel n'est **pas terminée**. Le périmètre
exact et les limites sont dans [docs/COMMANDES.md](docs/COMMANDES.md).

## Sauvegarde

Sous Linux : `~/.local/share/RedTeamSimulator/career.json`.
Sous Windows : `%LOCALAPPDATA%/RedTeamSimulator/career.json`.
Les écritures sont atomiques, avec une copie précédente `.previous`.
`REDTEAM_SAVE_DIR` permet de choisir un autre dossier (son ancien nom,
`RVB_SAVE_DIR`, reste accepté avec un avertissement). Les tests utilisent des
sauvegardes temporaires, séparées de celles du joueur.

## Vérifier

```bash
backend/.venv/bin/python -m pytest -q backend/tests
python3 scripts/check_ui.py
```

Voir [docs/VERIFICATION.md](docs/VERIFICATION.md) pour les résultats et leurs limites.

## Architecture et distribution

- `game/` : interface Godot, GDScript typé, scènes et profils d'export.
- `backend/` : moteur Python, données JSON et API locale.
- `scripts/` : lancement et construction du paquet autonome.
- `packaging/` : dépendances de construction et notice du paquet.

L'architecture retenue conserve le moteur Python testé et utilise Godot pour le
bureau et la distribution PC. Le paquet prévoit un moteur autonome : le joueur
n'aura pas à installer Python. La construction de ce paquet n'a pas encore pu
être validée ici ; voir [docs/STEAM.md](docs/STEAM.md).

Le prototype web a été retiré : le jeu se lance uniquement avec `./run.sh`.
Un verrou empêche deux moteurs de modifier simultanément le même dossier de sauvegarde.

Le suivi du plan original est dans [docs/ROADMAP.md](docs/ROADMAP.md).

### Missions et communautés

Douze parcours de campagne et six défaites sont vérifiés par les commandes via
l’API, avec 42 sauvegardes/reprises. Chaque environnement possède son briefing, son réseau
et ses comptes. Les forums et messageries disposent d’une activité écrite persistante.
Voir [le bilan de réalisme et ses limites](docs/REALISME.md).

Validation reproductible, dans une carrière temporaire :

```bash
backend/.venv/bin/python backend/validation.py build/validation/scenarios.json
```

La qualification étendue se lance avec `python3 scripts/check_ui.py` : deux parcours
par mission, six défaites et 42 sauvegardes/reprises, puis rejeu dans les contrôles
Godot. Hors tutoriel, les réactions des victimes varient selon le contexte et leur
historique ; reprendre une sauvegarde conserve leur état aléatoire.

Les cinq missions après le tutoriel disposent désormais de règles réseau par
origine, de politiques EDR explicites et d'archives du support à recouper.
Les forums incluent litiges, affiliation et conséquences d'incident ; le rapport
sépare les effets vérifiés des affirmations. Les limites et la progression solo
Red Team → Blue Team → multijoueur sont décrites dans `docs/REALISME.md` et
`docs/ROADMAP.md`.

Guide avec spoilers : [scénarios de A à Z et cheat sheet](docs/GUIDE_COMPLET_SCENARIOS.md).
Il inclut les consoles, commandes, conditions de victoire et règlements vérifiés.

Le lancement natif ouvre désormais un menu d'accueil. F5 sauvegarde depuis le
bureau ; les emplacements se gèrent via Sauvegardes / Charger au menu.
Voir [SAUVEGARDES.md](docs/SAUVEGARDES.md) et les
[propositions de gameplay](docs/IDEES_GAMEPLAY.md).

Identité d'accueil : **Darknet Operator**, logo et illustration dans
`game/assets/branding/`. Le dossier du projet et les chemins de sauvegarde
conservent leur nom technique pour la compatibilité des profils existants.

## Acte I - Darknet Operator

Dix chapitres, huit petits contrats et invitation en MP : [guide et solutions](docs/ACTE_I.md).
Sauvegardes anciennes compatibles ; durée cible de 4 à 6 h non mesurée en tests joueurs.


## Archive Linux et solution complète

Une distribution portable de développement pour Linux x86_64 peut être assemblée
avec `backend/.venv/bin/python scripts/build_portable_linux.py`. Elle contient
Godot, Python, les bibliothèques, le jeu et une solution HTML complète.
Extraire l’archive puis lancer `./Jouer.sh`. `./Verifier.sh` lance les vérifications
hors réseau sur des profils temporaires. Voir [PAQUET_LINUX.md](docs/PAQUET_LINUX.md)
pour les résultats et la vérification graphique restant à effectuer.

Révision 0.4.1 : [réputation locale, accès progressifs et portefeuille matériel](docs/PORTEFEUILLE_ET_ACCES.md). Les fonds sont dans ColdVault, hors des forums ; les achats payants demandent une confirmation sur l’appareil simulé.

Son : trois compositions originales Dreamwave/Retrowave, Chillwave/Vaporwave et Synthwave/Cyberpunk, douze effets, volumes séparés et mode muet dans Paramètres. Voir [SON_ET_MUSIQUE.md](docs/SON_ET_MUSIQUE.md).

La progression, les conséquences et les achats de la version 0.4.4 sont décrits
dans [PARCOURS_ET_ECONOMIE.md](docs/PARCOURS_ET_ECONOMIE.md).

Revue des débuts et des notifications :
[REVUE_PREMIERS_PAS.md](docs/REVUE_PREMIERS_PAS.md) (0.4.5).

Qualité des missions, variantes et reprises sensibles :
[QUALITE_MISSIONS_ET_REPRISES.md](docs/QUALITE_MISSIONS_ET_REPRISES.md) (0.4.6).

Le choix **Démo** à la création réunit trois exercices et le dossier ouvert
**Le contretemps**. La fin propose de poursuivre la campagne sur la même sauvegarde.
Le dossier reste facultatif dans la campagne, après Une porte oubliée. Ses choix
modifient les relations et une proposition ultérieure ; aucun achat requis.
Voir [DEMO_ET_CONTRETEMPS.md](docs/DEMO_ET_CONTRETEMPS.md).

Acte I : consignes graduées, aide par phase et réactions persistantes des contacts.
Le bilan et les limites sont dans [ACTE_I_APPRENTISSAGE.md](docs/ACTE_I_APPRENTISSAGE.md).

L’acte II est intégré : dix dossiers, six contrats facultatifs et quatre nouveaux
contacts sur Telegrid après la recommandation. Voir [ACTE_II_GUIDE.md](docs/ACTE_II_GUIDE.md)
et [ACTE_II_COUVERTURE.md](docs/ACTE_II_COUVERTURE.md) pour le périmètre réellement simulé.

La progression 0.5.1 réserve Hashcat, Impacket et l’exploitation binaire à la suite :
[acte I actuel et migration](docs/ACTE_I_ACTUEL.md). Sept exercices préparent
Ravelle ; les anciennes missions en cours gardent leur contenu et leur prime.

La [passe de finition 0.5.2](docs/FINITION_ACTE_I.md) précise les corrections de parcours, de budget et de messageries ainsi que les limites de validation.

Le lecteur audio et la [playlist par chapitres](docs/SON_ET_MUSIQUE.md) continuent entre les étapes et missions. L’album YouTube demandé attend son fichier source local ; il n’est pas inclus dans l’archive.


## Branches et releases

Le dépôt est privé. `main` correspond à la version publiée et vérifiée ; `dev`
porte la prochaine version de développement. La release `v0.6.0` vise `main` ;
la préversion `v0.6.1-dev.1` vise `dev`. Chaque archive Linux dispose d’une
empreinte SHA-256. Les sources restent disponibles sur les deux branches.

Le paquet Linux portable contient Python, Godot et les bibliothèques nécessaires.
Après extraction, lancer `./Jouer.sh` ; `./Verifier.sh` exécute les parcours de
vérification hors réseau. Les résultats et limites de la distribution figurent
dans [PAQUET_LINUX.md](docs/PAQUET_LINUX.md). Aucun paquet Windows n’est fourni
pour cette release.
