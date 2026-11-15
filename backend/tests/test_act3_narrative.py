"""Le lot transmis à TLS provient de la copie d'audit effectivement acquise."""
import copy
import hashlib
import pytest
from engine import conversation_scenes as scenes, social
from engine.career import Career
from test_tls_arc import _career, _answer, ARC
from test_act3_contracts import play_path, confirm


def prepare_tls(tmp_path, stance):
    career=_career(tmp_path,stance)
    career.data['completed'].append('act3_tamper')
    for ident,option in zip(ARC,['histoire','independance','resume','refus','questionner']):
        _answer(career,ident,option)
    _answer(career,'tls-lenoir-pause','musique')
    return career


@pytest.mark.parametrize('stance',['professionnel','amitie','attirance'])
@pytest.mark.parametrize('choice',['refuser','expurge','lot_complet'])
def test_explicit_industrial_delivery_all_links_and_replayed_choices(tmp_path,stance,choice):
    career=prepare_tls(tmp_path,stance)
    assert 'lenoir-lot' not in career.data['social'].get('documents',{})
    s,loop=play_path('act3_dossier');confirm(s,loop)
    career.settle('validated-industrial-lot',s)
    social.prepare(career)
    document=career.data['social']['documents']['lenoir-lot']
    assert document['content']==s.terminal_files['/home/operator/loot/lot-industriel.txt']
    assert document['sha256']==hashlib.sha256(document['content'].encode()).hexdigest()
    assert 'tls-lenoir-demande' not in career.data['social'].get('transmissions',{})
    career.save();career=Career(career.path)
    scenes.choose(career,'chordly','Madame_TLS','tls-lenoir-demande',choice,'NightShift')
    snapshot=copy.deepcopy(career.data)
    scenes.choose(career,'chordly','Madame_TLS','tls-lenoir-demande',choice,'NightShift')
    assert career.data==snapshot
    tx=career.data['social'].get('transmissions',{}).get('tls-lenoir-demande')
    if choice=='refuser':assert tx is None
    else:
        sent=tx['documents'][0]
        assert sent['id']==('lenoir-lot' if choice=='lot_complet' else 'lenoir-expurge')
        assert ('184 €/unité' in sent['content'])==(choice=='lot_complet')
        assert sent['sha256']==hashlib.sha256(sent['content'].encode()).hexdigest()
    assert career.data['social']['bonds']['Madame_TLS']['stance']==stance
    social.advance(career,2);social.prepare(career)
    assert career.data['social']['scenes']['active']['Madame_TLS']=='tls-lenoir-retour'
    _answer(career,'tls-lenoir-retour','origine')
    assert career.data['social']['bonds']['Madame_TLS']['lenoir_retour']=='commanditaire_demande'


def test_completion_flag_alone_does_not_grant_industrial_lot_or_open_delivery(tmp_path):
    career=prepare_tls(tmp_path,'professionnel')
    career.data['completed'].append('act3_dossier')
    social.prepare(career)
    assert 'lenoir-lot' not in career.data['social'].get('documents',{})
    assert career.data['social']['scenes']['active'].get('Madame_TLS')!='tls-lenoir-demande'
    with pytest.raises(ValueError):
        scenes.choose(career,'chordly','Madame_TLS','tls-lenoir-demande','lot_complet','NightShift')
