# Réputation, accès et portefeuille — 0.4.1

## Réputation et progression

Chaque communauté possède sa réputation : `forum_reputation.breachboard`,
`exployt` et `xsx`. Une mission réussie augmente seulement la réputation du forum
qui porte le contrat. Le gain n’est attribué qu’à la première réussite du dossier,
et un même règlement de partie ne peut pas être répété. Les échecs et les
publications de messages ne créent aucun point. Les missions du prélude apportent
les premiers points sur la communauté d’origine, sans ouvrir le forum prématurément.

Le score historique `reputation` reste une confiance opérateur pour les conditions
des anciens contrats ; ce n’est plus le chiffre affiché sur tous les forums.
L’en-tête, le profil du joueur et ses messages affichent la réputation locale.

Pour une nouvelle carrière :

- BreachBoard : prélude terminé, dossier Ravelle réussi et confiance de départ.
- Boutique : Ravelle réussi, palier 1 et 40 points sur BreachBoard.
- Exployt : dix chapitres terminés, invitation explicitement acceptée, palier 2,
  100 points sur BreachBoard et route Tor active.
- XSX : recommandation après le dossier d’affiliation, palier 3 et 100 points sur
  Exployt, en plus de l’invitation de l’acte I.

Les conditions sont calculées par `engine/community.py`. L’API filtre les annonces,
refuse la lecture/publication des sujets verrouillés et refuse les achats trop tôt.
Les onglets et favoris non accessibles ne sont pas proposés par le client ; une
adresse saisie à la main ne permet pas de contourner les conditions. La boutique
est désactivée dans le menu et son ouverture est également contrôlée.
Les anciennes carrières conservent leur progression historique par palier.

## ColdVault, hors des forums

Les communautés n’ont plus de solde ni de portefeuille interne. Les fonds sont
consultables dans l’application de bureau **ColdVault**, un appareil matériel
fictif. Il utilise la monnaie du jeu (₵), sans connexion à une blockchain réelle
ni à un véritable appareil Ledger. Aucun PIN réel ni phrase de récupération
n’est demandé.

La boutique prépare un paiement payant avec montant et destinataire déterminés
par le moteur. Le joueur ouvre ColdVault, connecte l’appareil, le déverrouille et
confirme la demande. Le débit et l’acquisition se produisent alors ensemble.
L’API vérifie de nouveau les fonds et les conditions ; un identifiant déjà traité
ne peut pas servir à repayer. Refuser ou déconnecter annule la demande sans débit.
Les services gratuits sont activés directement, sans signature de montant nul.

Le journal enregistre le solde repris, les règlements de mission, les achats et
les frais de route. Les frais de route sont prélevés au premier départ du dossier et identifiés
séparément dans le journal. La route déjà réglée couvre les nouvelles tentatives
du même dossier ; ces passages sont conservés dans les sauvegardes.
La connexion, le déverrouillage et les demandes en attente sont temporaires :
ils ne sont pas restaurés lors d’un redémarrage ou d’un chargement de partie.

## Sauvegardes et migration

La monnaie existante est conservée à l’identique : le champ historique `money`
reste le solde canonique de compatibilité du portefeuille. Aucun montant n’est
copié par forum et la migration ne crédite aucun fonds supplémentaire.
Un mouvement d’ouverture reprend ce solde ; les opérations suivantes ont chacune
un identifiant et un solde après opération. Les nouvelles structures sont
validées et conservées dans les emplacements de sauvegarde.

Les réputations anciennes sont réparties selon les contrats terminés. Le reliquat
éventuel de l’ancien score reste sur BreachBoard ; il n’est pas recopié dans les
autres communautés. L’identifiant de l’appareil reste stable entre sauvegardes.
Les fichiers personnels du joueur ne sont pas modifiés par les tests.

## Vérification

`backend/tests/test_community_wallet.py` couvre les accès anticipés, les appels
API directs, les migrations, l’attribution unique, les confirmations, refus,
identifiants rejoués et erreurs de disque. `game/tests/test_progression_wallet.gd`
couvre la boutique verrouillée, les onglets, l’absence de solde sur les forums,
la réputation locale et les états de confirmation de l’appareil.

La passe de progression et d’équilibrage 0.4.4 est détaillée dans
[PARCOURS_ET_ECONOMIE.md](PARCOURS_ET_ECONOMIE.md).
