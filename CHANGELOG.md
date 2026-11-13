# Journal des changements

## Non publié — corrections de revue

- Tutoriel : consignes GoPhish complètes dans Chordly ; dossier Ravelle avec domaine, DNS simulé (`host`) et IP publique.
- Fin de mission : l’état final arrive toujours au client (tampon temps réel agrandi, relecture HTTP en secours) ; la boucle de jeu survit à une erreur ponctuelle.
- Sauvegardes : archive avant nouvelle partie pour tout contenu du joueur, trois autosauvegardes toujours différentes, écriture UTF-8, une seule écriture par point de sauvegarde, plus d’écriture quand rien ne change.
- Missions : le poste Kali suit l’opérateur d’un contrat au suivant et après un redémarrage ; preuves, scans et réactions de la cible restent propres à leur mission ; un achat s’applique à la mission en cours.
- Terminal : variables remplacées avant tous les outils, texte entre crochets conservé, `exit` local sans effet sur la console, `mysql … > fichier`, `export VAR=~/…`, historique des consoles restauré à la reprise, mot de passe masqué par des étoiles.
- Bureau : menu Applications cliquable au-dessus des fenêtres, Échap et clavier selon le focus, fenêtre réduite non active, manette sans effet sur l’interface, musique en pause conservée.
- Forum et messagerie : plus de reconstruction ni de vue comptée à chaque sondage, lecture marquée au clic, onglets verrouillés ignorés à la fermeture.
- Moteur : une seule règle de joignabilité (machine isolée ou chiffrée refusée par tous les outils), droits de lecture Windows respectés, fin de mission en un seul endroit, règles de visibilité et mots-clés du dialogue sortis de l’API.
- Aucun mot de passe n’est cassé sans correspondance dans une liste de mots.
- Retrait des restes de l’ancien jeu à deux équipes : prototype web, scénario `mvp_demo`, score, capacités de défense jouables, joueurs à jeton, routes `/api/scenarios`, `/api/games/{id}/action` et suppression d’une partie ; une partie est toujours un contrat. La variable `RVB_SAVE_DIR` devient `REDTEAM_SAVE_DIR`.
- `scripts/check_ui.py` lance tous les contrôles et affiche un résumé.

## 0.5.3 — musique continue et lecteur audio

- La réussite d’une étape, le débriefing, la pause de mission et le lancement du dossier suivant ne changent plus de morceau.
- Playlist continue avec fondu de 2,5 secondes, précédent/suivant, pause/reprise, volume et recherche dans le morceau.
- Lecteur accessible par le bouton ♪ et le menu Applications ; fermer sa fenêtre laisse la musique jouer.
- Notification silencieuse du titre, différée pour préserver les messages de mission, avec lien vers le lecteur.
- Retour du menu : reprise du morceau de jeu à sa position, sans recommencer au début.
- Découpage local préparé pour les 12 chapitres demandés : Wake Sequence au menu, les 11 autres dans l’ordre en jeu.
- L’audio YouTube n’a pas pu être téléchargé (DNS bloqué) et n’est pas inclus. La bibliothèque originale sert de repli jusqu’à l’import d’un fichier source.


## 0.5.2 — finition du parcours et des échanges

- Ravelle : titre, indices et débriefing alignés sur les sources publiques ; retrait des anciens conseils administrateur.
- Offres isolées par messagerie ; contact rencontré sur un canal conservé sur ce canal.
- Prochaine piste associée au bon dossier ; petits contrats identifiés et deuxième départ impossible expliqué.
- Reprise active et brouillons préservés pendant l’actualisation des propositions.
- Réserve financière calculée sur le prochain dossier de l’acte II et sa route déjà couverte ; compatibilité de la chaîne historique.
- Première piste de l’acte II visible dans la campagne ; accès direct au contact et titre adapté aux petites fenêtres.
- Présentation persistante de Cendre et réactions de passation pour 0xvanta et nullroute.
- Propositions générées actualisées sans remplacer les notes du joueur.
- Sept tests de régression moteur supplémentaires et neuf contrôles d’interface supplémentaires.


## 0.5.1 — actes mieux séparés

