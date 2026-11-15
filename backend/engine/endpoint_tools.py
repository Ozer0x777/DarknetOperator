"""État Defender des seules machines fictives ; aucun appel au système hôte."""
from .data_tools import fact
from .models import LogEvent


def event(state, host, ident, text):
    state.tool_data.setdefault('endpoint_events', []).append(dict(host=host, id=ident, text=text, tick=state.tick))
    state.logs.append(LogEvent(str(ident), host, state.tick, {'message': text}))


def parse(command, args, state):
    from .terminal import TerminalResult
    names = {'get-mpcomputerstatus', 'get-mppreference', 'set-mppreference', 'get-winevent'}
    if command not in names:
        return None
    host = state.terminal_host
    spec = state.environment.get('defender_profiles', {}).get(host)
    if not spec:
        return TerminalResult(False, ['Defender : module absent de cette image du laboratoire.'])
    if command == 'get-winevent':
        if [a.casefold() for a in args] != ['-logname', 'microsoft-windows-windows defender/operational']:
            return TerminalResult(False, ['Get-WinEvent -LogName "Microsoft-Windows-Windows Defender/Operational"'])
        fact(state, 'defender:events:' + host)
        return TerminalResult(True, [f"{e['id']} {e['text']}" for e in state.tool_data.get('endpoint_events', []) if e['host'] == host] or ['Aucun événement dans ce journal.'])
    if command.startswith('get-'):
        if args:
            return TerminalResult(False, ['Ce relevé couvre la commande sans filtre.'])
        fact(state, 'defender:' + command + ':' + host, realtime=spec.get('realtime', True), tamper=spec.get('tamper', True), events=sum(e['host'] == host for e in state.tool_data.get('endpoint_events', [])))
        if command == 'get-mpcomputerstatus':
            fields = dict(AMProductVersion=spec['version'], AntivirusEnabled=True,
                          RealTimeProtectionEnabled=spec.get('realtime', True), IsTamperProtected=spec.get('tamper', True))
        else:
            fields = dict(DisableRealtimeMonitoring=not spec.get('realtime', True), ExclusionPath=spec.get('exclusions', []))
        return TerminalResult(True, [f'{key} : {value}' for key, value in fields.items()])
    if len(args) != 2 or args[0].casefold() != '-disablerealtimemonitoring' or args[1].casefold() not in {'$true', '$false'}:
        return TerminalResult(False, ['Sous-ensemble : Set-MpPreference -DisableRealtimeMonitoring $true|$false'])
    if state.terminal_access not in {'ADMIN', 'SYSTEM'}:
        event(state, host, 5007, 'Modification refusée : droits insuffisants.')
        return TerminalResult(False, ['Set-MpPreference : Access is denied.'])
    if spec.get('tamper', True):
        fact(state, 'defender:tamper-blocked:' + host)
        event(state, host, 5013, 'Tamper protection blocked a change to Microsoft Defender Antivirus.')
        return TerminalResult(False, ['Set-MpPreference : modification bloquée par la protection contre les falsifications.'])
    spec['realtime'] = args[1].casefold() == '$false'
    fact(state, 'defender:changed:' + host)
    event(state, host, 5007, 'Configuration modifiée sur cette image de contrôle uniquement.')
    return TerminalResult(True)


def artifact_blocked(state, tool):
    host = state.terminal_host
    spec = state.environment.get('defender_profiles', {}).get(host, {})
    if tool not in spec.get('blocked_artifacts', []) or not spec.get('realtime', True):
        return False
    fact(state, 'defender:artifact-blocked:' + host)
    event(state, host, 1116, 'Artefact virtuel détecté : ' + tool + ' ; exécution refusée, aucune collecte créée.')
    return True


def observe_scan(state, target, ports):
    origin = state.network_origin()
    for rule in state.environment.get('scan_responses', []):
        if rule['source'] != origin or rule['target'] != target or rule['port'] not in ports:
            continue
        key = 'defender:isolated:' + origin
        if key in state.tool_data.get('facts', {}):
            continue
        state.hosts[origin].status = 'ISOLATED'
        fact(state, key, target=target)
        event(state, origin, 'EDR-ISOLATION', 'Relais isolé après la sonde du segment administration ; les routes ne sont pas supprimées.')
