"""Compose the system prompt from profile markdown files.

This is the bridge between the soul (markdown) and the AI provider (API call).
It reads, resolves inheritance, and stitches — but adds no creative content of its own.
"""

from dataclasses import dataclass
from pathlib import Path

from pipeidea.config import Config
from pipeidea.soul.profiles import ensure_defaults, load_profile_snapshot


@dataclass(frozen=True)
class PromptSection:
    """A resolved section of the composed prompt."""

    key: str
    title: str
    content: str
    kind: str
    source_profile: str | None = None
    source_path: str | None = None


@dataclass(frozen=True)
class PromptComposition:
    """Structured prompt composition plus the final system prompt."""

    profile: str
    active_profile_dir: str
    default_profile_dir: str | None
    sections: list[PromptSection]
    system_prompt: str


def _add_soul_section(
    sections: list[PromptSection],
    snapshot,
    key: str,
    title: str,
) -> None:
    entry = snapshot.files.get(key)
    if entry is None:
        return

    sections.append(
        PromptSection(
            key=key,
            title=title,
            content=entry.content,
            kind="soul",
            source_profile=entry.source_profile,
            source_path=str(entry.source_path),
        )
    )


def compose_prompt(
    cfg: Config,
    profile: str,
    mode: str,
    random_stimulus: str | None = None,
    garden_echoes: list[str] | None = None,
    web_stimuli: list[str] | None = None,
    active_profile_dir: Path | None = None,
    default_profile_dir: Path | None = None,
) -> PromptComposition:
    """Assemble the full system prompt for an AI call.

    Args:
        cfg: Application config.
        profile: Profile name to use.
        mode: Interaction mode (bloom, collision, forage, revisit).
        random_stimulus: A random stimulus string to inject (optional).
        garden_echoes: Past ideas from the garden (optional).
        web_stimuli: Web content for foraging (optional).

    Returns:
        The complete system prompt as a string.
    """
    if active_profile_dir is None and default_profile_dir is None:
        ensure_defaults(cfg)

    snapshot = load_profile_snapshot(
        cfg=cfg,
        profile=profile,
        active_profile_dir=active_profile_dir,
        default_profile_dir=default_profile_dir,
    )

    sections: list[PromptSection] = []

    # Core identity — who you are
    _add_soul_section(sections, snapshot, "identity.md", "Identity")

    # Taste — the most important file
    _add_soul_section(sections, snapshot, "taste.md", "Taste")

    # Ambition
    _add_soul_section(sections, snapshot, "ambition.md", "Ambition")

    # Knowledge — how to traverse domains
    _add_soul_section(sections, snapshot, "knowledge.md", "Knowledge")

    # Randomness — permission to be chaotic
    _add_soul_section(sections, snapshot, "randomness.md", "Randomness")

    # Techniques — internalized creative methods
    _add_soul_section(sections, snapshot, "techniques.md", "Techniques")

    # Thinking protocol
    _add_soul_section(sections, snapshot, "protocol.md", "Protocol")

    # Multi-turn dialogue behavior
    _add_soul_section(sections, snapshot, "dialogue.md", "Dialogue")

    # Output format
    _add_soul_section(sections, snapshot, "output.md", "Output")

    # Mode-specific instructions
    mode_key = f"modes/{mode}.md"
    _add_soul_section(sections, snapshot, mode_key, f"Mode: {mode}")

    # Runtime context injections
    if random_stimulus:
        sections.append(
            PromptSection(
                key="runtime/random_stimulus",
                title="Random Stimulus",
                kind="runtime",
                content=(
                    f"# Random Stimulus\n\n"
                    f"A random element has been injected into your creative space. "
                    f"You didn't ask for it. It has no obvious connection to anything. "
                    f"Use it, ignore it, or let it derail you — your call.\n\n"
                    f"**Random stimulus:** {random_stimulus}"
                ),
            )
        )

    if garden_echoes:
        echoes_text = "\n\n---\n\n".join(garden_echoes)
        sections.append(
            PromptSection(
                key="runtime/garden_echoes",
                title="Garden Echoes",
                kind="runtime",
                content=(
                    f"# Garden Echoes\n\n"
                    f"These are past ideas from your garden that may relate to the current seed. "
                    f"Apply your taste gate: only engage with ones that still feel alive. "
                    f"Use them for cross-pollination, not repetition.\n\n{echoes_text}"
                ),
            )
        )

    if web_stimuli:
        stimuli_text = "\n\n---\n\n".join(web_stimuli)
        sections.append(
            PromptSection(
                key="runtime/web_stimuli",
                title="Web Stimuli",
                kind="runtime",
                content=(
                    f"# Web Stimuli\n\n"
                    f"These are raw materials foraged from the web. Most of it is probably noise. "
                    f"Apply your taste gate ruthlessly — discard anything generic. "
                    f"Keep only what surprises you. Collide the survivors with the seed.\n\n"
                    f"{stimuli_text}"
                ),
            )
        )

    system_prompt = "\n\n---\n\n".join(section.content for section in sections)
    return PromptComposition(
        profile=profile,
        active_profile_dir=str(snapshot.active_profile_dir),
        default_profile_dir=(
            str(snapshot.default_profile_dir) if snapshot.default_profile_dir is not None else None
        ),
        sections=sections,
        system_prompt=system_prompt,
    )


def compose_system_prompt(
    cfg: Config,
    profile: str,
    mode: str,
    random_stimulus: str | None = None,
    garden_echoes: list[str] | None = None,
    web_stimuli: list[str] | None = None,
    active_profile_dir: Path | None = None,
    default_profile_dir: Path | None = None,
) -> str:
    """Backwards-compatible helper returning only the prompt string."""
    composition = compose_prompt(
        cfg=cfg,
        profile=profile,
        mode=mode,
        random_stimulus=random_stimulus,
        garden_echoes=garden_echoes,
        web_stimuli=web_stimuli,
        active_profile_dir=active_profile_dir,
        default_profile_dir=default_profile_dir,
    )
    return composition.system_prompt


def compose_user_message(seeds: list[str], mode: str) -> str:
    """Build the user message for the AI call.

    Args:
        seeds: One or more seed strings from the user.
        mode: Interaction mode.

    Returns:
        The user message.
    """
    if mode == "collision":
        seed_parts = [f"**Input {i + 1}:** {s}" for i, s in enumerate(seeds)]
        return "Collide these:\n\n" + "\n\n".join(seed_parts)
    elif mode == "forage":
        if seeds:
            return f"Forage around this topic and bring back collisions: {seeds[0]}"
        return "Forage freely. Find something interesting in the world and build ideas from it."
    else:
        # bloom (default)
        return f"Seed: {seeds[0]}"
