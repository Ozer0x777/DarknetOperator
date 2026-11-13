"""Le texte des consoles survit à la reprise d'une sauvegarde, sans conserver les mots de passe."""
import asyncio
import httpx
import api.main as api


def test_console_text_is_restored_after_resume_without_passwords():
    async def run():
        async with httpx.AsyncClient(transport=httpx.ASGITransport(app=api.app), base_url='http://test') as client:
            assert (await client.post('/api/profile/new', json={'handle': 'NightShift', 'confirm': True})).status_code == 200
            game = (await client.post('/api/games', json={'contract': 'intro_terminal', 'handle': 'NightShift', 'rng_seed': 0})).json()
            gid = game['id']

            async def command(line, console='main'):
                response = (await client.post(f'/api/games/{gid}/terminal', json={'line': line, 'console_id': console})).json()
                while api.GAMES[gid].loop._queue: api.GAMES[gid].loop.tick()
                return response

            await command('pwd')
            await command('nmap -sV 10.20.0.21', 'term-2')
            assert (await command('ssh m.leroux@10.20.0.21', 'term-3'))['password_prompt']
            await command('Password123!', 'term-3')
            await command('echo temporaire', 'term-4')
            await command('clear', 'term-4')
            api.career().checkpoint(api.GAMES[gid].state)
            api.career().save()

            # Nouveau lancement du jeu : plus aucune session en mémoire.
            api.GAMES.clear(); api._CAREER = None
            resumed = (await client.post('/api/profile/resume', json={})).json()
            transcripts = resumed['state']['terminal_transcripts']
            main = transcripts['main']
            assert '┌──(operator㉿kali)-[~]' in main and '└─$ pwd' in main and '/home/operator' in main
            scan = '\n'.join(transcripts['term-2'])
            assert '└─$ nmap -sV 10.20.0.21' in scan and 'Nmap scan report' in scan
            login = transcripts['term-3']
            assert "m.leroux@10.20.0.21's password:" in login and not any('Password123!' in line for line in login)
            assert transcripts.get('term-4') == []
            # Les mises à jour en direct ne transportent pas tout l'historique des consoles.
            assert 'terminal_transcripts' not in api.serialize_state(api.GAMES[resumed['id']].state)
    asyncio.run(run())
