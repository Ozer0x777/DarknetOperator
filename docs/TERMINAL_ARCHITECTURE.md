# Terminal : cible de fidélité et limites

Le terminal graphique, le shell et le système de fichiers sont trois couches
séparées. Une présentation crédible ne suffit pas à reproduire Bash, cmd ou
PowerShell. Le jeu vise un ensemble cohérent de comportements testés, pas une
promesse « Linux et Windows à 100 % ».

## Correction actuelle de la saisie

La saisie utilise un éditeur TextEdit avec retour visuel à la ligne : une longue
commande reste une seule commande logique. Elle n'est pas tronquée au début par
le défilement horizontal d'un LineEdit. Entrée soumet ; la saisie secrète n'affiche
pas les caractères. Le repliement, l'insertion au début, le collage, la sélection,
l'historique et les rafraîchissements de contexte sont vérifiés séparément.
Le texte non envoyé et les secrets partiellement saisis ne sont pas sauvegardés.

## Fichiers actuellement couverts

Dans Kali : mkdir, touch, cp, mv, rm, rmdir, ll, et les ls/cd/cat existants.
Dans cmd : mkdir/md, copy, move, del/erase, rmdir/rd, et dir/type/cd existants.
Dans PowerShell : Remove-Item et ses alias de suppression, Set-Content,
Add-Content, New-Item -ItemType Directory, et les commandes déjà couvertes.
Les redirections textuelles > et >> sont couvertes dans le sous-ensemble décrit.
Chaque commande signale les options qui ne sont pas prises en charge.

Les fichiers et dossiers sont partagés entre consoles de la même machine et
conservés dans les sauvegardes. Les chemins Windows sont distingués des chemins
Linux. Les droits d'écriture sont simplifiés : utilisateur local dans son home et
/tmp ; utilisateur Windows dans son profil ; SYSTEM dans les autres dossiers du
modèle. Ce ne sont pas des ACL Windows ou des permissions POSIX exhaustives.
Les suppressions ne touchent jamais les fichiers du système hébergeant le jeu.

## Journaux et futur rôle Blue Team

Les mutations de fichiers disposent d'un journal moteur distinct : machine,
console, identité, opération, chemin et empreintes avant/après. Modifier un fichier
accessible au personnage ne réécrit pas ce journal d'autorité, ni les alertes déjà
émises. Le débriefing et la future Blue Team pourront exploiter cette distinction.
Il ne s'agit pas encore d'une simulation complète de la collecte et rétention.

Un journal applicatif texte, le fichier Security.evtx de Windows et les événements
centralisés d'un collecteur ne sont pas des formats ou des objets équivalents.
Ne pas présenter l'édition d'un texte comme l'émulation fidèle d'un événement
Windows. Le modèle EVTX, les collecteurs, les éditeurs nano/vim et les outils de
journalisation spécialisés restent à développer.

## Suite recommandée

- Un registre de commandes par shell, avec options, prérequis, effets et erreurs.
- Une seule API de fichiers pour toutes les commandes, les transferts et les
  outils, puis métadonnées, liens, droits détaillés et horodatages.
- Des processus virtuels, stdin/stdout/stderr et codes de sortie ; ensuite les
  pipes et redirections complexes. Une option inconnue doit rester une erreur.
- Des tests de comportement à partir des shells et versions choisis dans un
  laboratoire contrôlé, puis des essais graphiques avec de longs chemins et du
  texte international. Les tests headless seuls ne certifient pas le rendu réel.
- Un éventuel véritable émulateur VT/ANSI pour les interfaces terminal plein écran.
  Cela ne nécessite pas de donner au terminal du jeu le shell de la machine réelle.
