"""Heuristics for detecting prompts that need a more grounded register."""

from __future__ import annotations

import re
from dataclasses import dataclass


_SENSITIVE_PATTERNS = (
    r"\bgaza\b",
    r"\bisrael\b",
    r"\bpalestin(?:e|ian|ians)\b",
    r"\bhamas\b",
    r"\bceasefire\b",
    r"\bwar\b",
    r"\bconflict\b",
    r"\bgenocide\b",
    r"\bethnic cleansing\b",
    r"\bterror(?:ism|ist|ists)?\b",
    r"\bhostage(?:s)?\b",
    r"\brefugee(?:s)?\b",
    r"\bdisplacement\b",
    r"\bfamine\b",
    r"\bhumanitarian\b",
    r"\batrocit(?:y|ies)\b",
    r"\babuse\b",
    r"\bsuicid(?:e|al)\b",
    r"\bself-harm\b",
    r"\boverdose\b",
    r"\bepidemic\b",
    r"\bpandemic\b",
    r"\boutbreak\b",
    r"\bmassacre\b",
    r"\bshooting\b",
)

_SENSITIVE_RE = re.compile("|".join(_SENSITIVE_PATTERNS), re.IGNORECASE)


@dataclass(frozen=True)
class SensitivityAssessment:
    """Structured result for prompt sensitivity checks."""

    is_sensitive: bool
    reason: str | None = None


def assess_prompt_sensitivity(seeds: list[str], mode: str) -> SensitivityAssessment:
    """Return whether a prompt likely needs grounded, high-stakes handling."""
    haystack = " ".join(seeds).strip()
    if not haystack:
        return SensitivityAssessment(is_sensitive=False)

    match = _SENSITIVE_RE.search(haystack)
    if not match:
        return SensitivityAssessment(is_sensitive=False)

    trigger = match.group(0).strip().lower()
    reason = (
        f"The user's prompt includes a live high-stakes topic ({trigger}). "
        f"Respond with humane, concrete, non-decorative language."
    )
    if mode == "collision":
        reason += " Keep the collision tightly anchored and avoid playful metaphor."
    else:
        reason += " Prefer direct mechanisms and grounded framing over bloom-style abstraction."
    return SensitivityAssessment(is_sensitive=True, reason=reason)
