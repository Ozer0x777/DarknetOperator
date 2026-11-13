"""Cursus courant : acte I sans techniques avancées, puis acte II, par API."""
import asyncio
import copy
import json
import tempfile
from pathlib import Path
from act1_validation import PATHS, FINALS, play as play_act1
from act2_validation import play as play_act2
from engine.career import Career

CURRENT_PATHS=copy.deepcopy(PATHS)
CURRENT_PATHS.pop('intro_hash')
CURRENT_PATHS['intro_transfer']=[('c','scp m.leroux@10.20.0.21:C:/Users/m.leroux/Documents/transfert.txt ~/loot/transfert.txt'),('c','Password123!'),('c','cat ~/loot/transfert.txt')]
CURRENT_PATHS['tuto_p0']=[('c','cat ~/mission/ravelle.txt'),('c','host www.ravelle-associes.fr'),('c','nmap -sV 51.91.204.27'),('c','curl http://www.ravelle-associes.fr/'),('c','curl http://www.ravelle-associes.fr/mentions.txt'),('c','curl -o ~/loot/ravelle.txt http://www.ravelle-associes.fr/documents/RAV-26-001.txt'),('c','cat ~/loot/ravelle.txt'),('m','livraison RAV-26-001')]
CURRENT_PATHS['act1_empreinte']=[('c','cat ~/mission/passation.txt'),('s','ssh planning@10.61.6.21'),('s','Atelier2026!'),('s','whoami'),('c','scp planning@10.61.6.21:/srv/planning/OR-26-311.csv ~/loot/planning.csv'),('c','Atelier2026!'),('c','cat ~/loot/planning.csv'),('m','livraison OR-26-311')]
CURRENT_PATHS['act1_service']=[('c','cat ~/mission/reperes.txt'),('s','ssh svc.ticket@10.61.7.30'),('s','Maintenance2026!'),('s','whoami'),('s','systemctl status ticketd'),('s','cat /home/svc.ticket/README.txt'),('s','cat /etc/ticketd/database.ini'),('c','mysql -h 10.61.7.10 -u ticket_ro -p -D ticketing -e "SELECT * FROM tickets;" > ~/loot/tickets.tsv'),('c','TicketRead2026!'),('c','cat ~/loot/tickets.tsv'),('m','livraison TK-26 tickets')]


async def qualify(output):
    output.mkdir(parents=True,exist_ok=True);reports=[]
    with tempfile.TemporaryDirectory(prefix='darknet-current-curriculum-') as folder:
        for first,second in [('sqlmap','pivot'),('connecteur','smb')]:
            profile=Career(Path(folder)/(first+'.json'))
            report=await play_act1(profile,first,True,output/('current-act1-'+first+'.json'),paths=CURRENT_PATHS,finals=FINALS,curriculum='current',buy_first=False)
            assert profile.data['campaign_version']==4 and 'intro_hash' not in profile.data['completed']
            assert report['chapters']==10 and report['side_jobs']==7 and report['side_income']==310
            assert not report['first_purchase'] and profile.data['inventory']==['nullvad']
            before=profile.data['money']
            continuation=await play_act2(profile,second,True,bootstrap=False)
            assert continuation['missions']==10 and continuation['sides']==6 and continuation['balance']>before
            assert profile.data['choices']['litige118']==('publication' if first=='sqlmap' else 'mediation')
            assert profile.data['choices']['act2_binome']=='binome_'+second
            reports.append(dict(act1=report,act2=continuation))
    (output/'curriculum-qualification.json').write_text(json.dumps(reports,ensure_ascii=False,indent=2)+'\n', encoding='utf-8')
    print('Cursus courant : deux actes I allégés sans achat, sept exercices et sept petits contrats ; deux actes II complets, choix et reprises conservés.')
    return reports


if __name__=='__main__':
    import sys
    asyncio.run(qualify(Path(sys.argv[1]) if len(sys.argv)>1 else Path('build/validation')))
