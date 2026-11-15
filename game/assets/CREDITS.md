# Sources des éléments visuels

Les polices et ressources nécessaires sont livrées dans le projet : aucune
connexion distante n'est nécessaire pour les afficher.

- **Dragon Kali** : dessin issu de l'icône `distributor-logo-kali-linux.svg` du
  thème [Candy Icons, EliverLara](https://github.com/EliverLara/candy-icons).
  Copie locale d'origine : `/usr/share/icons/candy-icons/apps/scalable/`.
  L'original est conservé dans `icons/kali.svg`. `icons/dragon.svg` adapte ce
  dessin en monochrome et retire son cadre circulaire. Le fond `wallpaper.svg`
  reprend ce dessin adapté sur une composition vectorielle isométrique.
  Licence de cette ressource et de ses adaptations : GPL-3.0, texte fourni
  dans `licenses/candy-icons-GPL-3.0.txt`.
- **Dossiers, corbeille et ordinateur** : icônes Adwaita du projet GNOME,
  copiées depuis le thème local. Notices et licences fournies dans
  `licenses/adwaita-*`.
- **Cantarell** : police du projet GNOME. Licence OFL fournie dans
  `licenses/cantarell-OFL.txt`.
- **DejaVu Sans Mono** : police DejaVu. Notice fournie dans
  `licenses/dejavu-LICENSE.txt`.
- Autres pictogrammes : dessins SVG créés pour les applications fictives du jeu.

Références visuelles du bureau :
[Kali/Xfce 2025.1](https://www.kali.org/blog/kali-linux-2025-1-release/),
[menu Kali 2025.2](https://www.kali.org/blog/kali-linux-2025-2-release/).
Le fond est une recomposition ; il n'est pas présenté comme un wallpaper officiel
récupéré sur le site Kali.

Chordly, Telegrid, Sessyon, BreachBoard, Exployt et XSX sont des applications et
communautés fictives de RedTeamSimulator. Elles ne se connectent pas aux
services réels dont les conventions visuelles ont servi de références.

Icônes d’action `search.svg`, `info.svg`, `menu.svg`, `attach.svg`, `send.svg` et `smile.svg` : dessins SVG originaux du projet, sans ressource externe.

Icône `wallet.svg` : dessin original du projet pour le portefeuille matériel fictif ColdVault. Aucun lien avec un fabricant réel.

Bande-son et effets : compositions originales synthétisées pour Darknet Operator, sources dans `scripts/generate_audio.py`. Aucun échantillon externe ni audio de la référence YouTube n’est incorporé. Voir `game/assets/audio/README.md`.

Illustrations orbitales v0.4.2 : deux scènes originales générées avec l’outil imagegen intégré, dans une direction anime spatial rétro inspirée de la référence visuelle fournie par le joueur. Le fichier de référence n’est pas incorporé au paquet. Fond de bureau : `backgrounds/orbital-drift-desktop-v1.png` ; accueil : `branding/darknet-operator-orbital-keyart-v2.png`. Direction et prompts : `branding/ORBITAL_PROMPTS.md`. L’ancien fond vectoriel et les anciennes illustrations sont conservés comme ressources historiques.

Icône `music.svg` : dessin vectoriel original du projet pour le lecteur audio. Le manifeste `audio/chapter-album/` contient les titres et repères fournis par le joueur, sans audio de la vidéo.

Portraits orbitaux : dix-neuf avatars originaux générés avec l’outil imagegen
intégré à partir du fond de bureau original du jeu et, pour les trois profils
existants, de leur ancien avatar. Ils représentent des adultes fictifs. Les PNG
sources restent intacts ; Godot importe des textures de 200 pixels. Ressources
et prompts exacts : `avatars/README.md` et `avatars/orbital-manifest.json`.

Bannières des forums : trois scènes originales générées puis éditées avec
l’outil imagegen intégré, une pour BreachBoard, Exployt et XSX. Chacune comporte
un personnage féminin adulte. Le fond orbital sert de référence de style ; les
titres sont rendus par Godot. Fichiers, dimensions, empreintes et prompts de
production : `forums/manifest.json`. Aucun fichier situé dans le répertoire
privé du générateur n’est nécessaire à l’exécution du jeu.
