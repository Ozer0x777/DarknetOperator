"""Filtres utilisés pendant l'enquête : résultats, erreurs et fichiers partagés."""
import hashlib
from engine.models import GameState
from engine.terminal import parse
from engine.persistence import state_to_dict, state_from_dict


def prepared():
    state=GameState(hosts={},users={})
    state.terminal_files['/home/operator/loot/a.csv']='ref;client;lot\nAF-26;Nacre;B\nAF-24;Orme;A\nAF-26;Nacre;B\n'
    return state


def test_pipeline_filters_count_and_redirect_persist():
    state=prepared()
    result=parse('cat ~/loot/a.csv | grep AF-26 | cut -d ";" -f 3 | sort | uniq -c > ~/loot/resultat.txt',state,{})
    assert result.ok and not result.output
    assert state.terminal_files['/home/operator/loot/resultat.txt']=='      2 B\n'
    assert parse('wc -l ~/loot/a.csv',state,{}).output==['4 /home/operator/loot/a.csv\n']
    assert parse('head -n 1 ~/loot/a.csv',state,{}).output==['ref;client;lot\n']
    assert parse('tail -n 1 ~/loot/a.csv',state,{}).output==['AF-26;Nacre;B\n']
    reloaded=state_from_dict(state_to_dict(state))
    assert reloaded.terminal_files['/home/operator/loot/resultat.txt']=='      2 B\n'
    assert 'operator:/home/operator/loot/a.csv' in reloaded.tool_data['read_files']


def test_grep_exits_patterns_and_missing_file():
    state=prepared()
    assert parse('grep -in nacre ~/loot/a.csv',state,{}).output==['2:AF-26;Nacre;B\n4:AF-26;Nacre;B\n']
    assert parse("grep -E 'AF-24|AF-26' ~/loot/a.csv",state,{}).output==['AF-26;Nacre;B\nAF-24;Orme;A\nAF-26;Nacre;B\n']
    assert parse('grep absent ~/loot/a.csv',state,{}).exit_code==1
    assert parse('grep -c absent ~/loot/a.csv',state,{}).output==['0\n']
    assert parse('grep absent ~/loot/a.csv | wc -l',state,{}).output==['0\n']
    assert parse('grep -Z x ~/loot/a.csv',state,{}).exit_code==2
    assert parse("grep '[' ~/loot/a.csv",state,{}).exit_code==2
    assert parse('grep x ~/loot/manquant.txt',state,{}).exit_code==2
    assert not parse('head -n 1 ~/loot/a.csv > ~/absent/test.txt',state,{}).ok
    assert not parse('head -n 1 ~/loot/a.csv > /etc/passwd',state,{}).ok


def test_recursive_fixed_inverted_and_sha256():
    state=prepared()
    state.terminal_files['/home/operator/loot/b.txt']='AF.26\nAF-24\n'
    result=parse("grep -rFn 'AF.26' ~/loot",state,{})
    assert result.output==['/home/operator/loot/b.txt:1:AF.26\n']
    assert parse("grep -v 'AF' ~/loot/a.csv",state,{}).output==['ref;client;lot\n']
    expected=hashlib.sha256(state.terminal_files['/home/operator/loot/b.txt'].encode()).hexdigest()
    assert parse('sha256sum ~/loot/b.txt',state,{}).output==[expected+'  /home/operator/loot/b.txt\n']
    assert parse('cat ~/loot/b.txt | sha256sum',state,{}).output==[expected+'  -\n']
