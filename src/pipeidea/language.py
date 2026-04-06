"""Detect the dominant language of user seeds via Unicode script analysis."""

from __future__ import annotations

import unicodedata

# Unicode script ranges mapped to language names.
# We use the Unicode General Category + script lookup via unicodedata.
_SCRIPT_LANGUAGES: list[tuple[str, str, set[str]]] = [
    # (language_name, display_name, set of Unicode script names)
    ("Chinese", "Chinese", {"CJK"}),
    ("Japanese", "Japanese", {"HIRAGANA", "KATAKANA"}),
    ("Korean", "Korean", {"HANGUL"}),
    ("Russian", "Russian", {"CYRILLIC"}),
    ("Arabic", "Arabic", {"ARABIC"}),
    ("Thai", "Thai", {"THAI"}),
    ("Hindi", "Hindi", {"DEVANAGARI"}),
]


def _script_of(ch: str) -> str:
    """Return a simplified script category for a character."""
    name = unicodedata.name(ch, "")
    upper = name.upper()

    # CJK Unified Ideographs (shared by Chinese/Japanese/Korean)
    if "CJK" in upper:
        return "CJK"

    # Japanese-specific scripts
    if "HIRAGANA" in upper:
        return "HIRAGANA"
    if "KATAKANA" in upper:
        return "KATAKANA"

    # Korean
    if "HANGUL" in upper:
        return "HANGUL"

    # Cyrillic
    if "CYRILLIC" in upper:
        return "CYRILLIC"

    # Arabic
    if "ARABIC" in upper:
        return "ARABIC"

    # Thai
    if "THAI" in upper:
        return "THAI"

    # Devanagari
    if "DEVANAGARI" in upper:
        return "DEVANAGARI"

    return "OTHER"


def detect_seed_language(seeds: list[str]) -> str | None:
    """Detect the dominant non-English language from seed text.

    Returns a language name (e.g. "Chinese", "Japanese") if ≥30% of
    non-whitespace characters belong to a non-Latin script.
    Returns ``None`` for English / Latin-script input.
    """
    combined = " ".join(seeds).strip()
    if not combined:
        return None

    # Count characters by script
    script_counts: dict[str, int] = {}
    total_non_ws = 0

    for ch in combined:
        if ch.isspace():
            continue
        total_non_ws += 1
        script = _script_of(ch)
        script_counts[script] = script_counts.get(script, 0) + 1

    if total_non_ws == 0:
        return None

    # Check each language's scripts against the threshold
    threshold = 0.30

    # Special case: Japanese uses both CJK ideographs and Kana.
    # If any Kana is present, it's Japanese (CJK alone could be Chinese).
    kana_count = script_counts.get("HIRAGANA", 0) + script_counts.get("KATAKANA", 0)
    cjk_count = script_counts.get("CJK", 0)

    if kana_count > 0 and (kana_count + cjk_count) / total_non_ws >= threshold:
        return "Japanese"

    # Korean: Hangul characters present
    hangul_count = script_counts.get("HANGUL", 0)
    if hangul_count / total_non_ws >= threshold:
        return "Korean"

    # Chinese: CJK without Kana or Hangul
    if cjk_count / total_non_ws >= threshold and kana_count == 0 and hangul_count == 0:
        return "Chinese"

    # Other scripts
    for lang, _display, scripts in _SCRIPT_LANGUAGES:
        if lang in ("Chinese", "Japanese", "Korean"):
            continue  # Already handled above
        count = sum(script_counts.get(s, 0) for s in scripts)
        if count / total_non_ws >= threshold:
            return lang

    return None


def language_guidance(language: str) -> str:
    """Build the runtime guidance string for a detected language."""
    return (
        f"⚠️ LANGUAGE REQUIREMENT — NON-NEGOTIABLE ⚠️\n\n"
        f"The user wrote their prompt in {language}. "
        f"You MUST write your ENTIRE response in {language}. "
        f"Every word of output — title, mechanism, prose, trailing thread — "
        f"must be in {language}. Do NOT write in English. "
        f"Only universally recognized proper nouns (brand names, place names) "
        f"may remain in their original form. Everything else: {language}."
    )
