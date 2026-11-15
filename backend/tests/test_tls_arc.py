"""Premier arc TLS : trois liens, vrais envois de pièces et reprises aux cinq scènes."""
import asyncio
import copy
import hashlib

import httpx
import pytest

import api.main as api
from engine import contracts, conversation_scenes as scenes, social, terminal
from engine.career import Career
from engine.game_loop import GameLoop, load_all_abilities
from engine.mission_data import desk_after, inherit
from engine.save_store import SaveStore


ARC = ['tls-arc-exposition','tls-arc-desaccord','tls-arc-veille','tls-arc-limite','tls-arc-retour']


def _career(tmp_path, stance='professionnel'):
    career=Career(tmp_path/'career.json')
    career.data.update(handle='NightShift', campaign_version=4, tier=1, reputation=100,
                       completed=['tuto_p0','act1_portail'])
    social.prepare(career)['published'].append('tls-contact')
    social.prepare(career)
    _answer(career,'tls-premier-lien',stance)
    return career


def _answer(career, scene_id, option):
    assert career.data['social']['scenes']['active']['Madame_TLS']==scene_id
    scenes.choose(career,'chordly','Madame_TLS',scene_id,option,'NightShift')
    social.advance(career,2)
    social.prepare(career)


def _round_trip(career):
    career.save()
    return Career(career.path)


@pytest.mark.parametrize('stance',['professionnel','amitie','attirance'])
@pytest.mark.parametrize('favor',['communique','resume','refus'])
@pytest.mark.parametrize('disclosure',['note_privee','public_seulement','refus'])
def test_five_scenes_with_three_links_and_all_document_choices_survive_resumes(tmp_path,stance,favor,disclosure):
    career=_career(tmp_path,stance)
    before=(career.data['money'],career.data['reputation'],copy.deepcopy(career.data.get('choices',{})))
    for ident, option in zip(ARC,['histoire','independance',favor,disclosure,'questionner']):
        career=_round_trip(career)  # reprise avec la question ouverte
        active=next(s for s in social.view(career)['scene_choices'] if s['peer']=='Madame_TLS')
        assert active['id']==ident and len(active['options'])==3
        assert all('reply' not in o and 'effects' not in o and 'transmit_documents' not in o for o in active['options'])
        scenes.choose(career,'chordly','Madame_TLS',ident,option,'NightShift')
        career=_round_trip(career)  # reprise avant réception de la réponse
        snapshot=copy.deepcopy(career.data)
        scenes.choose(career,'chordly','Madame_TLS',ident,option,'NightShift')
        assert career.data==snapshot  # aucun renvoi de pièce ou message en double
        social.advance(career,2)
        social.prepare(career)
    world=career.data['social'];bond=world['bonds']['Madame_TLS']
    assert bond['stance']==stance
    assert bond['arc_opinion']=='independance'  # contredire n'enlève pas le lien
    assert (career.data['money'],career.data['reputation'],career.data.get('choices',{}))==before
    for ident in ARC:
        assert sum(m.get('id')=='scene:'+ident for m in career.data['conversations'].values())==1
        assert sum(m.get('id')=='scene:answer:'+ident for m in career.data['conversations'].values())==1
    transmissions=world.get('transmissions',{})
    if favor=='refus': assert 'tls-arc-veille' not in transmissions
    else:
        document=transmissions['tls-arc-veille']['documents'][0]
        assert document['classification']=='public'
        assert 'BRUME-17' not in document['content'] and 'Marot' not in document['content']
        if favor=='resume': assert 'Lenoir' not in document['content'] and 'Orme' not in document['content']
    if disclosure=='note_privee':
        document=transmissions['tls-arc-limite']['documents'][0]
        assert document['id']=='tls-passation' and 'Élise Marot' in document['content']
        assert document['sha256']==hashlib.sha256(document['content'].encode()).hexdigest()
        assert document['content'] in career.data['conversations']['scene:answer:tls-arc-limite']['text']
        assert bond['arc_resolution']=='diffusion_questionnee'
        assert 'sources publiques' in world['documents']['tls-retour-prive']['content']
    else:
        assert all(doc['classification']!='privé' for entry in transmissions.values() for doc in entry['documents'])
        assert bond['arc_resolution']=='sources_demandees'
        assert 'BRUME-17' in world['documents']['tls-retour-public']['content']
        reply=career.data['conversations'][world['scenes']['choices']['tls-arc-retour']['reply_id']]['text']
        assert 'origine' in reply and 'pas' in reply
    # La première chaîne d'introduction reprend ensuite, sans exiger l'acte II pour l'arc.
    assert not any(cid.startswith('act2_') for cid in career.data['completed'])


@pytest.mark.parametrize('stance',['professionnel','amitie','attirance'])
def test_three_links_open_with_different_words_and_restore_from_a_manual_slot(tmp_path,stance):
    career=_career(tmp_path,stance)
    question=career.data['conversations']['scene:tls-arc-exposition']['text']
    expected={'professionnel':'cadre professionnel','amitie':'tu aurais','attirance':'envie de te demander'}
    assert expected[stance] in question.casefold()
    slot=SaveStore(career.path).write(career.data,'Avant le musée')
    restored=Career(tmp_path/'restored.json')
    restored.replace(SaveStore(career.path).read(slot['id'])['profile'])
    assert social.view(restored)['scene_choices']==social.view(career)['scene_choices']
    assert restored.data['social']['bonds']['Madame_TLS']['stance']==stance


