# Progression Red Team — le parcours du pirate

> Suivi d’implémentation actuel : `ROADMAP.md`. Architecture PC : `STEAM.md`.
> Document de conception du jeu solo RedTeamSimulator. Certaines sections
> décrivent la cible future. Voir README.md pour les fonctionnalités présentes.
> Le terminal devra reproduire la syntaxe authentique des outils pris en charge
> et leurs sorties ; sa syntaxe simplifiée actuelle reste à remplacer.
> Le blueprint Red/Blue historique est désormais conservé dans RedVsBlue.


## Intention

Pour l'instant, le jeu se concentre sur **la Red Team en solo**. Le multijoueur est
reporté. Le joueur incarne un pirate qui commence petit et monte en gamme. Ce qui
change d'un palier à l'autre, ce n'est pas seulement la difficulté des cibles :
c'est **sa façon de se cacher, de trouver du travail et d'entrer chez la cible**.

La boucle est du même genre qu'un « hacker sim » (contrats → argent → équipement →
contrats plus durs → risque d'être pris). Notre différence est le réalisme technique
(vraie chaîne d'attaque Active Directory, vrais Event IDs Windows) et le
**débriefing côté Blue** après chaque mission.

Tout est simulé : aucune commande réelle n'est exécutée, aucun vrai réseau n'est touché.

## Règles de nommage (décidées)

| Catégorie | Règle | Exemples |
|---|---|---|
| Outils offensifs | **Uniquement de l'open source**, vrais noms, toujours gratuits | nmap, impacket, mimikatz, hashcat… |
| Discrétion | Tor (open source) sous son vrai nom ; VPN fictifs | Tor, **NullVad** |
| Messageries | Noms fictifs (aucune marque commerciale) | voir §3 |
| Forums | Noms fictifs proches des vrais forums, **à finaliser** | voir §3 |
| Ransomwares | Familles fictives, achetées | voir §5 |
| Logiciels commerciaux | **Aucun** (pas de Cobalt Strike, Brute Ratel, etc.) | — |

---

## 1. Les trois paliers

```
PALIER 1 — Débutant          PALIER 2 — Confirmé           PALIER 3 — Pro
──────────────────────       ──────────────────────        ──────────────────────────
Discrétion : VPN             Discrétion : VPN + Tor        Discrétion : Tor → RDP/SSH acheté
Contacts : Chordly + forum   Contacts : Telegrid + forum   Contacts : Sessyon + forum privé
Entrée : phishing, scan      Entrée : phishing ciblé       Entrée : accès RDP/SSH acheté
Achats : VPN                 Achats : ransomware           Achats : accès + ransomware
Cibles : petites structures  Cibles : PME / ETI            Cibles : grands comptes
```

### Passage au palier suivant

Il faut à la fois :
- atteindre un seuil de **réputation sur le forum** (palier 2 : 100 ; palier 3 : 300) ;
- réussir un **contrat de passage**, proposé par un « parrain » du forum, qui apprend la
  nouvelle mécanique (Tor au palier 2, accès acheté et machine relais au palier 3).

Tor est gratuit et open source. Ce n'est pas l'argent qui le débloque mais le contrat de
passage : le parrain explique pourquoi un VPN ne suffit plus.

---

## 2. La chaîne de discrétion (route réseau)

Le joueur se connecte à la cible à travers une **route** : une liste d'intermédiaires
affichée en permanence à l'écran.

```
Palier 1 :  Joueur → VPN → cible
Palier 2 :  Joueur → VPN → Tor → cible
Palier 3 :  Joueur → Tor → RDP/SSH acheté (machine relais) → cible
```

| Intermédiaire | Coût | Résistance au traçage | Temps de recharge ajouté | Particularité |
|---|---|---|---|---|
| Aucun (connexion directe) | 0 | 0 | +0 | Toute détection = arrestation immédiate |
| FreeShield (VPN gratuit) | 0 | 15 | +0 | Garde des logs : **35 %** de chance de les livrer quand le traçage l'atteint, ce qui le fait sauter d'un coup |
| **NullVad** (VPN payant) | 50 ₵ / contrat | 25 | +0 | Ne garde pas de logs |
| Tor | 0 | 40 | +1 | Lent : toutes les actions coûtent un tick de plus |
| RDP/SSH acheté | 300 à 5 000 ₵ | 35 | +0 | **Jetable** : s'il est atteint par le traçage, il est grillé (perdu) mais protège le reste de la route ce tour-là |

### Jauge de traçage

- Chaque alerte SIEM liée au joueur **lance ou accélère une enquête**. Le traçage avance
  à chaque tick tant qu'une enquête est ouverte (+2 par alerte haute, +4 par alerte
  critique).
