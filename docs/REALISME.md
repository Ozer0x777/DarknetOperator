# Réalisme : corrections et limites vérifiées

État au 10 novembre 2026. Ce fichier décrit ce qui fonctionne dans le monde
simulé et les vérifications qui restent nécessaires. Le jeu utilise des parsers
et un moteur local ; ce n'est pas une machine virtuelle exécutant Kali et Windows.

## Victimes et progression : ce qui a changé

Hors tutoriel, la réponse du destinataire principal n'est plus une issue unique
écrite à l'avance. Le modèle combine la formation du personnage, sa suspicion,
les messages déjà reçus, leur répétition et leur proximité dans le temps. Il peut
soumettre des informations, ignorer le message ou le signaler. Les délais varient
également. Les horaires, le filtre, la disponibilité SMTP et la configuration de
la page interviennent avant cette décision.

Les décisions utilisent l'aléatoire sauvegardé du monde. Une nouvelle partie
reçoit une graine différente ; reprendre la même sauvegarde conserve l'état du
générateur et la mémoire des personnages. Répéter un message augmente la suspicion.
Plusieurs signalements peuvent entraîner une escalade puis une réaction du défenseur.
Le tutoriel garde une réaction stable afin de permettre l'apprentissage.

Les membres des forums et des tchats ont des créneaux de disponibilité partagés
par leur présence affichée et le planificateur des réponses. Une réponse ordinaire
ne part plus pendant une absence annoncée. L'aide pédagogique immédiate reste une
exception explicite. Le bouton « Attendre 5 minutes dans le jeu » avance aussi la
mission et la défense ; il ne suspend pas leurs conséquences.

Le contenu social comprend 15 sujets, leurs archives, des groupes, des suivis de
mission et 23 événements d'ambiance écrits. Il se conserve sans rejouer les mêmes
messages à chaque chargement. Les conversations et les décisions restent des
modèles finis, pas une simulation complète de la psychologie humaine.

## Terminal, outils et droits

- **Anciennes commandes retirées.** `gophish cible`, `psexec cible --as compte`
  et les autres grammaires du prototype ne sont plus exécutables. Les véritables
  alias PowerShell (`ls`, `cat`, `cd`, etc.) restent disponibles dans PowerShell.
- **Déploiement visible.** Les artefacts Windows du laboratoire se trouvent dans
  `~/tools`. SCP demande une authentification ; SMB contrôle l'identité et les
  droits du partage administratif. Un outil absent ou un fichier non reconnu ne
  devient pas automatiquement un programme fonctionnel. `cat ~/tools/README.txt`
  explique les transports pris en charge. Ces artefacts sont des marqueurs virtuels,
  jamais des exécutables lancés sur l'ordinateur du joueur.
- **Sessions distinctes.** Kali, cmd et PowerShell ont leurs invites et leurs
  commandes. Les retours imbriqués cmd/PowerShell/Kali, environnements, répertoires
  et droits sont conservés par console et après sauvegarde.
- **PowerShell 5.1.** Le périmètre comprend les requêtes de fichiers, emplacements,
  copies, existence d'un chemin, processus/services, aide et variables d'environnement.
  Les options non couvertes provoquent une erreur ; elles ne sont pas ignorées.
- **Authentification cohérente.** Un mot de passe correctement trouvé peut être
  utilisé même s'il ne venait pas du phishing. Une identité sans secret fourni
  déclenche une invite. Une rotation ou une désactivation est vérifiée à la
  résolution ; une commande en attente ne récupère pas silencieusement un autre
  secret ajouté au butin. Une session ordinaire n'hérite pas des droits SYSTEM
  d'une autre console.
- **Statuts de sortie.** L'API distingue une commande terminée d'un traitement
  en attente. Le terminal expose `$?`, `%ERRORLEVEL%` et `$LASTEXITCODE` dans leur
  shell respectif. Les codes couverts incluent la commande absente, les erreurs
  curl et l'épuisement d'un dictionnaire ; leur état reste propre à la console.
- **Hashcat et fichiers.** Le mode 1000 lit réellement les empreintes et les mots
  du dictionnaire virtuel. Un nom de fichier ne suffit plus à récupérer un secret.
  L'épuisement, `-a 0`, `--show` et le potfile sont représentés. Les empreintes NT
  des comptes fictifs sont calculées avec MD4/UTF-16LE, vérifié par des vecteurs
  RFC et Microsoft. L'exécutable Hashcat, ses pilotes et les performances GPU ne
  sont pas reproduits ; les dictionnaires livrés sont de petits jeux de données.
- **Transferts documentaires.** Rclone copie le répertoire demandé, pas tous les
  fichiers de la machine. SMB permet un téléchargement ciblé. Copier les outils
  dans `C:\Tools` ne les transforme pas en documents métier pour le règlement.
- **Anciennes sauvegardes.** Les réseaux et comptes sont conservés. Les empreintes
  artificielles identifiables du prototype sont converties avec leurs fichiers de
  butin ; une compatibilité ciblée accepte les anciennes valeurs déjà observées.

## GoPhish, reconnaissance et défense

