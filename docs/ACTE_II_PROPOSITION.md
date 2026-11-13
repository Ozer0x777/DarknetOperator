# Acte II — Gagner des accès

**Plan actualisé le 12 novembre 2026 ; les dossiers sont intégrés en 0.5.0.**
Le guide et l’état réel figurent dans [ACTE_II_GUIDE.md](ACTE_II_GUIDE.md) et
[ACTE_II_COUVERTURE.md](ACTE_II_COUVERTURE.md). Les exigences non encore couvertes
restent une cible de développement, pas une fonctionnalité annoncée.
Cette proposition remplace le premier périmètre de six missions. Le périmètre
retenu pour la conception est de **dix missions principales et six contrats
facultatifs**, reliés par une chaîne de prestataires. Aucune durée n’est mesurée.

Exigence du joueur : commandes authentiques, vérifications Windows et Linux
complètes pour les situations proposées, aucun raccourci inventé qui remplace
le raisonnement. Voir [ACTE_II_FIDELITE.md](ACTE_II_FIDELITE.md).

## Progression proposée

| Mission | Situation | Techniques à développer |
|---|---|---|
| 1. Une vieille passation | Vérifier une empreinte et la validité d’un compte ancien | Hashcat, fichiers de résultats, dictionnaire, échec de correspondance |
| 2. Un compte ne suffit pas | Accéder à un serveur et comprendre ses droits | SSH, SCP, identité, groupes, permissions et services Linux |
| 3. Une machine mal entretenue | Examiner un Linux avant de choisir une élévation | Distribution, versions de paquets, correctifs et configuration ; cas Polkit de laboratoire |
| 4. Derrière le serveur | Comprendre l’existence d’un réseau interne | Interfaces, routes, DNS, ports, visibilité selon l’origine |
| 5. Le passage étroit | Atteindre ce réseau depuis un hôte intermédiaire | Tunnel SSH, écoute locale, durée de vie du processus, reconnaissance via le passage |
| 6. Le réseau du prestataire | Examiner un domaine Windows et les relations de droits | LDAP, outils Windows/PowerShell disponibles, SharpHound et BloodHound |
| 7. Un service trop privilégié | Vérifier une piste liée à un compte de service | Kerberoasting avec Impacket, type d’empreinte adapté, Hashcat et validation du résultat |
| 8. Changer de machine | Utiliser un compte sur une autre machine | Impacket, SMB, contexte Windows, droits et services nécessaires |
| 9. La passation douteuse | Démontrer les limites d’une promesse de vendeur | Recoupement, permissions, versions et plusieurs chemins possibles |
| 10. Premier travail en binôme | Préparer une livraison et une passation vérifiables | Combinaison des acquis, pivot, accès Linux ou Windows, preuves et choix de partenaire |

Les six contrats facultatifs réutilisent ces acquis : vérification d’accès,
analyse d’empreintes, audit de permissions, diagnostic d’un tunnel, inventaire AD
et récupération ciblée. Aucun n’est obligatoire pour payer une route indispensable
ou débloquer la suite. Argent et relations doivent avoir des conditions visibles.

## Continuité

L’entrée conserve l’invitation et le choix public/privé du litige de l’acte I.
Les deux choix doivent permettre de finir l’acte. Les interlocuteurs réagissent
aux observations et aux engagements déjà enregistrés. Un client peut se tromper ;
sa demande n’est pas une preuve technique. Une mauvaise hypothèse doit produire
un résultat compréhensible, pas une impasse ou une commande à deviner.

La répartition discutée réserve Impacket, Hashcat, Kerberoasting et l’élévation
Linux à cette progression. **La version jouable 0.4.8 n’a pas encore été
redistribuée : Ravelle utilise toujours Impacket et Hashcat/ticketd restent dans
l’acte I.** Ce déplacement exige de nouveaux objectifs et une migration dédiée ;
ne pas présenter cette proposition comme une modification déjà livrée.

## Ordre de production suivi et extensions

1. Définir les versions de référence et le catalogue des commandes nécessaires.
2. Étendre le modèle système : paquets, correctifs, comptes, droits, services,
   annuaire et visibilité réseau selon l’origine.
3. Construire la première tranche Hashcat → SSH avec les vérifications et les
   cas négatifs, puis la reprendre depuis des sauvegardes.
4. Ajouter l’élévation Linux et le pivot avant d’écrire les scénarios AD complets.
5. Ajouter LDAP, les collecteurs et l’analyse BloodHound, puis les contrats associés.
6. Migrer la répartition des actes et qualifier les parcours complets.

Les anciens contrats de palier 2 restent distincts. Aucun contrat historique ne
se transforme silencieusement en chapitre d’acte II.
