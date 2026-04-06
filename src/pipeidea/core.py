"""Shared application logic for CLI and web entry points."""

from dataclasses import dataclass, replace
from hashlib import sha256
from pathlib import Path
from collections.abc import Callable

import re

from pipeidea.config import Config, load_config
from pipeidea.providers.registry import get_provider
from pipeidea.sensitivity import assess_prompt_sensitivity
from pipeidea.soul.composer import (
    compose_prompt,
    compose_user_message,
    compose_diverge_prompt,
    compose_select_prompt,
    compose_diverge_user_message,
    compose_select_user_message,
    compose_render_user_message,
)
from pipeidea.soul.profiles import ensure_defaults
from pipeidea.soul.random_stimulus import get_random_stimulus, is_seed_rich


@dataclass(frozen=True)
class CreativeRunTrace:
    """Structured trace for a creative run."""

    requested_profile: str
    resolved_profile: str
    mode: str
    seeds: list[str]
    random_stimulus: str | None
    garden_echo_count: int
    web_stimulus_count: int
    user_message: str
    system_prompt_hash: str
    prompt_sections: list[dict[str, str | None]]
    provider_name: str
    provider_model: str | None
    temperature: float
    active_profile_dir: str | None
    default_profile_dir: str | None
    pipeline: str  # "three-stage" or "single-pass"
    mechanism_spec: str | None
    revision_attempted: bool
    revision_applied: bool
    initial_failure_tags: list[str]
    final_failure_tags: list[str]


@dataclass(frozen=True)
class CreativeRunResult:
    """Output plus trace metadata for calibration and debugging."""

    output: str
    trace: CreativeRunTrace


_REVISION_TAG_WEIGHTS: dict[str, float] = {
    "drifts_off_topic": 1.7,
    "template_output": 1.6,
    "surface_analogy": 1.5,
    "mechanism_missing": 1.5,
    "generic_futurism": 1.2,
    "too_many_ideas": 1.0,
    "format_drift": 1.1,
    "favorite_undercommitted": 0.8,
    "favorite_is_weak": 0.8,
    "ending_lacks_pull": 0.8,
    "thread_missing": 0.8,
    "randomness_absent": 0.3,
    "collision_not_load_bearing": 1.2,
    "too_incremental": 1.0,
}


def _revision_badness(failure_tags: list[str]) -> float:
    return sum(_REVISION_TAG_WEIGHTS.get(tag, 0.0) for tag in failure_tags)


def _revision_focus_score(assessment) -> float:
    axis_scores = assessment.axis_scores
    return (
        axis_scores.get("output_contract", 0.0) * 0.4
        + axis_scores.get("structural_depth", 0.0) * 0.3
        + axis_scores.get("topic_discipline", 0.0) * 0.2
        + axis_scores.get("randomness_integration", 0.0) * 0.1
    )


async def _heuristic_assessment_for_output(
    *,
    cfg: Config,
    run_id: str,
    case_id: str,
    profile: str,
    mode: str,
    seeds: list[str],
    stimulus: str | None,
    output: str,
    trace: CreativeRunTrace,
):
    from pipeidea.realist.evaluator import assess_sample
    from pipeidea.realist.schemas import CreativeSample

    sample = CreativeSample(
        run_id=run_id,
        case_id=case_id,
        mode=mode,
        seeds=seeds,
        stimulus=stimulus,
        requested_profile=profile,
        resolved_profile=trace.resolved_profile,
        output=output,
        error=None,
        trace=trace.__dict__,
    )
    return await assess_sample(sample=sample, rubric_text="", cfg=cfg, provider_name=None)


