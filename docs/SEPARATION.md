# Séparation du 10 novembre 2026

## Destination des fonctionnalités

| Projet | Responsabilité | Port par défaut |
|---|---|---|
| RedVsBlue | Simulation pédagogique à deux équipes et tableau de supervision | 8000 |
| RedTeamSimulator | Jeu solo, bureau, messagerie, contrats et terminal | 8001 |

RedVsBlue reprend la base Red/Blue du commit
`c174b110fb15c6a33231db709a72ed64f5363e82`.
RedTeamSimulator reprend les sources de travail du jeu solo présentes au moment
de la séparation, avec les modifications non enregistrées.

Les deux dépôts conservent l'historique commun antérieur à la séparation.
Ils n'ont aucun remote entre eux et évoluent séparément. Les moteurs sont des
copies indépendantes : une évolution dans un projet ne modifie pas l'autre.

## Sauvegarde

L'état initial complet des sources et de Git est conservé dans
`/home/ozer/Documents/RedVsBlue-backups/20261110-115531`.
Le manifeste voisin décrit les emplacements et le commit de départ.
Les environnements virtuels et caches générés sont exclus de cette sauvegarde.

## Périmètre

Cette intervention sépare les projets et leurs points d'entrée. Elle ne refond
pas le gameplay ni le système de commandes. La documentation de progression
solo décrit aussi des fonctionnalités futures, pas seulement ce qui est livré.
