# Fidélité obligatoire - commandes et systèmes de l’acte II

**Exigence de conception, pas état des fonctionnalités livrées.**
L’expression « BloodHound simplifié » est retirée du plan : les actions proposées
au joueur devront correspondre au logiciel et à la version de référence choisis.
Un petit domaine fictif peut réduire le volume des données ; il ne justifie ni
une syntaxe inventée ni un graphe sans collecte ou droits cohérents.

## Principe de livraison

- Pour chaque mission, implémenter toutes les commandes nécessaires à l’observation,
  aux alternatives raisonnables documentées, à la vérification de faiblesse et au
  compte rendu. Ne pas livrer une mission qui exige une commande encore absente.
- Conserver les noms, options, paramètres, règles de shell, erreurs et codes de
  retour de la version retenue ; vérifier les commandes dans les sources officielles.
- Ne jamais transformer une commande authentique en bouton générique d’attaque.
- Une commande valide ne réussit pas automatiquement : vérifier contexte, origine
  réseau, version, fichier, compte, privilèges, services et politique locale.
- Les sorties proviennent des données des machines et de l’annuaire. Elles doivent
  rester cohérentes entre outils, changements d’état, consoles et rechargements.
- Distinguer un défaut d’implémentation d’une erreur réelle de commande. La liste
  actuelle des limites reste dans COMMANDES.md ; ne pas annoncer « Windows/Linux
  complets » sur la seule base d’un ensemble fini de commandes.

## LDAP et BloodHound

LDAP est un protocole d’accès aux annuaires, pas un logiciel d’attaque. Prévoir
ldapsearch et les outils Windows/PowerShell du scénario pour consulter objets,
attributs, groupes et relations effectivement accessibles. Les filtres, bases de
recherche, modes d’authentification, droits et erreurs doivent être modélisés.

BloodHound sert à analyser des relations et chemins de droits. Prévoir un
collecteur compatible avec la version choisie, dont SharpHound pour Windows,
les fichiers collectés puis leur import et leur consultation. Une collecte ne
révèle ni une session jamais observée ni une machine injoignable. Séparer données
anciennes, collecte partielle, hypothèse de chemin et accès réellement vérifié.
Les exécutables et modules absents doivent être installés/transférés dans le monde
avant utilisation ; ne pas supposer RSAT ou un module AD sur chaque poste.

## Catalogue à spécifier avant chaque mission

Les noms ci-dessous sont une base de couverture prévue, **pas une liste de
commandes déjà prises en charge**. Leurs options et versions doivent être fixées
par des fiches de conformité et des traces de référence.

| Besoin | Windows / PowerShell | Linux |
|---|---|---|
| Identité et privilèges | whoami /all, /groups, /priv ; groupes locaux/domaine | id, whoami, groups, sudo -l |
| Système et correctifs | systeminfo, Get-CimInstance, Get-HotFix, version/build | uname, /etc/os-release, inventaire dpkg/rpm selon distribution |
| Réseau et pivot | ipconfig /all, route print, netstat, Resolve-DnsName, Test-NetConnection | ip addr, ip route, ss, résolution DNS, clients SSH/curl/Nmap selon origine |
| Processus et services | tasklist, sc.exe, Get-Process, Get-Service | ps, systemctl, configuration du service et processus d’écoute |
| Fichiers et droits | dir, type, icacls, Get-ChildItem, Get-Content, Get-Acl | ls -l, stat, find, getcap, droits d’accès et d’exécution |
| Domaine et annuaire | net, nltest, outils AD si présents ; SharpHound | ldapsearch et collecteur compatible si prévu |
| Lecture et traitement | findstr, Select-String, Where-Object, Select-Object, exports | grep, head/tail, cut, sort/uniq, redirections et pipelines |

## Vérifier une faiblesse

La mission doit permettre d’observer le problème avant de choisir une technique :
versions, correctifs, permissions, configuration et conditions d’accès. Les outils
d’inventaire comme LinPEAS/WinPEAS agrègent ces faits ; ils ne fournissent pas un
bouton garantissant root ou SYSTEM. Le joueur doit pouvoir vérifier les constats
utiles avec les commandes natives prévues pour le scénario.

Pour le cas Polkit : distinguer version affichée, correctif de distribution
éventuellement rétroporté, état du paquet et conditions locales. Prévoir une
machine vulnérable et un cas corrigé. Une version ancienne seule ne prouve pas
l’exploitabilité ; une tentative doit respecter les conditions du modèle.

Pour un pivot : l’origine de la connexion, les interfaces d’écoute, la résolution
et les routes déterminent les services joignables. Un tunnel arrêté ne doit plus
transporter les commandes ; une session distante ne transforme pas toute console
locale en session pivotée. Conserver ces différences après sauvegarde.

## Preuves de conformité avant validation

Pour chaque commande indispensable : aide officielle/version retenue, grammaire,
prérequis, sorties de référence, mutations, erreurs et tests des options utilisées.
Pour chaque faiblesse : au moins un cas applicable et un cas non applicable,
avec vérification des droits avant et après. Ajouter des tests entre consoles,
des chemins alternatifs et des reprises avant/après la transition.

Une documentation de conception ne suffit pas pour déclarer cette couverture
implémentée. La qualification du jeu et l’essai graphique restent distincts.

## Références primaires

- OpenLDAP : https://www.openldap.org/doc/admin26/intro.html
- ldapsearch, exemple de recherche : https://www.openldap.org/doc/admin26/quickstart.html
- SharpHound CE et import des collectes : https://bloodhound.specterops.io/collect-data/ce-collection/sharphound
- Windows whoami : https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/whoami
- Windows systeminfo : https://learn.microsoft.com/en-us/windows-server/administration/windows-commands/systeminfo
