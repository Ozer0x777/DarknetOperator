# Acte III : couverture jouable

Douze dossiers séquentiels Lenoir/Aster sont disponibles après les dix dossiers
de l'acte II, sur Telegrid avec Traverse. Exployt affiche les douze étapes.
Les six premières missions gardent leur réseau initial de cinq machines.
Les six suivantes utilisent 38 machines réparties sur huit segments ; seuls les
services et accès déclarés sont utilisables. La présence d'une machine dans le
scénario ne l'affiche pas au joueur et ne lui accorde aucune route.

## Dossiers livrés

| N° | Dossier | Preuve attendue |
|---|---|---|
| 1 | Une machine qu'on ne voit pas | Découverte filtrée, SSH ouvert avec `-Pn`, HTTP fermé |
| 2 | La porte du prestataire | Ancien relais retiré, compte lecteur et passation actuelle |
| 3 | Le réseau vu d'ici | Filtrage depuis Kali, accès depuis Aster, routes et registre |
| 4 | Le retour est possible | Lecture HTTP par redirection inverse Chisel |
| 5 | La même adresse, plusieurs chemins | Scan TCP par ProxyChains et comparaison directe |
| 6 | Une console sans bureau | WinRM autorisé, identité et périmètre lecteur |
| 7 | Le réseau des droits | Appartenances LDAP et refus WinRM sur une autre machine |
| 8 | Le fichier arrive, rien ne s'exécute | Artefact présent, exécution bloquée, journal Defender et lecture LDAP alternative |
| 9 | Administrateur ne suffit pas | Anti-tamper résistant à l'administrateur local, contrôle modifiable, relecture des états |
| 10 | Le second passage | Avenant lu, deux SOCKS actifs et bordereau lu depuis la passerelle Recherche |
| 11 | Le gardien se réveille | Premier relais isolé, nouvelle lecture du bordereau par le secours |
| 12 | Le dossier qui ne devait pas sortir | Lot téléchargé par deux passages, copie conforme et relue |

Ces dossiers sont au palier d'accès 2 ; le troisième débloque le palier 3.
Le numéro de l'acte ne représente pas un privilège. Aucun accès SYSTEM n'est
accordé au démarrage. Chaque contrat recharge ses machines : la persistance
continue de toute l'infrastructure entre missions reste à construire.
Les fichiers locaux et les acquis de carrière suivent les règles habituelles.

## Infrastructure et frontières

| Segment | Plage fictive | Machines |
|---|---|---:|
| DMZ Aster | 10.90.10.0/24 | 4 |
| Postes Lenoir | 10.90.20.0/24 | 6 |
| Identités | 10.90.30.0/24 | 4 |
| Applications | 10.90.40.0/24 | 6 |
| Prestataire Aster | 10.91.10.0/24 | 4 |
| Recherche | 10.92.10.0/24 | 5 |
| Administration | 10.90.60.0/24 | 5 |
| Sauvegardes | 10.90.70.0/24 | 4 |

Les postes, serveurs SQL, PKI, sauvegardes et contrôleurs secondaires ont des
empreintes de services cohérentes avec leur rôle. Ils ne proposent pas tous une
mission ou une session interactive. `lenoir.lab` est l'annuaire interrogeable ;
`aster.lab` est déclaré dans l'inventaire sans approbation avec Lenoir. Le moteur
ne fournit pas encore deux annuaires LDAP indépendants ni toute une forêt AD.

`network_routes` déclare les réseaux accessibles par origine. Une origine absente
ne reçoit aucune route. `network_rules` filtre ensuite source, cible et port.
`discovery_rules` peut masquer la découverte sans fermer TCP/22. `-Pn` saute cette
phase ; il n'ouvre ni route ni pare-feu. Les scans gardent leur origine et leurs
observations de ports. Un hôte isolé cesse de fournir une origine utilisable.

Pour la Recherche, Kali rejoint d'abord le SOCKS inverse sur Kali:1080.
Un second serveur Chisel écoute sur Aster:8001 ; son client s'exécute sur la
passerelle applicative. Son SOCKS inverse écoute sur Aster:1081. La chaîne stricte
passe par ces deux écouteurs ; les ACL empêchent Kali d'atteindre directement le
second. Le relais de secours a son propre chemin et ses propres processus. La réaction
SOC du dossier 11 est scénarisée sur une sonde donnée ; elle ne constitue pas
un système général de détection comportementale.

## Commandes et protections

