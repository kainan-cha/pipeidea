"""Schemas used by the calibration and evaluator tooling."""

from dataclasses import asdict, dataclass, field, is_dataclass
from pathlib import Path
from typing import Any


def clamp_score(value: float | int | None, default: float = 0.0) -> float:
    """Clamp a score into the 0..1 range."""
    if value is None:
        return default
    return max(0.0, min(1.0, float(value)))


def to_json_dict(value: Any) -> Any:
    """Convert dataclasses and pathlib objects into JSON-safe values."""
    if is_dataclass(value):
        return to_json_dict(asdict(value))
    if isinstance(value, Path):
        return str(value)
    if isinstance(value, dict):
        return {str(key): to_json_dict(item) for key, item in value.items()}
    if isinstance(value, list | tuple | set):
        return [to_json_dict(item) for item in value]
    return value


@dataclass(frozen=True)
class IdeaNote:
    """Short note about an alive or dead idea in a sample."""

    title: str
    why: str

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "IdeaNote":
        return cls(
            title=str(data.get("title", "")).strip(),
            why=str(data.get("why", "")).strip(),
        )


@dataclass(frozen=True)
class SeedCase:
    """A single benchmark case."""

    id: str
    mode: str
    seeds: list[str]
    stimulus: str | None = None
    notes: str = ""
    web_stimuli: list[str] = field(default_factory=list)
    garden_echoes: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "SeedCase":
        return cls(
            id=str(data["id"]),
            mode=str(data["mode"]),
            seeds=[str(seed) for seed in data.get("seeds", [])],
            stimulus=data.get("stimulus"),
            notes=str(data.get("notes", "")),
            web_stimuli=[str(item) for item in data.get("web_stimuli", [])],
            garden_echoes=[str(item) for item in data.get("garden_echoes", [])],
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True)
class RunManifest:
    """Top-level metadata for a calibration run."""

    run_id: str
    created_at: str
    finished_at: str | None
    status: str
    pack_name: str
    pack_path: str
    profile: str
    provider_name: str | None
    evaluator_provider_name: str | None
    rubric_path: str | None
    realist_enabled: bool
    temperature: float | None
    candidate_label: str | None
    profile_dir: str | None
    default_dir: str | None
    sample_count: int
    notes: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RunManifest":
        return cls(
            run_id=str(data["run_id"]),
            created_at=str(data["created_at"]),
            finished_at=data.get("finished_at"),
            status=str(data.get("status", "unknown")),
            pack_name=str(data.get("pack_name", "")),
            pack_path=str(data.get("pack_path", "")),
            profile=str(data.get("profile", "")),
            provider_name=data.get("provider_name"),
            evaluator_provider_name=data.get("evaluator_provider_name"),
            rubric_path=data.get("rubric_path"),
            realist_enabled=bool(data.get("realist_enabled", False)),
            temperature=data.get("temperature"),
            candidate_label=data.get("candidate_label"),
            profile_dir=data.get("profile_dir"),
            default_dir=data.get("default_dir"),
            sample_count=int(data.get("sample_count", 0)),
            notes=[str(item) for item in data.get("notes", [])],
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True)
class CreativeSample:
    """One generated output plus the trace used to create it."""

    run_id: str
    case_id: str
    mode: str
    seeds: list[str]
    stimulus: str | None
    requested_profile: str
    resolved_profile: str
    output: str
    error: str | None
    trace: dict[str, Any]
    notes: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "CreativeSample":
        return cls(
            run_id=str(data["run_id"]),
            case_id=str(data["case_id"]),
            mode=str(data.get("mode", "")),
            seeds=[str(seed) for seed in data.get("seeds", [])],
            stimulus=data.get("stimulus"),
            requested_profile=str(data.get("requested_profile", "")),
            resolved_profile=str(data.get("resolved_profile", "")),
            output=str(data.get("output", "")),
            error=data.get("error"),
            trace=dict(data.get("trace", {})),
            notes=[str(item) for item in data.get("notes", [])],
            metadata=dict(data.get("metadata", {})),
        )


