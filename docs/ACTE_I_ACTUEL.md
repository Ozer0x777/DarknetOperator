# Acte I actuel - Se faire un nom (0.5.1)

Les nouvelles carrières utilisent la progression 4 : sept exercices privés,
puis Ravelle, dix chapitres au total et sept petits contrats facultatifs.
Aucun achat payant n’est nécessaire pour terminer l’acte I. Tous les outils et
les machines décrits ici appartiennent au monde simulé du jeu.

## Prélude

Dans Chordly, ouvrir le dossier de k0rvid. Suivre les exercices de terminal,
reconnaissance, connexion SSH, transfert, comparaison de preuves, campagne
GoPhish et manipulation de fichiers Windows. Les commandes inchangées sont
expliquées dans [le guide du prélude](PRELUDE_CHORDLY.md), sections 1 à 3,
5, 6 et 8. L’ancien exercice Hashcat est retiré de ce parcours.

Le transfert du quatrième exercice utilise maintenant le compte personnel fourni :

```text
scp m.leroux@10.20.0.21:C:/Users/m.leroux/Documents/transfert.txt ~/loot/transfert.txt
Password123!
cat ~/loot/transfert.txt
```

## Ravelle : vérifier une source publique

Lire le briefing, identifier le site et comparer les documents avant la livraison.

```text
cat ~/mission/ravelle.txt
host www.ravelle-associes.fr
nmap -sV 51.91.204.27
curl http://www.ravelle-associes.fr/
curl http://www.ravelle-associes.fr/mentions.txt
curl -o ~/loot/ravelle.txt http://www.ravelle-associes.fr/documents/RAV-26-001.txt
cat ~/loot/ravelle.txt
```

Dans Chordly, rendre compte avec `livraison RAV-26-001`. L’invitation ouvre
BreachBoard avec 740 ₵ et 40 points de réputation. Les aides permettent de
reprendre une erreur sans acheter de matériel.

## Chapitres 2 à 10

Le parcours conserve le partage SMB invité, les dates SQL, SQLmap, le contrôle
d’accès web, la vérification d’identité, la médiation et les deux voies finales.
Leurs solutions figurent dans [le guide de l’acte I](ACTE_I.md), à l’exception
des chapitres 6 et 7 remplacés ci-dessous. Le petit contrat ancien lié au hash
est réservé à la suite ; les sept autres restent facultatifs.

### 6 - Une passation à vérifier

Le compte est fourni. Vérifier la session, récupérer le document et lire la preuve.
Utiliser deux consoles pour garder la session distante ouverte pendant le transfert.

```text
cat ~/mission/passation.txt
ssh planning@10.61.6.21
Atelier2026!
whoami
```

Dans la console locale :

```text
scp planning@10.61.6.21:/srv/planning/OR-26-311.csv ~/loot/planning.csv
Atelier2026!
cat ~/loot/planning.csv
```

Compte rendu : `livraison OR-26-311`.

### 7 - Un service, des permissions

Le compte de maintenance fourni permet d’examiner le service et sa configuration.
Il conserve des droits limités ; le compte SQL ne peut lire que le périmètre prévu.

```text
cat ~/mission/reperes.txt
ssh svc.ticket@10.61.7.30
Maintenance2026!
whoami
systemctl status ticketd
cat /home/svc.ticket/README.txt
cat /etc/ticketd/database.ini
```

Depuis la console locale :

```text
mysql -h 10.61.7.10 -u ticket_ro -p -D ticketing -e "SELECT * FROM tickets;" > ~/loot/tickets.tsv
TicketRead2026!
cat ~/loot/tickets.tsv
```

Compte rendu : `livraison TK-26 tickets`.

## Passage à l’acte II

Accepter l’invitation finale, prendre l’accès NullVad gratuit et configurer Tor.
Le prochain contact est Cendre sur Telegrid. L’acte II contient dix missions et
six contrats facultatifs : inventaire Linux/Windows, Hashcat, Polkit, relais SSH,
LDAP, SharpHound/BloodHound et Impacket. Voir [le guide détaillé](ACTE_II_GUIDE.md).
Les achats de dictionnaires et GPU sont signalés comme matériel pour l’acte II.

## Anciennes sauvegardes

L’adaptation intervient à l’entrée dans la carrière ou au chargement d’un slot.
Une sauvegarde « Avant adaptation de l’acte I » protège la carrière adaptée à
l’entrée. Le slot chargé reste intact. Argent, réputation, inventaire, décisions
et dossiers validés sont conservés. Un dossier ancien déjà lancé garde son monde,
ses commandes en attente et sa récompense jusqu’à sa fin ; les dossiers suivants
utilisent la nouvelle progression. Les dossiers anciens déjà terminés conservent
leur définition pour la relecture. Les anciennes carrières avancées des premières
progressions gardent leur fonctionnement compatible.

La qualification automatique joue deux actes I actuels sans achat, puis les deux
voies de l’acte II, ainsi que les reprises et migrations sensibles. Elle ne remplace
pas une vérification graphique native sur un poste Linux.
