# Drift And Quality Fix Loop

This plan turns the current ad hoc debugging into a staged unattended loop.

## Objective

Reduce the following failure modes without collapsing ambition or vividness:

- `drifts_off_topic`
- `randomness_absent`
- `format_drift`
- `too_many_ideas`
- `generic_futurism`
- `surface_analogy`

## Iterations

### 1. Measurement Layer

Ship focused pack families, suite config, and automated reporting before major prompt tuning.

Deliverables:

- focused packs under `calibration/seed_packs/`
- suite definition under `calibration/suites/`
- scripts:
  - `scripts/build_eval_pack.py`
  - `scripts/run_eval_suite.py`
  - `scripts/run_heuristic_eval.py`

Exit criteria:

- suite runner produces machine-readable reports
- focused packs run end-to-end
- evaluator exposes `topic_discipline`

### 2. Output Discipline

Primary targets:

- `format_drift`
- `too_many_ideas`

Files to tune first:

- `src/pipeidea/profiles/default/output.md`
- `src/pipeidea/profiles/default/protocol.md`
- `src/pipeidea/profiles/default/taste.md`

Acceptance:

- `format_v1` and `discipline_v1` both improve on `output_contract`
- `format_drift` and `too_many_ideas` counts fall

### 3. Topic Discipline And Randomness

Primary targets:

- `drifts_off_topic`
- `randomness_absent`
- randomness-induced derailment

Files to tune first:

- `src/pipeidea/profiles/default/randomness.md`
- `src/pipeidea/profiles/default/knowledge.md`
- `src/pipeidea/profiles/default/protocol.md`
- runtime guidance in `src/pipeidea/core.py`

Acceptance:

- `discipline_v1` average `topic_discipline` improves
- `randomness_v1` shows fewer absent or derailing stimulus failures

### 4. Anti-Slop And Structural Quality

Primary targets:

- `generic_futurism`
- `surface_analogy`

Files to tune first:

- `src/pipeidea/profiles/default/taste.md`
- `src/pipeidea/profiles/default/ambition.md`
- `src/pipeidea/profiles/default/techniques.md`

Acceptance:

- `anti_slop_v1` improves on `structural_depth`
- counts of `generic_futurism` and `surface_analogy` drop

### 5. Final Validation

Run one AI-backed 200-case acceptance pack and compare against the baseline candidate.

Recommended composition:

- 60 from `discipline_v1`
- 40 from `randomness_v1`
- 30 from `format_v1`
- 30 from `anti_slop_v1`
- 40 from `fuzz_1000_v1`

Build command:

```bash
env PYTHONPATH=/Users/kainan/projects/pipe_idea/src \
  /Users/kainan/projects/pipe_idea/.venv/bin/python \
  /Users/kainan/projects/pipe_idea/scripts/build_eval_pack.py \
  --output /tmp/final_acceptance_200.jsonl \
  --source discipline_v1 15 \
  --source randomness_v1 12 \
  --source format_v1 8 \
  --source anti_slop_v1 10 \
  --source fuzz_1000_v1 40
```

Note:

The current focused packs are starter packs, not yet large enough to yield the full 200-case mix on their own. Expand each family before final acceptance so the final 200-case run does not repeat cases.

Acceptance gates:

- no increase in `pipeline_bug`
- lower counts for:
  - `drifts_off_topic`
  - `format_drift`
  - `too_many_ideas`
  - `generic_futurism`
  - `surface_analogy`
- no regression in `topic_discipline`, `output_contract`, or `structural_depth`
- no obvious collapse in ambition or vividness

## Operating Rule

Do not promote a candidate solely because overall score rises.

If `overall_score` improves while any of the primary failure counts regress, reject the candidate and keep tuning.
