"""Découpage local de la bande-son ; aucune connexion YouTube dans les tests."""
import copy
import importlib.util
import json
from pathlib import Path
import shutil
import subprocess
import pytest

ROOT=Path(__file__).resolve().parents[2]
spec=importlib.util.spec_from_file_location('chapter_music',ROOT/'scripts/import_chapter_music.py')
module=importlib.util.module_from_spec(spec);spec.loader.exec_module(module)


def test_requested_chapters_and_menu_assignment():
    d=module.description()
    assert len(d['tracks'])==12
    assert [e['title'] for e in d['tracks'] if e['menu']]==['Wake Sequence']
    assert d['tracks'][1]['start']==207 and d['tracks'][-1]['start']==2354
    assert len({e['file'] for e in d['tracks']})==12


@pytest.mark.skipif(not shutil.which('ffmpeg') or not shutil.which('ffprobe'),reason='FFmpeg requis pour le test de découpage')
def test_audio_video_source_is_split_and_short_source_keeps_previous_album(tmp_path):
    source=tmp_path/'source avec espaces.wav'
    subprocess.run(['ffmpeg','-v','error','-f','lavfi','-i','sine=frequency=440:duration=3.2','-ar','44100','-ac','2',str(source)],check=True)
    d=module.description()
    for index,entry in enumerate(d['tracks']):entry['start']=index*.25
    output=tmp_path/'album avec espaces'
    result=module.import_album(source,output,chapters=d)
    saved=json.loads((output/'manifest.json').read_text())
    assert saved==result and len(list(output.glob('*.ogg')))==12
    assert saved['tracks'][-1]['seconds']==.45
    for entry in saved['tracks']:
        actual=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-of','json',str(output/entry['file'])],text=True))
        assert abs(float(actual['format']['duration'])-entry['seconds'])<.05
    previous=(output/'manifest.json').read_bytes()
    with pytest.raises(ValueError,match='durée'):module.import_album(source,output)
    assert (output/'manifest.json').read_bytes()==previous
