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
    runtime_guidance: str | None = None,
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
        runtime_guidance: Extra runtime instruction for the current prompt (optional).

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
                    f"Use it, contain it, or discard it. It may bend the path, but it should not replace the seed.\n\n"
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

    if runtime_guidance:
        sections.append(
            PromptSection(
                key="runtime/guidance",
                title="Runtime Guidance",
                kind="runtime",
                content=(
                    "# Runtime Guidance\n\n"
                    "Honor this situational instruction for the current prompt.\n\n"
                    f"{runtime_guidance}"
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


_DIVERGE_PREAMBLE = """\
You are an idea mechanism generator. Your job is to produce three distinct, \
concrete mechanism sketches for a creative prompt. Do not write prose, titles, \
or metaphors. Write in plain operational language: who does what, by what rule \
or material or incentive, and what changes first.

Each candidate must:
- Describe a specific mechanism, not a mood or metaphor
- Stay visibly connected to the user's seed
- Be ambitious (level 7-10: the kind of idea that makes people nervous)
- Pass this test: if you remove all analogy and figurative language, is there \
still an operational mechanism left?

Kill on sight:
- Surface analogy ("X is like Y" without shared deep structure)
- Generic futurism ("AI-powered X", "blockchain-based Y")
- Wrapper ambition (calling something a platform/ecosystem/protocol without \
changing the underlying mechanism)
- Incremental improvement (a better version of an existing thing)

Output exactly this format, nothing else:

CANDIDATE 1:
Mechanism: [2-3 sentences. What happens? Who does what, by what rule/material/\
incentive/interface? What changes first?]
Seed connection: [1 sentence. How does this directly answer the user's prompt?]
Ambition: [1 sentence. What does the world look like if this wins?]

CANDIDATE 2:
Mechanism: [...]
Seed connection: [...]
Ambition: [...]

CANDIDATE 3:
Mechanism: [...]
Seed connection: [...]
Ambition: [...]
"""

_SELECT_PREAMBLE = """\
You are a taste judge for creative ideas. You will receive three mechanism \
candidates and the original seed. Pick the single best one.

Selection criteria (in order):
1. Strongest mechanism — can you explain what happens in plain language?
2. Most ambitious — does it change a category, not just improve a product?
3. Closest to seed — is the user's prompt still visibly load-bearing?
4. Passes the "remove the metaphor" test — is anything left without analogy?

Output exactly this format, nothing else:

WINNER: [1, 2, or 3]
REASON: [1 sentence explaining why this candidate beats the others]
"""


def compose_diverge_prompt(
    *,
    cfg: Config,
    profile: str,
    mode: str,
    random_stimulus: str | None = None,
    runtime_guidance: str | None = None,
    active_profile_dir: Path | None = None,
    default_profile_dir: Path | None = None,
) -> PromptComposition:
    """Build the Stage 1 (Diverge) system prompt — mechanism generation only.

    Uses a minimal subset of the soul: just invention-relevant rules
    (mechanism test, dead patterns, false bigness, mode instructions).
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

    # Preamble with structured output format
    sections.append(
        PromptSection(
            key="diverge_preamble",
            title="Diverge Preamble",
            content=_DIVERGE_PREAMBLE,
            kind="pipeline",
        )
    )

    # Mode-specific instructions (important for collision mechanics)
    mode_key = f"modes/{mode}.md"
    _add_soul_section(sections, snapshot, mode_key, f"Mode: {mode}")

    # Random stimulus (if applicable)
    if random_stimulus:
        sections.append(
            PromptSection(
                key="runtime/random_stimulus",
                title="Random Stimulus",
                kind="runtime",
                content=(
                    f"A random element for creative perturbation. "
                    f"Use it only if it strengthens a mechanism. Discard it if it weakens topic discipline.\n\n"
                    f"**Random stimulus:** {random_stimulus}"
                ),
            )
        )

    if runtime_guidance:
        sections.append(
            PromptSection(
                key="runtime/guidance",
                title="Runtime Guidance",
                kind="runtime",
                content=runtime_guidance,
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


def compose_select_prompt() -> str:
    """Build the Stage 2 (Select) system prompt — taste judgment."""
    return _SELECT_PREAMBLE


def compose_diverge_user_message(seeds: list[str], mode: str) -> str:
    """Build the user message for Stage 1 (Diverge)."""
    base = compose_user_message(seeds, mode)
    return f"{base}\n\nGenerate three mechanism candidates. No prose, no titles, no metaphors."


def compose_select_user_message(
    seeds: list[str], mode: str, candidates: str
) -> str:
    """Build the user message for Stage 2 (Select)."""
    seed_text = " + ".join(seeds)
    return (
        f"Original seed: {seed_text}\n"
        f"Mode: {mode}\n\n"
        f"Candidates:\n\n{candidates}\n\n"
        "Pick the best candidate."
    )


def compose_render_user_message(
    seeds: list[str], mode: str, mechanism_spec: str
) -> str:
    """Build the user message for Stage 3 (Render)."""
    base = compose_user_message(seeds, mode)
    return (
        f"{base}\n\n"
        "You have already extracted the core mechanism. Here it is:\n\n"
        "---\n"
        f"{mechanism_spec}\n"
        "---\n\n"
        "Render this mechanism into your final output. The mechanism is your "
        "foundation — preserve it faithfully. Your job now is voice, vividness, "
        "and format. Do not invent a new mechanism; deepen and render the one above."
    )


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