- Le traçage doit « traverser » chaque intermédiaire, en partant de la cible. Un
  intermédiaire de résistance 40 demande 40 points de traçage avant de passer au suivant.
- Si le traçage traverse toute la route et atteint le joueur, celui-ci est **arrêté** :
  contrat échoué, grosse perte de réputation, saisie d'une partie de l'argent.
- Le joueur peut **se déconnecter** à tout moment : le contrat échoue, mais il reste libre.
  C'est la source principale de tension.

Ce système s'appuie sur ce qui existe : le `noise` des abilities alimente la suspicion,
les règles de `siem.py` produisent les alertes, et les alertes font avancer le traçage.

---

## 3. Contacts : messageries et forums

Le forum est le fil conducteur : on y gagne la réputation, on y trouve les contrats et la
boutique. La messagerie sert à discuter avec le client. Le choix de la messagerie fixe le
**risque de piège** : un contrat qui vient en réalité d'un enquêteur infiltré.

| Palier | Messagerie (fictive) | Inspirée de | Risque de piège |
|---|---|---|---|
| 1 | **Chordly** | Discord | 15 % |
| 2 | **Telegrid** | Telegram | 7 % |
| 3 | **Sessyon** | Session | 2 % |

Un contrat piège n'est pas une fatalité, il laisse des indices : compte client récent,
réputation nulle sur le forum, prime anormalement haute, urgence. Un joueur attentif
peut le refuser. C'est aussi un message pédagogique.

### Forums (noms provisoires, à finaliser)

| Palier | Nom provisoire | Accès |
|---|---|---|
| 1 | **BreachBoard** | Ouvert, accessible en clair |
| 2 | **Exployt** | Accessible via Tor, réputation ≥ 100 |
| 3 | **XSX** | Sur invitation (parrainage), réputation ≥ 300 |

---

## 4. Outils : open source, gratuits

Tous les outils offensifs sont open source et **gratuits** dès qu'ils sont débloqués par le
palier. L'argent ne sert jamais à acheter un outil, seulement des services (VPN, accès,
ransomware). Chaque outil correspond à une ou plusieurs abilities JSON.

| Outil | Rôle dans le jeu | Ability(s) | Palier |
|---|---|---|---|
| nmap | Découverte d'hôtes et de services | `red.recon_scan` (existe) | 1 |
| GoPhish | Campagne de phishing | `red.phishing_initial_access` (existe) | 1 |
| hashcat / John the Ripper | Cassage de hash, durée selon le GPU | `red.crack_hash` (à créer) | 1 |
| mimikatz | Extraction d'identifiants en mémoire | `red.mimikatz_dump` (existe) | 1 |
| impacket (psexec.py) | Mouvement latéral | `red.psexec_lateral` (existe) | 1 |
| impacket (secretsdump.py) | DCSync | `red.dcsync` (existe) | 2 |
| impacket (ticketer.py) | Golden Ticket | `red.golden_ticket` (existe) | 2 |
| BloodHound CE | Cartographie AD, révèle les chemins d'attaque | `red.ad_enum` (à créer) | 2 |
| evil-winrm | Accès distant discret | `red.winrm_lateral` (à créer) | 2 |
| rclone | Exfiltration de fichiers | `red.exfiltrate` (à créer) | 2 |
| xfreerdp / OpenSSH | Connexion à l'accès acheté | `red.rdp_access`, `red.ssh_access` (à créer) | 3 |

