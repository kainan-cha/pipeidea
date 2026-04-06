"""Run a calibration-style generation pass with heuristic or model-backed evaluation."""

import argparse
import asyncio
import json
from collections import Counter
from pathlib import Path

from pipeidea.config import load_config
from pipeidea.core import run_creative_with_trace
from pipeidea.realist.evaluator import assess_sample
from pipeidea.realist.runner import resolve_profile_dirs, resolve_rubric, resolve_seed_pack
from pipeidea.realist.schemas import CreativeSample, to_json_dict


async def evaluate_case(
    case,
    *,
    cfg,
    profile: str,
    provider_name: str,
    evaluator_provider_name: str | None,
    rubric_text: str,
    semaphore,
    active_dir,
    fallback_dir,
):
    async with semaphore:
        try:
            result = await run_creative_with_trace(
                seeds=case.seeds,
                mode=case.mode,
                profile=profile,
                provider_name=provider_name,
                wild=False,
                cfg=cfg,
                random_stimulus_override=case.stimulus,
                garden_echoes=case.garden_echoes,
                web_stimuli=case.web_stimuli,
                active_profile_dir=active_dir,
                default_profile_dir=fallback_dir,
            )
            sample = CreativeSample(
                run_id="heuristic-eval",
                case_id=case.id,
                mode=case.mode,
                seeds=case.seeds,
                stimulus=case.stimulus,
                requested_profile=profile,
                resolved_profile=result.trace.resolved_profile,
                output=result.output,
                error=None,
                trace=result.trace.__dict__,
                metadata=case.metadata,
            )
        except Exception as exc:
            sample = CreativeSample(
                run_id="heuristic-eval",
                case_id=case.id,
                mode=case.mode,
                seeds=case.seeds,
                stimulus=case.stimulus,
                requested_profile=profile,
                resolved_profile=profile,
                output="",
                error=str(exc),
                trace={
                    "requested_profile": profile,
                    "mode": case.mode,
                    "seeds": case.seeds,
                    "web_stimulus_count": len(case.web_stimuli),
                    "garden_echo_count": len(case.garden_echoes),
                    "prompt_sections": [],
                },
                metadata=case.metadata,
            )

        assessment = await assess_sample(
            sample=sample,
            rubric_text=rubric_text,
            cfg=cfg,
            provider_name=evaluator_provider_name,
        )
        return sample, assessment


async def run_pack_heuristic(
    *,
    pack: str,
    provider: str,
    profile: str,
    concurrency: int,
    evaluator_provider: str | None = None,
    rubric: str = "realist",
    output: str | None = None,
) -> dict:
    cfg = load_config()
    _, _, cases = resolve_seed_pack(pack)
    active_dir, fallback_dir = resolve_profile_dirs(cfg, profile)
    semaphore = asyncio.Semaphore(concurrency)
    rubric_text = ""
    if evaluator_provider:
        _, _, rubric_text = resolve_rubric(rubric)

    tasks = [
        evaluate_case(
            case,
            cfg=cfg,
            profile=profile,
            provider_name=provider,
            evaluator_provider_name=evaluator_provider,
            rubric_text=rubric_text,
            semaphore=semaphore,
            active_dir=active_dir,
            fallback_dir=fallback_dir,
        )
        for case in cases
    ]

    results = await asyncio.gather(*tasks)
    samples = [sample for sample, _ in results]
    assessments = [assessment for _, assessment in results]

    tag_counts = Counter(tag for assessment in assessments for tag in assessment.failure_tags)
    avg_overall = sum(item.overall_score for item in assessments) / max(1, len(assessments))
    avg_profile = sum(item.profile_match_score for item in assessments) / max(1, len(assessments))
    avg_mode = sum(item.mode_match_score for item in assessments) / max(1, len(assessments))
    avg_topic = (
        sum(item.axis_scores.get("topic_discipline", 0.0) for item in assessments) / max(1, len(assessments))
    )

    summary = {
        "sample_count": len(cases),
        "average_overall_score": avg_overall,
        "average_profile_match": avg_profile,
        "average_mode_match": avg_mode,
        "average_topic_discipline": avg_topic,
        "top_failure_tags": tag_counts.most_common(10),
        "drifts_off_topic_cases": [
            {
                "case_id": assessment.case_id,
                "mode": sample.mode,
                "topic_discipline": assessment.axis_scores.get("topic_discipline", 0.0),
                "issues": assessment.issues,
                "failure_tags": assessment.failure_tags,
            }
            for sample, assessment in results
            if "drifts_off_topic" in assessment.failure_tags
        ][:20],
        "pipeline_errors": [
            {"case_id": sample.case_id, "error": sample.error}
            for sample in samples
            if sample.error
        ][:20],
    }

    payload = {
        "summary": summary,
        "assessments": [to_json_dict(item) for item in assessments],
    }
    if output:
        output_path = Path(output)
        output_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2))
        samples_path = output_path.with_name("samples.jsonl")
        assessments_path = output_path.with_name("realist.jsonl")
        samples_path.write_text(
            "".join(json.dumps(to_json_dict(item), ensure_ascii=True, sort_keys=True) + "\n" for item in samples),
            encoding="utf-8",
        )
        assessments_path.write_text(
            "".join(json.dumps(to_json_dict(item), ensure_ascii=True, sort_keys=True) + "\n" for item in assessments),
            encoding="utf-8",
        )
    return payload


async def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("pack")
    parser.add_argument("--provider", default="deepseek")
    parser.add_argument("--profile", default="default")
    parser.add_argument("--concurrency", type=int, default=5)
    parser.add_argument("--evaluator-provider", default=None)
    parser.add_argument("--rubric", default="realist")
    parser.add_argument("--output", required=True)
    args = parser.parse_args()

    await run_pack_heuristic(
        pack=args.pack,
        provider=args.provider,
        profile=args.profile,
        concurrency=args.concurrency,
        evaluator_provider=args.evaluator_provider,
        rubric=args.rubric,
        output=args.output,
    )


if __name__ == "__main__":
    asyncio.run(main())
