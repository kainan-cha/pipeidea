"""Internal evaluator for calibration runs."""

from __future__ import annotations

import json
import re
from typing import Any

from pipeidea.realist.mappers import map_failure_tags
from pipeidea.realist.schemas import CreativeSample, IdeaNote, RealistAssessment, clamp_score
from pipeidea.config import Config
from pipeidea.providers.registry import get_provider

HEDGING_MARKERS = ("maybe", "might", "could", "perhaps", "possibly", "consider", "somewhat")
BUZZWORD_MARKERS = (
    "ai-powered",
    "blockchain",
    "platform",
    "marketplace",
    "dashboard",
    "assistant",
    "app",
)
TRANSFORM_MARKERS = (
    "replace",
    "reimagine",
    "reinvent",
    "world",
    "city",
    "economy",
    "infrastructure",
    "planet",
    "ritual",
    "species",
    "without central planning",
    "new category",
)
STRUCTURAL_MARKERS = (
    "structure",
    "pattern",
    "feedback",
    "ecosystem",
    "evolution",
    "symbiosis",
    "topology",
    "phase transition",
    "ritual",
    "emergence",
)
CONCRETE_MARKERS = (
    "street",
    "room",
    "kitchen",
    "floor",
    "screen",
    "door",
    "city",
    "bench",
    "light",
    "sound",
    "body",
    "hands",
    "table",
    "market",
    "garden",
)
THREAD_MARKERS = ("what if", "opens the door", "and if that works", "this opens", "which means")
STOPWORDS = {
    "about",
    "after",
    "around",
    "because",
    "before",
    "could",
    "first",
    "from",
    "into",
    "just",
    "like",
    "more",
    "over",
    "that",
    "their",
    "there",
    "these",
    "this",
    "those",
    "through",
    "under",
    "very",
    "with",
    "would",
}


def _clip(value: float) -> float:
    return clamp_score(value)


def _unique(items: list[str]) -> list[str]:
    result: list[str] = []
    for item in items:
        item = item.strip()
        if item and item not in result:
            result.append(item)
    return result


def _extract_keywords(text: str, limit: int = 5) -> list[str]:
    words = re.findall(r"[a-zA-Z]{4,}", text.lower())
    keywords: list[str] = []
    for word in words:
        if word in STOPWORDS:
            continue
        if word not in keywords:
            keywords.append(word)
        if len(keywords) >= limit:
            break
    return keywords


def _idea_blocks(output: str) -> list[str]:
    blocks = [block.strip() for block in re.split(r"\n\s*\n", output.strip())]
    return [block for block in blocks if len(block) >= 40]


def _block_title(block: str) -> str:
    first_line = block.splitlines()[0].strip()
    title = re.sub(r"^[#>*\-\s]+", "", first_line)
    title = title.replace("🪈", "").strip()
    if not title:
        words = block.split()
        return " ".join(words[:6]).strip()
    return title[:80]


def _count_hits(text: str, phrases: tuple[str, ...]) -> int:
    lowered = text.lower()
    return sum(lowered.count(phrase) for phrase in phrases)


def _has_thread(output: str) -> bool:
    tail = output.lower()[-300:]
    return "?" in tail or any(marker in tail for marker in THREAD_MARKERS)


def _list_line_count(output: str) -> int:
    count = 0
    for line in output.splitlines():
        stripped = line.lstrip()
        if stripped.startswith(("-", "*")):
            count += 1
        elif re.match(r"^\d+\.\s+", stripped):
            count += 1
    return count


def _seed_coverage(output: str, seeds: list[str]) -> list[float]:
    lowered = output.lower()
    coverage: list[float] = []
    for seed in seeds:
        keywords = _extract_keywords(seed)
        if not keywords:
            coverage.append(1.0 if seed.lower() in lowered else 0.0)
            continue
        matches = sum(1 for keyword in keywords if keyword in lowered)
        coverage.append(matches / max(1, len(keywords)))
    return coverage


