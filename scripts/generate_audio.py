"""Compositions et effets originaux déterministes ; NumPy et FFmpeg, construction seulement."""
from pathlib import Path
import json
import math
import subprocess
import tempfile
import wave
import numpy as np

ROOT = Path(__file__).resolve().parents[1]
OUTPUT = ROOT/'game/assets/audio'
RATE = 44100
rng = np.random.default_rng(20261111)


def frequency(midi): return 440 * 2 ** ((midi-69)/12)


def envelope(t, duration, attack=.02, release=.12):
    return np.minimum(1,t/max(attack,.001)) * np.minimum(1,np.maximum(0,(duration-t))/max(release,.001))


def oscillator(note, duration, kind='pad', velocity=1):
    t=np.arange(round(duration*RATE),dtype=np.float32)/RATE
    hz=frequency(note)
    phase=2*np.pi*hz*t
    if kind=='pad':
        signal=(np.sin(phase)+.20*np.sin(2*phase)+.08*np.sin(3*phase))*.55
        signal+=.24*np.sin(phase*1.0023)+.24*np.sin(phase*.9977)
        signal*=envelope(t,duration,.65,1.5)
    elif kind=='bass':
        signal=(np.sin(phase)+.24*np.sin(2*phase)+.09*np.sin(3*phase)) * np.exp(-t*2)
        signal*=envelope(t,duration,.009,.09)
    elif kind=='arp':
        signal=(np.sin(phase)+.22*np.sin(2*phase)+.10*np.sin(4*phase)) * np.exp(-t*5)
        signal*=envelope(t,duration,.008,.12)
    else:
        signal=(np.sin(phase)+.16*np.sin(2*phase*1.001)) * np.exp(-t*.6)
        signal*=envelope(t,duration,.045,.35)
    return signal.astype(np.float32)*velocity


def drum(kind):
    duration={'kick':.32,'snare':.22,'hat':.07}[kind]
    t=np.arange(round(duration*RATE),dtype=np.float32)/RATE
    noise=rng.normal(0,1,len(t)).astype(np.float32)
    if kind=='kick':
        phase=2*np.pi*(46*t+52*(1-np.exp(-t*28))/28)
        signal=np.sin(phase)*np.exp(-t*15)
    elif kind=='snare':
        noise=np.convolve(noise,np.array([-.5,1,-.5],dtype=np.float32),mode='same')
        signal=.48*noise*np.exp(-t*24)+.22*np.sin(2*np.pi*182*t)*np.exp(-t*28)
    else:
        noise=np.diff(noise,prepend=0)
        signal=noise*np.exp(-t*75)*.17
    return (signal*envelope(t,duration,.002,.012)).astype(np.float32)


def write_wav(path, samples):
    pcm=(np.clip(samples,-.98,.98)*32767).astype('<i2')
    with wave.open(str(path),'wb') as stream:
        stream.setnchannels(2 if pcm.ndim==2 else 1)
        stream.setsampwidth(2)
        stream.setframerate(RATE)
        stream.writeframes(pcm.tobytes())