async def _maybe_refine_output(
    *,
    cfg: Config,
    provider_name: str | None,
    runtime_cfg: Config,
    trace: CreativeRunTrace,
    profile: str,
    mode: str,
    seeds: list[str],
    stimulus: str | None,
    draft_output: str,
    draft_assessment,
    mechanism_spec: str | None = None,
) -> tuple[str, bool, list[str], list[str]]:
    trigger_tags = [tag for tag in draft_assessment.failure_tags if tag in _REVISION_TAG_WEIGHTS]
    if not trigger_tags:
        return draft_output, False, draft_assessment.failure_tags, draft_assessment.failure_tags

    edit_cfg = replace(runtime_cfg)
    edit_cfg.temperature = min(edit_cfg.temperature, 0.35)
    editor = get_provider(edit_cfg, provider_name)
    critique = "\n".join(f"- {issue}" for issue in draft_assessment.issues[:6])
    seed_text = "\n".join(f"- {seed}" for seed in seeds)
    tag_guidance_map = {
        "drifts_off_topic": "Make the user's actual seed legible in the first sentence and keep it load-bearing throughout.",
        "template_output": "Collapse repeated titled cards into one prose-led artifact. Use a standalone title only if it truly helps.",
        "format_drift": "Delete labels, headings, separators, and list formatting. Keep the answer lean and prose-first.",
        "surface_analogy": "Replace metaphor-first framing with literal structural language and visible consequences.",
        "mechanism_missing": "Name the mechanism plainly: who does what, by what rule, material, incentive, or interface, and what changes first.",
        "generic_futurism": "Cut wrapper words like platform, ecosystem, or protocol unless you explain the concrete mechanism behind them.",
        "too_many_ideas": "Keep only the strongest idea unless a second one is equally strong and clearly distinct.",
        "favorite_undercommitted": "Make the favorite unmistakable and let it carry the answer.",
        "favorite_is_weak": "Mark exactly one favorite with the pipe and make it clearly the strongest idea.",
        "ending_lacks_pull": "End with a final sentence that creates forward pull instead of wrapping the idea up.",
        "thread_missing": "Leave a live next question, implication, or unresolved tension at the end.",
        "randomness_absent": "Either let the random stimulus visibly change the mechanism or discard it cleanly; do not leave it as decorative garnish.",
        "too_incremental": "Push beyond a feature or adjacent product into a category-changing mechanism.",
        "collision_not_load_bearing": "Ensure both supplied inputs are mechanically necessary, not just flavor.",
    }
    revision_guidance = "\n".join(
        f"- {tag_guidance_map[tag]}"
        for tag in trigger_tags
        if tag in tag_guidance_map
    )
    system_prompt = (
        "You are a hidden final-pass editor for a creative idea generator.\n"
        "Revise the draft so it more directly answers the user's prompt while preserving the strongest live idea.\n"
        "Default to one strong idea. Keep a second idea only if it is equally strong and genuinely distinct.\n"
        "Prefer one short prose artifact over repeated titled cards.\n"
        "Use a standalone title only if it genuinely sharpens recall.\n"
        "Every surviving idea must contain a literal mechanism sentence: who does what, by what rule/material/interface, and what changes first.\n"
        "Cut decorative analogy, wrapper language, and any random-stimulus use that is not load-bearing.\n"
        "Mark exactly one favorite with the pipe emoji and end with a sentence that leaves forward pull.\n"
        "Return only the revised final answer with no notes about the editing process."
    )
    mechanism_section = ""
    if mechanism_spec:
        mechanism_section = (
            f"Original mechanism spec (preserve this faithfully):\n{mechanism_spec}\n\n"
        )
    user_prompt = (
        f"Mode: {mode}\n"
        f"Seeds:\n{seed_text}\n\n"
        f"Random stimulus: {stimulus or '(none)'}\n\n"
        f"{mechanism_section}"
        "Revision priorities:\n"
        f"{revision_guidance or '- Tighten the answer while preserving the strongest idea.'}\n\n"
        "Heuristic critique of the draft:\n"
        f"{critique or '- The output needs tightening.'}\n\n"
        "Draft output to revise:\n"
        f"{draft_output}"
    )
    revised_output = await editor.generate(
        system_prompt,
        [{"role": "user", "content": user_prompt}],
    )

    revised_assessment = await _heuristic_assessment_for_output(
        cfg=cfg,
        run_id="live-revision",
        case_id="live-revision",
        profile=profile,
        mode=mode,
        seeds=seeds,
        stimulus=stimulus,
        output=revised_output,
        trace=replace(
            trace,
            provider_name=editor.name,
            provider_model=getattr(editor, "model", None),
            temperature=edit_cfg.temperature,
            revision_attempted=True,
            revision_applied=False,
            initial_failure_tags=list(draft_assessment.failure_tags),
            final_failure_tags=list(draft_assessment.failure_tags),
        ),
    )

    draft_badness = _revision_badness(draft_assessment.failure_tags)
    revised_badness = _revision_badness(revised_assessment.failure_tags)
    draft_focus = _revision_focus_score(draft_assessment)
    revised_focus = _revision_focus_score(revised_assessment)
    should_accept = False
    if revised_badness < draft_badness and revised_focus >= draft_focus - 0.03:
        should_accept = True
    elif (
        revised_badness == draft_badness
        and revised_focus > draft_focus + 0.04
    ):
        should_accept = True

    if should_accept:
        return (
            revised_output,
            True,
            draft_assessment.failure_tags,
            revised_assessment.failure_tags,
        )
    return (
        draft_output,
        True,
        draft_assessment.failure_tags,
        draft_assessment.failure_tags,
    )


