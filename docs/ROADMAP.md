# Feuille de route : suivi de réalisation

La proposition [Acte III : Les frontières invisibles](ACTE_III_PROPOSITION.md)
décrit douze missions sur huit segments, les outils de transport prévus et
l'exigence de résolution sans recherche sur Internet. La [couverture livrée](ACTE_III_COUVERTURE.md) décrit les douze dossiers
jouables et les limites des outils et de l'infrastructure.

## État courant - 0.6.0, passe narrative du 15 novembre 2026

L’acte I courant comporte sept exercices privés, dix chapitres et sept petits
contrats facultatifs, sans achat payant obligatoire. Les anciennes sauvegardes
sont adaptées avec conservation des dossiers en cours et des acquis ; voir
[ACTE_I_ACTUEL.md](ACTE_I_ACTUEL.md). L’acte II livre dix missions et six contrats
facultatifs, avec inventaire système, Polkit, tunnel SSH, LDAP, analyse de graphe
et outils simulés ; les limites sont décrites dans
[ACTE_II_COUVERTURE.md](ACTE_II_COUVERTURE.md).
La [passe de finition](FINITION_ACTE_I.md) couvre les consignes, les offres et la réserve de route.
L’acte III livre douze missions : découverte, Chisel, ProxyChains, Evil-WinRM,
droits LDAP, profils Defender, anti-tamper, second pivot, repli et lot industriel.
Les six derniers dossiers déclarent 38 machines sur huit segments ; les systèmes
secondaires et le domaine Aster ont une couverture limitée, détaillée dans le guide.
La persistance continue du réseau, l’acte IV, Steam et les essais humains restent à poursuivre. Les sections suivantes conservent l’historique du plan.

La passe narrative reprend les sujets du forum, les contacts, les événements
sociaux et les échanges des clients. Madame_TLS prépare un intérêt amoureux
possible dont la proximité sert sa mission d'espionne contre le joueur.
Trente et une scènes à trois réponses et les liens persistants sont présents.
Un premier arc de cinq scènes avec Madame_TLS relie goûts, désaccord, veille
économique, transmission de pièces et soupçon vérifiable, pour les trois liens.
La révélation et les conséquences de la trahison restent à développer. Voir
[RELATIONS_NARRATIVES.md](RELATIONS_NARRATIVES.md) pour la séparation entre
contenu livré et branches futures.

Les [forums et portraits orbitaux](FORUMS_ET_AVATARS.md) disposent de catégories,
de repères de lecture persistants, de dix-neuf avatars et de trois bannières avec
personnage féminin. Les portraits des sujets larges et des profils font 200 pixels.


Le document `03-red-progression.md` décrit la vision d'origine. Ce suivi distingue
la boucle jouable présente de ce qui reste nécessaire pour une version commerciale.

| Étape du plan | État au 11 novembre 2026 |
|---|---|
| Brouillard de guerre et tutoriel | Présents ; API filtrée et temps du tutoriel arrêté pendant la lecture |
| Route, traçage, défenseur | Présents ; exposition sans arrestation, confinement temporaire et reprise des accès |
| Profil, boutique, contrats de palier 1 | Présents ; sauvegarde atomique, argent, réputation, inventaire et missions |
| Bureau, terminal, messagerie, forum, réseau | Client Godot refondu : Xfce, trois messageries, navigation et publication sur les forums |
| Débriefing côté défense | Présent : historique, alertes, événements, traçage, règlement et conseils |
| Paliers 2 et 3 | Campagne jouable : Tor, affiliation, accès SSH, exfiltration et chiffrement |
| Portage Godot | Interface portée maintenant ; moteur Python conservé et paquet autonome préparé |

Un test enchaîne les six contrats, les passages de palier, les achats et les
sauvegardes jusqu'à la mission finale. L’offre urgente reste optionnelle et rémunère désormais une réussite vérifiée.

## Ce qui n'est pas encore terminé

- Fidélité exhaustive des outils et des retours : voir `COMMANDES.md`.
- Compléter les shells Linux/Windows désormais partiellement distincts, puis PowerShell et les processus détaillés.
- Outils John, BloodHound, evil-winrm, RDP et variantes de contrats associées.
- Enquête plus détaillée : les jauges actuelles sont un modèle de jeu, pas une
  reproduction d'une procédure d'investigation réelle.
- Approfondir les litiges et les preuves des vendeurs : les discussions actuelles
  sont des événements écrits, pas encore un système complet de transactions.
- La négociation de rançon, les variantes d'accès et les familles de ransomware
  ne disposent pas encore de parcours narratifs complets.
- Travail visuel, sons, retours de testeurs, accessibilité et équilibrage sur durée.
- Construction et validation des paquets PC, puis intégration et publication Steam.

La version 0.4.0 est une base de campagne jouable en développement. Elle n'est pas
présentée comme une version commerciale achevée ni comme une émulation intégrale
de Kali ou des outils de sécurité.

## Révision du réalisme et des communautés

Douze parcours et six défaites passent par l’API et les commandes du terminal,
avec 42 sauvegardes/reprises. Les environnements, réseaux et comptes sont distincts.
Le détail de la validation et les critères restant à remplir sont dans
[REALISME.md](REALISME.md). Dix-huit sujets, des archives, des groupes et des échanges
différés persistants constituent la première série de contenus sociaux écrits.
La reproduction visuelle exacte des services et la validation graphique manuelle
restent ouvertes ; elles ne sont pas couvertes par les tests headless.