### Choix tactique : casser ou réutiliser un hash

Un hash NTLM récupéré n'est pas immédiatement utilisable en clair :
- **le casser** avec hashcat prend des ticks (selon le GPU et la liste de mots) mais ne
  fait aucun bruit chez la cible ;
- **le réutiliser directement** (pass-the-hash) est immédiat mais déclenche la règle
  `_match_pass_the_hash` de `siem.py`.

---

## 5. Achats

| Article | Prix | Effet |
|---|---|---|
| NullVad (par contrat) | 50 ₵ | Intermédiaire VPN sans logs |
| Liste de mots premium | 150 ₵ | Cassage de hash plus rapide |
| GPU (3 niveaux) | 400 / 1 200 / 3 000 ₵ | Divise la durée de cassage |
| Accès RDP/SSH utilisateur | 300 à 800 ₵ | Point d'entrée + intermédiaire jetable |
| Accès RDP/SSH administrateur local | 1 000 à 2 500 ₵ | Idem, avec privilèges admin sur l'hôte |
| Accès administrateur de domaine | 5 000 ₵ et plus | Rare, uniquement sur le forum de palier 3 |
| Ransomware : affiliation | 0 ₵ d'entrée | L'opérateur garde **30 %** de chaque rançon |
| Ransomware : licence | 450 ₵ | Le joueur garde 100 %, mais doit gérer lui-même la négociation |

Le prix d'un accès dépend de la taille de la cible et du niveau de privilège. Dans les
contrats de palier 3, **il n'y a plus de chemin par phishing** : l'accès acheté est le seul
point d'entrée, ce qui impose la progression.

### Ransomware (familles fictives)

Deux familles au départ, par exemple **Vesper** (affiliation, chiffrement rapide mais
bruyant) et **Glasswing** (licence, plus lent mais plus discret). La rançon versée dépend :
- du pourcentage d'hôtes chiffrés (`ENCRYPTED`) ;
- de la destruction préalable des sauvegardes (lien naturel avec `svc_backup`) ;
- de la réussite de l'exfiltration avant chiffrement (double extorsion).

Si les sauvegardes sont intactes, la victime a de bonnes chances de ne pas payer.

---

## 6. Exemples de contrats

| Palier | Contrat | Objectif | Particularité |
|---|---|---|---|
| 1 | Le cabinet Morel | Voler `contrats_2026.xlsx` sur FILE-01 | Bonus de 50 % si aucune alerte critique |
| 1 | Un concurrent jaloux | Récupérer les identifiants d'un utilisateur précis | Contrat de passage vers le palier 2 |
| 2 | Logistique Varenne | Compromettre le domaine (DCSync puis Golden Ticket) | Il faut Tor : NullVad seul ne résiste pas au traçage |
| 2 | Première affiliation | Chiffrer 60 % des hôtes avec Vesper | Introduit le ransomware |
| 3 | Groupe hospitalier fictif | Accès SSH acheté → domaine → exfiltration → chiffrement | Pas de phishing possible, route complète obligatoire |

---

## 7. Débriefing côté Blue

À la fin de chaque contrat, réussi ou non :
- la chronologie des logs que le joueur a générés, mêlés au bruit de fond ;
- les alertes SIEM déclenchées et l'action qui les a provoquées ;
- la progression du traçage à travers chaque intermédiaire ;
- un conseil : « Le 4663 sur lsass.exe t'a trahi. Casser le hash de `svc_backup` aurait évité l'alerte. »

C'est l'argument pédagogique et ce qui différencie le jeu.

---

## 8. Changements dans le moteur

