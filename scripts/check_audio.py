"""Contrôle les fichiers audio livrés : décodage, durée, niveau et frontière de boucle."""
from pathlib import Path
import json
import subprocess
import wave
import numpy as np
ROOT=Path(__file__).resolve().parents[1]
folder=ROOT/'game/assets/audio'
manifest=json.loads((folder/'manifest.json').read_text())
report=[]
for track in manifest['tracks']:
    path=folder/track['file']
    decoded=subprocess.run(['ffmpeg','-v','error','-i',str(path),'-f','f32le','-ac','2','-ar','44100','-'],check=True,capture_output=True).stdout
    samples=np.frombuffer(decoded,dtype='<f4').reshape(-1,2)
    duration=len(samples)/44100
    peak=float(np.max(np.abs(samples)))
    rms=float(np.sqrt(np.mean(samples**2)))
    seam=float(np.max(np.abs(samples[0]-samples[-1])))
    assert abs(duration-track['seconds'])<.12,(path,duration)
    assert peak<.98 and .02<rms<.3,(path,peak,rms)
    assert seam<.08,(path,'frontière de boucle',seam)
    report.append({'file':path.name,'duration':round(duration,3),'peak':round(peak,4),'rms':round(rms,4),'loop_seam':round(seam,5)})
for path in sorted(folder.glob('*.wav')):
    with wave.open(str(path),'rb') as stream:
        assert stream.getsampwidth()==2 and stream.getframerate()==44100,path
        samples=np.frombuffer(stream.readframes(stream.getnframes()),dtype='<i2').astype(np.float32)/32768
        assert 0<len(samples)<44100 and .01<float(np.max(np.abs(samples)))<.98,path
assert len(list(folder.glob('*.wav')))==12
output=ROOT/'build/audio-validation.json'
output.parent.mkdir(exist_ok=True)
output.write_text(json.dumps({'tracks':report,'effects':12,'scope':'Décodage et niveaux numériques ; aucune écoute sur haut-parleur dans cet environnement.'},ensure_ascii=False,indent=2)+'\n')
print(json.dumps(report,indent=2))
print('Audio : 3 musiques et 12 effets décodés sans saturation numérique.')
