"""Les nouvelles interfaces sociales publient et relisent de véritables données de jeu."""
import asyncio
from pathlib import Path
import httpx
from api.main import app, career
from engine.career import Career
from engine.persistence import state_from_dict, state_to_dict
from engine import contracts
from engine.game_loop import load_all_abilities


def test_chat_reply_archive_and_no_duplicate_checkpoint():
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
            game=(await client.post('/api/games',json={'contract':'tuto_p0','handle':'Operator'})).json()
            gid=game['id']
            original=[m for m in (await client.get('/api/messages')).json() if m.get('peer')=='k0rvid']
            assert len(original)==1
            result=await client.post(f'/api/games/{gid}/chat',json={'channel':'chordly','text':'Bonjour, quel est l’objectif ?'})
            assert result.status_code==200
            messages=result.json()['messages']
            assert [m['sender'] for m in messages[-2:]]==['Operator','k0rvid']
            assert all(m['peer']=='k0rvid' for m in messages)
            assert all(m['time'] for m in messages)
            assert len({m['id'] for m in messages})==len(messages)
            state=state_from_dict(career().data['active'])
            career().checkpoint(state)
            career().checkpoint(state)
            archive=[m for m in (await client.get('/api/messages')).json() if m.get('peer')=='k0rvid']
            assert len(archive)==len(messages)
            restored=Career(career().path)
            assert len([m for m in restored.data['conversations'].values() if m.get('peer')=='k0rvid'])==len(messages)
            assert (await client.post(f'/api/games/{gid}/chat',json={'channel':'telegrid','text':'Salut'})).status_code==400
            assert (await client.post(f'/api/games/{gid}/chat',json={'channel':'chordly','peer':'wrong-contact','text':'Salut'})).status_code==400
            assert (await client.post(f'/api/games/{gid}/chat',json={'channel':'chordly','text':'   '})).status_code==400
    asyncio.run(run())


def test_forum_replies_persist_and_locked_forums_are_enforced():
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app),base_url='http://test') as client:
            original_posts=(await client.get('/api/forum/threads/welcome')).json()
            assert len(original_posts)==2
            result=await client.post('/api/forum/threads/welcome',json={'handle':'Operator','text':'Bonjour, nouveau sur le forum.'})
            assert result.status_code==200
            assert result.json()[-1]['text']=='Bonjour, nouveau sur le forum.'
            assert (await client.get('/api/forum/threads/welcome')).json()==result.json()
            assert Career(career().path).data['forum_posts']['welcome'][-1]['author']=='Operator'
            assert (await client.get('/api/profile')).json()['forum_counts']['welcome']==3
            assert (await client.get('/api/forum/threads/tor')).status_code==403
            assert (await client.get('/api/forum/threads/private')).status_code==403
            assert (await client.get('/api/forum/threads/unknown')).status_code==404
            career().data['tier']=2
            assert (await client.get('/api/forum/threads/tor')).status_code==403
            career().data['route']='tor'
            assert (await client.get('/api/forum/threads/tor')).status_code==200
    asyncio.run(run())


def test_help_message_does_not_reveal_future_tutorial_steps():
    abilities=load_all_abilities()
    contract=contracts.load_contract(Path(__file__).parents[1]/'contracts/tuto_p0.json',known_ability_ids=set(abilities))
    state=contracts.start_contract(contract,'Operator',known_ability_ids=set(abilities))
    contracts.player_message(state,'chordly','Je suis perdu, aide-moi.')
    assert state.messages[-1].text.startswith('Indice 1/2')
    assert len(state.messages[-1].text)<len(contract['brief'])
    assert 'it.presta' not in state.messages[-1].text
    assert state_from_dict(state_to_dict(state)).messages[-1].time==state.messages[-1].time
