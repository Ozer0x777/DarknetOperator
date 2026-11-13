"""Vérifie les identités fictives du scénario, indépendamment du butin connu."""
from .models import Credential
from .ntlm import nt_hash


def authenticate(state, host, username, secret, kind='PLAINTEXT'):
    if not host or host.id not in state.discovered or host.status in {'ISOLATED','ENCRYPTED'}: return None
    if kind=='NTLM_HASH': secret=state.tool_data.get('legacy_hash_aliases',{}).get(secret.lower(),secret)
    account = next((u for u in state.users.values() if u.username.casefold()==username.casefold()),None)
    if not account or account.status!='ACTIVE': return None
    known = next((c for c in reversed(state.loot) if c.username==account.username and c.type==kind and c.valid and (c.value.casefold()==secret.casefold() if kind=='NTLM_HASH' else c.value==secret)),None)
    if account.password is not None:
        expected = nt_hash(account.password) if kind=='NTLM_HASH' else account.password
        if (expected.casefold()!=secret.casefold() if kind=='NTLM_HASH' else expected!=secret): return None
    elif known is None:
        return None  # Une ancienne sauvegarde ne contient pas de secret de référence.
    if known: return known
    credential=Credential(kind,account.username,nt_hash(account.password) if kind=='NTLM_HASH' else secret,host.id)
    state.loot.append(credential)
    return credential


def current(state, credential):
    if credential is None or not credential.valid: return False
    account=state.users.get(credential.username)
    if account is None: return credential.type=='KRBTGT_HASH'
    if account.status!='ACTIVE': return False
    if account.password is None:return True
    if credential.type=='PLAINTEXT':return credential.value==account.password
    if credential.type=='NTLM_HASH':return credential.value.casefold()==nt_hash(account.password)
    return True
