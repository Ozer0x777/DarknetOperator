# Son et musique - 0.5.3

## Continuité

Les étapes réussies, changements de statut, débriefings, pauses de mission et
missions suivantes ne redémarrent plus la musique. Le service audio reste unique
entre les scènes. Les morceaux de jeu s’enchaînent avec un fondu de 2,5 secondes.
Le mode manuel permet de boucler un morceau ; les commandes précédent/suivant du
lecteur reprennent la playlist. La pause musicale est indépendante de la pause
du jeu, et les volumes n’arrêtent pas le lecteur.

Le menu dispose de son morceau dédié. Quand on revient au jeu, son morceau
précédent reprend à la position conservée au lieu de repartir de zéro.

## Lecteur et notifications

Le bouton ♪ du panneau ouvre **Lecteur audio**, également présent dans Applications.
Il propose précédent, pause/reprise, suivant, position, durée, volume et sélection
par double-clic dans la playlist. Fermer ou réduire cette fenêtre ne coupe pas
la musique. Les volumes général, musique et effets restent dans Paramètres.

Une notification silencieuse annonce le titre lorsqu’il change et ouvre le lecteur
au clic. Elle attend la fermeture d’une notification importante et ne remplace pas
un message de mission. Les préférences restent dans `user://audio.cfg`, hors des
sauvegardes de carrière.

## Album demandé par chapitres

Source fournie : <https://www.youtube.com/watch?v=_Gajv2yJt5M>.
**Le téléchargement est bloqué dans cet environnement : résolution DNS de YouTube
indisponible. Aucun audio de cette vidéo n’est inclus dans cette version.**
Les titres et limites sont préparés dans
`game/assets/audio/chapter-album/manifest.json`.

| Début | Titre | Destination |
|---|---|---|
| 00:00 | Pulse Reconnected | Jeu |
| 03:27 | Wake Sequence | Menu, en boucle |
| 06:46 | Lost Frequency | Jeu |
| 10:14 | Echo of Earth | Jeu |
| 13:29 | Drift Into Memory | Jeu |
| 17:12 | Signal From the Past | Jeu |
| 21:01 | Cyber Tears | Jeu |
| 24:35 | Reclaim The Moment | Jeu |
| 28:35 | Cold Starlight | Jeu |
| 32:22 | Archive Chamber | Jeu |
| 34:34 | The Halcyon Dream | Jeu |
| 39:14 | The Human Algorithm | Jeu, jusqu’à la fin de la source |

Pour importer un fichier audio ou vidéo local complet :

```bash
python3 scripts/import_chapter_music.py "/chemin/vers/la/source.mp4"
```

Dans le paquet portable, `./Importer-musique.sh "/chemin/vers/la/source.mp4"` utilise le Python embarqué.

FFmpeg et FFprobe sont nécessaires à ce découpage, pas pour jouer. Le script
vérifie la piste audio et la durée, encode les douze fichiers Ogg puis écrit le
manifeste. Les chemins contenant des espaces sont pris en charge. Relancer le jeu
après l’import : Wake Sequence devient le morceau du menu et les onze autres
suivent l’ordre ci-dessus, sans Wake dans la playlist de jeu. Le dernier revient
au premier avec un fondu. Un album incomplet laisse la bibliothèque de repli active.

## Bibliothèque originale disponible

En attendant la source, trois compositions originales restent livrées :
Neon Dreams (Dreamwave/Retrowave, 87 s), Afterhours Grid (Chillwave/Vaporwave,
120 s), Night Runner (Synthwave/Cyberpunk, 107 s). Aucun extrait extérieur n’y est
incorporé. Le menu utilise Neon Dreams ; le jeu enchaîne les trois compositions.
Les douze effets courts restent séparés de la musique.

## Vérification

Les tests Godot vérifient la continuité réelle de position avec le pilote muet,
la pause, les fondus, le retour du menu, les volumes, les réglages persistants,
la fenêtre compacte et les notifications. Le chargement des douze chapitres et
l’affectation de Wake sont testés avec des fichiers de test temporaires, **pas
avec l’album YouTube**. Les tests Python vérifient le découpage sur une source
synthétique et le refus d’une source trop courte.

L’environnement ne permet pas une écoute humaine sur casque ou haut-parleurs ;
les tests numériques et le pilote muet ne remplacent pas cette validation.
