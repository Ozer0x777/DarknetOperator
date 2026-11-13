"""Droits de lecture explicites des fichiers d'un hôte du laboratoire."""

def readable(state,filename,user=None,host=None):
    host=host or state.hosts.get(state.terminal_host)
    if not host:return True
    user=user or state.terminal_user
    rules=state.environment.get('file_permissions',{}).get(host.id,{})
    for prefix,allowed in sorted(rules.items(),key=lambda p:len(p[0]),reverse=True):
        if filename==prefix or filename.startswith(prefix.rstrip('/')+'/'):
            return user in allowed or user=='root'
    return True
