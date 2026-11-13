# Bande-son et effets originaux

Ces fichiers sont synthétisés pour Darknet Operator par `scripts/generate_audio.py`.
Ils ne contiennent aucun extrait, échantillon ou enregistrement extérieur.
La vidéo indiquée par l’utilisateur sert uniquement de référence de direction
musicale ; son audio n’est pas inclus dans le jeu.

- `neon-dreams.ogg` : Dreamwave / Retrowave, 88 BPM, 1 min 27 s.
- `afterhours-grid.ogg` : Chillwave / Vaporwave, 96 BPM, 2 min.
- `night-runner.ogg` : Synthwave / Cyberpunk, 108 BPM, 1 min 47 s.

Trois compositions instrumentales stéréo, accords de synthétiseur, basse,
arpèges et percussions électroniques. Les queues d’écho sont repliées au début
pour boucler sans coupure franche. Les musiques sont livrées en Ogg Vorbis ; les
12 effets courts sont en WAV PCM 16 bits / 44,1 kHz.

Sources reproductibles : NumPy et FFmpeg sont requis pour régénérer les fichiers,
mais ne sont pas nécessaires au joueur. `scripts/check_audio.py` vérifie le
décodage, les niveaux et la frontière de boucle ; les commandes et contrôles
Godot sont décrits dans `docs/SON_ET_MUSIQUE.md`.

Depuis la 0.5.3, ces trois compositions s’enchaînent sans changement aux réussites. Le dossier `chapter-album/` ne contient que les repères du futur album demandé ; son audio n’a pas été téléchargé. Voir `docs/SON_ET_MUSIQUE.md` et `scripts/import_chapter_music.py`.
