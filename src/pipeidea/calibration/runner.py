"""Calibration run orchestration and summaries."""

from __future__ import annotations

import json
import subprocess
from collections import Counter
from datetime import UTC, datetime
from pathlib import Path
from typing import Any
from collections.abc import Callable

from pipeidea.calibration.artifacts import (
    append_jsonl,
    artifact_paths,
    ensure_directory,
    find_run_dir,
    load_json,
    load_jsonl,
    write_json,
)
from pipeidea.calibration.compare import render_comparison_markdown
from pipeidea.calibration.realist import assess_sample
from pipeidea.calibration.schemas import (
    ComparisonReport,
    CreativeSample,
    PromotionRecord,
    RealistAssessment,
    RunManifest,
    SeedCase,
)
from pipeidea.config import Config, load_config
from pipeidea.core import run_creative_with_trace

REPO_ROOT = Path(__file__).resolve().parents[3]
REPO_CALIBRATION_DIR = REPO_ROOT / "calibration"
REPO_DEFAULT_PROFILE_DIR = REPO_ROOT / "src" / "pipeidea" / "soul" / "defaults" / "profiles" / "default"
DEFAULT_RUBRIC_NAME = "realist"


def _slugify(value: str) -> str:
    return "".join(char.lower() if char.isalnum() else "-" for char in value).strip("-")


def _timestamp() -> str:
    return datetime.now(UTC).isoformat()


def _run_id(profile: str, candidate_label: str | None = None) -> str:
    stamp = datetime.now(UTC).strftime("%Y%m%dT%H%M%SZ")
    slug = _slugify(candidate_label or profile or "run")
    return f"{stamp}-{slug}"


def resolve_seed_pack(pack_ref: str | Path) -> tuple[str, Path, list[SeedCase]]:
    """Resolve a seed pack name or path into cases."""
    pack_path = Path(pack_ref)
    if not pack_path.exists():
        candidate = REPO_CALIBRATION_DIR / "seed_packs" / str(pack_ref)
        if not candidate.suffix:
            candidate = candidate.with_suffix(".jsonl")
        pack_path = candidate

    if not pack_path.exists():
        raise FileNotFoundError(f"Seed pack not found: {pack_ref}")

    cases: list[SeedCase] = []
    for line in pack_path.read_text().splitlines():
        if not line.strip():
            continue
        cases.append(SeedCase.from_dict(json.loads(line)))

    return pack_path.stem, pack_path, cases


def resolve_rubric(rubric_ref: str | Path) -> tuple[str, Path, str]:
    """Resolve a rubric name or path into text."""
    rubric_path = Path(rubric_ref)
    if not rubric_path.exists():
        candidate = REPO_CALIBRATION_DIR / "rubrics" / str(rubric_ref)
        if not candidate.suffix:
            candidate = candidate.with_suffix(".md")
        rubric_path = candidate

    if not rubric_path.exists():
        raise FileNotFoundError(f"Rubric not found: {rubric_ref}")

    return rubric_path.stem, rubric_path, rubric_path.read_text()


def resolve_profile_dirs(
    cfg: Config,
    profile: str,
    profile_dir: str | Path | None = None,
    default_dir: str | Path | None = None,
) -> tuple[Path | None, Path | None]:
    """Resolve which profile directories calibration should read from."""
    active_dir = Path(profile_dir) if profile_dir is not None else None
    fallback_dir = Path(default_dir) if default_dir is not None else None

    if active_dir is None:
        if profile == "default" and REPO_DEFAULT_PROFILE_DIR.exists():
            active_dir = REPO_DEFAULT_PROFILE_DIR
        else:
            active_dir = cfg.profiles_dir / profile

    if fallback_dir is None and profile != "default":
        fallback_dir = REPO_DEFAULT_PROFILE_DIR if REPO_DEFAULT_PROFILE_DIR.exists() else cfg.profiles_dir / "default"

    return active_dir, fallback_dir


