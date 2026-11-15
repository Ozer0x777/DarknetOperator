# Contrat de fidélité du terminal

La cible est une syntaxe authentique, des sorties liées au monde et des erreurs
cohérentes. Le catalogue ci-dessous décrit la version présente, pas la couverture
complète des exécutables réels. Les identifiants et fichiers sont fictifs.

| Famille | Prise en charge actuelle | Limites |
|---|---|---|
| Shell | whoami, hostname, id, uname -a, ip addr, pwd, ls, cd, cat, exit, which, echo, export, jobs, kill | Sessions séparées, fichiers locaux partagés ; redirections > et >>, variables et $(cat fichier) ; pas un shell Bash/cmd complet |
| Nmap | Cible unique ou /24, -sn, -sV, -sS, -sT, -Pn, -n, -p liste, -T0 à -T5 | -Pn saute la découverte sans ouvrir de route ; -sn ne révèle pas les services ; -p accepte une liste, pas une plage ; ports par défaut limités aux services du scénario ; pas de pile réseau réelle |
| Chisel | Serveur local inverse, client distant, redirection TCP inverse ou SOCKS | Une redirection par client ; processus et dépendances sauvegardés ; [couverture acte III](ACTE_III_COUVERTURE.md) |
| ProxyChains-NG | -f, strict_chain, un SOCKS5 local ; Nmap -sT -Pn -n, curl, Evil-WinRM | TCP ; pas de chaînes multiples ou de sondes brutes ; usage propre à chaque commande |
| Evil-WinRM | -i, -u, -p ou -H, -S, -P ; session PowerShell | Transport, identité et autorisation requis ; pas de droits SYSTEM implicites |
| OpenSSH | ssh utilisateur@cible, invite de mot de passe masquée, session persistante | Authentification par mot de passe uniquement ; pas de négociation SSH ni de clés |
| Impacket psexec | Identité domaine/utilisateur:mot_de_passe@cible ; -hashes LM:NT | Options documentées par help uniquement ; droits et services contrôlés |
| Impacket secretsdump | Identité, -just-dc, -hashes | Contrôleur de domaine et droits de réplication requis |
| Mimikatz | C:\Tools\mimikatz.exe, privilege::debug et sekurlsa::logonpasswords | Artefact à transférer ; session SYSTEM réelle dans le modèle ; sorties simplifiées |
| hashcat | -m 1000 [-a 0] fichier_hash liste_de_mots ; --show | Lit les fichiers virtuels, calcule les empreintes NT, conserve le potfile et distingue Cracked/Exhausted ; dictionnaires limités à 4 096 entrées |
| rclone | copy C:\Data remote:loot dans Windows ; alias /srv conservé | Destination de jeu préconfigurée ; copie des fichiers de la session |
| ticketer | -nthash, -domain-sid, -domain, utilisateur | Création du fichier ccache hors ligne ; authentification ultérieure via KRB5CCNAME et impacket-psexec -k -no-pass |
| lookupsid | -domain-sids, identité et -hashes LM:NT | SID du domaine interrogé avec un identifiant valide ; contrôleur et SMB requis |
| GoPhish | gophish --config, --mode, --disable-mailer ; API via curl ; interface web propre | GET/POST des campagnes et ressources ; un destinataire connu par campagne dans cette version ; laboratoire préconfiguré |
| Vesper / Glasswing | vesper encrypt / glasswing encrypt dans une session distante administrateur | Familles fictives ; effets calculés dans le monde |
| Sauvegardes Windows | vssadmin delete shadows /all /quiet | Résolution dans la session distante, sans appel au système hôte |

`hosts`, `loot` et `help` sont des commandes du jeu. `clear` est traité par le client.
Les anciennes syntaxes du prototype avec `--as` ont été retirées du parseur et des tests.
Les alias PowerShell authentiques sont disponibles seulement dans PowerShell.

## Exigence pour les prochaines missions

Toutes les commandes nécessaires à l’observation, à la vérification des faiblesses,
aux chemins prévus et à la livraison doivent être disponibles avec leur syntaxe
authentique avant validation du scénario. Le détail Windows/Linux/LDAP/BloodHound
est dans [ACTE_II_FIDELITE.md](ACTE_II_FIDELITE.md). Ce document fixe une exigence,
sans transformer les fonctionnalités prévues en fonctionnalités déjà livrées.

## Travaux nécessaires avant de revendiquer une fidélité complète

- Compléter les shells Linux et cmd partiellement séparés, et ajouter PowerShell.
- Représenter les options des outils et leurs conséquences, version par version.
- Étendre les sorties détaillées et les codes de retour, puis les comparer à des
  captures d'un laboratoire contrôlé.
