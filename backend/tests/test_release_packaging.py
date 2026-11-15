"""Un paquet reprend les ressources distribuables et exclut les fichiers locaux ignorés."""
import importlib.util
from pathlib import Path
import subprocess


def test_package_selection_excludes_local_audio_and_cache_but_keeps_manifest(tmp_path):
    source=Path(__file__).parents[2]/'scripts/build_portable_linux.py'
    spec=importlib.util.spec_from_file_location('portable_build',source)
    module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)
    subprocess.run(['git','init','-q',str(tmp_path)],check=True)
    (tmp_path/'.gitignore').write_text('.godot/\ngame/assets/audio/chapter-album/*\n!game/assets/audio/chapter-album/manifest.json\n')
    for name in ['game/project.godot','game/assets/audio/original.ogg','game/assets/audio/chapter-album/manifest.json','game/assets/audio/chapter-album/local.ogg','game/.godot/private-cache.bin']:
        p=tmp_path/name;p.parent.mkdir(parents=True,exist_ok=True);p.write_bytes(b'fixture')
    selected={str(p.relative_to(tmp_path)) for p in module.game_source_files(tmp_path)}
    assert selected=={'game/project.godot','game/assets/audio/original.ogg','game/assets/audio/chapter-album/manifest.json'}