def _parse_winner(select_output: str, candidates_text: str) -> str:
    """Extract the winning candidate from the select stage output."""
    match = re.search(r"WINNER:\s*(\d)", select_output)
    if not match:
        # Fallback: return first candidate
        return _extract_candidate(candidates_text, 1)
    winner_idx = int(match.group(1))
    return _extract_candidate(candidates_text, winner_idx)


def _extract_candidate(candidates_text: str, idx: int) -> str:
    """Extract a specific candidate block from the diverge output."""
    # Split on CANDIDATE N: headers
    parts = re.split(r"CANDIDATE\s+\d+:", candidates_text)
    # parts[0] is before first candidate, parts[1..] are the candidates
    if idx < len(parts):
        return parts[idx].strip()
    # Fallback to first candidate
    return parts[1].strip() if len(parts) > 1 else candidates_text.strip()


async def _run_three_stage(
    *,
    seeds: list[str],
    mode: str,
    profile: str,
    provider_name: str | None,
    cfg: Config,
    runtime_cfg: Config,
    stimulus: str | None,
    runtime_guidance: str | None,
    active_profile_dir: Path | None,
    default_profile_dir: Path | None,
) -> tuple[str, str]:
    """Run the 3-stage pipeline: Diverge -> Select -> Render.

    Returns (mechanism_spec, rendered_output).
    """
    # Stage 1: Diverge — generate 3 mechanism candidates
    diverge_prompt = compose_diverge_prompt(
        cfg=cfg,
        profile=profile,
        mode=mode,
        random_stimulus=stimulus,
        runtime_guidance=runtime_guidance,
        active_profile_dir=active_profile_dir,
        default_profile_dir=default_profile_dir,
    )
    diverge_user_msg = compose_diverge_user_message(seeds, mode)
    diverge_cfg = replace(runtime_cfg)
    # Keep temperature high for variety in diverge stage
    diverge_provider = get_provider(diverge_cfg, provider_name)
    candidates_text = await diverge_provider.generate(
        diverge_prompt.system_prompt,
        [{"role": "user", "content": diverge_user_msg}],
    )

    # Stage 2: Select — pick the best candidate
    select_system = compose_select_prompt()
    select_user_msg = compose_select_user_message(seeds, mode, candidates_text)
    select_cfg = replace(runtime_cfg)
    select_cfg.temperature = 0.3
    select_provider = get_provider(select_cfg, provider_name)
    select_output = await select_provider.generate(
        select_system,
        [{"role": "user", "content": select_user_msg}],
    )

    mechanism_spec = _parse_winner(select_output, candidates_text)

    # Stage 3: Render — full soul prompt with mechanism as foundation
    render_user_msg = compose_render_user_message(seeds, mode, mechanism_spec)
    render_prompt = compose_prompt(
        cfg=cfg,
        profile=profile,
        mode=mode,
        random_stimulus=stimulus,
        active_profile_dir=active_profile_dir,
        default_profile_dir=default_profile_dir,
    )
    render_provider = get_provider(runtime_cfg, provider_name)
    rendered_output = await render_provider.generate(
        render_prompt.system_prompt,
        [{"role": "user", "content": render_user_msg}],
    )

    return mechanism_spec, rendered_output