def _manifest(
    *,
    run_id: str,
    pack_name: str,
    pack_path: Path,
    profile: str,
    provider_name: str | None,
    evaluator_provider_name: str | None,
    rubric_path: Path | None,
    realist_enabled: bool,
    temperature: float | None,
    candidate_label: str | None,
    profile_dir: Path | None,
    default_dir: Path | None,
    sample_count: int,
) -> RunManifest:
    return RunManifest(
        run_id=run_id,
        created_at=_timestamp(),
        finished_at=None,
        status="running",
        pack_name=pack_name,
        pack_path=str(pack_path),
        profile=profile,
        provider_name=provider_name,
        evaluator_provider_name=evaluator_provider_name,
        rubric_path=str(rubric_path) if rubric_path is not None else None,
        realist_enabled=realist_enabled,
        temperature=temperature,
        candidate_label=candidate_label,
        profile_dir=str(profile_dir) if profile_dir is not None else None,
        default_dir=str(default_dir) if default_dir is not None else None,
        sample_count=sample_count,
    )


async def run_calibration(
    *,
    pack: str | Path,
    profile: str | None = None,
    provider_name: str | None = None,
    evaluator_provider_name: str | None = None,
    rubric: str | Path = DEFAULT_RUBRIC_NAME,
    profile_dir: str | Path | None = None,
    default_dir: str | Path | None = None,
    output_dir: str | Path | None = None,
    candidate_label: str | None = None,
    temperature: float | None = None,
    realist_enabled: bool = True,
    wild: bool = False,
    progress: Callable[[str], None] | None = None,
) -> tuple[RunManifest, Path]:
    """Execute a calibration run and write artifacts to disk."""
    cfg = load_config()
    selected_profile = profile or cfg.default_profile
    pack_name, pack_path, cases = resolve_seed_pack(pack)
    rubric_name = None
    rubric_path = None
    rubric_text = ""
    if realist_enabled:
        rubric_name, rubric_path, rubric_text = resolve_rubric(rubric)

    active_dir, fallback_dir = resolve_profile_dirs(
        cfg=cfg,
        profile=selected_profile,
        profile_dir=profile_dir,
        default_dir=default_dir,
    )

    run_id = _run_id(selected_profile, candidate_label)
    run_dir = Path(output_dir) if output_dir is not None else cfg.calibration_runs_dir / run_id
    ensure_directory(run_dir)
    if progress is not None:
        progress(f"Starting calibration run `{run_id}` with pack `{pack_name}`.")

    chosen_evaluator = evaluator_provider_name or cfg.default_realist_provider or provider_name
    manifest = _manifest(
        run_id=run_id,
        pack_name=pack_name,
        pack_path=pack_path,
        profile=selected_profile,
        provider_name=provider_name,
        evaluator_provider_name=chosen_evaluator,
        rubric_path=rubric_path,
        realist_enabled=realist_enabled,
        temperature=temperature,
        candidate_label=candidate_label,
        profile_dir=active_dir,
        default_dir=fallback_dir,
        sample_count=len(cases),
    )
    paths = artifact_paths(run_dir)
    write_json(paths["manifest"], manifest)

    samples: list[CreativeSample] = []
    assessments: list[RealistAssessment] = []

    for index, case in enumerate(cases, start=1):
        if progress is not None:
            progress(f"[{index}/{len(cases)}] Generating `{case.id}` ({case.mode}).")
        try:
            result = await run_creative_with_trace(
                seeds=case.seeds,
                mode=case.mode,
                profile=selected_profile,
                provider_name=provider_name,
                wild=wild,
                cfg=cfg,
                random_stimulus_override=case.stimulus,
                garden_echoes=case.garden_echoes,
                web_stimuli=case.web_stimuli,
                active_profile_dir=active_dir,
                default_profile_dir=fallback_dir,
                temperature_override=temperature,
            )
            sample = CreativeSample(
                run_id=run_id,
                case_id=case.id,
                mode=case.mode,
                seeds=case.seeds,
                stimulus=case.stimulus,
                requested_profile=selected_profile,
                resolved_profile=result.trace.resolved_profile,
                output=result.output,
                error=None,
                trace=result.trace.__dict__,
                metadata=case.metadata,
            )
        except Exception as exc:
            sample = CreativeSample(
                run_id=run_id,
                case_id=case.id,
                mode=case.mode,
                seeds=case.seeds,
                stimulus=case.stimulus,
                requested_profile=selected_profile,
                resolved_profile=selected_profile,
                output="",
                error=str(exc),
                trace={
                    "requested_profile": selected_profile,
                    "mode": case.mode,
                    "seeds": case.seeds,
                    "web_stimulus_count": len(case.web_stimuli),
                    "garden_echo_count": len(case.garden_echoes),
                    "prompt_sections": [],
                },
                metadata=case.metadata,
            )

        samples.append(sample)
        append_jsonl(paths["samples"], sample)

        if realist_enabled:
            if progress is not None:
                progress(f"[{index}/{len(cases)}] Evaluating `{case.id}` with `realist`.")
            assessment = await assess_sample(
                sample=sample,
                rubric_text=rubric_text,
                cfg=cfg,
                provider_name=chosen_evaluator,
            )
            assessments.append(assessment)
            append_jsonl(paths["realist"], assessment)
        elif progress is not None:
            progress(f"[{index}/{len(cases)}] Stored `{case.id}` without evaluator scoring.")

    manifest = RunManifest(
        **{
            **manifest.__dict__,
            "finished_at": _timestamp(),
            "status": "completed",
            "provider_name": manifest.provider_name
            or next(
                (
                    str(sample.trace.get("provider_name"))
                    for sample in samples
                    if sample.trace.get("provider_name")
                ),
                None,
            ),
            "notes": manifest.notes + (
                [f"Rubric: {rubric_name}"] if rubric_name else []
            ),
        }
    )
    write_json(paths["manifest"], manifest)

    summary = render_summary_markdown(manifest, samples, assessments)
    paths["summary"].write_text(summary)
    if progress is not None:
        progress(f"Completed calibration run `{manifest.run_id}`. Artifacts written to `{run_dir}`.")
    return manifest, run_dir