def _find_block_with_marker(blocks: list[str], marker: str) -> str | None:
    for block in blocks:
        if marker in block:
            return block
    return None


def _heuristic_assessment(sample: CreativeSample) -> dict[str, Any]:
    output = sample.output.strip()
    trace = sample.trace or {}
    failure_tags: list[str] = []
    strengths: list[str] = []
    issues: list[str] = []
    notes: list[str] = []

    if sample.error:
        failure_tags.append("pipeline_bug")
        files, directions, high_risk = map_failure_tags(failure_tags, sample.mode)
        if high_risk:
            notes.append(f"High-risk files implicated: {', '.join(high_risk)}.")
        return {
            "evaluation_mode": "heuristic",
            "mechanical_status": "broken",
            "overall_score": 0.0,
            "profile_match_score": 0.0,
            "mode_match_score": 0.0,
            "axis_scores": {
                "output_contract": 0.0,
                "ambition": 0.0,
                "vividness": 0.0,
                "conviction": 0.0,
                "structural_depth": 0.0,
                "randomness_integration": 0.0,
                "mode_fidelity": 0.0,
            },
            "strengths": [],
            "issues": [f"Generation failed before an output could be evaluated: {sample.error}"],
            "failure_tags": failure_tags,
            "alive_ideas": [],
            "dead_ideas": [],
            "likely_files_to_tune": files,
            "suggested_edit_direction": directions,
            "confidence": 0.95,
            "notes": notes,
        }

    prompt_sections = trace.get("prompt_sections", [])
    section_keys = {section.get("key") for section in prompt_sections}

    mechanical_status = "ok"
    if f"modes/{sample.mode}.md" not in section_keys:
        mechanical_status = "suspect"
        failure_tags.append("wrong_mode")
        issues.append("The requested mode instructions were not present in the composed prompt trace.")

    if sample.mode == "forage" and not trace.get("web_stimulus_count"):
        mechanical_status = "suspect"
        failure_tags.append("forage_missing_stimuli")
        issues.append("Forage mode ran without any web stimuli in the trace.")

    if sample.mode == "revisit" and not trace.get("garden_echo_count"):
        mechanical_status = "suspect"
        failure_tags.append("revisit_missing_echoes")
        issues.append("Revisit mode ran without any garden echoes in the trace.")

    if not output:
        mechanical_status = "broken"
        failure_tags.append("pipeline_bug")
        issues.append("The run completed without any output text.")

    blocks = _idea_blocks(output)
    block_count = len(blocks)
    favorite_present = "🪈" in output
    thread_present = _has_thread(output)
    list_lines = _list_line_count(output)
    hedge_hits = _count_hits(output, HEDGING_MARKERS)
    buzz_hits = _count_hits(output.lower(), BUZZWORD_MARKERS)
    transform_hits = _count_hits(output.lower(), TRANSFORM_MARKERS)
    structural_hits = _count_hits(output.lower(), STRUCTURAL_MARKERS)
    concrete_hits = _count_hits(output.lower(), CONCRETE_MARKERS)
    seed_coverage = _seed_coverage(output, sample.seeds)

    output_contract = 0.45
    if favorite_present:
        output_contract += 0.15
        strengths.append("The output clearly chose a favorite instead of flattening every idea.")
    else:
        failure_tags.append("favorite_is_weak")
        issues.append("The output never marked a single favorite idea.")

    if thread_present:
        output_contract += 0.15
        strengths.append("The ending leaves a live thread instead of closing the thought completely.")
    else:
        failure_tags.append("thread_missing")
        issues.append("The ending feels closed rather than leaving an unresolved thread.")

    if list_lines > 2:
        output_contract -= 0.15
        failure_tags.append("format_drift")
        issues.append("The output leaned on list formatting more than the profile contract wants.")

    if block_count > 5:
        output_contract -= 0.2
        failure_tags.append("too_many_ideas")
        issues.append("The output likely presented too many idea blocks instead of curating harder.")
    elif block_count in {2, 3}:
        output_contract += 0.1
        strengths.append("The idea count stayed in the profile's preferred few-better range.")

    ambition = 0.4 + 0.08 * transform_hits - 0.08 * buzz_hits
    if len(output) > 350:
        ambition += 0.05
    if buzz_hits > 0:
        failure_tags.append("generic_futurism")
        issues.append("The output leaned on generic product or futurist language.")
    if ambition < 0.45:
        failure_tags.append("too_incremental")
        issues.append("The ideas feel closer to features or adjacent products than category-bending leaps.")
    else:
        strengths.append("The output contains language that reaches beyond incremental product thinking.")

    vividness = 0.35 + 0.05 * concrete_hits
    if len(output) > 250:
        vividness += 0.1
    if list_lines == 0:
        vividness += 0.05
    if vividness < 0.45:
        failure_tags.append("not_vivid")
        issues.append("The descriptions do not land as strongly in visible, concrete scenes.")
    else:
        strengths.append("The output paints at least some concrete scenes rather than staying abstract.")

    conviction = 0.75 - 0.08 * hedge_hits
    if hedge_hits >= 3:
        failure_tags.append("voice_drift")
        issues.append("The voice drifted toward hedging instead of decisive conviction.")
    else:
        strengths.append("The voice mostly avoids hedging and sounds committed to its own claims.")

    structural_depth = 0.35 + 0.08 * structural_hits - 0.07 * buzz_hits
    if structural_depth < 0.45:
        failure_tags.append("surface_analogy")
        issues.append("The ideas do not show enough evidence of deep structural bridges.")
    else:
        strengths.append("There are signs of structural language rather than pure surface mashups.")

    randomness_integration = 0.55
    if sample.stimulus:
        stimulus_keywords = _extract_keywords(sample.stimulus)
        stimulus_used = any(keyword in output.lower() for keyword in stimulus_keywords)
        randomness_integration = 0.75 if stimulus_used else 0.3
        if stimulus_used:
            strengths.append("The output appears to absorb the injected random stimulus.")
        else:
            failure_tags.append("randomness_absent")
            issues.append("The injected random stimulus did not leave a visible trace in the output.")

    mode_fidelity = sum(seed_coverage) / max(1, len(seed_coverage))
    if sample.mode == "collision" and any(score < 0.25 for score in seed_coverage):
        failure_tags.append("collision_not_load_bearing")
        issues.append("At least one collision input barely shows up in the resulting ideas.")

    if sample.mode == "bloom" and mode_fidelity >= 0.4:
        strengths.append("The output still feels anchored to the seed while roaming outward.")

    profile_match_score = _clip((ambition + vividness + conviction + structural_depth) / 4)
    mode_match_score = _clip(mode_fidelity)
    axis_scores = {
        "output_contract": _clip(output_contract),
        "ambition": _clip(ambition),
        "vividness": _clip(vividness),
        "conviction": _clip(conviction),
        "structural_depth": _clip(structural_depth),
        "randomness_integration": _clip(randomness_integration),
        "mode_fidelity": _clip(mode_fidelity),
    }
    overall_score = _clip(
        (
            axis_scores["output_contract"] * 0.2
            + axis_scores["ambition"] * 0.2
            + axis_scores["vividness"] * 0.15
            + axis_scores["conviction"] * 0.1
            + axis_scores["structural_depth"] * 0.2
            + axis_scores["randomness_integration"] * 0.05
            + axis_scores["mode_fidelity"] * 0.1
        )
    )

    alive_ideas: list[IdeaNote] = []
    dead_ideas: list[IdeaNote] = []

    favorite_block = _find_block_with_marker(blocks, "🪈")
    if favorite_block:
        alive_ideas.append(
            IdeaNote(
                title=_block_title(favorite_block),
                why="This block was explicitly marked as the favorite, which is the clearest sign of what the profile thinks is alive.",
            )
        )
    elif blocks and overall_score >= 0.6:
        alive_ideas.append(
            IdeaNote(
                title=_block_title(blocks[0]),
                why="The opening block carries the strongest heuristic signal even though the output never marked a favorite.",
            )
        )

    if ("generic_futurism" in failure_tags or "too_incremental" in failure_tags) and blocks:
        dead_ideas.append(
            IdeaNote(
                title=_block_title(blocks[0]),
                why="The output shows feature-level or buzzword-heavy patterns that usually kill an idea on arrival.",
            )
        )

    strengths = _unique(strengths)
    issues = _unique(issues)
    failure_tags = _unique(failure_tags)
    files, directions, high_risk = map_failure_tags(failure_tags, sample.mode)
    if high_risk:
        notes.append(f"High-risk files implicated: {', '.join(high_risk)}.")

    return {
        "evaluation_mode": "heuristic",
        "mechanical_status": mechanical_status,
        "overall_score": overall_score,
        "profile_match_score": profile_match_score,
        "mode_match_score": mode_match_score,
        "axis_scores": axis_scores,
        "strengths": strengths,
        "issues": issues,
        "failure_tags": failure_tags,
        "alive_ideas": alive_ideas,
        "dead_ideas": dead_ideas,
        "likely_files_to_tune": files,
        "suggested_edit_direction": directions,
        "confidence": 0.55 if mechanical_status == "ok" else 0.85,
        "notes": notes,
    }