- Nouveau cursus par défaut : sept exercices, transfert utilisateur et Ravelle fondé sur les sources publiques.
- Planning : compte de lecture fourni ; service : permissions et configuration, sans exploitation binaire.
- Hashcat et les techniques avancées sont introduits dans l’acte II ; l’ancien petit contrat NTLM est regroupé avec son équivalent.
- Premier accès communautaire conservé à 740 ₵ et 40 de réputation, sans achat obligatoire.
- Migration des carrières modernes : acquis et choix inchangés, sauvegarde préalable, contrat actif conservé avec son prix.
- Chargement d’un ancien emplacement : adaptation de la suite, original de l’emplacement conservé.
- Qualification de deux cursus actuels complets jusqu’aux deux finales de l’acte II, en plus des archives classiques.

## 0.5.0 — Gagner des accès

- Acte II : dix dossiers séquentiels, six contrats facultatifs et deux voies finales.
- Nouveaux contacts Cendre, Traverse, Iris et Quartz ; réactions et choix de partenaire conservés.
- Inventaire Linux/Windows, paquets, correctifs, droits et logiciels disponibles selon la machine.
- Polkit : artefact virtuel, image vulnérable et image avec correctif rétroporté.
- Tunnel SSH local lié au processus, à sa console et aux règles réseau de son relais.
- Annuaire LDAP : authentification, portée, filtres composés, attributs et erreurs.
- Collecte SharpHound transférée, import vérifié et graphe de relations dans le bureau.
- GetUserSPNs et Hashcat mode 13100 : empreintes RC4-HMAC fictives calculées, dictionnaire et potfile.
- Qualification des deux parcours depuis l’acte I, des contrats secondaires et des reprises.
- Couverture bornée et documentée ; aucune exécution d’attaque sur le système hôte.

## 0.4.8 — apprentissage et continuité de l’acte I

- Briefings gradués : nouvelle notion accompagnée, puis réutilisation et choix autonome.
- Échantillon : les chiffres du rapport ne sont plus donnés dans les consignes.
- Aide par phase pour SMB, SQLite, SQLmap et ticketd, liée aux preuves observées et conservée à la reprise.
- Repères locaux ; ticketd explique protections, symboles, script fourni et session limitée.
- Finale : les points d’entrée restent à retrouver ; rappel détaillé toujours disponible sans pénalité.
- Réactions entre dossiers, reconnaissance de la correction du client et continuité du choix de litige.
- Invitation finale liée à la résolution du litige et à la voie réellement utilisée.
- Sauvegardes en cours : ajout des repères manquants sans écraser les notes du joueur.

## 0.4.7 — dossier ouvert, relations et démo

- Le contretemps : registre HTTP ou partage SMB, archives trompeuses et journal facultatif.
- Choix explicite de signalement ou de remise privée, vérifié sur les preuves courantes.
- Relations conservées, réponses des contacts et prime annoncée de confiance de 30 ₵ sur une offre ultérieure.
- Démo en quatre étapes, conclusion et poursuite sans perdre preuves, primes ni décisions.
- Acte I inchangé à dix chapitres ; nouveau dossier facultatif après Une porte oubliée.
- Parcours API et interface sans affichage ; qualification graphique native toujours à faire.

## 0.4.6 — cohérence des missions et reprises

- Exports et bases nommés librement, colonnes SQL réordonnées et contrôles de contenu conservés.
- Preuves de lecture liées à la version du fichier ; suivi des bases SQLite copiées ou déplacées.
- Variantes curl et cat, redirections adjacentes et diagnostics de saisie.
- Comptes rendus reformulés et aide progressive sur les enquêtes ; choix ambigus non validés.
- Les relectures ne réécrivent pas les décisions de carrière.
- Chargement écrit avant fermeture des sessions ; reprises sensibles qualifiées.

## 0.4.5 — premiers pas et lecture

- Accès Console / Objectif / Indice dans le dossier, sans toucher au brouillon.
- Résumés automatiques courts, indices progressifs et rappel détaillé sur demande.
- Aide isolée par dossier et conservée pendant les reprises.
- Synchronisation silencieuse des archives et notifications regroupées ; clic ciblé.
- Objectifs compacts et suivi du défilement lors du redimensionnement.
- Parcours novice qualifié avec erreurs et reprises ; lancement graphique bloqué
  dans l’environnement de validation, sans mesure d’une heure humaine.

## 0.4.4 — parcours, conséquences et économie