| Outil | Couverture | Limites |
|---|---|---|
| Chisel | Serveur Kali ou relais équipé ; client distant ; inverse TCP ou SOCKS | Une liaison par client ; HTTP, sans TLS/UDP ni authentification Chisel |
| ProxyChains-NG | `-f CONFIG`, `strict_chain`, plusieurs SOCKS5 IPv4 ; Nmap, curl, LDAP, Evil-WinRM | TCP ; pas de DNS distinct par origine ; LDAP `-w`, pas d'invite `-W` via ProxyChains |
| Nmap sur SOCKS | `-sT -Pn -n`, ports explicites, versions | Pas de SYN brut, ICMP ou UDP sur SOCKS |
| Evil-WinRM | `-i`, `-u`, `-p` ou `-H`, `-P`, `-S`, session PowerShell | Endpoint, secret et utilisateurs autorisés vérifiés ; pas de menu d'évasion, téléversement ou certificat |
| Defender | `Get-MpComputerStatus`, `Get-MpPreference`, `Get-WinEvent -LogName "Microsoft-Windows-Windows Defender/Operational"` | Modèle des profils fictifs, pas un Defender complet |
| Configuration Defender | `Set-MpPreference -DisableRealtimeMonitoring $true` ou `$false` | Droits locaux exigés ; refus si anti-tamper actif ; portée limitée à l'hôte courant |

Les versions et correctifs sont observables (`Get-HotFix`). L'image protégée
conserve sa protection malgré le compte administrateur. Le témoin autorise une
modification parce que son anti-tamper est désactivé par configuration ; ce n'est
pas une exploitation de sa version. Aucune CVE Defender ni chaîne de pilote
vulnérable n'est simulée ici. L'alternative LDAP évite de présenter une collecte
bloquée comme une collecte réussie. Les événements 1116, 5007 et 5013 sont des
traces simplifiées, pas le schéma complet des événements Windows.

Chaque processus garde sa console, son hôte et son PID. Ctrl+C, fermeture ou
arrêt coupe son passage. Un serveur relancé ne réanime pas ses anciens clients.
Les actions en attente et les sessions WinRM vérifient tous les SOCKS de leur
chaîne, y compris après sauvegarde. Aucun socket ou logiciel d'attaque réel n'est
lancé par ces commandes.

Références : [Chisel](https://github.com/jpillora/chisel),
[ProxyChains-NG](https://github.com/rofl0r/proxychains-ng),
[Evil-WinRM](https://github.com/Hackplayers/evil-winrm),
[Get-MpComputerStatus](https://learn.microsoft.com/en-us/powershell/module/defender/get-mpcomputerstatus),
[protection contre les falsifications](https://learn.microsoft.com/en-us/defender-endpoint/tamper-protection-overview).
Les inspirations de post-mortem restent détaillées dans la
[proposition](ACTE_III_PROPOSITION.md) ; Lenoir n'est pas la reproduction d'une victime réelle.

## Madame_TLS et le lot industriel

Trois scènes prolongent son arc : une pause personnelle après le dossier 9,
une demande de lot après le dossier 12, puis un retour selon l'envoi.
Elle demande le calendrier, le fournisseur et le coût cible pour sa veille
économique ; elle ne résout pas les commandes à la place du joueur.

Le lot narratif est créé uniquement à partir de la copie d'audit acquise et
vérifiée dans la mission 12. Une marque de progression seule ne suffit pas.
La consultation d'audit est autorisée ; la redistribution du lot complet est
explicitement exclue. La validation du contrat n'envoie rien à Madame_TLS.

Dans Chordly, le joueur refuse, joint la synthèse expurgée autorisée ou joint le
lot complet. L'envoi archive le contenu et son SHA-256, et reste idempotent à la
reprise. Il joint la copie narrative archivée, pas un fichier local modifié après
l'audit. Ces choix gardent le lien professionnel, amical ou attiré déjà choisi.
La révélation complète du commanditaire et le piège final restent à écrire.

## Apprentissage et validation

Les passations sont dans `~/mission`, les aides dans `~/docs`, les configurations
dans `~/routes`. Les indices gradués puis le rappel détaillé sont disponibles
sur Telegrid. Aucun téléchargement ni recherche Internet n'est nécessaire.

`backend/act3_validation.py` joue les douze missions via l'API après les actes I
et II réellement parcourus, avec 24 écritures/rechargements de sauvegarde.
Le corpus `build/validation/act3-qualification.json` conserve commandes, sorties,
consoles et états ; Godot le rejoue dans `game/tests/test_act3.gd`.
Les tests moteur vérifient également les refus, les tentatives de raccourci,
les transports interrompus, les fausses copies et les neuf combinaisons de lien
et de transmission à Madame_TLS.

Le [protocole de 30 minutes](ACTE_III_PLAYTEST.md) utilise une carrière isolée
préparée au début de l'acte III. Une qualification automatisée ne constitue pas
un essai avec un débutant ni une inspection graphique native.


## Vérifications du 15 novembre 2026

- Suite moteur : 499 tests réussis, y compris les transferts HTTP sans ajout de
  saut de ligne, les copies exactes et les neuf branches de transmission Lenoir.
- Qualification API : douze missions depuis les actes I et II, 24 chargements de
  sauvegarde, lot narratif identique à la copie d'audit et aucune transmission
  automatique à Madame_TLS.
- Contrôle complet API/Godot : 35/35 réussis en 356 secondes, dont 218 assertions
  Godot pour l’acte III ; aucun `SCRIPT ERROR:` ou `ERROR:`. Un avertissement de
  quatre objets non libérés apparaît à la fermeture d’un processus Godot.
- Aucun essai humain de 30 minutes ni inspection graphique native inclus.