def _extract_json_object(text: str) -> dict[str, Any] | None:
    cleaned = text.strip()
    if not cleaned:
        return None

    candidates = [cleaned]
    fenced = re.findall(r"```(?:json)?\s*(\{.*?\})\s*```", cleaned, re.DOTALL)
    candidates.extend(fenced)

    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start != -1 and end != -1 and end > start:
        candidates.append(cleaned[start : end + 1])

    for candidate in candidates:
        try:
            parsed = json.loads(candidate)
        except json.JSONDecodeError:
            continue
        if isinstance(parsed, dict):
            return parsed
    return None


async def _model_assessment(
    sample: CreativeSample,
    heuristic: dict[str, Any],
    rubric_text: str,
    cfg: Config,
    provider_name: str | None,
) -> dict[str, Any] | None:
    if not provider_name:
        return None

    provider = get_provider(cfg, provider_name)
    system_prompt = (
        "You are `realist`, an internal calibration evaluator for pipeidea.\n"
        "You are critical but reasonable. Your job is to distinguish pipeline bugs from profile issues,\n"
        "identify what is alive before you explain what is dead, and map failures back to likely markdown files.\n"
        "Return a single JSON object and no surrounding prose.\n\n"
        f"{rubric_text.strip()}\n\n"
        "Required keys: mechanical_status, overall_score, profile_match_score, mode_match_score, "
        "axis_scores, strengths, issues, failure_tags, alive_ideas, dead_ideas, "
        "likely_files_to_tune, suggested_edit_direction, confidence."
    )
    payload = {
        "case": {
            "id": sample.case_id,
            "mode": sample.mode,
            "seeds": sample.seeds,
            "stimulus": sample.stimulus,
            "requested_profile": sample.requested_profile,
        },
        "trace": sample.trace,
        "output": sample.output,
        "heuristic_findings": {
            "mechanical_status": heuristic["mechanical_status"],
            "failure_tags": heuristic["failure_tags"],
            "axis_scores": heuristic["axis_scores"],
            "strengths": heuristic["strengths"],
            "issues": heuristic["issues"],
        },
    }
    response = await provider.generate(
        system_prompt,
        [{"role": "user", "content": json.dumps(payload, ensure_ascii=True, indent=2)}],
    )
    return _extract_json_object(response)


