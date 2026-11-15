"""Construit hors ligne une archive Linux avec Godot, Python et leurs bibliothèques."""
from pathlib import Path
import argparse
import ctypes.util
import hashlib
import importlib.metadata
import json
import os
import re
import shutil
import subprocess
import sys
import sysconfig
import zipfile

ROOT = Path(__file__).resolve().parents[1]
NAME = 'DarknetOperator-0.5.4-dev-Linux-x86_64'
STAGE = ROOT/'build/portable-linux'/NAME
DIST = ROOT/'dist'
EXCLUDED = {'__pycache__', '.pytest_cache', '.venv', 'site-packages', 'ensurepip', 'idlelib', 'turtledemo', 'test', 'tests', 'pip'}
SITE_EXCLUDED = {'__pycache__', 'pip', '_pytest', 'pytest', 'pygments', 'iniconfig', 'pluggy', 'py.py'}


def ignored(_directory, names):
    return [name for name in names if name in EXCLUDED or name.endswith(('.pyc', '.a')) or name.startswith(('_test', '_ctypes_test', '_xxtest', 'xx', '_tkinter'))]


def copy_tree(source, target, ignore=None):
    shutil.copytree(source, target, dirs_exist_ok=True, ignore=ignore)


def dependencies(binary):
    result = subprocess.run(['ldd', str(binary)], text=True, capture_output=True)
    if result.returncode and 'not a dynamic executable' not in result.stderr:
        raise RuntimeError(f'ldd impossible : {binary}\n{result.stdout}{result.stderr}')
    paths = []
    for line in result.stdout.splitlines():
        if '=> not found' in line: raise RuntimeError(f'Bibliothèque absente pour {binary} : {line}')
        match = re.search(r'=>\s+(/\S+)', line) or re.match(r'\s*(/\S+)', line)
        if match: paths.append(Path(match.group(1)))
    return paths


def runtime_libraries(godot, python, runtime):
    library_dir = runtime/'lib'
    library_dir.mkdir(parents=True, exist_ok=True)
    seeds = [godot, python, *runtime.rglob('*.so'), *runtime.rglob('*.so.*')]
    # Bibliothèques ouvertes à la demande par le serveur d’affichage/audio.
    lookup = subprocess.run(['ldconfig', '-p'], text=True, capture_output=True, check=True).stdout
    for name in ('X11','Xcursor','Xinerama','Xi','Xrandr','Xrender','wayland-client','wayland-cursor','wayland-egl','xkbcommon','xkbcommon-x11','asound','pulse','dbus-1','udev','GL','EGL','GLX','GLdispatch'):
        soname = ctypes.util.find_library(name)
        if not soname: continue
        match = re.search(r'^\s*'+re.escape(soname)+r'\s+.*=>\s+(/\S+)', lookup, re.MULTILINE)
        if match: seeds.append(Path(match.group(1)))
    copied = {}
    for binary in seeds:
        for library in ([binary] if binary not in [godot,python] and '/usr/lib' in str(binary) else []) + dependencies(binary):
            if library.name.startswith('ld-linux-'): continue
            if library.name in copied: continue
            source = library.resolve()
            target = library_dir/library.name
            shutil.copy2(source, target)
            copied[library.name] = str(source)
    loader = Path('/usr/lib64/ld-linux-x86-64.so.2')
    if not loader.exists(): loader = Path('/lib64/ld-linux-x86-64.so.2')
    shutil.copy2(loader.resolve(), runtime/'ld-linux-x86-64.so.2')
    (runtime/'ld-linux-x86-64.so.2').chmod(0o755)
    return copied


def licenses(stage, libraries, godot, python):
    directory = stage/'Licences'
    directory.mkdir(exist_ok=True)
    if Path('/usr/share/licenses/spdx').is_dir(): copy_tree(Path('/usr/share/licenses/spdx'), directory/'textes-spdx')
    shutil.copy2(Path(sysconfig.get_path('stdlib'))/'LICENSE.txt', directory/'Python-LICENSE.txt')
    copy_tree(ROOT/'game/assets/licenses', directory/'ressources')
    shutil.copy2(ROOT/'game/assets/CREDITS.md', directory/'CREDITS-RESSOURCES.md')
    packages = {}
    for source in {str(godot), str(python), *libraries.values()}:
        owner = subprocess.run(['pacman','-Qoq',source], text=True, capture_output=True)
        if owner.returncode: continue
        for package in owner.stdout.splitlines():
            if package in packages: continue
            info = subprocess.run(['pacman','-Qi',package], text=True, capture_output=True, check=True).stdout
            fields = {}
            for line in info.splitlines():
                if ':' in line:
                    key,value = line.split(':',1)
                    if key.strip() in {'Name','Version','URL','Licenses'}: fields[key.strip()] = value.strip()
            packages[package] = fields
            source_directory = Path('/usr/share/licenses')/package
            if source_directory.is_dir(): copy_tree(source_directory,directory/package)
    for metadata in (stage/'runtime/python/lib'/f'python{sys.version_info.major}.{sys.version_info.minor}'/'site-packages').glob('*.dist-info'):
        for source in metadata.rglob('*'):
            if source.is_file() and ('license' in str(source.relative_to(metadata)).lower() or source.name.upper() in {'COPYING','NOTICE','AUTHORS'}):
                target = directory/'python-modules'/metadata.name/source.relative_to(metadata)
                target.parent.mkdir(parents=True,exist_ok=True)
                shutil.copy2(source,target)
    (directory/'COMPOSANTS.json').write_text(json.dumps(packages,ensure_ascii=False,indent=2)+'\n')
    return packages


