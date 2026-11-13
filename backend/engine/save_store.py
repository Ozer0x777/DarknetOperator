"""Emplacements locaux versionnés, vérifiés et écrits atomiquement."""
from pathlib import Path
from datetime import datetime, timezone
import copy
import hashlib
import json
import os
import re
import uuid


def atomic_json(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    temp = path.with_suffix('.tmp')
    with temp.open('w', encoding='utf-8') as stream:
        json.dump(data, stream, ensure_ascii=False, indent=2)
        stream.flush(); os.fsync(stream.fileno())
    temp.replace(path)


def validate_profile(data):
    if not isinstance(data, dict) or data.get('version') != 1:
        raise ValueError('Version de sauvegarde incompatible.')
    if any(type(data.get(k)) is not int or data[k] < 0 for k in ('money','reputation','tier')):
        raise ValueError('Profil de sauvegarde invalide.')
    for key in ('inventory','completed','settled'):
        if not isinstance(data.get(key), list): raise ValueError('Inventaire ou progression invalide.')
    if 'campaign_version' in data and (type(data['campaign_version']) is not int or data['campaign_version']<1):
        raise ValueError('Version de progression invalide.')
    if data.get('play_mode', 'campaign') not in {'campaign', 'demo'}:
        raise ValueError('Parcours de sauvegarde invalide.')
    if 'classic_progression' in data and not isinstance(data['classic_progression'],bool):
        raise ValueError('Choix de progression invalide.')
    if 'legacy_completed' in data and (not isinstance(data['legacy_completed'],list) or any(not isinstance(cid,str) for cid in data['legacy_completed'])):
        raise ValueError('Historique de progression invalide.')
    if 'act2_started' in data and not isinstance(data['act2_started'],bool):
        raise ValueError('Progression de l’acte II invalide.')
    if 'trust_offer' in data and data['trust_offer'] not in {'', 'act1_echantillon', 'act1_boutique', 'act1_recommandation'}:
        raise ValueError('Proposition de confiance invalide.')
    if 'forum_reputation' in data:
        scores = data['forum_reputation']
        if not isinstance(scores, dict) or set(scores) != {'breachboard', 'exployt', 'xsx'} or any(type(value) is not int or value < 0 for value in scores.values()):
            raise ValueError('Réputation des communautés invalide.')
    if 'route_passes' in data:
        passes = data['route_passes']
        if not isinstance(passes, list) or any(not isinstance(item, str) or not re.fullmatch(r'[a-z0-9_]+:(vpn|relay)', item) for item in passes) or len(passes) != len(set(passes)):
            raise ValueError('Passages de route invalides.')
    if 'career_events' in data:
        events = data['career_events']
        if not isinstance(events, list): raise ValueError('Historique de carrière invalide.')
        seen = set()
        for event in events:
            if not isinstance(event, dict) or not isinstance(event.get('id'), str) or event['id'] in seen or not isinstance(event.get('contract'), str) or event.get('outcome') not in {'SUCCESS','FAILED'} or type(event.get('payout')) is not int or event['payout'] < 0 or type(event.get('minute')) is not int:
                raise ValueError('Événement de carrière invalide.')
            seen.add(event['id'])
    if 'wallet' in data:
        wallet = data['wallet']
        if not isinstance(wallet, dict) or wallet.get('version') != 1 or not isinstance(wallet.get('device_id'), str) or not isinstance(wallet.get('entries'), list):
            raise ValueError('Portefeuille invalide.')
        identifiers = set()
        for entry in wallet['entries']:
            if not isinstance(entry, dict) or not isinstance(entry.get('id'), str) or entry['id'] in identifiers or type(entry.get('amount')) is not int or type(entry.get('balance')) is not int or entry['balance'] < 0:
                raise ValueError('Historique du portefeuille invalide.')
            identifiers.add(entry['id'])
    if data.get('active'):
        from .persistence import state_from_dict
        try: state_from_dict(copy.deepcopy(data['active']))
        except Exception as exc: raise ValueError('Mission sauvegardée invalide.') from exc
    return data


class SaveStore:
    def __init__(self, career_path): self.folder = Path(career_path).parent/'slots'

    def path(self, ident):
        if not re.fullmatch(r'(manual-[a-f0-9]{32}|auto-[0-2]|recovery)', ident):
            raise ValueError('Emplacement invalide.')
        return self.folder/(ident+'.json')

    def read(self, ident):
        try: envelope = json.loads(self.path(ident).read_text(encoding='utf-8'))
        except (OSError, ValueError) as exc: raise ValueError('Sauvegarde absente ou illisible.') from exc
        if not isinstance(envelope,dict) or envelope.get('format') != 1:
            raise ValueError('Format de sauvegarde incompatible.')
        data = envelope.get('profile')
        digest = self.checksum(data)
        if digest != envelope.get('checksum'): raise ValueError('Sauvegarde endommagée : vérification impossible.')
        validate_profile(data)
        return envelope

    def write(self, data, name, ident=None, overwrite=False, kind='manual'):
        validate_profile(data)
        ident = ident or 'manual-'+uuid.uuid4().hex
        path = self.path(ident)
        if path.exists() and not overwrite: raise ValueError('Confirme l’écrasement de cet emplacement.')
        active = data.get('active') or {}
        meta = {'id':ident,'name':name.strip()[:80] or 'Sauvegarde','kind':kind,
                'date':datetime.now(timezone.utc).isoformat(), 'handle':data.get('handle',''),
                'mission':active.get('scenario_name','Bureau'), 'tick':active.get('tick',0),
                'play_seconds':data.get('play_seconds',0), 'money':data['money'], 'tier':data['tier']}
        payload = copy.deepcopy(data)
        envelope = {'format':1,'metadata':meta,'profile':payload,
                    'checksum':self.checksum(payload)}
        atomic_json(path,envelope)
        return meta

    @staticmethod
    def checksum(data):
        return hashlib.sha256(json.dumps(data,sort_keys=True,ensure_ascii=False).encode()).hexdigest()

    def _stored_checksum(self, path):
        try: return json.loads(path.read_text(encoding='utf-8')).get('checksum')
        except (OSError, ValueError, AttributeError): return None

    def has_identical(self, data):
        """Vrai si un emplacement contient déjà exactement cette carrière."""
        if not self.folder.exists(): return False
        digest = self.checksum(data)
        return any(self._stored_checksum(path) == digest for path in self.folder.glob('*.json'))

    def autosave(self, data, force=False):
        paths = [self.path('auto-'+str(i)) for i in range(3)]
        import time
        existing = [p for p in paths if p.exists()]
        newest = max(existing,key=lambda p:p.stat().st_mtime,default=None)
        if not force and newest is not None and time.time()-newest.stat().st_mtime < 60: return
        # Les trois emplacements tournants doivent rester trois états différents :
        # un état déjà présent dans le plus récent n'en écrase pas un plus ancien.
        if newest is not None and self._stored_checksum(newest) == self.checksum(data): return
        path = min(paths,key=lambda p:p.stat().st_mtime if p.exists() else 0)
        self.write(data,'Autosauvegarde',path.stem,True,'auto')

    def list(self):
        result=[]
        if not self.folder.exists(): return result
        for path in self.folder.glob('*.json'):
            try: result.append({**self.read(path.stem)['metadata'],'valid':True})
            except ValueError as exc:
                result.append({'id':path.stem,'name':path.stem,'valid':False,'error':str(exc),'date':''})
        return sorted(result,key=lambda row:row['date'],reverse=True)
