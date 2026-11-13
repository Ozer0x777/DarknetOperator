"""Prix et réserves du jeu solo ; aucun paiement réel."""
GPU_PRICES = {1: 400, 2: 1200, 3: 3000}
DESCRIPTIONS = {
    'nullvad': 'Active NullVad et, au palier 2, Tor. 50 ₵ au premier départ de chaque dossier ; les reprises du même dossier sont couvertes.',
    'wordlist': 'Dictionnaire local enrichi dans ~/wordlist.txt. Utilisé avec Hashcat, réduit le délai de deux ticks ; ne garantit pas un résultat.',
    'gpu1': 'Hashcat : délai de base de 9 à 5 ticks. Aucun mot de passe n’est révélé sans correspondance dans le dictionnaire.',
    'gpu2': 'Hashcat : délai de base de 3 ticks. Le prix tient compte du meilleur GPU déjà acquis.',
    'gpu3': 'Hashcat : délai de base de 2 ticks. Le prix tient compte du meilleur GPU déjà acquis.',
    'relay': 'Passage SSH pour un dossier. Consommé au premier départ ; les nouvelles tentatives de ce même dossier restent couvertes.',
    'vesper': 'Affiliation gratuite : conserve 30 % du règlement des contrats marqués affiliation.',
    'glasswing': 'Licence permanente : conserve 100 % du règlement modulé des contrats marqués affiliation. Le grand compte n’a pas cette retenue. Une licence n’est pas forcément rentable si les sauvegardes réduisent le règlement.',
}


def price(data, item):
    if item['id'] not in {'gpu2', 'gpu3'}: return item['price']
    owned = max((level for level in GPU_PRICES if 'gpu'+str(level) in data['inventory']), default=0)
    return max(0, item['price'] - GPU_PRICES.get(owned, 0))


def reserve(data):
    from .campaign import enabled
    if not enabled(data) or not data.get('forum_invitation_accepted'): return 0
    passes = data.get('route_passes', [])
    from .curriculum import current
    legacy_route=data.get('tier',0)>=3 or 'varenne' in data['completed'] or ((data.get('active') or {}).get('contract') or {}).get('contract_id') in {'varenne','affiliation','grand_compte'}
    if current(data) and (data.get('act2_started') or not legacy_route):
        from .act2 import CHAPTERS
        next_id=next((cid for cid,*_ in CHAPTERS if cid not in data['completed']),None)
        if data.get('route')=='relay':
            return 300 if next_id and next_id+':relay' not in passes and 'relay' not in data['inventory'] else 0
        return 50 if next_id and next_id+':vpn' not in passes else 0
    if ('varenne' in data['completed'] or data['tier'] >= 3) and 'grand_compte' not in data['completed'] and 'grand_compte:relay' not in passes and 'relay' not in data['inventory']: return 300
    if 'varenne' not in data['completed'] and 'varenne:vpn' not in passes: return 50
    return 0


def item_reason(data, item):
    ident = item['id']
    if ident.startswith('gpu') and any('gpu'+str(level) in data['inventory'] for level in range(int(ident[-1])+1, 4)):
        return 'Un GPU supérieur est déjà installé.'
    amount = price(data, item)
    if amount > data['money']: return 'Fonds insuffisants.'
    if amount and ident != 'relay' and data['money'] - amount < reserve(data):
        return f"Garde {reserve(data)} ₵ pour la route obligatoire du prochain dossier."
    return ''


def catalog(data, items):
    result = []
    for item in items:
        owned = item['id'] in data['inventory'] and not item.get('consumable')
        reason = 'Article déjà acquis.' if owned else ('Palier insuffisant.' if item['tier'] > data['tier'] else item_reason(data, item))
        description=DESCRIPTIONS[item['id']]
        from .curriculum import current
        if current(data) and item['id'] in {'wordlist','gpu1','gpu2','gpu3'}:
            description+=' Matériel prévu pour l’acte II ; aucun achat n’est nécessaire pour finir l’acte I.'
        result.append({**item, 'price': price(data, item), 'base_price': item['price'], 'description': description,
                       'owned': owned, 'unlocked': not reason, 'reason': reason, 'reserve': reserve(data)})
    return result
