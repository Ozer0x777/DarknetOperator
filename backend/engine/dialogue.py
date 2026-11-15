"""Répliques écrites et mémoire de conversation, sans déduire un choix de relation.

Les intentions servent uniquement à trouver une réplique. Elles ne valent ni
consentement, ni confiance acquise, ni confidence vraie. Les futurs choix
explicites pourront s'appuyer sur les scènes et leurs identifiants stables.
"""
import re
import unicodedata


def _normalize(text: str) -> str:
    return ''.join(c for c in unicodedata.normalize('NFD', text.casefold())
                   if unicodedata.category(c) != 'Mn').replace('’', "'")


INTENTS = (
    ('boundary', ("je prefere pas", "je prefere ne pas", "je ne veux pas", "j'ai pas envie", "pas tes affaires", "garde mes distances", "pas de romance", "ne t'aime pas", "laisse tomber", "change de sujet", "arrete de")),
    ('suspicion', ('espionne', 'espion', 'tu me manipules', 'tu travailles pour qui', 'tu me caches', 'tu me pieges', 'tu me mens')),
    ('ransom', ('rancon', 'ransom', 'chiffrement', 'sauvegarde')),
    ('dispute', ('escrow', 'litige', 'arnaque', 'vendeur')),
    ('defense', ('edr', 'pare-feu', 'firewall')),
    ('fatigue', ('fatigue', 'creve', 'epuise', 'dormir', 'pas dormi', 'nuit blanche', 'ca va pas', 'stresse')),
    ('wellbeing', ('comment tu vas', 'comment vas-tu', 'comment ca va', 'ca va', 'tu vas bien', 'comment allez-vous', 'comment vous allez')),
    ('flirt', ('tu me plais', 'je t aime', "je t'aime", 'attire', 'amoureux', 'amoureuse', 'flirter', 'flirt', 'rendez-vous', 'tu me manques')),
    ('trust', ('confiance', 'relation', 'contretemps', 'ct-26-071')),
    ('people', ('spectre', 'nullroute', 'traverse', 'cinquieme', '0xvanta', 'cendre')),
    ('expertise', ('cti', 'osint', 'ingenierie sociale', 'social engineering', 'veille strategique', 'ton metier')),
    ('fashion', ('la mode', 'de mode', 'vetements', 'tenues', 'couture')),
    ('museums', ('musee', 'musees', 'exposition', 'expositions')),
    ('personal', ('ta vie', 'temps libre', 'en dehors', 'tu aimes quoi', 'parle-moi de toi', 'parle moi de toi', 'qui es-tu', 'the', 'cafe', 'musique', 'plantes', 'voisine', 'sport', 'courir', 'concert', 'sortir', 'danser', 'culture')),
    ('thanks', ('merci', 'recu', 'compris', 'ok')),
    ('greeting', ('bonjour', 'salut', 'hello', 'coucou', 'bonsoir')),
)


def intent(text: str) -> str:
    normalized = _normalize(text)
    for name, phrases in INTENTS:
        if any(re.search(r'(?<!\w)' + re.escape(phrase) + r'(?!\w)', normalized) for phrase in phrases):
            return name
    return 'unknown'


def reply(contact: dict, text: str, memory: dict, handle: str) -> str:
    """Varie les répliques à la reprise sans tirage aléatoire ni compteur d'affection."""
    topic = intent(text)
    lines = contact.get('dialogue', {})
    if topic not in lines:
        topic = 'unknown'
    options = lines.get(topic, [contact.get('followup', 'Je ne suis pas sûr de comprendre. Tu peux préciser ?')])
    replies = memory.setdefault('replies', {})
    index = replies.get(topic, 0)
    replies[topic] = index + 1
    memory['last_intent'] = topic
    return options[index % len(options)].replace('{handle}', handle)
