# Essai de compréhension de l'acte III — 30 minutes

Statut : protocole et carrière disponibles ; essai humain non réalisé.
L'objectif est de mesurer la compréhension des six premières missions et la
charge des consoles. Les douze parcours automatisés vérifient les preuves et les
reprises ; ils ne donnent aucune durée de jeu humain.

Depuis la racine du dépôt, préparer le profil avec :

```bash
backend/.venv/bin/python backend/act3_validation.py
REDTEAM_SAVE_DIR="$PWD/build/validation/act3-playtest" ./run.sh
```

La préparation parcourt les actes précédents et exporte une carrière arrivée au
début de l'acte III. Elle ne valide pas ses missions à la place du testeur.
Ne pas relancer la préparation pendant un essai : elle remplace cette carrière
de revue. La carrière habituelle est distincte.

| Temps indicatif | Observation recherchée |
|---|---|
| 0–3 min | Continuer, trouver l'offre de Traverse et la documentation locale |
| 3–8 min | Comparer découverte normale et `-Pn`, expliquer open/closed/filtered |
| 8–13 min | Reconnaître l'ancienne passation, ouvrir SSH avec le bon compte |
| 13–18 min | Comprendre pourquoi le même serveur répond depuis le relais |
| 18–25 min | Garder serveur, client et console de lecture indépendants ; établir Chisel puis SOCKS |
| 25–28 min | Atteindre WinRM et distinguer lecteur d'administrateur, si le rythme le permet |
| 28–30 min | Sauvegarder, reprendre et décrire le prochain objectif sans aide |

Ne pas accélérer le testeur pour atteindre la sixième mission. Noter le dernier
dossier atteint au bout de 30 minutes ; un arrêt plus tôt mesure aussi le rythme.
L'observateur laisse chercher puis note le premier indice demandé. Il n'explique
pas spontanément la différence entre serveur, client et console de test.

Pour chaque hésitation, noter : minute, dossier, commande ou écran, attente du
joueur, résultat reçu, indice utilisé, reprise autonome ou aide nécessaire.
Relever particulièrement une commande lancée depuis le mauvais hôte, une console
occupée, une tentative de tout faire depuis Kali et un refus pris pour un bug.

Au débriefing, demander au testeur d'expliquer : pourquoi `-Pn` n'ouvre pas un
pare-feu ; où écoute le SOCKS ; quel compte est ouvert ; ce qu'il garderait comme
preuve. Conserver les transcriptions et la sauvegarde isolée avec ces notes.

La seconde séance couvre les dossiers 7–12 et la demande de Madame_TLS : peut-on
reconnaître un blocage de protection, reprendre par un autre chemin et refuser un
envoi sans croire que cela annule l'attirance ? Aucun résultat de cette séance
n'est actuellement revendiqué.