Une collecte ne crée pas une session distante ni un processus Word sur la cible.
La capture d'un mot de passe dépend maintenant des options de la landing page.
Le formulaire GoPhish possède « Capture Submitted Data » et « Capture Passwords ».
Le second choix dépend du premier. Une page sans capture de mots de passe ne
fournit pas magiquement celui du destinataire.

Un serveur arrêté, un profil SMTP indisponible, un message retenu par le filtre,
un destinataire absent et une absence de soumission ont des résultats distincts.
La campagne conserve ses événements et continue après le retour de curl.

Nmap distingue les ports ouverts, fermés et filtrés dans le périmètre modélisé.
`-Pn`, les temporisations couvertes et `-sV` ont des conséquences. Un sous-réseau
malformé est rejeté ; un scan limité ne révèle plus tous les autres services via
la commande d'aide `hosts`. Le SID du domaine nécessite une interrogation séparée.

Un ticket est créé hors ligne puis utilisé avec un nom de service. Le domaine,
le secret de signature représenté dans le modèle et l'expiration sont vérifiés.
La création seule ne produit pas un accès distant. Les journaux ne déduisent plus
Kerberos d'un simple mot de passe en clair et ne présentent plus une seule longueur
de clé comme une preuve certaine de vol de hash. L'isolation n'annule pas le
chiffrement déjà effectué.

Le modèle des sauvegardes représente les instantanés locaux du scénario.
`vssadmin delete shadows` ne constitue pas une simulation de destruction de
sauvegardes hors site, immuables ou gérées par un autre produit.

## Qualification des six missions

| Contrat | Entreprise et réseau | Résultat métier contrôlé |
|---|---|---|
| Tutoriel | Ravelle, 10.20.0.0/24 | Accès administrateur au serveur |
| Morel | Morel Expertise, 10.31.4.0/24 | Transfert du document demandé |
| Rival | Atelier Dumas, 10.42.8.0/24 | Mot de passe en clair retrouvé |
| Varenne | Varenne Logistique, 10.53.12.0/24 | Authentification avec le ticket créé |
| Affiliation | Imprimerie Belin, 10.64.16.0/24 | Seuil de chiffrement et règlement conditionnel |
| Grand compte | Valmont, laboratoire administratif, 10.75.20.0/24 | Archive transférée, instantanés supprimés et seuil de chiffrement |

La qualification comprend **12 parcours de réussite**, **6 défaites après reprise**
et **42 sauvegardes/reprises**. Les variantes portent notamment sur SCP/SMB,
cmd/PowerShell et les téléchargements SMB/rclone. Elles ne constituent pas douze
techniques d'intrusion entièrement différentes.

Les graines des parcours de référence sont fixées et inscrites dans le rapport
pour reproduire les tests. Des tests distincts parcourent 64 graines pour vérifier
la diversité des réactions et contrôlent l'effet de la répétition. Une réussite
sur une graine ne prouve pas que toute tentative doit réussir.

Le corpus des réponses API est aussi rejoué dans les vrais contrôles Godot :
focus, touche Entrée, envoi de la commande et de son identifiant de console,
saisie secrète, contexte de shell, débriefing et reprise des fenêtres. C'est un
rejeu automatique headless, pas une session humaine sur un affichage graphique.
Il a corrigé la restauration des fenêtres et l'actualisation du règlement affiché.

```bash
backend/.venv/bin/python -m pytest -q backend/tests
python3 scripts/check_ui.py
```

Rapports : `build/validation/qualification.json` et `ui-replays.json`.
La qualification ne lit ni ne modifie la carrière réelle du joueur.

## Références vérifiées et portée de la comparaison

