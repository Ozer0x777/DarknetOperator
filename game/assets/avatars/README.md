# Portraits de la communauté

Dix-neuf avatars originaux de personnages adultes fictifs, générés avec l'outil
imagegen intégré à partir de la direction du fond orbital du jeu : anime SF
années 1990, encrage, aplats mats, grain discret, prune, olive et lumière menthe.

Les dix-huit profils de `backend/data/social_world.json` possèdent chacun un portrait distinct, ainsi que le compte client temporaire `urgent_client_01`.
La correspondance utilisée est dans `game/scripts/ui/avatars.gd`. Les groupes et
les pseudos du joueur conservent un monogramme. Ces illustrations sont des
avatars choisis par les personnages ; elles ne constituent pas des photographies
ni des preuves de leur identité dans le récit.

Les fichiers `*-orbital-v*.png` sont les sorties originales, sans retouche de
l'image. Les trois portraits précédents `k0rvid-v1.png`, `miette-v1.png` et
`sable-v1.png` restent conservés ; leurs nouvelles versions reprennent leurs
traits distinctifs en harmonisant le rendu. La direction visuelle repose sur les ressources originales du jeu. La seconde
version de Madame_TLS s’inspire aussi de l’illustration `pasted file.png` fournie
par l’utilisateur : cheveux blonds, yeux bleus et boucles triangulaires roses.
Cette référence externe n’est pas utilisée comme ressource dans le jeu. La v1
reste conservée ; la v2 active possède un fond carré plein cadre, sans cercle dessiné.

Les sujets en fenêtre large et les fiches de profil affichent les portraits en
200 × 200 pixels. Les sujets compacts utilisent 56 pixels ; les listes et les
messageries gardent des miniatures adaptées à leur contexte. Les forums utilisent
un cadrage carré, les messageries leur masque circulaire.
Les paramètres d'import limitent les textures de cette série à 200 pixels dans
Godot, sans redimensionner les PNG sources. Les originaux permettent une future
réutilisation à plus grande taille.

`orbital-manifest.json` consigne pour chaque personnage le fichier final, les
références, le prompt complet, le mode de génération, les dimensions sources et
l'empreinte SHA-256. Les PNG distribués se trouvent tous dans ce répertoire ;
aucune ressource du jeu ne dépend du répertoire privé du générateur.