def _normalize_idea_list(items: Any) -> list[IdeaNote]:
    if not isinstance(items, list):
        return []
    result: list[IdeaNote] = []
    for item in items:
        if isinstance(item, dict):
            result.append(IdeaNote.from_dict(item))
    return result


def _blend_scores(primary: float, secondary: float | None, weight_secondary: float = 0.65) -> float:
    if secondary is None:
        return _clip(primary)
    return _clip(primary * (1 - weight_secondary) + secondary * weight_secondary)


async def assess_sample(
    sample: CreativeSample,
    rubric_text: str,
    cfg: Config,
    provider_name: str | None = None,
) -> RealistAssessment:
    """Assess a generated sample using heuristics plus optional model critique."""
    heuristic = _heuristic_assessment(sample)
    model_data: dict[str, Any] | None = None
    notes = list(heuristic["notes"])

    if provider_name and not sample.error:
        try:
            model_data = await _model_assessment(
                sample=sample,
                heuristic=heuristic,
                rubric_text=rubric_text,
                cfg=cfg,
                provider_name=provider_name,
            )
        except Exception as exc:
            notes.append(f"Model-backed evaluation unavailable; fell back to heuristics. ({exc})")

    if model_data is None:
        return RealistAssessment(
            run_id=sample.run_id,
            case_id=sample.case_id,
            evaluation_mode=heuristic["evaluation_mode"],
            mechanical_status=heuristic["mechanical_status"],
            overall_score=heuristic["overall_score"],
            profile_match_score=heuristic["profile_match_score"],
            mode_match_score=heuristic["mode_match_score"],
            axis_scores=heuristic["axis_scores"],
            strengths=heuristic["strengths"],
            issues=heuristic["issues"],
            failure_tags=heuristic["failure_tags"],
            alive_ideas=heuristic["alive_ideas"],
            dead_ideas=heuristic["dead_ideas"],
            likely_files_to_tune=heuristic["likely_files_to_tune"],
            suggested_edit_direction=heuristic["suggested_edit_direction"],
            confidence=heuristic["confidence"],
            notes=notes,
        )

    model_tags = [str(item) for item in model_data.get("failure_tags", [])]
    merged_tags = _unique(heuristic["failure_tags"] + model_tags)
    mapped_files, mapped_directions, high_risk = map_failure_tags(merged_tags, sample.mode)
    if high_risk:
        notes.append(f"High-risk files implicated: {', '.join(high_risk)}.")

    axis_scores = dict(heuristic["axis_scores"])
    for key, value in dict(model_data.get("axis_scores", {})).items():
        axis_scores[str(key)] = _blend_scores(axis_scores.get(str(key), 0.0), clamp_score(value))

    mechanical_status = heuristic["mechanical_status"]
    if mechanical_status == "ok" and model_data.get("mechanical_status"):
        mechanical_status = str(model_data["mechanical_status"])

    likely_files = _unique(
        [str(item) for item in model_data.get("likely_files_to_tune", [])] + mapped_files
    )
    suggested_directions = _unique(
        [str(item) for item in model_data.get("suggested_edit_direction", [])] + mapped_directions
    )

    return RealistAssessment(
        run_id=sample.run_id,
        case_id=sample.case_id,
        evaluation_mode="hybrid",
        mechanical_status=mechanical_status,
        overall_score=_blend_scores(
            heuristic["overall_score"], clamp_score(model_data.get("overall_score"))
        ),
        profile_match_score=_blend_scores(
            heuristic["profile_match_score"],
            clamp_score(model_data.get("profile_match_score")),
        ),
        mode_match_score=_blend_scores(
            heuristic["mode_match_score"],
            clamp_score(model_data.get("mode_match_score")),
        ),
        axis_scores=axis_scores,
        strengths=_unique(
            [str(item) for item in model_data.get("strengths", [])] + heuristic["strengths"]
        ),
        issues=_unique([str(item) for item in model_data.get("issues", [])] + heuristic["issues"]),
        failure_tags=merged_tags,
        alive_ideas=_normalize_idea_list(model_data.get("alive_ideas")) or heuristic["alive_ideas"],
        dead_ideas=_normalize_idea_list(model_data.get("dead_ideas")) or heuristic["dead_ideas"],
        likely_files_to_tune=likely_files,
        suggested_edit_direction=suggested_directions,
        confidence=_blend_scores(
            heuristic["confidence"], clamp_score(model_data.get("confidence")), weight_secondary=0.75
        ),
        notes=notes,
    )
