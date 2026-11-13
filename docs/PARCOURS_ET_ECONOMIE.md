# Parcours, conséquences et économie — 0.4.4

## Début de partie

Une nouvelle carrière commence avec 100 ₵ et le seul contact k0rvid. Huit
exercices courts introduisent lecture, reconnaissance, authentification,
transfert, comparaison de sources, campagne, dictionnaire et session Windows.
Le premier exercice verse 25 ₵. Le prélude complet mène à 440 ₵ et 40 points
sur BreachBoard, dont l’accès reste fermé jusqu’à la réussite de Ravelle.
Après Ravelle : 740 ₵, palier 1, communauté et fournisseurs accessibles.

L’accueil privé explique le parcours et la reprise. La carte de dossier indique
la prochaine piste, sa messagerie ou les MP du forum ; elle ne révèle aucune
commande ni identifiant futur. Elle reste combinée à l’offre lorsqu’une offre
est disponible, pour éviter deux cartes répétitives. Aucun achat n’est requis
pour terminer l’acte I. Les anciens dossiers Morel/Rival ne détournent plus une
nouvelle carrière de sa progression avant l’invitation de l’acte I.

## Conséquences

Les résultats alimentent un historique persistant et un retour privé du client :
règlement réel, réputation locale gagnée, prochaine piste et éventuelles alertes
critiques. La première livraison Ravelle reçoit une recommandation publique
sans révéler ses détails. Le choix publication/médiation du litige reste conservé.
Un échec ne verse rien, n’ajoute aucune réputation et ne retire aucun accès.
Les échecs répétés modifient le retour du client et invitent à reprendre les
observations ou demander un indice. Ils ne sont pas publiés sur le forum.

Une seule prime et un seul gain de réputation sont attribués par dossier,
y compris avec un nouvel identifiant de partie. Les relectures restent possibles,
avec la mention « Déjà réglé » et une prime disponible de zéro. Les primes
bonus ne peuvent pas être répétées non plus.

## Achats et routes

La boutique explique l’effet, le prix et le motif d’un refus avant la demande
de signature ColdVault. Un achat payant ne débite rien avant confirmation ; le
prix et l’éligibilité sont revérifiés au moment de signer.

- Dictionnaire premium : 150 ₵, ensemble enrichi distinct du gratuit dans
  `~/wordlist.txt`. Son utilisation avec Hashcat retire deux ticks au délai,
  sans inventer de correspondance ni garantir un mot de passe.
- GPU : valeurs 400 / 1 200 / 3 000 ₵ ; délais de base 9 → 5 → 3 → 2 ticks.
  La valeur du meilleur modèle possédé est déduite lors d’une amélioration.
  Les délais peuvent aussi dépendre de la route et du dictionnaire.
- Vesper : activation gratuite, part opérateur de 30 % sur les seuls contrats
  marqués affiliation.
- Glasswing : licence permanente de 450 ₵, part de 100 % sur ces mêmes contrats.
  Les sauvegardes et autres conditions continuent à moduler le montant. La
  licence peut être moins rentable que l’affiliation gratuite selon le parcours.
  Le grand compte conserve sa règle propre, sans cette retenue ; il ne faut pas
  compter un gain de licence sur ce dossier.

Un premier départ par NullVad/Tor coûte 50 ₵ par dossier ; le passage SSH est
consommé au premier départ par relais. Le droit de reprendre ce même dossier
par la route déjà réglée persiste dans les sauvegardes, même après un échec.
Un nouveau dossier ne réutilise pas le passage SSH d’un autre. Cela évite qu’une
succession d’échecs épuise les fonds nécessaires à une route imposée.

Pour les nouvelles carrières après invitation, une dépense facultative ne peut
pas entamer la réserve du prochain accès obligatoire : 50 ₵ pour Varenne, puis
300 ₵ pour un relais de grand compte dès Varenne validé, s’il n’est pas déjà
acquis ou couvert. Cette réserve reste donc protégée avant l’affiliation.
Le service gratuit reste activable. Le matériel et la route sont appliqués
au départ de la mission ; un achat ne modifie pas une mission déjà commencée.

## Qualification reproductible

`backend/act1_validation.py` vérifie le prélude et les dix chapitres, deux voies
finales, les huit petits contrats et les reprises. Après Ravelle, il prépare le
premier achat de 150 ₵, vérifie l’absence de débit avant signature, refuse une
signature sans appareil déverrouillé, confirme, refuse le rejeu puis recharge
une sauvegarde contenant les 590 ₵ restants et le dictionnaire acquis. Chaque
ligne du journal est rapprochée du solde.

`backend/journey_validation.py` prolonge deux carrières neuves jusqu’au grand
compte par les commandes publiques, sans créditer ni débloquer le profil :
une voie Vesper et une voie Glasswing. Sur les parcours de référence avec tous
les petits contrats : solde après acte I 4 440 ₵ ; solde final 9 222 ₵ avec
Vesper, 9 140 ₵ avec Glasswing. Ce dernier écart illustre le risque du coût de
licence lorsque les sauvegardes réduisent la rémunération d’affiliation.
Les chiffres décrivent ces choix de référence, pas toutes les façons de jouer.

`backend/tests/test_journey_economy.py` couvre notamment les primes rejouées,
les routes après échec et rechargement, les réserves, les effets matériels,
les conditions d’affiliation et les conséquences persistantes.
`game/tests/test_journey.gd` vérifie la piste, son application cible, les fiches
d’achat et la rédaction dans une fenêtre de 600 × 420 px.

Ces parcours accélèrent le temps et ne mesurent pas une première heure humaine.
Les tests API s’exécutent en mémoire et les vues sont des exports de composition.
Une partie manuelle avec affichage et audio réels reste à éprouver sur Linux.