- Étendre les pipes, scripts, complétion et gestion des jobs ; les redirections simples, variables et interruptions sont présentes.
- Ajouter John, BloodHound, evil-winrm et RDP avec leurs interfaces et contextes propres.

Une option non implémentée est une limite de développement, pas une modification
présentée comme la véritable syntaxe de l'outil.


## GoPhish : source de vérité

Le serveur possède une interface web et une API ; ce ne sont pas des boutons
génériques qui remplacent les commandes de tous les outils. La mise en route et
les paramètres simulés suivent le [programme officiel](https://github.com/gophish/gophish/blob/master/gophish.go).
Le format des campagnes et l’authentification suivent la
[documentation API](https://docs.getgophish.com/api-documentation/campaigns).

Le laboratoire fournit `~/gophish/api-key.txt`, `campaign.json`, `README.txt` et
`admin.txt`. Le profil et les ressources sont déjà configurés pour le scénario.
Le compte fourni n'est pas présenté comme un compte par défaut d'une installation réelle.
L’interface propre à GoPhish comprend connexion, dashboard, campagnes/résultats,
groupes, templates, pages, profils SMTP et clé API. La couverture des options et
endpoints reste partielle ; aucun serveur ni message externe n'est réellement créé.

### Édition du terminal

- Clic droit dans la saisie ou la sortie : Copier, Coller, Tout sélectionner, Effacer, Nouvelle fenêtre.
- Ctrl+C copie la sélection ; sans sélection, il interrompt le processus de cette console. Ctrl+Maj+C copie également.
- Ctrl+V ou Ctrl+Maj+V colle au curseur et remplace la sélection. Un bloc de plusieurs lignes est refusé avec une explication : copie une seule commande. Le collage ne valide pas la commande.
- Gauche/Droite déplacent le curseur ; Maj sélectionne, Ctrl déplace par mot. Début/Fin vont aux extrémités.
- Haut/Bas parcourent l’historique et conservent le brouillon. Page précédente/suivante font défiler la sortie.
- Tab complète les commandes, les chemins virtuels, certains paramètres et les hôtes déjà découverts. En cas d’ambiguïté, les possibilités s’affichent sous la saisie. Aucune complétion pendant une saisie de mot de passe.

Le niveau de validation des six contrats, les réactions humaines et les limites
sont détaillés dans [REALISME.md](REALISME.md).

## Déploiement et shells

Les fichiers `~/tools/*.exe` sont des artefacts virtuels. Lis `cat ~/tools/README.txt`.
SCP demande un mot de passe ; SMB exige les droits du partage. Un fichier absent
ne produit plus un succès. Les transferts et les fichiers sont conservés à la reprise.

`powershell` ouvre le sous-ensemble PowerShell 5.1 ; `exit` revient au shell parent.
`Get-ChildItem`, `Get-Content`, `Set-Location`, `Get-Location`, `Copy-Item`, `Test-Path`,
`Get-Process`, `Get-Service`, `Get-Help`, `Get-Command` et `Write-Output` sont couverts
avec les options explicitement implémentées. Les pipelines et scripts généraux ne
sont pas interprétés. Les variables d'environnement restent propres à chaque console.

Les statuts sont consultables avec `echo $?` dans Kali, `echo %ERRORLEVEL%` dans cmd
et `$?` / `$LASTEXITCODE` dans PowerShell. Une commande en attente n'est pas présentée
comme un processus déjà terminé. Les codes exacts des outils non couverts ne sont
pas garantis par cette version.

## Invites interactives et changement de shell

`impacket-psexec utilisateur@cible` demande `Password:` dans la même console.
La saisie est masquée et ne rejoint pas l'historique. Une réponse vide est envoyée
comme mot de passe vide ; un mauvais mot de passe termine cet essai Impacket.
SSH/SCP conservent leurs invites utilisateur@hôte et leurs nouvelles tentatives.
Les espaces et caractères spéciaux d'un mot de passe collé sont conservés.
Une option invalide ou un transport SMB indisponible ne demande pas de secret.
Ctrl+C annule l'invite et efface le brouillon masqué.

Kali utilise son invite sur deux lignes ; cmd et PowerShell affichent leur chemin
sur la ligne de saisie, sans flèche Kali. L'entrée dans Windows conserve le contexte
parent ; `exit` depuis PowerShell revient à cmd, puis à Kali. Une coupure distante
retire aussi les shells imbriqués de cet hôte et restaure le parent local complet.

Les opérations de fichiers et les limites propres aux shells sont détaillées dans
[TERMINAL_ARCHITECTURE.md](TERMINAL_ARCHITECTURE.md). Le tutoriel fournit désormais
`cat ~/mission/lecons.txt`, un carnet expliquant chaque outil et argument du parcours.


## Filtres textuels et HTTP des dossiers d’enquête

Kali et sessions bash : `grep` (options -i, -n, -v, -c, -r/-R, -E, -F, -e),
`head -n`, `tail -n`, `wc -l/-w/-c`, `cut -d/-f`, `sort -r/-u/-n`,
`uniq -c` et `sha256sum`. Les filtres acceptent des fichiers et des pipes entre
ces commandes, avec `cat` en entrée. Les redirections `>` et `>>` écrivent dans
les dossiers virtuels accessibles. `grep` renvoie 0 pour une correspondance,
1 sans correspondance, 2 pour une erreur ; le dernier filtre détermine le statut
du pipeline. Le shell général, les scripts et toutes les expressions GNU ne
sont pas émulés. Les expressions complexes non prises en charge sont refusées.

`curl` peut lire les routes HTTP déclarées du scénario, avec GET/HEAD, -i, -f et
les redirections. Ces réponses viennent des fichiers des hôtes du jeu, respectent
les services et règles réseau, et distinguent 200, 404 et 405. Aucune requête
n’est effectuée vers un site extérieur. Les routes publiques ne donnent pas
accès aux autres fichiers de l’hôte. Les API GoPhish gardent leur fonctionnement.


## Outils de l’acte I

- `sqlmap -u URL -p param --batch --dbs`, `-D base --tables`, `-T table --columns`,
  `--dump`, `-C colonnes`, `--where=condition`, `--output-dir=répertoire` et
  `--cookie=valeur`. Seuls les paramètres vulnérables déclarés du scénario réagissent.
  Les tables invisibles restent refusées ; le CSV contient les données réelles du dossier.
- `sqlite3 fichier.db < dump.sql`, `.read`, `.tables`, `.schema`, requêtes SELECT,
  `-csv`, `-header`. Base virtuelle persistante, exécution en mémoire, lectures externes
  et extensions refusées. Pas de shell SQL interactif ni d’écriture SQL arbitraire.
- `mysql -h hôte -u compte -p -D base -e "SELECT ..."`, `--batch`, SHOW TABLES,
  SHOW DATABASES, DESCRIBE. Mot de passe masqué à l’invite ; droits par table.
  Dialecte de lecture limité, évalué par SQLite ; pas un serveur MySQL complet.
- `smbclient -L hôte -N`, partages nommés en invité ou avec `-U compte%secret`,
  `-c "ls"` et `-c "get source destination"`. Les chemins ne sortent pas du partage.
- `scp compte@hôte:source destination` récupère un fichier avec contrôle d’identité,
  service SSH et droits de lecture ; la direction inverse reste disponible.
- `checksec`, `gdb`, `nc` et `python3` couvrent uniquement le build ticketd du dossier.
  Le script fourni n’est jamais exécuté sur le système hôte.
- `tar -tf archive`, `tar -xf archive -C dossier` : conteneur virtuel avec membres
  déclarés, liste, extraction et rejet de traversée de répertoires.

Conventions consultées : [usage SQLmap](https://github.com/sqlmapproject/sqlmap/wiki/Usage),
[CLI SQLite](https://www.sqlite.org/cli.html), [documentation pwntools](https://docs.pwntools.com/en/stable/commandline.html).
Le [guide de l’acte I](ACTE_I.md) indique les commandes qualifiées pour chaque dossier.

Les variantes de syntaxe, les preuves et les reprises vérifiées en 0.4.6 sont
détaillées dans [QUALITE_MISSIONS_ET_REPRISES.md](QUALITE_MISSIONS_ET_REPRISES.md).

## Extension acte II - 0.5.0

La couverture ajoutée (inventaire système, tunnel, LDAP, collecte, graphe,
Kerberoasting RC4 et Hashcat 13100) est détaillée dans
[ACTE_II_COUVERTURE.md](ACTE_II_COUVERTURE.md). Le tableau historique ci-dessus
ne constitue plus à lui seul l’inventaire complet. Les limites explicites du
modèle restent applicables ; les parcours du guide acte II passent par les CLI.


## Extension acte III

Chisel inverse TCP/SOCKS, ProxyChains strict à plusieurs passages, Evil-WinRM,
LDAP via SOCKS et relevés Defender sont détaillés dans
[ACTE_III_COUVERTURE.md](ACTE_III_COUVERTURE.md). L'anti-tamper peut refuser une
modification malgré l'administrateur local ; l'image de contrôle reste un cas de
configuration distinct, sans exploitation de CVE Defender. Toute commande reste
résolue dans l'état fictif du jeu.
