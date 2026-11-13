# Démo, dossier ouvert et relations — 0.4.7

La création d’une partie propose Campagne complète (par défaut) ou Démo.
Une ancienne sauvegarde continue en campagne. La démo comprend :

1. Prendre ses marques : lire la préparation locale.
2. Lire le réseau : scanner le réseau annoncé.
3. Comparer les sources : comparer les deux documents puis consigner la conclusion.
4. Le contretemps : choisir sa source, vérifier le registre et décider de sa transmission.

Les trois exercices sont ceux du prélude, présentés dans cet ordre pour la démo.
Leur solution figure dans PRELUDE_CHORDLY.md. La démo se termine sur une carte
Chordly chez miette, avec le bilan de la décision et Continuer la campagne.
Ce bouton conserve les primes, fichiers, décisions et relations. Le prochain
exercice est Vérifier un accès ; les exercices déjà réussis ne sont pas répétés.
Le solde de fin de démo est 340 ₵, dont les 100 ₵ initiaux. Les communautés et
la boutique restent verrouillées jusqu’au vrai contrat Ravelle en campagne.
Aucun achat n’est nécessaire dans la démo ou l’acte I.

## Le contretemps

Dans la campagne, la proposition privée de miette arrive après Une porte oubliée.
Ce dossier facultatif ne bloque aucun des dix chapitres de l’acte I.
Une annonce du 6 novembre marque CT-26-071 livré par anticipation. Le registre
courant du 9 novembre reporte la livraison au 12. Le journal facultatif explique
l’annulation du transport le 8 : une annonce n’est pas une preuve de réception.
La lecture de ce journal aide à comprendre la contradiction sans conditionner la prime.

Deux voies équivalentes (tout se passe dans le laboratoire simulé) :

```sh
nmap -sV 10.62.1.10
curl http://10.62.1.10/
curl http://10.62.1.10/archive.txt
curl http://10.62.1.10/journal.txt
curl -o ~/loot/preuve.txt http://10.62.1.10/suivi.txt
cat ~/loot/preuve.txt
```

Ou :

```sh
smbclient -L 10.62.1.10 -N
smbclient //10.62.1.10/public -N -c "ls"
smbclient //10.62.1.10/public -N -c "get courant/CT-26-071.txt /home/operator/loot/preuve.txt"
cat ~/loot/preuve.txt
```

Dans Chordly, confirmer par exemple :

- « CT-26-071 est reporté, source web : je choisis signaler. »
- « CT-26-071 est reporté, source partage : je choisis discret. »

Les deux décisions conviennent avec les deux voies. Le rapport doit mentionner
la référence, le report, la source utilisée et une seule décision. La copie doit
être intacte et relue après son dernier transfert. Une archive, une copie
retouchée ou une simple déclaration ne remplace pas cette vérification.
Les noms de fichiers dans ~/loot sont libres. Écrire indice fournit une aide
progressive ; le rappel détaillé indique les syntaxes du laboratoire.

## Conséquences

Les deux issues paient 140 ₵ et établissent la confiance de miette.
Signaler déclenche une correction écrite de l’annonce dans le récit ; bytewarden
inclut 30 ₵ de confiance dans la recommandation finale si elle reste à faire.
Discret garde les preuves chez le client ; une prime de 30 ₵ est incluse dans
la première offre encore à faire parmi Échantillon gratuit, Derrière la boutique
et la recommandation finale. Cette offre est fixée à la résolution du dossier.
Si les trois sont déjà réglées, aucun règlement passé n’est recalculé.

Les conditions figurent dans l’offre et le briefing avant acceptation. Le détail
du contact montre la relation ; parler de confiance ou de CT-26-071 obtient une
réponse liée à la décision. La relation s’appuie sur la décision de carrière
sauvegardée. Rejouer ne la remplace pas et ne reverse aucune prime.

## Vérification

`backend/.venv/bin/python backend/demo_validation.py` joue les quatre
combinaisons via l’API en mémoire avec profils temporaires, rechargement avant
la décision et en fin de démo, rejeu sans nouvelle prime et poursuite en campagne.
`test_demo.py` vérifie aussi archives, lecture à jour, intentions ambiguës,
accès et versement unique de la prime de confiance. `game/tests/test_demo.gd`
contrôle la conclusion, le bouton de poursuite et le contact choisi en 720p et
fenêtre compacte. Ces contrôles sans affichage ne remplacent pas une session
graphique native ni un test humain de durée ou de difficulté.