- Accueil privé et prochaine piste contextualisée dans les offres et la campagne.
- Résultats persistants : retour client, recommandation publique de Ravelle et suivi des échecs.
- Prime unique par dossier, y compris les relectures et les bonus.
- Routes déjà payées conservées pour les nouvelles tentatives du même dossier.
- Boutique descriptive, réserve des prochains accès, prix d’amélioration des GPU,
  dictionnaire premium enrichi et licence d’affiliation rééquilibrée.
- Qualification de deux carrières neuves jusqu’au grand compte, premier achat
  confirmé puis restauré ; 214 tests backend et suite d’interface sans échec.
- Les tests automatisés ne remplacent pas une partie manuelle avec affichage réel.

## 0.4.0 — consoles et outils

- Plusieurs consoles, avec contextes, historique et sorties indépendants.
- Commandes disponibles avant mission et découverte via ls /usr/bin / which.
- GoPhish : service console, API curl et interface web propre au logiciel.
- Redirections, variables, substitution $(cat), jobs, kill et Ctrl+C ciblé.
- Suppression du lanceur générique d’abilities en interface graphique.
- 94 tests backend et 60 contrôles d’interface, plus le test de clics/bordures.


## Correctif des clics — 10 novembre 2026

- Les poignées de redimensionnement sont confinées aux bordures, au lieu d'être
  étirées par PanelContainer sur toute la fenêtre.
- Les poignées n'interceptent plus la souris lorsque la fenêtre est maximisée.
- Ajout d'un test de distribution réelle des événements souris : bouton, champ,
  coin de redimensionnement, maximisation et restauration.

## 0.3.0 — 10 novembre 2026 (développement)

- Refonte du bureau selon les conventions Kali/Xfce : panneau, menu, espaces de
  travail, fenêtres, raccourcis, icônes, fond vectoriel et polices embarquées.
- Trois messageries distinctes et navigateur de forums avec listes, sujets,
  profils, citations et publication réelle des réponses dans la sauvegarde.
- Conversations persistantes, réponses contextuelles des PNJ et compteurs non lus.
- Gestionnaire de fichiers avec navigation et lecture des identifiants virtuels.
- Galerie de onze compositions, 53 contrôles d’interface et 86 tests backend.


## 0.2.0 — 10 novembre 2026 (développement)

- Ajout du bureau Godot et de ses neuf applications.
- Ajout du lancement coordonné du client et du moteur local.
- Campagne de six contrats, trois paliers et une offre piège optionnelle.
- Profil persistant, boutique, équipement et règlement des missions.
- Routes réseau, traçage et défenseur automatique.
- Authentification SSH interactive, premières syntaxes authentiques d'outils,
  fichiers virtuels, filtrage des scans et reprise des actions différées.
- Débriefing détaillé et préparation des paquets PC autonomes.
- Migration des tests API vers un transport asynchrone ; 83 tests backend réussis.

Les paquets exportés, la validation graphique interactive et la fidélité complète
aux outils ne sont pas encore validés. Voir docs/ROADMAP.md et docs/VERIFICATION.md.

## Réalisme et vie des communautés — 10 novembre 2026

- Six environnements distincts ; dossiers de mission et passation de maintenance.
- Six parcours par l’API/CLI, avec 18 sauvegardes/reprises et vérification du règlement.
- Collecte GoPhish sans session automatique, délais et réactions écrites des destinataires.
- Ticket créé hors ligne puis utilisé ; SID obtenu séparément, sorties Nmap -sV contextualisées.
- Sessions Windows et privilèges isolés par console ; commandes en attente, interruption ciblée.
- L’isolation ne supprime plus l’état chiffré d’une machine.
- Quinze sujets avec archives, profils, annonces verrouillées et activité différée.
- Groupes de tchat, présences, réponses différées, suivis de mission et non-lus par conversation.
- Indices automatiques réglables ; copie individuelle des commandes du tutoriel.
- Conservation des anciens environnements lors d’une reprise de sauvegarde.

## Compléments du réalisme — 10 novembre 2026