def render_summary_markdown(
    manifest: RunManifest,
    samples: list[CreativeSample],
    assessments: list[RealistAssessment],
) -> str:
    """Render a markdown summary for a run."""
    lines = [
        f"# Calibration Run: {manifest.run_id}",
        "",
        f"- Profile: {manifest.profile}",
        f"- Pack: {manifest.pack_name}",
        f"- Provider: {manifest.provider_name or 'unset'}",
        f"- Realist evaluator: {'enabled' if manifest.realist_enabled else 'disabled'}",
        f"- Evaluator provider: {manifest.evaluator_provider_name or 'heuristic-only'}",
        f"- Sample count: {manifest.sample_count}",
        f"- Status: {manifest.status}",
    ]

    if assessments:
        average_overall = sum(item.overall_score for item in assessments) / len(assessments)
        average_profile = sum(item.profile_match_score for item in assessments) / len(assessments)
        average_mode = sum(item.mode_match_score for item in assessments) / len(assessments)
        lines.extend(
            [
                "",
                "## Scores",
                f"- Average overall score: {average_overall:.3f}",
                f"- Average profile match: {average_profile:.3f}",
                f"- Average mode match: {average_mode:.3f}",
            ]
        )

        tag_counts: Counter[str] = Counter()
        for item in assessments:
            tag_counts.update(item.failure_tags)

        lines.extend(["", "## Top failure tags"])
        if tag_counts:
            for tag, count in tag_counts.most_common(8):
                lines.append(f"- {tag}: {count}")
        else:
            lines.append("- None")

        mechanical_issues = [item for item in assessments if item.mechanical_status != "ok"]
        lines.extend(["", "## Mechanical issues"])
        if mechanical_issues:
            for item in mechanical_issues[:10]:
                lines.append(
                    f"- {item.case_id}: {item.mechanical_status} ({', '.join(item.failure_tags) or 'no tags'})"
                )
        else:
            lines.append("- None")

        lines.extend(["", "## Strongest cases"])
        for item in sorted(assessments, key=lambda case: case.overall_score, reverse=True)[:5]:
            lines.append(
                f"- {item.case_id}: {item.overall_score:.3f} ({', '.join(item.strengths[:2]) or 'no strengths logged'})"
            )

        lines.extend(["", "## Weakest cases"])
        for item in sorted(assessments, key=lambda case: case.overall_score)[:5]:
            lines.append(
                f"- {item.case_id}: {item.overall_score:.3f} ({', '.join(item.failure_tags[:3]) or 'no failure tags'})"
            )
    else:
        lines.extend(["", "## Scores", "- Realist evaluation was disabled for this run."])

    failed_samples = [sample for sample in samples if sample.error]
    if failed_samples:
        lines.extend(["", "## Generation errors"])
        for sample in failed_samples[:10]:
            lines.append(f"- {sample.case_id}: {sample.error}")

    return "\n".join(lines).strip() + "\n"