def solution(stage):
    destination = stage/'Solution'
    copy_tree(ROOT/'docs', destination/'docs')
    contents = ['# Solution complète - Darknet Operator\n\nSpoilers complets. Ce guide couvre le contenu jouable de cette archive : prélude, actes I et II, démo et anciens scénarios. Les commandes se saisissent dans les terminaux du jeu, une à la fois. Les actes III et IV restent à préparer.\n']
    for title, name in [('Première partie - Acte I actuel et transition','ACTE_I_ACTUEL.md'),('Archives - Prélude antérieur','PRELUDE_CHORDLY.md'),('Archives - Ancien acte I et petits contrats','ACTE_I.md'),('Troisième partie - Démo et Le contretemps','DEMO_ET_CONTRETEMPS.md'),('Quatrième partie - Acte II','ACTE_II_GUIDE.md'),('Cinquième partie - Anciens scénarios et références','GUIDE_COMPLET_SCENARIOS.md')]:
        text = (ROOT/'docs'/name).read_text()
        text = re.sub(r'(?m)^(#{1,5}) ',r'\1# ',text)
        text = re.sub(r'\]\((?!https?://)([A-Za-z0-9_./-]+\.md)(#[^)]*)?\)', lambda m: '](docs/'+m.group(1)+(m.group(2) or '')+')', text)
        contents.append('\n# '+title+'\n\n'+text)
    markdown = destination/'SOLUTION_COMPLETE.md'
    markdown.write_text('\n'.join(contents))
    subprocess.run(['pandoc',str(markdown),'--standalone','--toc','--toc-depth=3','--metadata','title=Solution complète - Darknet Operator','--metadata','lang=fr','--include-in-header',str(ROOT/'packaging/solution-style.html'),'-o',str(destination/'SOLUTION_COMPLETE.html')],check=True)


