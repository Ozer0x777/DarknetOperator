"""Fixture visuelle issue des données du jeu, dans une carrière temporaire."""
import json
import sys
import tempfile
from pathlib import Path
from engine.career import Career
from engine import social, contracts


def export(target: Path):
    with tempfile.TemporaryDirectory(prefix='redteam-preview-') as directory:
        career = Career(Path(directory) / 'career.json')
        career.data.update(tier=3, route='relay', handle='nightshift', reputation=350)
        social.advance(career, 96)
        data = social.view(career, contracts.load_all_contracts())
        from engine.save_store import SaveStore
        slot = SaveStore(career.path).write(career.data, 'Avant le serveur')
        data['save_slots'] = [slot | {'valid': True}]
        intro = Career(Path(directory) / 'intro.json')
        intro.data.update(campaign_version=3, handle='nightshift')
        data['onboarding_world'] = social.view(intro, contracts.load_all_contracts())
        from engine.economy import catalog
        from engine.career import CATALOG
        from engine.campaign import CHAPTERS
        from engine.onboarding import STAGES
        shop_profile=Career(Path(directory)/'shop.json')
        shop_profile.data.update(campaign_version=3,tier=2,money=900,reputation=465,completed=list(dict.fromkeys(STAGES+[row[0] for row in CHAPTERS])),forum_invitation_accepted=True,inventory=['nullvad','gpu1'])
        data['shop_catalog']=catalog(shop_profile.data,CATALOG)
        from api.serializers import serialize_state
        first_state=contracts.start_contract(contracts.load_all_contracts()['intro_terminal'],'nightshift')
        contracts.player_message(first_state,'chordly','indice')
        data['first_hour_state']=serialize_state(first_state)
        learning_state=contracts.start_contract(contracts.load_all_contracts()['act1_service'],'nightshift')
        contracts.player_message(learning_state,'chordly','rappel détaillé')
        data['learning_state']=serialize_state(learning_state)
        from engine import console_sessions, deployment, terminal, bloodhound
        from engine.game_loop import load_all_abilities
        ad_state=contracts.start_contract(contracts.load_all_contracts()['act2_annuaire'],'nightshift')
        ad_state.hosts['win'].files['/Users/audit/sharphound.exe']=deployment.TOOL_MARKERS['sharphound']
        console_sessions.enter(ad_state,ad_state.hosts['win'],'audit','USER')
        assert terminal.parse(r'C:\Users\audit\sharphound.exe --CollectionMethods Group,ObjectProps --OutputDirectory C:\Users\audit --ZipFileName preview.zip',ad_state,load_all_abilities()).ok
        ad_state.terminal_files['/home/operator/loot/preview.zip']=ad_state.hosts['win'].files['/Users/audit/preview.zip']
        data['bloodhound']=bloodhound.import_archive(ad_state,'/home/operator/loot/preview.zip')
        second=Career(Path(directory)/'act2.json')
        second.data.update(campaign_version=3,tier=2,route='tor',inventory=['nullvad'],completed=[row[0] for row in CHAPTERS]+['act2_passation','act2_compte'],forum_invitation_accepted=True,handle='nightshift',reputation=500,forum_reputation={'breachboard':500,'exployt':40,'xsx':0})
        data['act2_profile']=second.view()

        from engine import curriculum
        from engine.onboarding import CURRENT_STAGES
        current=Career(Path(directory)/'current.json')
        current.data.update(campaign_version=4,handle='nightshift',completed=CURRENT_STAGES[:-1],money=385,reputation=35,forum_reputation={'breachboard':35,'exployt':0,'xsx':0})
        data['current_world']=social.view(current,curriculum.definitions(current.data,contracts.load_all_contracts()))
        data['current_profile']=current.view()
        transition=Career(Path(directory)/'transition.json')
        transition.data.update(campaign_version=4,handle='nightshift',tier=2,route='tor',inventory=['nullvad'],completed=list(dict.fromkeys(CURRENT_STAGES+[row[0] for row in CHAPTERS])),forum_invitation_accepted=True,reputation=500,forum_reputation={'breachboard':500,'exployt':0,'xsx':0})
        data['transition_world']=social.view(transition,curriculum.definitions(transition.data,contracts.load_all_contracts()))
        data['transition_profile']=transition.view()

        data['onboarding_brief'] = contracts.load_all_contracts()['intro_terminal']['brief']
        chapter = Career(Path(directory) / 'chapter.json')
        chapter.data.update(tier=1,completed=['tuto_p0','morel'],handle='nightshift',reputation=90)
        data['chapter_world'] = social.view(chapter, contracts.load_all_contracts())
        data['chapter_posts'] = chapter.data['forum_posts']['aquila-portail']
        data['tutorial_guide'] = contracts.load_all_contracts()['tuto_p0']['guide'][0]['message']
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_text(json.dumps(data, ensure_ascii=False, indent=2) + '\n')


if __name__ == '__main__': export(Path(sys.argv[1]))
