# Distribution portable Linux x86_64

Une distribution de développement peut être assemblée hors ligne avec le binaire
Godot, Python et les dépendances déjà présents. Ce chemin est distinct de l’export
release Godot/PyInstaller décrit dans [STEAM.md](STEAM.md).

## Construire

Prérequis de construction : Linux x86_64, environnement `backend/.venv` préparé,
Godot importé une fois, `ldd`, `ldconfig`, `pandoc` et métadonnées de paquets Arch
pour les notices de cette machine. Le script copie les exécutables et bibliothèques
utilisés ; aucun téléchargement n’est effectué.

```bash
backend/.venv/bin/python scripts/build_portable_linux.py --no-zip
build/portable-linux/DarknetOperator-0.5.3-dev-Linux-x86_64/Verifier.sh
backend/.venv/bin/python scripts/build_portable_linux.py --zip-existing
```

Le constructeur refuse d’écraser un dossier d’assemblage existant. Conserver ou
renommer ce dossier avant une nouvelle construction complète. L’archive et son
SHA-256 sont créés dans `dist/` ; les droits d’exécution Unix sont conservés.

## Contenu et démarrage

`Jouer.sh` emploie le chargeur, Python et Godot du dossier `runtime/` avec leurs
bibliothèques. Il choisit un port local disponible, attend l’API puis ouvre le
menu ; fermer le jeu arrête les processus dont le lanceur est propriétaire.
Il ne lance aucun outil réel d’attaque : ceux du terminal restent simulés.
Le client utilise les scènes et scripts du dossier `game/`, avec les ressources
importées. Le moteur et ses données sont dans `engine/`.

Le paquet ne demande pas d’installer Python ou Godot et ne s’installe pas dans le
système. Il reste destiné à Linux x86_64 avec une session graphique et un pilote
OpenGL compatible. Il embarque des binaires construits pour la machine de
construction ; aucune certification de toutes les distributions ni de Steam Deck
n’est revendiquée.

Les sauvegardes restent dans leur dossier utilisateur habituel. Aucun profil,
cache d’identité, brouillon ou sauvegarde personnelle n’est ajouté au ZIP.
La solution HTML hors ligne réunit le prélude, les actes I et II, la démo et les anciens scénarios ;
les documents d’origine, notices et versions de composants sont aussi présents.

## Validation du 12 novembre 2026

Depuis un dossier temporaire avec un PATH ne contenant ni Python ni Godot :

- Interpréteur, bibliothèques natives et API embarqués exécutés correctement.
- Campagne prototype : douze parcours, six défaites et 42 sauvegardes/reprises.
- Acte I actuel : deux parcours complets sans achat, sept exercices, dix chapitres et sept petits contrats ; archives classiques également vérifiées.
- Moteur : 292 tests réussis, dont migration, aide par phase, réactions et reprise des anciennes missions.
- Acte II : deux parcours complets depuis l’acte I, dix dossiers, six secondaires, deux finales et rechargements.
- Démo : quatre parcours complets, choix persistants et poursuite sur la même sauvegarde.
- Client embarqué sans affichage : audio 45, lecteur 12, menu 13, bureau 62, composition 48,
  flux sociaux 32, portefeuille 11, parcours 18, premiers pas 23, démo 11 et acte II/analyse 13 contrôles.
- Vérifications des relations, des preuves datées et du versement unique de la prime.

Le diagnostic de démarrage HTTP complet est bloqué par l’interdiction des sockets
IPv4 dans l’environnement d’exécution (`Operation not permitted`). L’affichage
X11/Wayland n’est pas accessible non plus. **La session graphique complète et la
connexion réelle client/moteur restent à vérifier hors de cet environnement.**
L’album YouTube demandé n’est pas inclus : sa récupération est bloquée par le DNS. Le lecteur utilise les trois compositions originales ; le découpage local des douze chapitres est préparé dans `scripts/import_chapter_music.py`.

Le paquet comporte `Verifier.sh` et un mode `--headless --smoke-test` pour refaire
ces vérifications sans toucher à la carrière du joueur.