def compose(name,bpm,bars,chords,style):
    beat=60/bpm
    seconds=bars*4*beat
    count=round(seconds*RATE)
    mix=np.zeros((count,2),dtype=np.float32)
    def add(signal,when,pan=0):
        offset=round(when*RATE)
        indices=(offset+np.arange(len(signal)))%count
        mix[indices,0]+=signal*math.sqrt((1-pan)/2)
        mix[indices,1]+=signal*math.sqrt((1+pan)/2)
    pads=[oscillator(note,8*beat+1.5,'pad',.054) for chord in chords for note in chord]
    for bar in range(0,bars,2):
        chord_index=(bar//2)%len(chords)
        chord=chords[chord_index]
        for voice,_note in enumerate(chord):
            add(pads[chord_index*len(chord)+voice],bar*4*beat,(voice-1.5)*.22)
        # Une contre-mélodie évolue par phrases de huit mesures.
        if bar%8 in (2,6):
            for index,interval in enumerate([0,2,1,3]):
                note=chord[interval]+12
                add(oscillator(note,beat*1.5,'lead',.047), (bar*4+index*1.5)*beat, (-1)**index*.25)
    kick=drum('kick');snare=drum('snare');hat=drum('hat')
    for bar in range(bars):
        chord=chords[(bar//2)%len(chords)]
        phrase=bar%16
        intensity=.65 if style=='dream' else (.8 if style=='chill' else 1)
        # Interludes légers : les instruments changent, jamais un bruit d’alarme continu.
        if phrase in (0,1): intensity*=.65
        for position in ([0,2] if style=='dream' else [0,1.5,2,3.5]):
            add(kick*.21*intensity,(bar*4+position)*beat)
        for position in [1,3]: add(snare*.12*intensity,(bar*4+position)*beat,.10)
        for step in range(8): add(hat*.14*intensity,(bar*4+step/2)*beat,(-1)**step*.30)
        pattern=[0,0,7,0] if style!='cyber' else [0,0,12,7,0,0,7,12]
        for index,interval in enumerate(pattern):
            duration=beat*(.85 if len(pattern)==4 else .42)
            add(oscillator(chord[0]-12+interval,duration,'bass',.13),(bar*4+index*4/len(pattern))*beat)
        for step in range(8):
            if style=='dream' and step%2: continue
            pitch=chord[[0,2,1,3,2,1,3,2][step]]+12
            gain=.035 if style=='dream' else (.041 if style=='chill' else .046)
            if phrase>=12: gain*=.72
            add(oscillator(pitch,beat*.7,'arp',gain),(bar*4+step/2)*beat,math.sin(step*1.7)*.45)
    # Échos périodiques : les queues de fin sont repliées au début de la boucle.
    dry=mix.copy()
    for delay,gain in [(beat*.75,.16),(beat*1.5,.09),(beat*2.25,.045)]:
        rolled=np.roll(dry,round(delay*RATE),axis=0)
        mix[:,0]+=rolled[:,1]*gain
        mix[:,1]+=rolled[:,0]*gain
    mix=np.tanh(mix*1.1)
    peak=float(np.max(np.abs(mix)))
    rms=float(np.sqrt(np.mean(mix**2)))
    mix*=min(.76/max(peak,.001),.135/max(rms,.001))
    OUTPUT.mkdir(parents=True,exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='darknet-music-') as directory:
        wav=Path(directory)/(name+'.wav')
        write_wav(wav,mix)
        subprocess.run(['ffmpeg','-v','error','-y','-i',str(wav),'-c:a','libvorbis','-q:a','4','-metadata','title='+name,'-metadata','artist=Darknet Operator — composition originale',str(OUTPUT/(name+'.ogg'))],check=True)
    return {'file':name+'.ogg','bpm':bpm,'seconds':round(seconds,3),'style':style,'peak':round(float(np.max(np.abs(mix))),4),'rms':round(float(np.sqrt(np.mean(mix**2))),4)}


def effect(name,notes,duration=.24,level=.35):
    total=np.zeros(round(duration*RATE),dtype=np.float32)
    step=duration/max(len(notes),1)*.60
    for index,note in enumerate(notes):
        start=round(index*step*RATE)
        part=oscillator(note,duration-index*step,'arp',level)
        total[start:start+len(part)]+=part
    total*=envelope(np.arange(len(total))/RATE,duration,.003,.04)
    peak=np.max(np.abs(total))
    if peak>.65: total*=.65/peak
    write_wav(OUTPUT/(name+'.wav'),total)


def main():
    tracks=[
        compose('neon-dreams',88,32,[[50,57,60,64],[46,53,57,60],[53,60,64,67],[48,55,60,62]],'dream'),
        compose('afterhours-grid',96,48,[[45,52,55,59],[41,48,52,55],[48,55,59,62],[43,50,55,57]],'chill'),
        compose('night-runner',108,48,[[45,52,57,60],[41,48,53,57],[38,45,50,53],[40,47,52,55]],'cyber')]
    for name,notes,duration,level in [
        ('click',[89],.045,.18),('open',[62,69],.15,.23),('close',[69,62],.13,.20),
        ('notify',[79,86],.29,.34),('chordly',[79,83],.27,.30),('telegrid',[81,88],.25,.29),('sessyon',[76,83],.28,.29),
        ('sent',[72,79],.17,.23),('confirm',[69,76,81],.35,.31),('error',[60,56],.30,.26),
        ('success',[60,64,67,72],.72,.32),('failure',[57,53,50],.58,.27)]:
        effect(name,notes,duration,level)
    (OUTPUT/'manifest.json').write_text(json.dumps({'sample_rate':RATE,'original':True,'tracks':tracks,'effects':12},ensure_ascii=False,indent=2)+'\n')
    print(json.dumps(tracks,ensure_ascii=False,indent=2))

if __name__=='__main__': main()
