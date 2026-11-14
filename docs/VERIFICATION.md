# Vérification - révision du réalisme

État du 11 novembre 2026. Les limites sont décrites dans [REALISME.md](REALISME.md).

- **197 tests Python réussis** : moteur, API, sauvegardes, authentification,
  déploiement, shells, cryptographie des empreintes, fichiers, temps et réactions.
- **12 parcours de réussite**, **6 défaites** et **42 sauvegardes/reprises**.
- Parcours par les commandes des outils ; aucune injection d'identifiants ni
  d'objectif accompli dans les parcours de référence.
- Deux variantes par mission : transports SCP/SMB, cmd/PowerShell et récupération
  documentaire par SMB/rclone selon le contrat.
- **816 contrôles de rejeu Godot** : commandes saisies dans les champs réels,
  validation par Entrée, bonne console, secrets masqués, contextes, débriefings et reprise.
- **60 contrôles du bureau**, **34 de vie sociale** et **6 des formulaires/shells**.
- Suites distinctes des clics/bordures et du clavier, de la sélection, du collage
  et de la complétion du terminal.
- MD4 vérifié sur quatre vecteurs RFC 1320 ; NTOWF vérifié sur le vecteur Microsoft.
- Dictionnaires, potfile, épuisement et fichier de hash invalide vérifiés.
- Diversité des réactions contrôlée sur 64 graines ; mémoire et RNG conservés au
  rechargement ; signalements répétés puis réaction du défenseur vérifiés.
- Horaires des contacts et campagnes, filtrage des messages, capture de mots de
  passe désactivée, SMTP indisponible et attente qui avance la mission vérifiés.
- Authentification sans secret explicite, mot de passe trouvé par une autre voie,
  rotation pendant une commande en attente et isolement des droits vérifiés.
- Règlement actualisé dans l'interface et fenêtres de console recréées à la reprise.
- Compilation Python et `git diff --check`.

```bash
backend/.venv/bin/python -m pytest -q backend/tests
python3 scripts/check_ui.py
python3 scripts/preview_ui.py
```

`check_ui.py` construit le rapport `build/validation/qualification.json` et le
corpus `ui-replays.json` dans des carrières temporaires avant les suites Godot.
Le validateur simple reste disponible :

```bash
backend/.venv/bin/python backend/validation.py build/validation/scenarios.json
```

Les graines des réussites de référence sont fixées pour rendre les régressions
reproductibles et sont inscrites dans le rapport. Les tests probabilistes ne
présentent pas ces réussites comme un taux de réussite universel.

Le transport du rejeu fournit les réponses réelles capturées de l'API à Godot.
Il valide le client et son protocole sans sockets, mais ne remplace pas un test
réseau de l'application complète. Les commandes ne sont pas rejouées sur des
exécutables offensifs ni sur le système de l'utilisateur.

Les aperçus SVG/PNG proviennent des positions et styles de la scène Godot. Ils ne
sont pas des captures GPU. L'affichage réel, le presse-papiers système, les paquets
autonomes et Steam restent non validés dans cet environnement.

Révision solo Red Team : tests de non-arrestation après exposition, absence de
pression répétée des mêmes alertes, paiement de l'offre urgente, rétablissement
des accès et comptes après sauvegarde, absence de confinement répété et reprise
d'un ancien isolement. Les échéances des contrats restent actives.

Protections : origine des règles réseau et isolation des consoles, persistance,
blocage EDR répétable sans effet de compromission, mode audit, lecture des indices,
rejet d'une règle incohérente et absence de fuite de version sur port filtré.
Communauté : litige et réponse thématique conservés après reprise, événements sans
doublon ; navigation Godot sur les trois nouveaux fils issus du contenu réel.
La graine de référence Varenne est désormais 2 : l'ajout d'un service modifie le
flux de bruit partagé. Les parcours qualifiés restent des cas de réussite choisis,
complétés par les tests de diversité des décisions humaines.

Révision des consoles : invite Impacket/API isolée par console, mot de passe vide
ou avec espaces/@/:, refus avant demande de secret, annulation et sauvegarde
d'une invite. Vérification du retour cmd/PowerShell/Kali et de la restauration du
contexte après coupure. Godot contrôle l'absence de secret dans l'historique et les
sorties, le collage sans suppression d'espaces et les invites sans symbole Kali
sur Windows ou pendant l'authentification.

Menu et sauvegardes : huit tests moteur dédiés couvrent les emplacements et la
récupération. Treize contrôles Godot couvrent le menu, les métadonnées, les
confirmations et le retour au bureau. Les six suites antérieures restent actives.
Les aperçus incluent l'accueil, la création de carrière et le gestionnaire de slots.

Finitions du menu : disposition compacte en 1280 × 720, défilement de secours,
retour clavier par Échap, focus initial et actions adaptées à l'état du slot.
Un emplacement corrompu reste supprimable mais le bouton Charger est désactivé.
Les aperçus incluent aussi le menu et les sauvegardes en 720p.

Terminal : saisie repliée, insertion au début d'une longue commande et conservation
sur rafraîchissement ; opérations de fichiers Linux/cmd/PowerShell, droits simples,
partage des fichiers entre consoles, suppression persistante et journal des mutations.

Prélude Chordly : huit exercices rejoués par l’API, puis le dossier Ravelle complet,
avec invitation au forum uniquement après réussite. Les anciennes carrières
conservent leur accès. Les contrôles sociaux couvrent aussi les brouillons par
contact, les accusés d’envoi et la conservation des pages entre onglets.


Chapitre 08 : recommandation et conversation privées avant acceptation,
absence d’annonce publique, preuves insuffisantes refusées, ancienne IP refusée,
compte SSH limité, refus du partage avec le mauvais compte, archive ancienne
refusée, sauvegarde/reprise puis transfert récent, altération refusée et règlement
idempotent. Le rejeu du dossier remet les observations à zéro.
Les filtres sont vérifiés sur les correspondances, absence de résultat, erreurs,
pipes, redirections, comptage, empreinte et persistance des fichiers.


Acte I complet : deux parcours du prélude aux dix chapitres, 18 dossiers par
parcours, 14 reprises chacun, huit petits contrats par parcours, choix du litige,
invitation reçue puis acceptée et accès Tor au forum suivant. Le rapport est
`build/validation/act1-qualification.json`. **283 contrôles Godot supplémentaires**
rejouent les commandes des nouveaux chapitres, dont les secrets MySQL/SSH et les
contextes Linux/Windows. Les MP, leur bouton d’acceptation et le suivi 10 chapitres
sont couverts par les contrôles sociaux. Les 816 contrôles historiques restent actifs.

Tests négatifs : paramètre non injectable, colonne ou table interdite, export
incomplet, SQL sans lecture réelle des tables, accès au système hôte via SQL refusé,
session web absente, propriétaire contrôlé, mauvais offset de service, permissions
Linux, compte SQL limité, traversée de partage ou d’archive et paiement secondaire
unique. Ces contrôles n’émulent pas toute l’implémentation des outils réels.
