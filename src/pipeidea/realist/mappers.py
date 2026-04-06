"""Mapping from evaluator findings to profile tuning targets."""

FAILURE_FILE_MAP: dict[str, list[str]] = {
    "pipeline_bug": ["python-plumbing"],
    "wrong_profile": ["identity.md", "dialogue.md"],
    "wrong_mode": ["mode-specific"],
    "format_drift": ["output.md"],
    "template_output": ["output.md", "protocol.md"],
    "voice_drift": ["identity.md", "dialogue.md"],
    "too_incremental": ["ambition.md", "protocol.md"],
    "surface_analogy": ["knowledge.md", "protocol.md", "taste.md"],
    "mechanism_missing": ["taste.md", "techniques.md", "output.md"],
    "generic_futurism": ["taste.md", "ambition.md"],
    "not_vivid": ["output.md", "identity.md"],
    "too_many_ideas": ["output.md", "taste.md"],
    "favorite_is_weak": ["output.md", "taste.md"],
    "favorite_undercommitted": ["output.md", "taste.md"],
    "thread_missing": ["output.md", "dialogue.md"],
    "ending_lacks_pull": ["output.md", "dialogue.md"],
    "drifts_off_topic": ["knowledge.md", "protocol.md", "taste.md"],
    "randomness_overwhelmed": ["randomness.md", "protocol.md"],
    "randomness_absent": ["randomness.md", "protocol.md"],
    "collision_not_load_bearing": ["modes/collision.md", "techniques.md"],
    "forage_missing_stimuli": ["modes/forage.md", "python-plumbing"],
    "revisit_missing_echoes": ["modes/revisit.md", "python-plumbing"],
}

FAILURE_DIRECTION_MAP: dict[str, list[str]] = {
    "pipeline_bug": ["Fix the runtime before tuning markdown."],
    "wrong_profile": [
        "Check which profile directory was loaded and whether fallback files dominated the run."
    ],
    "wrong_mode": [
        "Tighten the mode instructions so the output visibly behaves like the requested mode."
    ],
    "format_drift": [
        "Reassert the output contract and trim any extra explanation or list-like scaffolding."
    ],
    "template_output": [
        "Collapse repeated titled cards into one prose-led artifact and cut reflex labels."
    ],
    "voice_drift": [
        "Restore conviction, energy, and anti-hedging language without flattening the tone."
    ],
    "too_incremental": [
        "Raise the anti-feature language and push the output toward world-shaping replacements."
    ],
    "surface_analogy": [
        "Ask for deeper structural bridges instead of shared words or decorative mashups."
    ],
    "mechanism_missing": [
        "Force every surviving idea to explain who does what and what changes first in plain language."
    ],
    "generic_futurism": [
        "Sharpen the ban on buzzword wrappers and force a vivid mechanism in the world."
    ],
    "not_vivid": [
        "Push descriptions toward concrete scenes, interactions, and visible consequences."
    ],
    "too_many_ideas": [
        "Reinforce fewer-better behavior and kill filler before the user sees it."
    ],
    "favorite_is_weak": [
        "Make the profile choose a stronger favorite instead of distributing conviction evenly."
    ],
    "favorite_undercommitted": [
        "Make the favorite unmistakable and let the strongest idea carry more of the answer."
    ],
    "thread_missing": [
        "End on a live question or opening instead of closing the loop too neatly."
    ],
    "ending_lacks_pull": [
        "Replace the closing summary with a final sentence that creates forward pull."
    ],
    "drifts_off_topic": [
        "Constrain the search radius and force the idea to stay legibly attached to the user's actual prompt."
    ],
    "randomness_overwhelmed": [
        "Let randomness disrupt the path without destroying coherence or profile identity."
    ],
    "randomness_absent": [
        "Give random stimuli more permission to bend the output when it improves surprise."
    ],
    "collision_not_load_bearing": [
        "Force both inputs to become necessary load-bearing parts of the idea."
    ],
    "forage_missing_stimuli": [
        "Wire real web stimuli into the run or skip forage scoring until the plumbing exists."
    ],
    "revisit_missing_echoes": [
        "Wire garden echoes into the run or skip revisit scoring until the plumbing exists."
    ],
}

HIGH_RISK_FILES = {"identity.md", "taste.md"}


def map_failure_tags(
    failure_tags: list[str],
    mode: str,
) -> tuple[list[str], list[str], list[str]]:
    """Map failure tags to likely files, edit directions, and high-risk files."""
    files: list[str] = []
    directions: list[str] = []
    high_risk: list[str] = []

    for tag in failure_tags:
        mapped_files = FAILURE_FILE_MAP.get(tag, [])
        expanded_files = [
            f"modes/{mode}.md" if item == "mode-specific" else item for item in mapped_files
        ]
        for item in expanded_files:
            if item not in files:
                files.append(item)
            if item in HIGH_RISK_FILES and item not in high_risk:
                high_risk.append(item)

        for item in FAILURE_DIRECTION_MAP.get(tag, []):
            if item not in directions:
                directions.append(item)

    return files, directions, high_risk