def summarize_run_artifacts(run_dir: Path) -> str:
    """Load artifacts from disk and render the summary markdown."""
    paths = artifact_paths(run_dir)
    manifest = RunManifest.from_dict(load_json(paths["manifest"]))
    samples = [CreativeSample.from_dict(item) for item in load_jsonl(paths["samples"])]
    assessments = [RealistAssessment.from_dict(item) for item in load_jsonl(paths["realist"])]
    return render_summary_markdown(manifest, samples, assessments)


def _git_commit() -> str:
    try:
        completed = subprocess.run(
            ["git", "-C", str(REPO_ROOT), "rev-parse", "--short", "HEAD"],
            check=True,
            capture_output=True,
            text=True,
        )
    except Exception:
        return "UNCOMMITTED"
    return completed.stdout.strip() or "UNCOMMITTED"


def _toml_list(items: list[str]) -> str:
    rendered = ", ".join(json.dumps(item, ensure_ascii=True) for item in items)
    return f"[{rendered}]"


def write_promotion_record(
    *,
    run_dir: Path,
    version: str,
    hypothesis: str,
    touched_files: list[str] | None = None,
    accepted: bool = True,
    comparison_report: ComparisonReport | None = None,
) -> Path:
    """Write a versioned promotion record and append a decision log entry."""
    manifest = RunManifest.from_dict(load_json(artifact_paths(run_dir)["manifest"]))
    samples = [CreativeSample.from_dict(item) for item in load_jsonl(artifact_paths(run_dir)["samples"])]
    model_name = ""
    for sample in samples:
        provider_model = str(sample.trace.get("provider_model", "")).strip()
        if provider_model:
            model_name = provider_model
            break

    report_note = ""
    if comparison_report is not None:
        report_note = render_comparison_markdown(comparison_report).strip()

    record = PromotionRecord(
        version=version,
        profile=manifest.profile,
        run_id=manifest.run_id,
        commit=_git_commit(),
        benchmark_pack=[manifest.pack_name],
        realist_rubric=Path(manifest.rubric_path).stem if manifest.rubric_path else "",
        provider=manifest.provider_name or "",
        model=model_name,
        hypothesis=hypothesis,
        touched_files=touched_files or [],
        accepted=accepted,
        notes=report_note,
    )

    version_dir = REPO_CALIBRATION_DIR / "versions" / manifest.profile
    ensure_directory(version_dir)
    version_path = version_dir / f"{version}.toml"
    version_path.write_text(
        "\n".join(
            [
                f'version = {json.dumps(record.version)}',
                f'profile = {json.dumps(record.profile)}',
                f'run_id = {json.dumps(record.run_id)}',
                f'commit = {json.dumps(record.commit)}',
                f"benchmark_pack = {_toml_list(record.benchmark_pack)}",
                f'realist_rubric = {json.dumps(record.realist_rubric)}',
                f'provider = {json.dumps(record.provider)}',
                f'model = {json.dumps(record.model)}',
                f'hypothesis = {json.dumps(record.hypothesis)}',
                f"touched_files = {_toml_list(record.touched_files)}",
                f"accepted = {'true' if record.accepted else 'false'}",
                f'notes = {json.dumps(record.notes)}',
                "",
            ]
        )
    )

    decision_path = REPO_CALIBRATION_DIR / "decisions" / f"{manifest.profile}.md"
    ensure_directory(decision_path.parent)
    with decision_path.open("a", encoding="utf-8") as handle:
        handle.write(
            "\n".join(
                [
                    f"## {version}",
                    "",
                    f"- Run: {record.run_id}",
                    f"- Accepted: {'yes' if accepted else 'no'}",
                    f"- Hypothesis: {record.hypothesis}",
                    f"- Touched files: {', '.join(record.touched_files) or 'none recorded'}",
                    f"- Commit: {record.commit}",
                    "",
                ]
            )
        )
        if report_note:
            handle.write(report_note + "\n\n")
        else:
            handle.write("\n")

    return version_path


def resolve_run_reference(run_ref: str | Path) -> Path:
    """Resolve a run id or path using the active config."""
    return find_run_dir(load_config(), run_ref)
