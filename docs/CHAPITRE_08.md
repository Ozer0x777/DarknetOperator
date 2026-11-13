# Chapitre 08 — Mauvaise adresse

Dossier jouable : **après le chapitre 7** dans les nouvelles carrières, ou après
Morel pour les anciennes carrières compatibles. Ouvrir Chordly puis
la conversation de **nullroute** : sa proposition privée possède un bouton
« Ouvrir le dossier ». Elle ne figure pas dans les annonces publiques.
Une mission déjà active doit être terminée ou reprise avant d’en accepter une autre.

Les dix chapitres sont décrits dans [ACTE_I.md](ACTE_I.md). Ce dossier utilise des hôtes,
comptes et fichiers fictifs ; toutes les commandes ci-dessous se saisissent dans
les consoles du jeu. **Spoilers complets.**

## Vérifier et corriger le brief

Dans une console Kali :

```text
cat ~/mission/enquete.txt
curl http://10.48.1.20/mentions.txt
```

Dans le navigateur, BreachBoard → Discussion → rechercher Aquila, ouvrir
**Aquila : deux sociétés, deux activités** et lire ses réponses. L’identifiant
AQC-441 correspond au conseil, AQF-882 au fret. Le client les a confondus.
Envoyer dans Chordly à nullroute :

```text
Aquila Conseil et Aquila Fret sont distinctes : AF-26-118.
```

Le contact reconnaît son erreur seulement après consultation des deux sources.
Une phrase recopiée sans ces observations ne débloque pas l’étape.

## Retrouver la bonne infrastructure

Ouvrir **Portail de suivi Aquila — ancienne adresse ?** dans Discussion.
Le premier message est ancien : les réponses corrigent l’adresse .30 en .31.

```text
curl http://10.48.8.31/mentions.txt
```

Envoyer à nullroute :

```text
AQF-PORTAIL 10.48.8.31 AF-26-118
```

## Obtenir le premier accès

Kali :

```text
nmap -sV 10.48.8.31
curl http://10.48.8.31/robots.txt
curl http://10.48.8.31/exports/support.env.old > ~/loot/support.env
grep -n SSH ~/loot/support.env
```

Le chemin de la sauvegarde est cité dans les réponses du forum. `robots.txt`
est un indice de chemin, pas une protection ni une autorisation. La copie exposée
contient un compte encore valable ; ce n’est pas une exécution de code par curl.

Ouvrir une autre console pour garder Kali disponible :

```text
ssh svc.portail@10.48.8.31
```

À l’invite du mot de passe, saisir la valeur lue dans le fichier :

```text
PortailFret2026!
```

La session obtenue est Windows, sous un utilisateur limité. Dans cette session :

```text
whoami
type C:\Users\svc.portail\Documents\reprise.txt
type C:\Users\svc.portail\Documents\connecteur.ini
```

Le connecteur contient un compte différent pour le serveur documentaire.
Le compte du portail ne dispose pas des droits du partage administratif.

## Identifier et transférer le bon document

Revenir dans la console **Kali**, puis :

```text
nmap -sV 10.48.8.0/24
smbclient //10.48.8.10/C$ -U svc.docs%DocsFret2026! -c "ls"
smbclient //10.48.8.10/C$ -U svc.docs%DocsFret2026! -c "get Data/Livraisons/2024/AF-118.csv /home/operator/loot/archive.csv"
head -n 5 ~/loot/archive.csv
```

L’archive est ancienne et porte AF-24-118. Une autre version porte AF-26-181 :
le numéro ressemble au bon, mais la référence n’est pas celle demandée.
Récupérer le document de novembre :

```text
smbclient //10.48.8.10/C$ -U svc.docs%DocsFret2026! -c "get Data/Livraisons/2026/AF-26-118.csv /home/operator/loot/livraison.csv"
head -n 4 ~/loot/livraison.csv
grep -n AF-26-118 ~/loot/livraison.csv
wc -l ~/loot/livraison.csv
cat ~/loot/livraison.csv | grep AF-26-118 | cut -d ";" -f 4 | sort | uniq
sha256sum ~/loot/livraison.csv
```

Attendus : **quatre lignes avec l’en-tête**, trois lignes de données, dates des
6 et 7 novembre 2026, lots L-318 à L-320. `sha256sum` calcule une empreinte :
il ne prouve pas à lui seul l’origine ou la fraîcheur d’un document.

Envoyer à nullroute :

```text
livraison AF-26-118
```

La validation exige la correction du brief, la confirmation de la cible,
la chaîne d’accès observée et une copie récente intacte consultée dans `~/loot`.
La prime est de **650 ₵**, avec **65 de réputation lors de la première réussite**.
Les observations, consoles et transferts sont conservés à la sauvegarde.

La durée de ce dossier reste à mesurer en tests joueurs.