Le périmètre est rapproché de sources primaires :
[PowerShell 5.1](https://learn.microsoft.com/en-us/powershell/module/microsoft.powershell.management/get-childitem?view=powershell-5.1),
[SCP/OpenSSH](https://man.openbsd.org/scp),
[SMB/Samba](https://www.samba.org/samba/docs/current/man-html/smbclient.1.html),
[Impacket 0.12.0](https://github.com/fortra/impacket/blob/impacket_0_12_0/examples/ticketer.py),
[capture GoPhish](https://docs.getgophish.com/user-guide/documentation/landing-pages),
[Nmap](https://nmap.org/book/man-version-detection.html),
[RFC 1320](https://www.rfc-editor.org/rfc/rfc1320.txt),
[NTOWF Microsoft](https://learn.microsoft.com/en-us/openspecs/windows_protocols/ms-nlmp/706eed15-d153-4d58-9399-7bd9ecc4b3ab).

Les interfaces sont inspirées des conventions de MyBB, Discord, Telegram et
Session. Leurs données et interactions ont été enrichies ; leur fidélité visuelle
pixel par pixel n'est pas établie.

## Ce qui reste réellement à valider ou à étendre

- Comparaison des sorties avec des exécutables et versions figés dans un
  laboratoire contrôlé : les sources et vecteurs vérifiés ne la remplacent pas.
- Session complète sur un affichage réel, presse-papiers système et rendu GPU.
  Le rejeu Godot et les aperçus de géométrie sont des preuves distinctes.
- Options non couvertes, scripts PowerShell généraux, cycle de vie détaillé des
  processus, dépendances d'installation et protocoles AD/Kerberos complets.
- Plus de topologies, chemins d'accès, arcs narratifs et dialogues. Les six réseaux
  actuels représentent de petits périmètres de laboratoire, pas des entreprises entières.
- Enquête réelle et psychologie humaine : le traçage, les horaires et les décisions
  probabilistes restent des mécanismes du jeu, avec des hypothèses écrites.

Les corrections rendent les causes et les conséquences plus cohérentes et les
réponses moins prévisibles. Elles ne transforment pas le jeu en émulation exhaustive
des outils ni en reproduction garantie d'une opération réelle.

## Direction solo Red Team — sécurité des cibles

Cette version propose uniquement le rôle Red Team. La sécurité automatique des
entreprises produit des obstacles scénarisés ; aucun joueur Blue Team n'est requis.
Une alerte forte peut déclencher un confinement de six ticks. Le réseau et les
comptes suspendus par cette réaction sont ensuite rétablis ; une console coupée doit
être reconnectée. Un hôte ne subit cette réaction qu'une fois par mission, et ces six
ticks sont ajoutés au délai du contrat. La récupération survit à la sauvegarde.
Les anciennes missions encore en cours avec un hôte isolé reçoivent également
ce rétablissement. Une partie déjà terminée n'est pas réécrite.

Le traçage compte chaque alerte forte une seule fois. Il expose éventuellement la
route, sans arrestation ni confiscation des gains. L'offre urgente n'annule plus
une réussite vérifiée. Ces choix sont des règles de jeu, pas une description de la
réaction d'une organisation réelle. Les objectifs et le délai restent à respecter :
la réussite n'est pas automatique. Les réactions humaines peuvent encore exiger
une nouvelle tentative de collecte. La qualification couvre des parcours précis,
pas toutes les suites de commandes possibles.

## Protections et enquêtes documentaires

Les cinq missions après le tutoriel déclarent des politiques de protection locale.
LabEndpoint est un produit fictif : aucune fidélité à un EDR commercial n'est
revendiquée. Les actions couvertes sont l'administration distante par PsExec,
la lecture de mémoire par l'action Mimikatz et l'action de chiffrement du jeu.
Les machines de maintenance journalisent ces actions (audit) ; le poste comptabilité
les bloque. Un blocage ne dépend pas d'un tirage au sort.
La politique et le service peuvent être observés dans une session Windows.

Les règles réseau évaluent source, destination et port ; la première règle qui
correspond s'applique, après les blocages globaux. Dans les cinq missions, SMB du
poste comptabilité est filtré depuis operator, mais reste joignable depuis le LAN.
PowerShell `Test-NetConnection nom -Port port` vérifie le service dans le contexte
de sa console. Ce premier modèle ne simule pas des routeurs, NAT, tunnels ou une
pile TCP complète ; les outils de pivot ne sont pas encore reproduits.
Le scan conserve une observation datée avec son origine : un port filtré ne
révèle pas la version cachée dans les données du scénario. L'EDR n'est plus révélé
par l'API Red avant compromission de la machine.

Les archives du support donnent une ancienne adresse .99 ; un avis de migration
récent indique son retrait et l'adresse actuelle. Cette fausse piste est résoluble
par les dates et le recoupement. Les fichiers n'offrent pas un nouveau secret.
Les chemins essentiels des missions restent ouverts ; la comptabilité protégée
est une branche d'investigation facultative.

## Communautés et conséquences d'une rançon

Dix-huit sujets écrits peuplent les forums. Trois nouveaux fils traitent d'un
litige vendeur, des conditions d'affiliation et d'un dossier après chiffrement.
Des mises à jour différées persistent sans se répéter ; réputation, annonce et
preuve sont des notions distinctes. Les contacts ont quelques réponses thématiques
sur les litiges, la protection locale et les conséquences de l'incident.
Ce n'est pas un dialogue libre ni une reproduction exhaustive d'un marché réel.

Le rapport final distingue machines chiffrées, fichiers transférés et instantanés
locaux retirés. Il n'en déduit pas la publication des fichiers, la destruction de
sauvegardes externes, un arrêt total de l'entreprise ou un paiement par la victime.
La rémunération du contrat de jeu ne prouve aucun de ces faits. Une négociation
jouable, les décisions d'assureur et le rétablissement détaillé restent à construire.


## Acte I — novembre 2026

Dix chapitres et huit petits contrats ont des parcours qualifiés, avec deux voies
finales et des décisions persistantes. Les bases synthétiques produisent des
requêtes et exports cohérents ; les droits web, fichiers et tables SQL sont testés.
Les modèles de SQLmap, GDB/checksec et du script ticketd restent des sous-ensembles
déclarés, pas les exécutables réels. Les archives utilisent un conteneur virtuel.
La durée 4–6 h reste à mesurer auprès de joueurs. Voir [ACTE_I.md](ACTE_I.md).
