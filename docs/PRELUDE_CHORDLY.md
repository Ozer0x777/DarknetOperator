# Prélude privé - solutions et explications

> Archive de la progression antérieure. Pour une nouvelle carrière 0.5.1, suivre [l’acte I actuel](ACTE_I_ACTUEL.md). Les passages remplacés restent utiles aux dossiers anciens déjà lancés.

Nouvelle carrière : ouvrir Chordly, sélectionner k0rvid, puis « Ouvrir le dossier ».
Une commande à la fois dans le terminal du jeu. Chaque succès ouvre le dossier suivant.
Les sauvegardes antérieures conservent leur progression.

## 1. Prendre ses marques

pwd situe le dossier courant ; ls liste ; cat lit sans exécuter.

```text
pwd
ls ~/mission
cat ~/mission/preparation.txt
```

## 2. Lire une reconnaissance

Comparer les hôtes, ports et services ; un port ouvert ne prouve aucune vulnérabilité.

```text
nmap -sV 10.20.0.0/24
```

## 3. Ouvrir une session

SSH ouvre une session avec le compte fourni. Le mot de passe est saisi à l’invite et reste masqué.

```text
ssh m.leroux@10.20.0.21
Password123!
```

## 4. Récupérer un document

smbclient accède au partage avec le compte fourni ; get copie le document vers le loot local.

```text
smbclient //10.20.0.10/C$ -U it.presta%Maintenance2026! -c "get Data/contrats_2026.xlsx /home/operator/loot/contrats_2026.xlsx"
```

## 5. Comparer deux indices

L’inventaire est ancien. Lire le changement récent avant d’écrire la conclusion.

```text
cat ~/mission/inventaire_ancien.txt
cat ~/mission/changement_recent.txt
echo "serveur migre" > ~/mission/conclusion.txt
```

## 6. Comprendre une campagne

Lancer GoPhish dans une console dédiée ; les deux commandes suivantes se font dans une autre console Kali. La clé autorise l’API locale ; le JSON décrit la campagne, ses cibles et ressources. Attendre une soumission : une campagne créée ne suffit pas.

```text
gophish --config /opt/gophish/config.json
API_KEY=$(cat ~/gophish/api-key.txt)
curl -k -H "Authorization: $API_KEY" -H "Content-Type: application/json" -d @/home/operator/gophish/campaign.json https://127.0.0.1:3333/api/campaigns/
```

## 7. Retrouver un mot de passe

Le mode 1000 correspond à NTLM ; le dictionnaire est le petit échantillon du simulateur. Le compte support.exercice est propre à cet exercice.

```text
hashcat -m 1000 ~/mission/exercice.ntlm /usr/share/wordlists/rockyou.txt
```

## 8. Manipuler un fichier Windows

Après SSH, type lit le fichier Windows et copy le duplique ; ces commandes ne s’exécutent plus dans Kali.

```text
ssh m.leroux@10.20.0.21
Password123!
type C:\Users\m.leroux\note.txt
copy C:\Users\m.leroux\note.txt C:\Users\m.leroux\preuve.txt
```

## 9. Dossier Ravelle et invitation

Reprendre le dossier complet proposé par k0rvid. Son parcours est détaillé dans
[le guide des scénarios](GUIDE_COMPLET_SCENARIOS.md). Sa réussite accorde
l’invitation au forum. Les huit exercices seuls ne suffisent pas.

Le prélude constitue le premier chapitre du nouvel [acte I en dix chapitres](ACTE_I.md).
Cet acte comporte 18 dossiers en comptant les huit exercices préparatoires,
plus huit petits contrats facultatifs. Les anciens scénarios restent compatibles.