def build():
    if sys.platform != 'linux' or os.uname().machine != 'x86_64': raise RuntimeError('Construire ce paquet sur Linux x86_64.')
    if STAGE.exists(): raise RuntimeError(f'Dossier de construction déjà présent : {STAGE}. Choisir un autre emplacement ou archiver la construction précédente.')
    STAGE.mkdir(parents=True)
    runtime = STAGE/'runtime'
    runtime.mkdir()
    godot = Path(shutil.which('godot') or shutil.which('godot4') or '')
    if not godot.is_file(): raise RuntimeError('Binaire Godot introuvable.')
    python = Path(sys.executable).resolve()
    stdlib = Path(sysconfig.get_path('stdlib'))
    python_root = runtime/'python'
    (python_root/'bin').mkdir(parents=True)
    shutil.copy2(python,python_root/'bin/python3')
    (python_root/'bin/python3').chmod(0o755)
    copy_tree(stdlib,python_root/'lib'/stdlib.name,ignored)
    site = Path(sysconfig.get_path('purelib'))
    target_site = python_root/'lib'/stdlib.name/'site-packages'
    def ignored_site(_directory, names):
        return [name for name in names if name in SITE_EXCLUDED or name.endswith('.pyc') or name.startswith(('pip-','pytest-','Pygments-','pygments-','iniconfig-','pluggy-')) or name == 'direct_url.json']
    copy_tree(site,target_site,ignored_site)
    shutil.copy2(godot,runtime/'godot')
    (runtime/'godot').chmod(0o755)
    libraries = runtime_libraries(godot,python,runtime)
    print(f'{len(libraries)} bibliothèques natives incluses.',flush=True)
    for folder in ('api','engine','abilities','contracts','scenarios','data'):
        copy_tree(ROOT/'backend'/folder,STAGE/'engine'/folder,shutil.ignore_patterns('__pycache__','*.pyc'))
    for filename in ('desktop_server.py','validation.py','validation_suite.py','act1_validation.py','journey_validation.py','first_hour_validation.py','mission_review_validation.py','save_review_validation.py','demo_validation.py','act2_validation.py','curriculum_validation.py','requirements.txt'):
        shutil.copy2(ROOT/'backend'/filename,STAGE/'engine'/filename)
    copy_tree(ROOT/'game',STAGE/'game',shutil.ignore_patterns('.godot'))
    for filename in ('uid_cache.bin','global_script_class_cache.cfg'):
        source = ROOT/'game/.godot'/filename
        if source.exists():
            (STAGE/'game/.godot').mkdir(exist_ok=True)
            shutil.copy2(source,STAGE/'game/.godot'/filename)
    copy_tree(ROOT/'game/.godot/imported',STAGE/'game/.godot/imported')
    shutil.copy2(ROOT/'packaging/portable_launcher.py',STAGE/'launcher.py')
    shell = '''#!/bin/sh
set -eu
PACKAGE_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
unset LD_LIBRARY_PATH LD_PRELOAD PYTHONPATH PYTHONHOME
PYTHONHOME="$PACKAGE_DIR/runtime/python"
PYTHONNOUSERSITE=1
PYTHONDONTWRITEBYTECODE=1
export PYTHONHOME PYTHONNOUSERSITE PYTHONDONTWRITEBYTECODE
exec "$PACKAGE_DIR/runtime/ld-linux-x86-64.so.2" --library-path "$PACKAGE_DIR/runtime/lib" "$PACKAGE_DIR/runtime/python/bin/python3" -s "$PACKAGE_DIR/launcher.py" "$@"
'''
    (STAGE/'Jouer.sh').write_text(shell)
    (STAGE/'Jouer.sh').chmod(0o755)
    (STAGE/'Importer-musique.sh').write_text(shell.replace('$PACKAGE_DIR/launcher.py', '$PACKAGE_DIR/scripts/import_chapter_music.py'))
    (STAGE/'Importer-musique.sh').chmod(0o755)
    (STAGE/'Verifier.sh').write_text('#!/bin/sh\nset -eu\nPACKAGE_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)\nexec "$PACKAGE_DIR/Jouer.sh" --self-test\n')
    (STAGE/'Verifier.sh').chmod(0o755)
    shutil.copy2(ROOT/'packaging/portable-player.txt',STAGE/'LIRE-MOI.txt')
    solution(STAGE)
    (STAGE/'scripts').mkdir(exist_ok=True)
    for name in ('generate_audio.py','check_audio.py','import_chapter_music.py'):
        if (ROOT/'scripts'/name).exists(): shutil.copy2(ROOT/'scripts'/name,STAGE/'scripts'/name)
    packages = licenses(STAGE,libraries,godot,python)
    metadata = {'game':'Darknet Operator','version':'0.5.4-dev','architecture':'Linux x86_64','type':'portable-source-runtime','godot':subprocess.check_output([str(godot),'--version'],text=True).strip(),'python':sys.version,'libraries':libraries,'system_packages':packages,'python_packages':{d.metadata['Name']:d.version for d in importlib.metadata.distributions() if d.metadata['Name'].lower() not in {'pip','pytest','pygments','pluggy','iniconfig'}},'personal_saves_included':False}
    (STAGE/'CONSTRUCTION.json').write_text(json.dumps(metadata,ensure_ascii=False,indent=2)+'\n')
    (STAGE/'VALIDATION.txt').write_text('Construction effectuée. Exécuter Verifier.sh puis consigner les vérifications avant diffusion.\n')
    print(STAGE,flush=True)


def archive():
    if not (STAGE/'Jouer.sh').is_file(): raise RuntimeError('Construire le dossier portable avant de l’archiver.')
    files = sorted(path for path in STAGE.rglob('*') if path.is_file() and path.name != 'MANIFEST.json')
    manifest = {str(path.relative_to(STAGE)):hashlib.file_digest(path.open('rb'),'sha256').hexdigest() for path in files}
    (STAGE/'MANIFEST.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2)+'\n')
    files.append(STAGE/'MANIFEST.json')
    DIST.mkdir(exist_ok=True)
    target = DIST/(NAME+'.zip')
    with zipfile.ZipFile(target,'w',compression=zipfile.ZIP_DEFLATED,compresslevel=6) as output:
        for path in files: output.write(path,Path(NAME)/path.relative_to(STAGE))
    digest = hashlib.file_digest(target.open('rb'),'sha256').hexdigest()
    target.with_suffix('.zip.sha256').write_text(digest+'  '+target.name+'\n')
    print(f'{target} - {target.stat().st_size/1024/1024:.1f} Mio\nSHA256 {digest}',flush=True)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--no-zip',action='store_true')
    parser.add_argument('--zip-existing',action='store_true')
    args = parser.parse_args()
    if not args.zip_existing: build()
    if not args.no_zip: archive()
