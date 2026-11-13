"""Ce qui suit l'opérateur d'un contrat au suivant, et ce qui appartient à une seule mission.

Le poste Kali est conservé : fichiers locaux, consoles et leur texte, services
(GoPhish) et potfile de hashcat. Tout le reste de `tool_data` décrit la mission
précédente (preuves d'objectifs, scans, défense de la cible, arborescences des
machines distantes) et n'est pas repris. La règle est une liste de ce qui est
conservé : une nouvelle donnée d'outil est propre à la mission par défaut.
"""
from copy import deepcopy

from . import console_sessions

# Données d'outils attachées au poste de l'opérateur, pas à un réseau cible.
PERSISTENT_TOOL_DATA = (
    "provisioned_tools", "provisioned_config_files",  # marqueurs des fichiers déjà installés sur Kali
    "gophish", "campaign_contracts",                  # serveur GoPhish local et campagnes rattachées à leur contrat
    "next_pid",                                       # numérotation des processus locaux
    "terminal_transcripts",                           # texte affiché dans les consoles
    "hashcat",                                        # potfile : conservé, voir docs/COMMANDES.md
    "sqlite",                                         # bases créées par le joueur dans ses fichiers locaux
    "bloodhound",                                     # collecte importée, marquée périmée hors de son contrat
)


def inherit(state, source: dict | None, contract: dict | None = None) -> None:
    """Prépare l'état d'un nouveau contrat à partir de la mission ou du bureau précédent."""
    if source:
        files = deepcopy(source.get("terminal_files", {}))
        files.update(state.terminal_files)  # les fichiers du nouveau contrat priment
        state.terminal_files = files
        state.tool_services = deepcopy(source.get("tool_services", {}))
        state.terminals = deepcopy(source.get("terminals", {}))
        previous = source.get("tool_data", {})
        state.tool_data = {key: deepcopy(previous[key]) for key in PERSISTENT_TOOL_DATA if key in previous}
        # Seule l'arborescence du poste local survit : les autres clés sont des machines de l'ancien réseau.
        local_dirs = previous.get("vfs_dirs", {}).get("operator")
        if local_dirs is not None: state.tool_data["vfs_dirs"] = {"operator": deepcopy(local_dirs)}
        for context in state.terminals.values():
            # Toute session distante appartenait à l'ancien réseau : retour au shell local.
            if context.get("terminal_host"):
                context["terminal_env"] = console_sessions.initial()["terminal_env"]
            context["terminal_shell"] = "bash"
            context["terminal_return_stack"] = []
            context["terminal_host"], context["terminal_user"], context["terminal_auth"] = None, "operator", {}
            context["terminal_access"] = "USER"
            context["terminal_cwd"] = "/home/operator"
    for service in state.tool_services.values():
        if service.get("kind") == "ssh-forward": service["running"] = False
    for context in state.terminals.values():
        pid = context.get("terminal_foreground")
        if any(s.get("kind") == "ssh-forward" and s.get("pid") == pid for s in state.tool_services.values()):
            context["terminal_foreground"] = None
    # Hashes obtenus pendant CETTE mission : le potfile conservé ne valide pas seul un objectif.
    state.tool_data["hashcat_session"] = []
    if contract and contract.get("investigation_steps"):
        # Un dossier d'enquête démarre avec ses registres d'observations, vides.
        state.tool_data.update(investigation={"steps": [], "threads": []}, read_http=[], read_files=[], facts={}, queries=[], decisions={})


def note_cracked(state, hashes) -> None:
    """Enregistre les hashes cassés ou relus (--show) pendant la mission en cours."""
    session = state.tool_data.setdefault("hashcat_session", [])
    for value in hashes:
        value = str(value).lower() if not str(value).startswith("$") else str(value)
        if value not in session: session.append(value)


def cracked_in_mission(state, value: str) -> bool:
    """Vrai si le hash a été obtenu pendant cette mission. Une ancienne sauvegarde
    sans suivi par mission se rabat sur le potfile seul."""
    session = state.tool_data.get("hashcat_session")
    return True if session is None else value in session
