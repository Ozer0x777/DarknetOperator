"""Nouvelle carrière jusqu'au dernier dossier, deux choix d'affiliation, via API/CLI."""
import asyncio
import json
import tempfile
from pathlib import Path
from act1_validation import play
from validation import play_campaign
from engine.career import Career


async def qualify(output):
    output.mkdir(parents=True,exist_ok=True)
    results=[]
    with tempfile.TemporaryDirectory(prefix='darknet-journey-') as folder:
        for variant,affiliation in [('sqlmap','vesper'),('connecteur','glasswing')]:
            path=Path(folder)/(affiliation+'.json')
            first=await play(Career(path),variant,True)
            before=Career(path).data['money']
            final=await play_campaign(existing=Career(path),contract_ids=['varenne','affiliation','grand_compte'],affiliation=affiliation)
            profile=Career(path).view()
            assert final['tier']==3 and 'grand_compte' in final['completed']
            assert profile['access']['forums']['xsx']['unlocked']
            ledger=Career(path).data['wallet']['entries'];balance=0
            for entry in ledger:
                balance+=entry['amount']
                assert balance==entry['balance']
            assert balance==profile['money']
            results.append(dict(affiliation=affiliation,first_purchase=first['first_purchase'],act1_balance=before,
                                final_balance=balance,forum_reputation=profile['forum_reputation'],journey=profile['journey'],
                                scenarios=final['scenarios'],career_events=profile['career_events']))
    report={'scope':'Deux carrières neuves, commandes de référence et temps accéléré ; aucun test graphique ni mesure de durée humaine.',
            'paths':results}
    (output/'journey-qualification.json').write_text(json.dumps(report,ensure_ascii=False,indent=2)+'\n', encoding='utf-8')
    print('Parcours complet : deux nouvelles carrières, premier achat confirmé et restauré, Exployt puis XSX ; journaux équilibrés.')
    return report


if __name__=='__main__':
    import sys
    asyncio.run(qualify(Path(sys.argv[1]) if len(sys.argv)>1 else Path('build/validation')))
