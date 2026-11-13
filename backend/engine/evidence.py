"""Lectures associées au contenu observé, pas seulement à un nom de fichier."""
import hashlib


def digest(content):
    return hashlib.sha256(content.encode()).hexdigest()


def read(state, path, host=None):
    host = host or state.terminal_host or 'operator'
    files = state.terminal_files if host == 'operator' else state.hosts[host].files
    if path not in files: return
    key = host+':'+path
    seen = state.tool_data.setdefault('read_files', [])
    if key not in seen: seen.append(key)
    state.tool_data.setdefault('file_read_versions', {})[key] = digest(files[path])


def invalidate(state, path, host=None):
    key = (host or state.terminal_host or 'operator')+':'+path
    state.tool_data['read_files'] = [item for item in state.tool_data.get('read_files', []) if item != key]
    state.tool_data.get('file_read_versions', {}).pop(key, None)


def inspected(state, path, host='operator'):
    files = state.terminal_files if host == 'operator' else state.hosts[host].files
    key = host+':'+path
    if path not in files or key not in state.tool_data.get('read_files', []): return False
    version = state.tool_data.get('file_read_versions', {}).get(key)
    # Les anciennes parties ne contiennent pas d'empreinte ; une nouvelle écriture invalide leur marque.
    return version is None or version == digest(files[path])