async def run_creative_with_trace(
    seeds: list[str],
    mode: str,
    profile: str,
    provider_name: str | None,
    wild: bool,
    on_chunk: Callable[[str], None] | None = None,
    cfg: Config | None = None,
    random_stimulus_override: str | None = None,
    garden_echoes: list[str] | None = None,
    web_stimuli: list[str] | None = None,
    active_profile_dir: Path | None = None,
    default_profile_dir: Path | None = None,
    temperature_override: float | None = None,
    single_pass: bool = False,
) -> CreativeRunResult:
    """Run the core creative flow and return output plus trace metadata."""
    cfg = cfg or load_config()
    if active_profile_dir is None and default_profile_dir is None:
        ensure_defaults(cfg)

    runtime_cfg = replace(cfg)
    if temperature_override is not None:
        runtime_cfg.temperature = temperature_override
    elif wild:
        runtime_cfg.temperature = min(runtime_cfg.temperature + 0.3, 1.5)

    sensitivity = assess_prompt_sensitivity(seeds, mode)
    runtime_guidance = sensitivity.reason
    if sensitivity.is_sensitive and not wild:
        runtime_cfg.temperature = min(runtime_cfg.temperature, 0.45)

    provider = get_provider(runtime_cfg, provider_name)

    # Conditional randomness: skip stimulus for rich seeds
    stimulus = random_stimulus_override
    if stimulus is None and not is_seed_rich(seeds, mode):
        try:
            stimulus = get_random_stimulus()
        except Exception:
            stimulus = None

    # Decide pipeline: three-stage by default, single-pass if wild or requested
    use_three_stage = not wild and not single_pass
    pipeline_name = "three-stage" if use_three_stage else "single-pass"

    mechanism_spec: str | None = None
    if use_three_stage:
        mechanism_spec, draft_output = await _run_three_stage(
            seeds=seeds,
            mode=mode,
            profile=profile,
            provider_name=provider_name,
            cfg=cfg,
            runtime_cfg=runtime_cfg,
            stimulus=stimulus,
            runtime_guidance=runtime_guidance,
            active_profile_dir=active_profile_dir,
            default_profile_dir=default_profile_dir,
        )
    else:
        # Single-pass: original behavior
        prompt = compose_prompt(
            cfg=cfg,
            profile=profile,
            mode=mode,
            random_stimulus=stimulus,
            garden_echoes=garden_echoes,
            web_stimuli=web_stimuli,
            runtime_guidance=runtime_guidance,
            active_profile_dir=active_profile_dir,
            default_profile_dir=default_profile_dir,
        )
        user_message = compose_user_message(seeds, mode)
        draft_output = await provider.generate(
            prompt.system_prompt,
            [{"role": "user", "content": user_message}],
        )

    # Build prompt for trace (always needed for heuristic assessment)
    prompt = compose_prompt(
        cfg=cfg,
        profile=profile,
        mode=mode,
        random_stimulus=stimulus,
        garden_echoes=garden_echoes,
        web_stimuli=web_stimuli,
        runtime_guidance=runtime_guidance,
        active_profile_dir=active_profile_dir,
        default_profile_dir=default_profile_dir,
    )
    user_message = compose_user_message(seeds, mode)

    trace = CreativeRunTrace(
        requested_profile=profile,
        resolved_profile=profile,
        mode=mode,
        seeds=list(seeds),
        random_stimulus=stimulus,
        garden_echo_count=len(garden_echoes or []),
        web_stimulus_count=len(web_stimuli or []),
        user_message=user_message,
        system_prompt_hash=sha256(prompt.system_prompt.encode("utf-8")).hexdigest(),
        prompt_sections=[
            {
                "key": section.key,
                "title": section.title,
                "kind": section.kind,
                "source_profile": section.source_profile,
                "source_path": section.source_path,
                "content": section.content,
            }
            for section in prompt.sections
        ],
        provider_name=provider.name,
        provider_model=getattr(provider, "model", None),
        temperature=runtime_cfg.temperature,
        active_profile_dir=prompt.active_profile_dir,
        default_profile_dir=prompt.default_profile_dir,
        pipeline=pipeline_name,
        mechanism_spec=mechanism_spec,
        revision_attempted=False,
        revision_applied=False,
        initial_failure_tags=[],
        final_failure_tags=[],
    )
    draft_assessment = await _heuristic_assessment_for_output(
        cfg=cfg,
        run_id="live-draft",
        case_id="live-draft",
        profile=profile,
        mode=mode,
        seeds=seeds,
        stimulus=stimulus,
        output=draft_output,
        trace=trace,
    )

    final_output = draft_output
    revision_applied = False
    initial_failure_tags = list(draft_assessment.failure_tags)
    final_failure_tags = list(draft_assessment.failure_tags)
    if not wild:
        final_output, revision_attempted, initial_failure_tags, final_failure_tags = await _maybe_refine_output(
            cfg=cfg,
            provider_name=provider_name,
            runtime_cfg=runtime_cfg,
            trace=trace,
            profile=profile,
            mode=mode,
            seeds=seeds,
            stimulus=stimulus,
            draft_output=draft_output,
            draft_assessment=draft_assessment,
            mechanism_spec=mechanism_spec,
        )
        revision_applied = final_output != draft_output
        trace = replace(
            trace,
            revision_attempted=revision_attempted,
            revision_applied=revision_applied,
            initial_failure_tags=initial_failure_tags,
            final_failure_tags=final_failure_tags,
        )

    if on_chunk is not None:
        on_chunk(final_output)

    return CreativeRunResult(output=final_output, trace=trace)


async def run_creative(
    seeds: list[str],
    mode: str,
    profile: str,
    provider_name: str | None,
    wild: bool,
    on_chunk: Callable[[str], None] | None = None,
    single_pass: bool = False,
) -> str:
    """Run the core creative flow and optionally stream chunks to a callback."""
    result = await run_creative_with_trace(
        seeds=seeds,
        mode=mode,
        profile=profile,
        provider_name=provider_name,
        wild=wild,
        on_chunk=on_chunk,
        single_pass=single_pass,
    )
    return result.output
