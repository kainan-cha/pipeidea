"""Run staged evaluation suites and write a machine-readable report."""

from __future__ import annotations

import argparse
import asyncio
import json
import tempfile
from datetime import UTC, datetime
from collections import Counter, defaultdict
from pathlib import Path
from typing import Any

from pipeidea.config import load_config
from pipeidea.realist.compare import compare_runs, render_comparison_markdown
from run_heuristic_eval import run_pack_heuristic


REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_TMP = Path(tempfile.gettempdir())


async def _run_stage(stage: dict[str, Any], profile: str, base_output_dir: Path) -> dict[str, Any]:
    stage_output_dir = base_output_dir / stage["name"]
    provider = stage.get("provider")
    if stage["type"] != "heuristic":
        raise SystemExit(f"Unsupported stage type: {stage['type']}")

    stage_output_dir.mkdir(parents=True, exist_ok=True)
    output_path = stage_output_dir / "heuristic_report.json"
    payload = await run_pack_heuristic(
        pack=stage["pack"],
        provider=provider,
        profile=profile,
        concurrency=int(stage.get("concurrency", 4)),
        output=str(output_path),
    )
    rows = payload["assessments"]
    (stage_output_dir / "realist.jsonl").write_text(
        "".join(json.dumps(row, ensure_ascii=True, sort_keys=True) + "\n" for row in rows),
        encoding="utf-8",
    )
    manifest = {
        "run_id": stage["name"],
        "created_at": datetime.now(UTC).isoformat(),
        "finished_at": datetime.now(UTC).isoformat(),
        "status": "completed",
        "pack_name": stage["pack"],
        "pack_path": stage["pack"],
        "profile": profile,
        "provider_name": provider,
        "evaluator_provider_name": None,
        "rubric_path": None,
        "realist_enabled": True,
        "temperature": None,
        "candidate_label": stage["name"],
        "profile_dir": None,
        "default_dir": None,
        "sample_count": len(rows),
        "notes": ["heuristic-only suite stage"],
        "metadata": {"suite_stage": stage["name"]},
    }
    (stage_output_dir / "manifest.json").write_text(
        json.dumps(manifest, indent=2, ensure_ascii=True, sort_keys=True) + "\n",
        encoding="utf-8",
    )

    axis_totals: dict[str, float] = defaultdict(float)
    tag_counts = Counter(tag for row in rows for tag in row.get("failure_tags", []))
    for row in rows:
        for axis, value in row.get("axis_scores", {}).items():
            axis_totals[axis] += float(value)

    axis_averages = {
        axis: round(total / max(1, len(rows)), 4)
        for axis, total in sorted(axis_totals.items())
    }

    summary = {
        "run_id": stage["name"],
        "pack": stage["pack"],
        "sample_count": len(rows),
        "average_overall_score": round(
            sum(row.get("overall_score", 0.0) for row in rows) / max(1, len(rows)), 4
        ),
        "failure_tags": dict(tag_counts),
        "axis_averages": axis_averages,
    }
    return summary


def _evaluate_gates(summary: dict[str, Any], gates: dict[str, Any] | None) -> list[str]:
    if not gates:
        return []

    failures: list[str] = []
    tag_counts = summary.get("failure_tags", {})
    axis_averages = summary.get("axis_averages", {})

    max_pipeline_bug = gates.get("max_pipeline_bug")
    if max_pipeline_bug is not None and tag_counts.get("pipeline_bug", 0) > max_pipeline_bug:
        failures.append(
            f"pipeline_bug exceeded: {tag_counts.get('pipeline_bug', 0)} > {max_pipeline_bug}"
        )

    for tag, limit in gates.get("max_failure_tags", {}).items():
        if tag_counts.get(tag, 0) > limit:
            failures.append(f"{tag} exceeded: {tag_counts.get(tag, 0)} > {limit}")

    for axis, floor in gates.get("min_average_axes", {}).items():
        if axis_averages.get(axis, 0.0) < floor:
            failures.append(f"{axis} below floor: {axis_averages.get(axis, 0.0):.4f} < {floor}")

    return failures


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("suite")
    parser.add_argument("--profile", default=None)
    parser.add_argument("--output-dir", default=None)
    args = parser.parse_args()

    cfg = load_config()
    suite_path = Path(args.suite)
    if not suite_path.exists():
        suite_path = REPO_ROOT / "calibration" / "suites" / args.suite
    if suite_path.suffix == "":
        suite_path = suite_path.with_suffix(".json")
    suite = json.loads(suite_path.read_text())

    profile = args.profile or suite.get("profile") or cfg.default_profile
    base_output_dir = Path(args.output_dir) if args.output_dir else DEFAULT_TMP / suite["name"]
    base_output_dir.mkdir(parents=True, exist_ok=True)

    report: dict[str, Any] = {
        "suite": suite["name"],
        "profile": profile,
        "stages": [],
        "final_acceptance": suite.get("final_acceptance", {}),
    }

    previous_run_dir: Path | None = None
    for stage in suite.get("stages", []):
        summary = await _run_stage(stage, profile=profile, base_output_dir=base_output_dir)
        gate_failures = _evaluate_gates(summary, stage.get("gates"))
        stage_report = {
            "name": stage["name"],
            "type": stage["type"],
            "summary": summary,
            "gate_failures": gate_failures,
        }

        current_run_dir = base_output_dir / stage["name"]
        if previous_run_dir is not None:
            try:
                comparison = compare_runs(previous_run_dir, current_run_dir)
            except ValueError:
                comparison = None
            if comparison is not None:
                comparison_path = current_run_dir / "compare.md"
                comparison_path.write_text(render_comparison_markdown(comparison), encoding="utf-8")
                stage_report["comparison"] = {
                    "baseline_run_id": comparison.baseline_run_id,
                    "candidate_run_id": comparison.candidate_run_id,
                    "average_overall_delta": comparison.average_overall_delta,
                    "failure_tag_deltas": comparison.failure_tag_deltas,
                    "acceptance_recommendation": comparison.acceptance_recommendation,
                }

        report["stages"].append(stage_report)
        previous_run_dir = current_run_dir

    report_path = base_output_dir / "suite_report.json"
    report_path.write_text(json.dumps(report, indent=2, ensure_ascii=True) + "\n", encoding="utf-8")
    print(report_path)


if __name__ == "__main__":
    asyncio.run(main())
