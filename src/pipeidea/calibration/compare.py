"""Comparison logic for calibration runs."""

from __future__ import annotations

from collections import Counter, defaultdict
from pathlib import Path

from pipeidea.calibration.artifacts import artifact_paths, load_json, load_jsonl
from pipeidea.calibration.schemas import ComparisonReport, RealistAssessment, RunManifest


def _load_manifest(run_dir: Path) -> RunManifest:
    return RunManifest.from_dict(load_json(artifact_paths(run_dir)["manifest"]))


def _load_assessments(run_dir: Path) -> dict[str, RealistAssessment]:
    assessments = load_jsonl(artifact_paths(run_dir)["realist"])
    return {
        item["case_id"]: RealistAssessment.from_dict(item)
        for item in assessments
    }


def compare_runs(baseline_run_dir: Path, candidate_run_dir: Path) -> ComparisonReport:
    """Compare two calibration runs and return aggregate deltas."""
    baseline_manifest = _load_manifest(baseline_run_dir)
    candidate_manifest = _load_manifest(candidate_run_dir)

    baseline = _load_assessments(baseline_run_dir)
    candidate = _load_assessments(candidate_run_dir)

    shared_case_ids = sorted(set(baseline) & set(candidate))
    if not shared_case_ids:
        raise ValueError("No overlapping case ids found between the two runs.")

    overall_delta_total = 0.0
    axis_delta_totals: dict[str, float] = defaultdict(float)
    axis_delta_counts: dict[str, int] = defaultdict(int)
    baseline_tag_counts: Counter[str] = Counter()
    candidate_tag_counts: Counter[str] = Counter()
    improved_cases: list[dict[str, float | str]] = []
    regressed_cases: list[dict[str, float | str]] = []
    mechanical_regressions: list[str] = []

    for case_id in shared_case_ids:
        baseline_item = baseline[case_id]
        candidate_item = candidate[case_id]

        delta = candidate_item.overall_score - baseline_item.overall_score
        overall_delta_total += delta
        improved_cases.append({"case_id": case_id, "delta": round(delta, 4)})
        regressed_cases.append({"case_id": case_id, "delta": round(delta, 4)})

        for axis, value in baseline_item.axis_scores.items():
            if axis in candidate_item.axis_scores:
                axis_delta_totals[axis] += candidate_item.axis_scores[axis] - value
                axis_delta_counts[axis] += 1

        baseline_tag_counts.update(baseline_item.failure_tags)
        candidate_tag_counts.update(candidate_item.failure_tags)

        if baseline_item.mechanical_status == "ok" and candidate_item.mechanical_status != "ok":
            mechanical_regressions.append(case_id)

    improved_cases.sort(key=lambda item: float(item["delta"]), reverse=True)
    regressed_cases.sort(key=lambda item: float(item["delta"]))

    average_axis_deltas = {
        axis: round(axis_delta_totals[axis] / axis_delta_counts[axis], 4)
        for axis in sorted(axis_delta_totals)
        if axis_delta_counts[axis]
    }
    failure_tag_deltas = {
        tag: candidate_tag_counts[tag] - baseline_tag_counts[tag]
        for tag in sorted(set(baseline_tag_counts) | set(candidate_tag_counts))
    }
    average_overall_delta = overall_delta_total / len(shared_case_ids)

    notes: list[str] = []
    acceptance_recommendation = "review"
    if mechanical_regressions:
        acceptance_recommendation = "reject"
        notes.append("Candidate introduced new mechanical regressions.")
    elif average_overall_delta > 0.03:
        acceptance_recommendation = "promote"
        notes.append("Candidate improves overall score without new mechanical regressions.")
    elif average_overall_delta < -0.03:
        acceptance_recommendation = "reject"
        notes.append("Candidate regresses overall score across shared cases.")
    else:
        notes.append("Net change is small; inspect case-level examples before promoting.")

    notes.append(
        f"Baseline pack: {baseline_manifest.pack_name}. Candidate pack: {candidate_manifest.pack_name}."
    )

    return ComparisonReport(
        baseline_run_id=baseline_manifest.run_id,
        candidate_run_id=candidate_manifest.run_id,
        shared_case_count=len(shared_case_ids),
        average_overall_delta=round(average_overall_delta, 4),
        average_axis_deltas=average_axis_deltas,
        failure_tag_deltas=failure_tag_deltas,
        mechanical_regressions=mechanical_regressions,
        improved_cases=improved_cases[:5],
        regressed_cases=regressed_cases[:5],
        acceptance_recommendation=acceptance_recommendation,
        notes=notes,
    )


def render_comparison_markdown(report: ComparisonReport) -> str:
    """Render a human-readable markdown summary for a comparison report."""
    lines = [
        f"# Comparison: {report.candidate_run_id} vs {report.baseline_run_id}",
        "",
        f"- Shared cases: {report.shared_case_count}",
        f"- Average overall delta: {report.average_overall_delta:+.4f}",
        f"- Recommendation: {report.acceptance_recommendation}",
        "",
        "## Axis deltas",
    ]

    if report.average_axis_deltas:
        for axis, delta in report.average_axis_deltas.items():
            lines.append(f"- {axis}: {delta:+.4f}")
    else:
        lines.append("- No axis deltas available.")

    lines.extend(["", "## Failure tag deltas"])
    if report.failure_tag_deltas:
        for tag, delta in report.failure_tag_deltas.items():
            lines.append(f"- {tag}: {delta:+d}")
    else:
        lines.append("- No failure tag deltas available.")

    lines.extend(["", "## Mechanical regressions"])
    if report.mechanical_regressions:
        for case_id in report.mechanical_regressions:
            lines.append(f"- {case_id}")
    else:
        lines.append("- None")

    lines.extend(["", "## Improved cases"])
    if report.improved_cases:
        for item in report.improved_cases:
            lines.append(f"- {item['case_id']}: {float(item['delta']):+.4f}")
    else:
        lines.append("- None")

    lines.extend(["", "## Regressed cases"])
    if report.regressed_cases:
        for item in report.regressed_cases:
            lines.append(f"- {item['case_id']}: {float(item['delta']):+.4f}")
    else:
        lines.append("- None")

    if report.notes:
        lines.extend(["", "## Notes"])
        for note in report.notes:
            lines.append(f"- {note}")

    return "\n".join(lines).strip() + "\n"