def test_open_question_and_replies_are_frozen_across_an_editorial_update(tmp_path,monkeypatch):
    career=_career(tmp_path,'amitie')
    scene=career.data['social']['scenes']['resolved']['tls-arc-exposition']
    question=scene['question'];reply=scene['options'][0]['reply']
    updated=copy.deepcopy(scenes.content())
    changed=next(s for s in updated['scenes'] if s['id']=='tls-arc-exposition')
    changed['question']='Version de la prochaine partie'
    changed['options'][0]['reply']='Réponse future'
    changed['variants']=[]
    monkeypatch.setattr(scenes,'content',lambda:updated)
    assert next(s for s in social.view(career)['scene_choices'] if s['peer']=='Madame_TLS')['question']==question
    _answer(career,'tls-arc-exposition','forme')
    received=career.data['social']['scenes']['choices']['tls-arc-exposition']['reply_id']
    assert career.data['conversations'][received]['text']==reply


def test_received_pieces_are_shared_local_files_and_deleted_copies_do_not_return(tmp_path):
    career=_career(tmp_path)
    _answer(career,ARC[0],'forme')
    _answer(career,ARC[1],'transparence')
    document=career.data['social']['documents']['tls-passation']
    abilities=load_all_abilities()
    state=contracts.start_contract(contracts.load_all_contracts()['intro_terminal'],'NightShift',known_ability_ids=set(abilities))
    scenes.provision_files(state,career.data)
    assert ''.join(terminal.parse('cat '+document['path'],state,abilities).output)==document['content']
    state.terminal_files[document['path']]='Ma copie annotée'
    scenes.provision_files(state,career.data)
    assert state.terminal_files[document['path']]=='Ma copie annotée'
    del state.terminal_files[document['path']]
    desk=desk_after(state)
    following=contracts.start_contract(contracts.load_all_contracts()['intro_recon'],'NightShift',known_ability_ids=set(abilities))
    inherit(following,desk)
    scenes.provision_files(following,career.data)
    assert document['path'] not in following.terminal_files
    # L'option envoie la pièce reçue en conversation, pas une copie locale potentiellement modifiée.
    _answer(career,ARC[2],'communique')
    scenes.choose(career,'chordly','Madame_TLS',ARC[3],'note_privee','NightShift')
    assert career.data['social']['transmissions'][ARC[3]]['documents'][0]['content']==document['content']


def test_documents_can_be_read_through_workspace_and_active_mission_api(tmp_path):
    async def run():
        api._CAREER=_career(tmp_path)
        _answer(api.career(),ARC[0],'histoire');_answer(api.career(),ARC[1],'transparence')
        path=api.career().data['social']['documents']['tls-passation']['path']
        state=contracts.start_contract(contracts.load_all_contracts()['intro_terminal'],'NightShift',known_ability_ids=set(api.ABILITIES))
        api.GAMES['arc-live']=api.GameSession('arc-live',GameLoop(state,api.ABILITIES))
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api.app),base_url='http://test') as client:
            for url in ('/api/workspace/terminal','/api/games/arc-live/terminal'):
                response=await client.post(url,json={'line':'cat '+path})
                assert response.status_code==200 and response.json()['ok']
                assert any('BRUME-17' in line for line in response.json()['output'])
    asyncio.run(run())


def test_library_variants_and_declared_transmissions_are_consistent():
    library=scenes.content()['documents'];ids={s['id'] for s in scenes.content()['scenes']}
    assert len({d['path'] for d in library.values()})==len(library)
    for scene in scenes.content()['scenes']:
        options={o['id'] for o in scene['options']}
        for version in [scene,*scene.get('variants',[])]:
            assert set(version.get('grant_documents',[]))<=set(library)
            assert set(version.get('requires_scene_choices',{}))<=ids
            if 'options' in version:
                changes=version['options'].values() if isinstance(version['options'],dict) else version['options']
                if isinstance(version['options'],dict): assert set(version['options'])<=options
                for option in changes:assert set(option.get('transmit_documents',[]))<=set(library)


def test_distance_at_the_exhibition_is_a_deliberate_return_to_professional_tone(tmp_path):
    career=_career(tmp_path,'attirance')
    _answer(career,ARC[0],'distance')
    assert career.data['social']['bonds']['Madame_TLS']['stance']=='professionnel'
    question=next(s for s in social.view(career)['scene_choices'] if s['peer']=='Madame_TLS')['question']
    assert question.startswith('Je reste sur le dossier')


def test_api_qualification_exports_three_playable_review_profiles(tmp_path):
    from tls_arc_validation import play
    output=tmp_path/'validation'
    report=asyncio.run(play(output))
    assert report['resumes']==36 and len(report['routes'])==3
    for stance in ('professionnel','amitie','attirance'):
        profile=Career(output/'tls-arc-playtest'/stance/'career.json')
        assert profile.data['social']['bonds']['Madame_TLS']['stance']==stance
        assert profile.data['social']['scenes']['active']['Madame_TLS']==ARC[0]
        assert 'tls-arc-limite' not in profile.data['social']['scenes']['choices']
