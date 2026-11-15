"""Lecture réelle des sujets : marqueur persistant, catégories et aucun compteur inventé."""
import asyncio
import httpx
from api import main as api
from engine import social
from engine.career import Career


def topic(profile, ident):
    return next(t for t in social.view(profile)['threads'] if t['id']==ident)


def test_read_watermark_survives_reload_and_notices_posts_at_the_same_minute():
    async def run():
        profile=api.career()
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api.app),base_url='http://test') as client:
            before=topic(profile,'welcome')
            assert before['unread']==3 and before['participants']==['bytewarden','miette','mod_echo']
            assert before['category']=='Vie du forum'
            assert (await client.get('/api/forum/threads/welcome')).status_code==200
            assert topic(profile,'welcome')['unread']==0
            restored=Career(profile.path)
            assert topic(restored,'welcome')['unread']==0
            posts=profile.data['forum_posts']['welcome']
            posts.append(social._post('new-at-same-minute','sable','Une précision.',posts[-1]['minute']))
            assert topic(profile,'welcome')['unread']==1
            views=profile.data['thread_views']['welcome']
            assert (await client.get('/api/forum/threads/welcome?refresh=true')).status_code==200
            assert topic(profile,'welcome')['unread']==0
            assert profile.data['thread_views']['welcome']==views
            profile.save=lambda: (_ for _ in ()).throw(AssertionError('Écriture répétée sans nouveau message'))
            assert (await client.get('/api/forum/threads/welcome?refresh=true')).status_code==200
    asyncio.run(run())


def test_unread_markers_do_not_unlock_a_forum_or_mutate_a_player_post(tmp_path):
    profile=Career(tmp_path/'career.json')
    profile.data['classic_progression']=True
    profile.data['campaign_version']=1
    profile.data['tier']=1
    social.prepare(profile)
    posts=profile.data['forum_posts']['welcome']
    posts.append(social._post('player:keep','Operator','Mon message à conserver.',0))
    profile.data['social']['forum_seen']={'welcome':'player:keep'}
    social.prepare(profile)
    assert posts[-1]['text']=='Mon message à conserver.'
    assert topic(profile,'welcome')['unread']==0
    assert not any(t['forum'] in {'exployt','xsx'} for t in social.view(profile)['threads'])


def test_posting_marks_own_reply_read_but_the_next_npc_reply_is_unread():
    async def run():
        profile=api.career()
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api.app),base_url='http://test') as client:
            assert (await client.get('/api/forum/threads/welcome')).status_code==200
            response=await client.post('/api/forum/threads/welcome',json={'handle':'Operator','text':'Bonjour à tous.'})
            assert response.status_code==200
            assert topic(profile,'welcome')['unread']==0
            social.advance(profile,5)
            assert topic(profile,'welcome')['unread']==1
    asyncio.run(run())
