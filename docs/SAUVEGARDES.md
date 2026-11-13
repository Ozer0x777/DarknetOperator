# Accueil et sauvegardes — client Godot

Le jeu démarre maintenant sur le menu d'accueil : Continuer, Nouvelle partie,
Sauvegardes / Charger, Paramètres, Crédits et Quitter. Le nom RedTeamSimulator
reste provisoire. Les paramètres du menu permettent le plein écran ; les réglages
de mission restent accessibles sur le bureau.

## Parcours joueur

- **Nouvelle partie** : choisir un pseudo ; le bouton Créer confirme la création.
  La carrière courante est d'abord archivée dans un emplacement manuel dès qu'elle
  contient quelque chose (dossier terminé, mission, fichiers du bureau, achats,
  messages écrits). Une carrière vierge, ou déjà archivée à l'identique, ne crée
  pas d'emplacement. Si l'archive ne peut pas être écrite, la nouvelle partie est
  refusée et la carrière courante reste intacte.
- **Autosauvegardes** : trois emplacements tournants, qui contiennent toujours
  trois états différents ; un état déjà présent n'en écrase pas un plus ancien.
  Une autosauvegarde impossible n'interrompt jamais la partie.
- **Entre deux contrats** : le poste Kali est conservé (fichiers locaux, consoles
  et leur texte, GoPhish, potfile de hashcat). Les preuves, scans et réactions de
  la cible appartiennent à leur mission et ne sont pas repris ; un hash déjà dans
  le potfile doit être cassé ou relu (`--show`) pendant la mission pour compter.
- **Continuer** : reprendre la carrière courante. Si une mission est active,
  ses consoles sont recréées et la mission est reprise ; sinon le bureau s'ouvre.
- **Sauvegardes / Charger** : sélectionner un emplacement pour consulter le nom,
  la date UTC, la mission, l'opérateur, le palier, l'argent, le tick et le temps
  cumulé en mission. Le temps au menu n'est pas compté.
- **Nouvel emplacement** : nommer une sauvegarde manuelle de la carrière entière.
- **Écraser, Charger, Supprimer** : confirmation obligatoire. Les autosauvegardes
  ne s'écrasent pas manuellement avec le bouton Écraser.
- **F5 sur le bureau** ou **Paramètres → Sauvegarder la partie** : nouvel
  emplacement manuel horodaté. Échap ouvre les paramètres ; ce raccourci seul
  ne suspend pas la mission. Le bouton Pause / Reprendre reste disponible.
- **Sauvegarder et revenir au menu** : suspendre la mission, écrire l'état courant
  et forcer une autosauvegarde. Le menu n'abandonne pas le contrat.
- La fermeture par la croix du client principal passe également par cette
  sauvegarde. Une erreur signalée empêche cette fermeture normale afin de ne pas
  prétendre avoir conservé une progression non écrite.

## Contenu et emplacements

Sous Linux, le dossier par défaut est `~/.local/share/RedTeamSimulator/`.
`REDTEAM_SAVE_DIR` permet d'en choisir un autre. Les emplacements Windows et macOS
restent ceux de Career.default_path().

- `career.json` : carrière courante, écriture atomique avec fsync du fichier.
- `career.previous` : copie précédente du profil courant.
- `slots/manual-<identifiant>.json` : sauvegardes manuelles nommées.
- `slots/auto-0.json` à `auto-2.json` : trois autosauvegardes tournantes. Au plus
  une écriture automatique par minute lors des checkpoints, plus une écriture
  forcée au retour au menu.
- `slots/recovery.json` : carrière avant le dernier chargement, pour revenir sur
  un chargement accidentel. Ce n'est pas un historique illimité de chargements.
- `career.corrupt-*.json` : copie d'un profil endommagé lors d'une récupération
  automatique depuis career.previous.

Un emplacement contient la progression, les gains, achats, contrats réglés,
conversations, messages de forum, le bureau virtuel enregistré, ainsi que l'état
de la mission : consoles, connexions, variables, outils, authentification en
attente, actions en file, personnages et RNG. Charger remplace la carrière
entière, y compris l'argent et les achats, et ferme les anciennes sessions moteur.
Les consoles du bureau hors mission sont aussi recréées au chargement.

Les textes saisis mais pas envoyés, la sélection, le presse-papiers, la disposition
précise des fenêtres et l'historique purement visuel des lignes saisies ne sont
pas encore conservés. L'historique des actions du moteur est conservé.
Aucune miniature, synchronisation Steam Cloud ou sauvegarde multijoueur n'est
annoncée comme implémentée.

## Intégrité et récupération

Chaque emplacement utilise un format versionné (actuellement 1), un checksum
SHA-256 et une validation de la structure du profil et de la mission. Il s'agit
d'une protection contre la corruption, pas d'un système anti-triche.
Les fichiers temporaires sont remplacés atomiquement après écriture.

Un emplacement invalide est signalé et ne peut pas être chargé. Le chargement est
validé avant de modifier la carrière. Une carrière courante endommagée récupère
la copie précédente si elle est valide. Si les deux copies sont abîmées mais qu'un
emplacement valide existe, le menu propose sa récupération sans réécrire les fichiers
abîmés. Sans aucune copie valide, le moteur signale l'erreur et conserve les fichiers.
Une future version de format inconnue est refusée ; la migration de nouveaux formats
reste à écrire lorsqu'ils existeront.

Le lanceur verrouille le dossier avant de charger ou récupérer le profil, pour
éviter deux moteurs écrivant simultanément. Cette gestion concerne le solo local.

## Qualification

Tests moteur : intégrité, confirmations, noms de fichiers, rotation, copie
précédente, récupération explicite, profil manquant, chargement non destructif
en cas d'erreur, reprise d'une invite et restauration des consoles du bureau.
Godot : actions du menu, création de carrière, détails d'un emplacement,
confirmation avant chargement et navigation menu → bureau → menu.
Les tests API utilisent des carrières temporaires ; ils ne réinitialisent pas la
sauvegarde du joueur. Les aperçus vectoriels ne remplacent pas un essai graphique
sur une machine avec affichage réel.