## Corrections suivantes du réalisme

Les anciennes syntaxes sont retirées. Les sessions cmd/PowerShell, le déploiement
SCP/SMB, les statuts de sortie, les fichiers Hashcat et l’authentification cohérente
sont désormais couverts. Les victimes ont des décisions contextuelles variables
hors tutoriel et les contacts des horaires partagés avec les réponses.
La qualification comprend 12 réussites, 6 défaites, 42 reprises et un rejeu du client
Godot. La fidélité exhaustive et les essais graphiques réels restent à vérifier ;
voir la matrice et les limites dans REALISME.md.

## Ordre de développement retenu

1. Solo Red Team : approfondir les protections, topologies, indices vérifiables,
   objectifs et débriefings. Les politiques réseau et EDR sont des données séparées
   des commandes et de l'interface ; elles sont conservées dans les sauvegardes.
2. Blue Team jouable : télémétrie, enquêtes, règles et interventions adaptées à
   un joueur défenseur. Le mode solo actuel n'expose aucun contrôle Blue jouable.
3. Multijoueur : serveur autoritaire, vues filtrées par rôle, synchronisation,
   reconnexion et validation des actions. Les registres existants ne constituent
   pas à eux seuls un multijoueur sécurisé ; cette étape reste à réaliser.

La révision actuelle ajoute des politiques EDR explicites (audit/blocage), des
règles réseau par origine, des documents anciens contredits par une migration,
des litiges de vendeurs et une analyse des conséquences de l'incident.

## Menu d'accueil, nom et sauvegardes - exigences utilisateur

Exigences retenues, désormais partiellement livrées :
- Un véritable menu avant le bureau, avec Continuer, Nouvelle partie, Charger,
  Paramètres, Crédits et Quitter ; états disponibles selon le profil enregistré.
- Nom commercial définitif à choisir, puis identité cohérente dans le menu,
  le lanceur et les paquets. Conserver une migration des chemins de sauvegarde.
- Plusieurs emplacements nommés, scénario, date et temps de jeu visibles ;
  autosauvegardes tournantes et sauvegardes manuelles séparées.
- Charger un point antérieur, confirmer écrasement/suppression, gérer les versions
  et récupérer une copie valide après erreur. Prévoir reconnexion et sauvegarde
  autoritaire seulement lorsque le multijoueur sera développé.

Le menu d’accueil, les emplacements manuels, trois autosauvegardes tournantes,
les confirmations et la récupération sont désormais livrés dans le client natif.
Le temps cumulé en mission est enregistré. Miniatures, disposition complète des
fenêtres, nom commercial et Steam Cloud restent ouverts. Voir [SAUVEGARDES.md](SAUVEGARDES.md).
Le [guide complet des scénarios](GUIDE_COMPLET_SCENARIOS.md) contient les parcours,
leurs commandes, les paiements vérifiés et les limites pédagogiques actuelles.

La prochaine série de propositions de gameplay et de nouveaux scénarios est dans
[IDEES_GAMEPLAY.md](IDEES_GAMEPLAY.md). Elle n'est pas annoncée comme implémentée.

## Cadre narratif revu

BreachBoard constitue désormais la cible de l'acte 1 d'une campagne plus longue.
Les actes suivants et leurs durées restent à construire : [CAMPAGNE_LONGUE.md](CAMPAGNE_LONGUE.md).
La fidélité des consoles et le futur traitement des journaux sont détaillés dans
[TERMINAL_ARCHITECTURE.md](TERMINAL_ARCHITECTURE.md).


## Acte I en dix chapitres

Dix chapitres, huit petits contrats, propositions dans les MP, recommandations
Chordly, choix public/privé et finale à deux voies sont implémentés. L’invitation
est reçue puis acceptée dans les MP. Les anciennes sauvegardes conservent leur
parcours et leurs accès. [Guide et limites](ACTE_I.md).
Les essais automatisés ne prouvent pas 4 à 6 heures de jeu ni une émulation exhaustive.

## Proposition de prochaine tranche de campagne

[Acte II - La chaîne de confiance](ACTE_II_PROPOSITION.md) décrit six missions
et recommande de commencer par deux dossiers complets et reliés. C’est une
proposition de conception, distincte des chapitres déjà jouables de l’acte I.

## Passe acte I - 12 novembre 2026 (0.4.8)

Consignes graduées, aide liée aux phases observées et repères locaux intégrés.
Les réactions et la recommandation reflètent les décisions conservées.
Il reste à mesurer la compréhension, le rythme et la difficulté avec un vrai
débutant, puis à valider une session graphique native complète. Les contrôles
automatisés ne remplacent pas ces deux étapes.

## Acte II - 0.5.0

Dix dossiers, six secondaires, quatre nouveaux contacts, inventaire système,
redirection SSH, annuaire, collecte et graphe sont intégrés. Voir
[ACTE_II_COUVERTURE.md](ACTE_II_COUVERTURE.md) pour les limites.
La redistribution des passages avancés de l’acte I, les shells complets, la
validation native et les essais de rythme restent à faire.