@dataclass(frozen=True)
class RealistAssessment:
    """Structured evaluator output for one sample."""

    run_id: str
    case_id: str
    evaluation_mode: str
    mechanical_status: str
    overall_score: float
    profile_match_score: float
    mode_match_score: float
    axis_scores: dict[str, float]
    strengths: list[str]
    issues: list[str]
    failure_tags: list[str]
    alive_ideas: list[IdeaNote]
    dead_ideas: list[IdeaNote]
    likely_files_to_tune: list[str]
    suggested_edit_direction: list[str]
    confidence: float
    notes: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "RealistAssessment":
        return cls(
            run_id=str(data["run_id"]),
            case_id=str(data["case_id"]),
            evaluation_mode=str(data.get("evaluation_mode", "unknown")),
            mechanical_status=str(data.get("mechanical_status", "unknown")),
            overall_score=clamp_score(data.get("overall_score")),
            profile_match_score=clamp_score(data.get("profile_match_score")),
            mode_match_score=clamp_score(data.get("mode_match_score")),
            axis_scores={
                str(key): clamp_score(value)
                for key, value in dict(data.get("axis_scores", {})).items()
            },
            strengths=[str(item) for item in data.get("strengths", [])],
            issues=[str(item) for item in data.get("issues", [])],
            failure_tags=[str(item) for item in data.get("failure_tags", [])],
            alive_ideas=[IdeaNote.from_dict(item) for item in data.get("alive_ideas", [])],
            dead_ideas=[IdeaNote.from_dict(item) for item in data.get("dead_ideas", [])],
            likely_files_to_tune=[
                str(item) for item in data.get("likely_files_to_tune", [])
            ],
            suggested_edit_direction=[
                str(item) for item in data.get("suggested_edit_direction", [])
            ],
            confidence=clamp_score(data.get("confidence")),
            notes=[str(item) for item in data.get("notes", [])],
        )


@dataclass(frozen=True)
class ComparisonReport:
    """Aggregate comparison between a baseline and candidate run."""

    baseline_run_id: str
    candidate_run_id: str
    shared_case_count: int
    average_overall_delta: float
    average_axis_deltas: dict[str, float]
    failure_tag_deltas: dict[str, int]
    mechanical_regressions: list[str]
    improved_cases: list[dict[str, Any]]
    regressed_cases: list[dict[str, Any]]
    acceptance_recommendation: str
    notes: list[str] = field(default_factory=list)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> "ComparisonReport":
        return cls(
            baseline_run_id=str(data["baseline_run_id"]),
            candidate_run_id=str(data["candidate_run_id"]),
            shared_case_count=int(data.get("shared_case_count", 0)),
            average_overall_delta=float(data.get("average_overall_delta", 0.0)),
            average_axis_deltas={
                str(key): float(value)
                for key, value in dict(data.get("average_axis_deltas", {})).items()
            },
            failure_tag_deltas={
                str(key): int(value)
                for key, value in dict(data.get("failure_tag_deltas", {})).items()
            },
            mechanical_regressions=[
                str(item) for item in data.get("mechanical_regressions", [])
            ],
            improved_cases=[dict(item) for item in data.get("improved_cases", [])],
            regressed_cases=[dict(item) for item in data.get("regressed_cases", [])],
            acceptance_recommendation=str(data.get("acceptance_recommendation", "review")),
            notes=[str(item) for item in data.get("notes", [])],
        )


@dataclass(frozen=True)
class PromotionRecord:
    """Versioned metadata for an accepted or rejected calibration proposal."""

    version: str
    profile: str
    run_id: str
    commit: str
    benchmark_pack: list[str]
    realist_rubric: str
    provider: str
    model: str
    hypothesis: str
    touched_files: list[str]
    accepted: bool
    notes: str = ""
