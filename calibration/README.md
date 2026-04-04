# Calibration

This folder holds the repo-managed side of Pipeidea's tuning system.

## Layout

- `rubrics/` contains evaluator prompts such as `realist.md`
- `seed_packs/` contains versioned benchmark packs in JSONL
- `decisions/` contains human decision logs per profile
- `versions/` contains versioned promotion records per profile

Raw run artifacts do not live here by default. They are written under `PIPEIDEA_HOME/calibration/runs/`.

## Intended Flow

1. Run `pipeidea calibrate run`.
2. Inspect the generated `summary.md`.
3. Tune the smallest relevant markdown files.
4. Re-run against the same pack.
5. Use `pipeidea calibrate compare`.
6. If accepted, record the promotion with `pipeidea calibrate promote`.
