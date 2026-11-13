# Architecture PC et préparation Steam

## Choix technique

**Godot 4 standard + GDScript typé** pour le bureau, les interactions et la couche
Steam à venir. Le moteur déterministe reste en Python pour réutiliser les règles
et les tests existants. Les scénarios, contrats et actions restent déclaratifs.

Ce choix évite une réécriture immédiate de toutes les règles. Le paquet prévu
contient deux exécutables : le jeu Godot et son moteur autonome construit avec
PyInstaller. Le joueur lance seulement le jeu ; le client démarre et arrête son
propre moteur local. Le protocole entre les deux utilise JSON et WebSocket.

C# serait une alternative valable, mais n'apporte pas de nécessité démontrée à ce
jeu principalement constitué d'interfaces et de règles. C++ n'est pas requis.
Le choix du langage ne suffit pas à garantir une publication Steam.

Références officielles :

- [Godot : interface et thèmes](https://docs.godotengine.org/en/stable/tutorials/ui/index.html)
- [Godot : GDScript typé](https://docs.godotengine.org/en/stable/tutorials/scripting/gdscript/static_typing.html)
- [Godot : exports PC et modèles](https://docs.godotengine.org/en/stable/tutorials/export/exporting_projects.html)
- [Valve : envoi des builds](https://partner.steamgames.com/doc/sdk/uploading)
- [Kali : environnement Xfce](https://www.kali.org/docs/general-use/xfce-faq/)

## Construire

Installer les modèles d'export correspondant exactement à la version de Godot.
La version présente sur cette machine est Godot 4.7.2 standard.

```bash
backend/.venv/bin/python -m pip install -r packaging/requirements.txt
backend/.venv/bin/python scripts/build.py linux
```

Pour Windows, exécuter la même construction **sur Windows** avec le Python du
venv Windows et `scripts/build.py windows`. PyInstaller ne construit pas ici un
exécutable Windows depuis un interpréteur Linux.

Les résultats vont dans `build/linux/` et `build/windows/`. Garder le dossier
`engine/` à côté de l'exécutable Godot. Les modèles Godot exportent le client ;
PyInstaller inclut le moteur et les données de jeu.

## Validation encore nécessaire

L’export release reste indisponible ici : PyInstaller et les modèles d’export
Godot sont absents. Une **distribution Linux portable distincte**, avec les
runtimes et les sources du jeu, a été assemblée et qualifiée hors réseau.
Voir [PAQUET_LINUX.md](PAQUET_LINUX.md) pour sa construction et les limites des tests.
Cela ne valide ni l’export release ni une publication Steam.

Avant diffusion :

1. Construire chaque système cible avec ses dépendances et modèles.
2. Tester le paquet sur une machine propre sans Python ni Godot installés.
3. Vérifier création du profil, reprise après fermeture, pare-feu local, modes
   d'affichage, mise à l'échelle et encodage des textes.
4. Ajouter les mentions de licences des composants effectivement distribués.
5. Configurer l'application et les dépôts dans le compte Steamworks du propriétaire.
6. Tester les builds dans une branche privée avant de demander une publication.

Aucun AppID, compte Steamworks ou SDK Steam propriétaire n'a été configuré.
Succès, Steam Cloud, overlay et compatibilité Steam Deck ne sont pas revendiqués.
Les contrôles présents sont pensés pour clavier et souris ; une prise en charge
manette ou Steam Deck demande une validation et des adaptations spécifiques.
