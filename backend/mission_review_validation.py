"""Deux actes I via des syntaxes et fichiers alternatifs, sans modifier les preuves."""
import asyncio
import copy
import json
import tempfile
from pathlib import Path
from act1_validation import PATHS, FINALS, play
from engine.career import Career


def alternatives():
    paths=copy.deepcopy(PATHS);finals=copy.deepcopy(FINALS)
    for cid,operations in paths.items():
        revised=[]
        for kind,line in operations:
            if cid=='act1_echantillon':
                line=line.replace('echantillon.db','analyse-nx.db').replace('SELECT date, COUNT(*)','SELECT COUNT(1) AS nombre,date').replace('rapport NX-26','Bilan NX‑26')
            elif cid=='act1_boutique':
                line=line.replace('/loot/sqlmap','/loot/autre-sql')
                if '--dump --batch' in line:line=line.replace('--dump --batch','--dump -C reference,id,date,client,montant --batch')
                line=line.replace('livraison PV-26 commandes','Commandes PV‑26 transmises')
            elif cid=='act1_portail':
                if kind=='c' and line.startswith('curl -H'):
                    line='curl --header="Cookie: session=ambre-client" --url="http://10.61.5.20/api/document?id=102" --output=~/loot/preuve-orme.csv'
                line=line.replace('~/loot/verre.csv','~/loot/preuve-orme.csv').replace('preuve VA-26-204 Orme','Constat VA‑26‑204 pour Orme')
            elif cid=='act1_empreinte':
                line=line.replace('~/loot/planning.csv','~/loot/passation.csv').replace('livraison OR-26-311','Je vous ai transmis OR‑26‑311')
            elif cid=='act1_service':
                line=line.replace('~/loot/tickets.tsv','~/loot/export-maintenance.tsv').replace(' > ','>')
                line=line.replace('livraison TK-26 tickets','Remise TK‑26 : tickets')
            elif cid=='act1_litige':
                line=line.replace('litige.db','comparaison.db').replace('SELECT source, reference, date','SELECT date, reference, source')
            if kind=='c' and line.startswith('cat ~/loot/'):line=line.replace('cat ','cat -n ',1)
            revised.append((kind,line))
        paths[cid]=revised
    for variant,operations in finals.items():
        revised=[]
        for kind,line in operations:
            line=line.replace('/loot/sqlmap','/loot/autre-final').replace('~/loot/boreal.tsv','~/loot/bordereaux.tsv')
            if kind=='m':line='Remis BR‑26 via '+variant
            if kind=='c' and line.startswith('cat ~/loot/'):line=line.replace('cat ','cat --number ',1)
            revised.append((kind,line))
        finals[variant]=revised
    return paths,finals


async def qualify(output):
    paths,finals=alternatives();reports=[]
    with tempfile.TemporaryDirectory(prefix='darknet-equivalent-') as folder:
        for variant in finals:
            profile=Career(Path(folder)/(variant+'.json'))
            result=await play(profile,variant,True,paths=paths,finals=finals)
            assert result['chapters']==10 and result['invitation_accepted']
            reports.append(result)
    output.mkdir(parents=True,exist_ok=True)
    (output/'mission-review-qualification.json').write_text(json.dumps({'scope':'Deux actes I par API/CLI, fichiers et syntaxes alternatifs ; aucun contournement des observations requises.','paths':reports},ensure_ascii=False,indent=2)+'\n', encoding='utf-8')
    print('Solutions équivalentes : deux actes I réussis, deux voies finales, exports renommés, colonnes SQL réordonnées et comptes rendus reformulés.')
    return reports


if __name__=='__main__':
    import sys
    asyncio.run(qualify(Path(sys.argv[1]) if len(sys.argv)>1 else Path('build/validation')))
