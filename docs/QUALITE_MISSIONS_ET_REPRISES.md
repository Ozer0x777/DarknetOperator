# Missions, terminal et reprises — 0.4.6

## Cohérence entre demande et validation

Le résultat annoncé par le client reste obligatoire. En revanche, les exemples
de chemins ne sont plus une commande secrète à reproduire à l’identique :

- Les exports Pivoine, ticketd, Verre et les deux voies Boreal peuvent porter un
  autre nom dans `~/loot`. Le même fichier doit contenir les données attendues
  et avoir été relu. Pour les tables, l’ordre des lignes et colonnes peut varier ;
  les colonnes, les valeurs et la multiplicité des lignes restent vérifiées.
- L’échantillon et le litige acceptent un nom de base choisi à l’import et un
  ordre différent des valeurs SQL. La base doit bien contenir la pièce fournie,
  pas une table fabriquée avec les seules réponses attendues.
- Copier ou déplacer une base SQLite locale conserve son contenu virtuel ;
  écraser le fichier invalide la base en mémoire. Les observations faites sur
  son contenu auparavant restent datées par une empreinte de source.
- Le partage Nacre accepte une récupération directe du bon document : l’étape
  `ls` n’est plus imposée si le transfert intact et la relecture sont prouvés.

Une lecture est liée au contenu observé. Si un fichier est remplacé après sa
lecture, il faut relire sa nouvelle version ; lire un ancien fichier ne suffit
pas à valider un export qui le remplace. Les anciennes sauvegardes sans empreinte
restent lisibles ; les écritures suivantes invalident leurs marques de lecture.

Les pièces incomplètes, mauvaises versions, exports avec en-têtes HTTP, fausses
bases et références incorrectes restent refusés. Un compte rendu insuffisant
indique les observations manquantes sans dérouler immédiatement toute la solution.

## Commandes et comptes rendus équivalents

Le terminal reste un sous-ensemble simulé des outils, sans lancer de programme
système pour exécuter les commandes du joueur. Les variantes ajoutées comprennent :

- `curl -o fichier`, `--output=fichier`, `--url=...`, `--header=...` et les autres
  options longues de requête déjà prises en charge avec `=` ;
- redirections adjacentes, par exemple `sqlite3 analyse.db<dump.sql` ou
  `echo resultat>fichier`, avec conservation du rôle des guillemets ;
- `cat -n`, `cat -b`, `--number` et `--number-nonblank` ;
- noms de fichiers cités contenant des espaces et exports SQL réordonnés.

Une faute proche d’un nom de commande connu donne une suggestion, jamais une
exécution automatique. Une invite collée avec la commande est signalée. Un pager
interactif non simulé est distingué d’une commande mal orthographiée.

Les comptes rendus acceptent notamment « transmis », « livré », « remis »,
« bilan » ou « constat », les accents, la casse et les tirets typographiques.
Les références du dossier et les observations nécessaires restent obligatoires.
Cela ne constitue pas une compréhension libre de toutes les formulations.

## Difficulté et décisions

L’aide progressive couvre aussi les enquêtes de l’acte I et les petits contrats :
première piste de raisonnement, vérification plus concrète, puis rappel détaillé.
La progression de l’aide est sauvegardée par dossier et étape. Lorsque deux voies
sont possibles, l’aide privilégie celle pour laquelle des observations existent.
Demander simplement l’objectif ne consomme pas un indice.

Une question hésitant entre publication et médiation ne décide plus à la place
du joueur. Une négation de livraison ou de publication ne valide rien. Une seule
décision explicite peut être enregistrée dans une étape exclusive.

Une relecture de mission ne modifie ni la prime, ni la réputation, ni les choix
établis dans la carrière. Pour explorer une autre branche de carrière, il faut
charger explicitement un point antérieur à la décision ; ce chargement remplace
toute la chronologie, y compris les fonds et les conséquences du choix.

## Sauvegardes sensibles

Le chargement valide l’emplacement, conserve le point de récupération et écrit
le profil restauré avant de fermer les sessions et d’annuler les demandes
transitoires. Les anciens identifiants de session et de paiement sont révoqués
avant d’attendre la fermeture des connexions ; une requête tardive ne peut agir
sur le profil restauré. Un échec d’écriture laisse la session et la demande ColdVault
courantes en place, avec une erreur explicite plutôt qu’un arrêt prématuré.

Les reprises vérifiées couvrent :

- une commande différée, exécutée une seule fois après reprise ;
- une session distante PowerShell, ses variables et un serveur GoPhish dans une
  autre console ;
- les états avant et après une décision, sans mélange des branches publique et
  privée ;
- une demande ColdVault non signée : un chargement réussi annule l’ancienne
  demande et déconnecte l’appareil ; l’ancien identifiant ne peut débiter les fonds.

## Qualification

`backend/tests/test_mission_review.py` couvre les cas positifs et les refus, la
relecture des preuves, les décisions et les erreurs de chargement.
`backend/mission_review_validation.py` termine deux actes I par les mêmes endpoints
que le jeu, avec noms de fichiers, colonnes, syntaxes et formulations alternatifs.
`backend/save_review_validation.py` qualifie les reprises sensibles sur des profils
temporaires préparés, y compris un échec de commit injecté.

Ces parcours automatisent l’API et le terminal du simulateur. Ils ne remplacent
pas une partie graphique manuelle ni un test d’exécution des vrais outils.
