"""
Générateur de pseudo de hacker pour l'inscription en un clic sur BreachBoard
(docs/03-red-progression.md, tutoriel palier 0).

Le hasard passe par un random.Random fourni (state.rng ou un rng de profil) :
même graine, même pseudo. Les listes de mots sont génériques et ne reprennent
aucun nom de groupe ou de personne réels.
"""
from __future__ import annotations

import random

PREFIXES = [
    "null", "void", "grey", "static", "silent", "cold", "hollow", "zero",
    "rust", "ghost", "low", "dark", "pale", "lost", "quiet", "frost",
    "neon", "dusk", "blind", "iron", "n0x", "0x", "gl1tch", "cipher", "r00t", "hex",
]
SUFFIXES = [
    "byte", "wire", "signal", "shell", "echo", "vector", "loop", "cipher",
    "daemon", "packet", "trace", "stack", "socket", "fault", "proxy",
    "hex", "cache", "kernel", "offset", "null",
]

LEET = {"a": "4", "e": "3", "i": "1", "o": "0", "s": "5"}


def _leetify(word: str, rng: random.Random) -> str:
    """Remplace UNE lettre au hasard par son équivalent leet, s'il y en a."""
    positions = [i for i, c in enumerate(word) if c in LEET]
    if not positions:
        return word
    i = rng.choice(positions)
    return word[:i] + LEET[word[i]] + word[i + 1:]


def generate_handle(rng: random.Random) -> str:
    """Renvoie un pseudo du type « NullMoth », « gr3yfox_42 » ou « Static_Rook »."""
    prefix, suffix = rng.choice(PREFIXES), rng.choice(SUFFIXES)
    style = rng.randrange(4)
    if style == 0:
        return prefix.capitalize() + suffix.capitalize()
    if style == 1:
        return f"{_leetify(prefix, rng)}{suffix}_{rng.randrange(10, 100)}"
    if style == 2:
        return f"{prefix.capitalize()}_{suffix.capitalize()}"
    return f"{prefix}{_leetify(suffix, rng)}{rng.randrange(1, 10)}"


def generate_choices(rng: random.Random, count: int = 3) -> list[str]:
    """Plusieurs pseudos distincts, pour que le joueur puisse « relancer »."""
    choices: list[str] = []
    while len(choices) < count:
        handle = generate_handle(rng)
        if handle not in choices:
            choices.append(handle)
    return choices


def is_valid_handle(handle: str) -> bool:
    """3 à 24 caractères : lettres, chiffres, _ - . (pas d'espace ni de balise)."""
    return 3 <= len(handle) <= 24 and all(c.isalnum() or c in "_-." for c in handle)
