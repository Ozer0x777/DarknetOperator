"""Portefeuille matériel fictif : fonds hors forums, journal et session d'appareil."""
import copy
import uuid


def ensure(data):
    if 'wallet' not in data:
        data['wallet'] = {'version': 1, 'device_id': 'CV-' + uuid.uuid4().hex[:8].upper(), 'entries': [
            {'id': 'opening', 'kind': 'opening', 'amount': data['money'], 'balance': data['money'], 'label': 'Solde initial ou repris', 'source': 'migration'}]}
    return data['wallet']


def record(data, ident, kind, amount, label, source):
    wallet = ensure(data)
    if any(entry['id'] == ident for entry in wallet['entries']): return
    wallet['entries'].append({'id': ident, 'kind': kind, 'amount': amount, 'balance': data['money'], 'label': label, 'source': source})


def view(career):
    wallet = ensure(career.data)
    session = career.wallet_session()
    return {'name': 'ColdVault', 'simulated': True, 'device_id': wallet['device_id'], 'balance': career.data['money'], 'currency': '₵',
            'connected': session['connected'], 'unlocked': session['unlocked'], 'pending': copy.deepcopy(session['pending']),
            'entries': copy.deepcopy(wallet['entries'][-100:])}