| Élément | Où | Description |
|---|---|---|
| Brouillard de guerre | `models.py`, nouvel effet `reveal_host` | Red ne voit que les hôtes et services révélés par ses actions |
| Profil joueur | `models.py` + `persistence.py` | Palier, argent, réputation, inventaire, sauvegardé entre contrats |
| Route et traçage | nouveau `engine/trace.py` | Liste d'intermédiaires, jauge de traçage, arrestation |
| IA défenseur | nouveau `engine/blue_ai.py` | Utilise les abilities Blue existantes selon la suspicion et la difficulté |
| Prédicats | `predicates.py` | `player_owns(item)`, `player_tier_at_least(n)` |
| Effets | `effects.py` | `reveal_host`, `encrypt_host`, `exfiltrate_file`, `destroy_backups` |
| Commande de terminal | champ `"command"` dans chaque JSON | `psexec.py {user}@{target_ip}` traduit en action |
| Contrats | nouveau dossier `backend/contracts/` | Scénario + objectifs + palier + messagerie + prime + risque de piège |
| Boutique | nouveau `backend/catalog/shop.json` | Articles, prix, palier requis |
| Objectifs | `win_conditions.py` | Vol de fichier, chiffrement à X %, discrétion (aucune alerte critique) |

## 9. Ordre de réalisation

1. ✅ Brouillard de guerre + champ `"command"` + parseur de terminal (`engine/terminal.py`,
   `POST /api/games/{id}/terminal`, tests dans `tests/test_terminal_fog.py`)
1 bis. Tutoriel palier 0 : notification Chordly → lien BreachBoard → inscription en un
   clic (pseudo généré) → bounty → mission guidée pas à pas par le contact
   - ✅ Scénario `scenarios/tuto_p0.json` (Cabinet Ravelle & Associés, 3 machines, seul
     POSTE-ACCUEIL connu, aucun défenseur). Chemin : nmap → gophish → mimikatz → psexec.
   - ✅ Objectifs déclarés dans le scénario (`objectives`, registre
     `win_conditions.OBJECTIVES` : `host_compromised`, `domain_compromised`). Sans
     objectifs, le mode d'origine s'applique (domaine ou score).
   - ✅ Identifiants pilotés par le scénario : `primary_user` (cible du phishing) et
     `cached_logons` (récupérés par mimikatz) sur chaque hôte. Les abilities ne
     contiennent plus de noms d'utilisateurs.
   - ✅ Générateur de pseudo (`engine/handles.py`). Tests : `tests/test_tutorial.py`.
   - ✅ Contrats (`engine/contracts.py`, `contracts/tuto_p0.json`) : client, bounty du
     forum, prime, guide d'étapes `{when, message}` envoyées sur Chordly au fil de la
     progression, messages de réussite et d'échec, débriefing révélé à la fin. Si le
     joueur saute des étapes, seul le message de l'étape la plus avancée part.
   - ✅ API : `GET /api/contracts` (bounties, sans le guide), `GET /api/handles`
     (pseudos proposés), `POST /api/games` avec `contract` + `handle`. L'état renvoyé
     contient `messages`, `objectives` (avec `met`) et `contract`.
     Tests : `tests/test_contracts.py`.
   - ✅ Interface : faux bureau sur `/red` (`frontend/red.html|css|js`, prototype web retiré le 13 novembre 2026 au profit du client Godot). Invitation de
     k0rvid (champ `intro` du contrat) → BreachBoard (inscription en un clic, liste des
     annonces, « Accepter le job ») → Chordly (messages, objectifs) + terminal →
     rapport de fin avec le débriefing côté défense. Fenêtres déplaçables, version
     mobile empilée. Dans les textes de contrat, les commandes s'écrivent entre
     backticks pour être affichées en code.
2. Route, jauge de traçage, IA défenseur
3. Profil joueur, boutique, contrats (palier 1 jouable de bout en bout)
4. Faux bureau dans l'interface web : terminal, messagerie, forum, carte réseau
5. Débriefing côté Blue
6. Paliers 2 et 3 : Tor, ransomware, accès achetés
7. Portage dans Godot une fois la boucle validée