- Retrait des grammaires simplifiées --as ; tests migrés vers les commandes reconnues.
- Déploiement d’artefacts virtuels avec SCP/SMB et contrôle des droits.
- Sessions cmd/PowerShell, retour au parent, fichiers, aide, processus/services et statuts.
- Authentification indépendante de l’origine du secret, invite de mot de passe et rotation vérifiée.
- NTOWF calculé, vrais contenus de fichiers pour le mode dictionnaire, potfile et épuisement.
- Réactions contextuelles variables hors tutoriel, mémoire des sollicitations, délais et escalade.
- Horaires, filtre de messagerie, capture explicite des mots de passe et disponibilité SMTP.
- Attente accélérée qui fait avancer la mission et la défense.
- Deux parcours par contrat, défaites reprises et rejeu Godot ; règlement et consoles restaurés.
- Conversion ciblée des anciennes empreintes du prototype en conservant les environnements.

### Solo Red Team : sécurité des cibles
- Suppression des arrestations automatiques et du piège annulant une réussite.
- Exposition calculée sur de nouvelles alertes, sans pression infinie des anciennes.
- Confinement de six ticks, reprise persistante des comptes et accès, délai compensé.
- Un confinement par hôte ; récupération des isolements des sauvegardes en cours.

### Protections, indices et contexte des incidents
- Politiques EDR audit/blocage configurées sur les cinq missions après le tutoriel.
- Filtrage réseau par origine, Test-NetConnection et observations de scan datées.
- Archives obsolètes et avis de migration à recouper dans le support.
- Trois fils communautaires supplémentaires et réponses thématiques différées.
- Rapport des conséquences vérifiées, sans supposer un paiement de rançon.
- Retrait du dernier échec immédiat d'une mission sur action critique refusée.

### Consoles et authentification
- Invites Password:/SSH/SCP distinctes des invites de shell, disposition Windows sur une ligne.
- Mots de passe vides et espaces collés conservés, secrets absents de l'historique.
- Validation du transport et des options Impacket avant la demande de secret.
- Retour complet au contexte parent après une coupure depuis un shell imbriqué.
- Suppression des invites de chemin en double dans les bannières de connexion.

### Accueil et emplacements de sauvegarde
- Menu avant le bureau : continuer, nouvelle carrière, charger, paramètres et crédits.
- Emplacements manuels, confirmations, trois autosauvegardes et copie avant chargement.
- Vérification d'intégrité, récupération de la copie précédente et sélection d'un slot valide.
- Retour au menu sans abandon, fermeture sauvegardée, F5 et restauration des consoles du bureau.
- Tests API sur carrières temporaires, contrôles Godot et aperçus des nouveaux écrans.

### Direction visuelle de l'accueil
- Palette anthracite/vermillon, titre à deux niveaux et navigation allégée.
- Illustration réseau originale en SVG et carte de reprise de carrière.
- Charte commune aux sauvegardes et à la création de carrière, états de focus clavier.

### Finitions de l'accueil
- Disposition compacte en 720p et défilement de secours pour les petites fenêtres.
- Navigation clavier, annulation par Échap et retour du focus.
- Sélection de sauvegarde conservée au rafraîchissement et actions selon sa validité.

### Saisie et pédagogie
- Saisie terminal repliée sur plusieurs lignes, sans supprimer le début d'une commande.
- Explications du tutoriel : but, arguments, résultats et limites de chaque outil.
- Carnet de cours accessible dans la mission et suggestion de pseudos techniques.
- Opérations de fichiers Linux/cmd/PowerShell partagées et journalisées dans le moteur.
- BreachBoard repositionné comme premier acte dans le plan de campagne longue.

### Identité Darknet Operator
- Logo et illustration nocturne intégrés à l'accueil, avec dégradé de lisibilité.
- Titre de fenêtre et crédits mis à jour ; chemins des profils conservés.
- Sources visuelles conservées dans game/assets/branding et aperçus adaptés au PNG.

## 0.4.1 — Progression et fonds

- Réputation distincte par communauté, attribution unique et migration des anciens profils.
- Boutique et forums contrôlés dans le moteur, l’API et le client ; accès avancés sur progression et recommandation.
- Fonds retirés des en-têtes des forums et application matérielle simulée ColdVault.
- Journal des règlements, achats et frais ; confirmation des achats payants, refus et protection des identifiants rejoués.

### Son et musique
- Trois compositions instrumentales originales et douze effets courts inclus localement.
- Ambiances menu/bureau/mission avec fondu et choix manuel.
- Volumes séparés, mode muet et réglages persistants depuis le menu et le bureau.
