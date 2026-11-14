# Acte I - apprentissage et continuité (0.4.8)

L’acte reste composé de dix chapitres, avec les mêmes objectifs, règlements et
accès. Aucun achat supplémentaire n’est requis. Demander des indices ne diminue
ni la prime ni la réputation et ne déclenche aucune décision à la place du joueur.

| Passage | Ce qui est accompagné | Ce que le joueur doit décider |
|---|---|---|
| Ravelle | Première chaîne complète, résumés et carnet de leçons | Vérifier services, comptes et contexte de console |
| Une porte oubliée | Syntaxe SMB, distinction partage/fichier, transfert | Choisir la référence et la version courantes |
| Échantillon gratuit | Import SQLite et structure de la table | Calculer les effectifs par date ; chiffres absents du briefing |
| Derrière la boutique | Première utilisation SQLmap par phases | Identifier le paramètre puis le bon périmètre d’export |
| Le carnet d’adresses | Rappel authentification / autorisation | Choisir les réponses à comparer et la bonne pièce |
| Le mot de passe de trop | Rappel Hashcat, SSH et SCP déjà rencontrés | Vérifier un accès encore valable, puis la copie |
| Un service fragile | Protections, symboles, script fourni, session puis SQL | Relier les observations aux paramètres et respecter les droits |
| Mauvaise adresse | Aide distincte pour attribution, cible, récupération | Contester le brief sur preuves avant d’agir |
| La réputation se paie | Rappel des pièces et de la visibilité des décisions | Composer la comparaison puis choisir public ou privé |
| Quelqu’un répond de toi | Objectif, périmètre et deux familles de méthodes | Retrouver les points d’entrée et livrer les seules lignes valides |

## Aide adaptée aux observations

Pour SMB, SQLite, SQLmap et ticketd, chaque phase possède deux indices puis un
rappel détaillé. Le compteur est distinct par phase et sauvegardé. Le passage à
la phase suivante dépend des preuves réellement observées ; avoir épuisé les
indices ne suffit pas. Une preuve modifiée peut nécessiter une nouvelle lecture.
Si toutes les preuves sont réunies, l’aide rappelle comment confirmer le rapport.
Elle n’impose pas de faire une observation facultative utilisée seulement pour
accompagner le raisonnement.

Dans Mauvaise adresse, les indices ne passent pas à une étape future tant que
le compte rendu précédent n’est pas confirmé. La finale reste à deux voies :
les adresses exactes ne figurent plus d’emblée dans le briefing, mais les sources
et l’aide détaillée permettent toujours de les retrouver.

Les dossiers proposent ~/mission/reperes.txt. Pour ticketd, les repères expliquent
NX, les symboles, l’offset fourni dans le fil et le rôle du script du laboratoire.
Il s’agit d’un exercice accompagné ; aucune écriture d’exploit n’est demandée.
Les commandes restent dans les consoles du jeu.

## Relations et conséquences

Des retours privés suivent la première réussite de Nacre, Pivoine, du planning,
de Mauvaise adresse et du litige. Les offres suivantes reprennent ces références.
Les fiches de k0rvid, hexcache, 0xvanta et nullroute reflètent le travail effectué.
Nullroute reconnaît explicitement que le joueur a corrigé son tableau.

Bytewarden conserve la distinction entre publication et médiation privée. Cette
décision modifie sa réaction, sa fiche, le briefing de recommandation et le texte
de l’invitation finale. Le choix privé ne bloque pas l’invitation et ne force
aucune publication ultérieure. L’invitation mentionne aussi la voie réellement
utilisée lors de la finale. Les primes des deux voies restent identiques.

Les relations du dossier facultatif Le contretemps et sa prime de confiance
restent compatibles. Les nouveaux retours utilisent des identifiants fixes ;
rejouer ne duplique pas les réactions et ne remplace pas la décision de carrière.
Sur une ancienne carrière, les fiches peuvent être déduites de la progression
conservée ; les messages de première réussite ne sont pas réémis rétroactivement.
Une mission active mise à jour reçoit les repères manquants sans écraser les notes.

## Vérification et limites

Les tests ciblent les changements de phase, leurs compteurs après sauvegarde,
les preuves manquantes, les dépendances d’enquête, les choix persistants et la
migration d’une mission active. Les deux parcours complets de qualification
contrôlent aussi les réactions, les fiches et les deux textes d’invitation.
La solution complète de chaque dossier reste dans ACTE_I.md.

Cette passe ne mesure pas la difficulté humaine. Une première partie avec un
vrai débutant et une session graphique native complète restent nécessaires avant
de considérer le rythme et le rendu comme validés pour une sortie commerciale.
