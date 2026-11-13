"""Découpe un fichier local en douze chapitres Ogg pour le lecteur du jeu."""
from pathlib import Path
import argparse
import json
import shutil
import subprocess
import tempfile

ROOT=Path(__file__).resolve().parents[1]
CHAPTERS=[('00:00','Pulse Reconnected'),('03:27','Wake Sequence'),('06:46','Lost Frequency'),('10:14','Echo of Earth'),('13:29','Drift Into Memory'),('17:12','Signal From the Past'),('21:01','Cyber Tears'),('24:35','Reclaim The Moment'),('28:35','Cold Starlight'),('32:22','Archive Chamber'),('34:34','The Halcyon Dream'),('39:14','The Human Algorithm')]


def seconds(value):
    minutes,secs=map(int,value.split(':'))
    return minutes*60+secs


# La vidéo source enchaîne l'album trois fois : le douzième chapitre s'arrête à la fin du premier passage.
ALBUM_END='42:21'


def description():
    return {'source_url':'https://www.youtube.com/watch?v=_Gajv2yJt5M','end':seconds(ALBUM_END),'tracks':[
        {'id':f'chapter_{index+1:02}', 'title':title,'start':seconds(start),
         'file':f'{index+1:02}-'+title.lower().replace(' ','-')+'.ogg','menu':index==1}
        for index,(start,title) in enumerate(CHAPTERS)]}


def import_album(source,output,*,chapters=None):
    source=Path(source).resolve();output=Path(output).resolve()
    if not source.is_file(): raise ValueError('Fichier source introuvable.')
    if not shutil.which('ffmpeg') or not shutil.which('ffprobe'):raise ValueError('FFmpeg et FFprobe sont requis pour le découpage, pas pour jouer.')
    metadata=json.loads(subprocess.check_output(['ffprobe','-v','error','-show_format','-show_streams','-of','json',str(source)],text=True))
    if not any(s.get('codec_type')=='audio' for s in metadata['streams']):raise ValueError('Le fichier ne contient aucune piste audio.')
    duration=float(metadata['format']['duration'])
    album=description() if chapters is None else chapters
    starts=[entry['start'] for entry in album['tracks']]
    album_end=min(album.get('end',duration),duration)
    if not starts or starts[0]!=0 or starts!=sorted(set(starts)) or starts[-1]>=album_end:raise ValueError('La durée de la source ne couvre pas tous les chapitres annoncés.')
    output.parent.mkdir(parents=True,exist_ok=True)
    # Tout encoder avant de remplacer les fichiers du précédent album.
    with tempfile.TemporaryDirectory(prefix='chapter-album-',dir=output.parent) as folder:
        staging=Path(folder)
        for index,entry in enumerate(album['tracks']):
            end=starts[index+1] if index+1<len(starts) else album_end
            length=end-entry['start']
            target=staging/entry['file']
            if target.parent!=staging or target.suffix!='.ogg':raise ValueError('Nom de chapitre invalide.')
            subprocess.run(['ffmpeg','-v','error','-nostdin','-y','-ss',str(entry['start']),'-i',str(source),'-t',str(length),'-vn','-map','0:a:0','-ar','44100','-ac','2','-c:a','libvorbis','-q:a','5','-metadata','title='+entry['title'],str(target)],check=True)
            entry['seconds']=round(length,3)
        output.mkdir(parents=True,exist_ok=True)
        for entry in album['tracks']:shutil.move(str(staging/entry['file']),output/entry['file'])
        temporary=output/'manifest.json.tmp'
        temporary.write_text(json.dumps(album,ensure_ascii=False,indent=2)+'\n')
        temporary.replace(output/'manifest.json')
    return album


if __name__=='__main__':
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('source',type=Path,help='Fichier audio ou vidéo complet déjà téléchargé')
    parser.add_argument('--output',type=Path,default=ROOT/'game/assets/audio/chapter-album')
    args=parser.parse_args()
    try:
        result=import_album(args.source,args.output)
        print(f"{len(result['tracks'])} chapitres importés. Wake Sequence au menu ; onze morceaux enchaînés en jeu. Relancer le jeu.")
    except (ValueError,subprocess.SubprocessError) as error:parser.exit(1,str(error)+'\n')
