"""Generate random stimuli for the Randomness pillar.

This is code, not content — it fetches random things from the world
to inject into the creative process.
"""

import random
import urllib.request
import json

# Fallback word list for when network is unavailable
_FALLBACK_WORDS = [
    "crystalline", "fermentation", "cartography", "mycelium", "resonance",
    "obsidian", "tidal", "origami", "phosphorescence", "migration",
    "archaeology", "synapse", "metamorphosis", "pendulum", "coral",
    "labyrinth", "combustion", "silk", "erosion", "constellation",
    "alchemy", "osmosis", "driftwood", "vortex", "patina",
    "tessellation", "murmuration", "bioluminescence", "stalactite", "aurora",
    "undertow", "pollination", "calcification", "whisper", "fracture",
    "petrification", "iridescence", "sedimentation", "echo", "membrane",
]

_FALLBACK_FACTS = [
    "Octopuses have three hearts and blue blood.",
    "The shortest war in history lasted 38 minutes (Anglo-Zanzibar War, 1896).",
    "Honey never spoils — edible honey has been found in 3000-year-old Egyptian tombs.",
    "There are more possible chess games than atoms in the observable universe.",
    "Tardigrades can survive in the vacuum of space.",
    "The inventor of the Pringles can is buried in one.",
    "Trees in a forest communicate through underground fungal networks called the Wood Wide Web.",
    "A group of flamingos is called a 'flamboyance'.",
    "The Japanese word 'komorebi' means sunlight filtering through leaves — untranslatable in English.",
    "Sharks are older than trees. Sharks have existed for ~400 million years, trees for ~350 million.",
    "The human body contains enough carbon to make 900 pencils.",
    "Venice was built on a foundation of petrified tree trunks from Slovenian forests.",
    "Slime molds can solve mazes and replicate efficient transit networks.",
    "The Great Wall of China was held together with sticky rice mortar.",
    "Crows can recognize human faces and hold grudges for years.",
]


def get_random_stimulus() -> str:
    """Get a random stimulus to inject into the creative process.

    Tries to fetch a random Wikipedia article title. Falls back to
    local word/fact lists if network is unavailable.
    """
    strategies = [
        _random_wikipedia_title,
        _random_word,
        _random_fact,
    ]

    # Pick a strategy, weighted toward Wikipedia (network-dependent)
    strategy = random.choices(strategies, weights=[3, 2, 2], k=1)[0]

    try:
        return strategy()
    except Exception:
        # If the chosen strategy fails, fall back
        return _random_word()


def _random_wikipedia_title() -> str:
    """Fetch a random Wikipedia article title."""
    url = "https://en.wikipedia.org/api/rest_v1/page/random/summary"
    req = urllib.request.Request(url, headers={"User-Agent": "pipeidea/0.1"})
    with urllib.request.urlopen(req, timeout=5) as resp:
        data = json.loads(resp.read())
        title = data.get("title", "")
        extract = data.get("extract", "")
        # Return title + first sentence for richer stimulus
        first_sentence = extract.split(".")[0] + "." if extract else ""
        return f"{title}: {first_sentence}".strip()


def _random_word() -> str:
    """Pick a random evocative word."""
    word = random.choice(_FALLBACK_WORDS)
    return f"Random word: {word}"


def _random_fact() -> str:
    """Pick a random surprising fact."""
    return f"Random fact: {random.choice(_FALLBACK_FACTS)}"
