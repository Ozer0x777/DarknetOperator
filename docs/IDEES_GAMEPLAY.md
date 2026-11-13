# Prochaines améliorations proposées

Menu et sauvegardes sont désormais implémentés dans le client natif. Les idées
suivantes restent des propositions, dans cet ordre de priorité.

1. **Hashcat et RTX 5090** : vrais formats et fichiers, vrai dictionnaire autorisé,
   travail effectué par candidat, règles et masques avant d'ajouter d'autres GPU.
   Calibrer chaque algorithme et mode sur un benchmark identifié ; conserver des
   durées réalistes et un état Cracked/Exhausted exact. Un mot de passe absent du
   dictionnaire ne doit pas apparaître sans candidats correspondants.
2. **Diversifier les accès** : trois nouvelles missions avec des systèmes distincts,
   plutôt que changer uniquement les noms du parcours accueil → mémoire → serveur.
   - Le prestataire : compte SSH Linux limité, droits de fichiers et passation
     obsolète à confronter aux configurations courantes.
   - Le portail oublié : application interne, plusieurs rôles, données de test et
     production séparées, indices dans les tickets et le dépôt fictif.
   - Le tenant de test : applications cloud, jetons et permissions déléguées ;
     l'accès au compte ne doit pas donner accès à toutes les applications.
3. **Objectifs proportionnés** : distinguer récupérer un fichier demandé et copier
   tout un dossier. Faire compter les données superflues, les accès inutiles, le
   temps et les alertes dans la qualité du rapport, sans effacer un objectif réussi.
4. **Enquête et personnes** : de véritables dossiers de litige, des interlocuteurs
   avec informations partielles et mémoire, des horaires de maintenance et des
   incidents de service annoncés. Une fausse piste doit être réfutable par une preuve.
5. **Après l'incident** : dossier d'activité, sauvegardes locales/externes et reprise
   séparés. Pour la rançon, simuler des décisions et réponses avec plusieurs issues,
   sans confondre demande, paiement, restauration et suppression des copies.
6. **Débriefing causal** : relier chaque alerte à l'action, à la trace produite et au
   capteur capable de la voir. Distinguer observation, soupçon et confirmation.
   Cette structure servira ensuite au joueur Blue Team.

Stabiliser ces boucles dans le solo avant le mode Blue Team, puis développer le
multijoueur avec serveur autoritaire, vues par rôle, reconnexion et équité des
réactions. Le choix du nom définitif peut avancer séparément sans modifier les
chemins des sauvegardes avant qu'une migration soit prête.
