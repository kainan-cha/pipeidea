"""Artifact IO helpers for calibration runs."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from pipeidea.calibration.schemas import to_json_dict
from pipeidea.config import Config


def artifact_paths(run_dir: Path) -> dict[str, Path]:
    """Return the standard artifact paths for a run directory."""
    return {
        "manifest": run_dir / "manifest.json",
        "samples": run_dir / "samples.jsonl",
        "realist": run_dir / "realist.jsonl",
        "summary": run_dir / "summary.md",
        "compare_dir": run_dir / "compare",
    }


def ensure_directory(path: Path) -> Path:
    """Create a directory if it does not already exist."""
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_json(path: Path, data: Any) -> None:
    """Write JSON with deterministic formatting."""
    ensure_directory(path.parent)
    path.write_text(
        json.dumps(to_json_dict(data), indent=2, ensure_ascii=True, sort_keys=True) + "\n"
    )


def append_jsonl(path: Path, data: Any) -> None:
    """Append a JSONL record."""
    ensure_directory(path.parent)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(to_json_dict(data), ensure_ascii=True, sort_keys=True) + "\n")


def load_json(path: Path) -> dict[str, Any]:
    """Load a JSON file into a dictionary."""
    return json.loads(path.read_text())


def load_jsonl(path: Path) -> list[dict[str, Any]]:
    """Load a JSONL file into a list of dictionaries."""
    if not path.exists():
        return []
    records = []
    for line in path.read_text().splitlines():
        if line.strip():
            records.append(json.loads(line))
    return records


def find_run_dir(cfg: Config, run_ref: str | Path) -> Path:
    """Resolve a run id or explicit path into a directory."""
    run_path = Path(run_ref)
    if run_path.exists():
        return run_path

    candidate = cfg.calibration_runs_dir / str(run_ref)
    if candidate.exists():
        return candidate

    raise FileNotFoundError(f"Calibration run not found: {run_ref}")

