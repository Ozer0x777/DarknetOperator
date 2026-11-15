# Revue du premier arc de Madame_TLS

L'arc « Tenir la forme » comporte cinq scènes après le choix du premier lien.
Il commence après sa rencontre liée au portail de l'acte I. Les formulations
suivent le lien professionnel, amical ou attiré ; les envois de pièces et les
réserves sur les sources ont leurs propres conséquences.

## Préparer une partie de revue

Depuis la racine du dépôt :

```bash
backend/.venv/bin/python backend/tls_arc_validation.py build/validation
```

Cette qualification passe par l'API et crée trois carrières d'essai juste avant
l'exposition, dans `build/validation/tls-arc-playtest/`. Leur contexte de campagne
est déjà acquis pour permettre de relire l'arc sans rejouer tout l'acte I.
Ce ne sont pas des mesures de progression ou d'économie d'une nouvelle partie.

Pour essayer le lien amical sans toucher à la carrière habituelle :

```bash
REDTEAM_SAVE_DIR="$PWD/build/validation/tls-arc-playtest/amitie" ./run.sh
```

Remplacer `amitie` par `professionnel` ou `attirance` pour les autres points de
départ. Depuis le menu, continuer puis ouvrir Chordly et la conversation de
Madame_TLS. Le lancement utilise le moteur et le client normaux ; les échanges
restent dans le monde du jeu. Relancer la qualification réinitialise uniquement
ces carrières de revue.

## Ce qu'il faut observer

- Comprend-on ce qu'elle demande, avant de choisir ? Les réponses expriment-elles
  des positions distinctes, sans annoncer une option « correcte » ?
- Peut-on la contredire sur le mécénat sans avoir l'impression de perdre son lien ?
- Le passage d'une pièce publique à une note privée est-il perceptible avant
  l'envoi ? Le nom de la source est-il explicitement visible ?
- Quand on refuse la note, remarque-t-on BRUME-17 dans le retour et retrouve-t-on
  les pièces à comparer ? Quand on l'envoie, comprend-on que cette connaissance
  vient de nous et ne prouve pas à elle seule une infiltration ?
- La dernière réponse et le lien choisi sont-ils conservés après fermeture ?
- La question et les trois boutons sont-ils lisibles dans une petite fenêtre ?

Les pièces reçues se lisent dans les conversations de leur auteur. Des copies
locales sont dans `~/dossiers/madame_tls/`. Le message envoyé conserve le texte
exact de la pièce jointe ; le bouton n'envoie pas une copie locale modifiée.

## Périmètre de validation

`tls_arc_validation.py` qualifie trois parcours API et 36 chargements d'emplacements
manuels. `game/tests/test_tls_arc.gd` rejoue leurs réponses dans les contrôles du
client. Les tests moteur couvrent aussi les combinaisons de lien et de transmission,
la stabilité d'une question déjà reçue et les fichiers partagés entre missions.
Les aperçus 68 à 71 montrent le désaccord, la demande privée et les deux retours.

Ces contrôles ne mesurent ni la compréhension d'un débutant ni la durée réelle.
Un testeur peut jouer sans aide, puis décrire à quel moment il a fait confiance
ou commencé à douter. La révélation complète de l'espionne reste hors de cet arc.


## Suite Lenoir livrée

Trois nouvelles scènes prolongent cet arc pendant l'acte III : pause après le
dossier 9, demande du lot après le dossier 12 et retour selon le document envoyé.
Le lot provient du téléchargement vérifié, pas d'un gain d'affection. Le joueur
peut refuser, envoyer la synthèse autorisée ou joindre le lot confidentiel complet.
Les neuf combinaisons de lien et d'envoi sont couvertes dans
`backend/tests/test_act3_narrative.py`. La synthèse masque les informations
commerciales ; la copie intégrale envoyée garde ses octets et son empreinte.
La révélation complète et le piège final restent hors de ces trois scènes.
