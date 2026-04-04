"""Profile management: list, create, resolve inheritance, bootstrap defaults."""

import shutil
from dataclasses import dataclass
from pathlib import Path

from pipeidea.config import Config

# All possible soul files in a complete profile
SOUL_FILES = [
    "identity.md",
    "taste.md",
    "ambition.md",
    "knowledge.md",
    "randomness.md",
    "techniques.md",
    "protocol.md",
    "dialogue.md",
    "output.md",
    "modes/bloom.md",
    "modes/collision.md",
    "modes/forage.md",
    "modes/revisit.md",
]

# Path to built-in defaults shipped with the package
_DEFAULTS_DIR = Path(__file__).parent / "defaults" / "profiles"


@dataclass(frozen=True)
class ResolvedSoulFile:
    """A resolved soul file with source metadata."""

    filename: str
    content: str
    source_profile: str
    source_path: Path


@dataclass(frozen=True)
class ProfileSnapshot:
    """A merged profile view with file provenance."""

    profile: str
    files: dict[str, ResolvedSoulFile]
    active_profile_dir: Path
    default_profile_dir: Path | None


def ensure_defaults(cfg: Config) -> None:
    """Copy built-in default profiles to ~/.pipeidea/profiles/ if they don't exist."""
    profiles_dir = cfg.profiles_dir
    default_dir = profiles_dir / "default"

    if default_dir.exists():
        return

    # Copy the entire defaults directory
    if _DEFAULTS_DIR.exists():
        shutil.copytree(_DEFAULTS_DIR, profiles_dir, dirs_exist_ok=True)


def list_profiles(cfg: Config) -> list[str]:
    """Return names of all available profiles."""
    profiles_dir = cfg.profiles_dir
    if not profiles_dir.exists():
        return []
    return sorted(
        d.name for d in profiles_dir.iterdir() if d.is_dir() and not d.name.startswith(".")
    )


def _resolve_profile_dirs(
    cfg: Config,
    profile: str,
    active_profile_dir: Path | None = None,
    default_profile_dir: Path | None = None,
) -> tuple[Path, Path | None]:
    """Resolve active/fallback profile directories."""
    active_dir = active_profile_dir or cfg.profiles_dir / profile

    fallback_dir: Path | None = None
    if profile != "default":
        fallback_dir = default_profile_dir or cfg.profiles_dir / "default"
    elif default_profile_dir is not None:
        fallback_dir = default_profile_dir

    return active_dir, fallback_dir


def resolve_profile_entry(
    cfg: Config,
    profile: str,
    filename: str,
    active_profile_dir: Path | None = None,
    default_profile_dir: Path | None = None,
) -> ResolvedSoulFile | None:
    """Resolve a soul file with provenance metadata."""
    if active_profile_dir is None and default_profile_dir is None:
        ensure_defaults(cfg)

    active_dir, fallback_dir = _resolve_profile_dirs(
        cfg=cfg,
        profile=profile,
        active_profile_dir=active_profile_dir,
        default_profile_dir=default_profile_dir,
    )

    active_path = active_dir / filename
    if active_path.exists():
        return ResolvedSoulFile(
            filename=filename,
            content=active_path.read_text(),
            source_profile=profile,
            source_path=active_path,
        )

    if fallback_dir is not None:
        fallback_path = fallback_dir / filename
        if fallback_path.exists():
            return ResolvedSoulFile(
                filename=filename,
                content=fallback_path.read_text(),
                source_profile="default",
                source_path=fallback_path,
            )

    return None


def resolve_profile_file(cfg: Config, profile: str, filename: str) -> str | None:
    """Read a soul file from a profile, falling back to default/ if missing.

    Returns the file content as a string, or None if not found anywhere.
    """
    entry = resolve_profile_entry(cfg, profile, filename)
    return entry.content if entry is not None else None


def load_full_profile(cfg: Config, profile: str) -> dict[str, str]:
    """Load all soul files for a profile, resolving inheritance from default/.

    Returns a dict mapping filename -> content.
    """
    result = {}
    for filename in SOUL_FILES:
        content = resolve_profile_file(cfg, profile, filename)
        if content is not None:
            result[filename] = content
    return result


def load_profile_snapshot(
    cfg: Config,
    profile: str,
    active_profile_dir: Path | None = None,
    default_profile_dir: Path | None = None,
) -> ProfileSnapshot:
    """Load a profile with provenance for each resolved file."""
    if active_profile_dir is None and default_profile_dir is None:
        ensure_defaults(cfg)

    active_dir, fallback_dir = _resolve_profile_dirs(
        cfg=cfg,
        profile=profile,
        active_profile_dir=active_profile_dir,
        default_profile_dir=default_profile_dir,
    )

    files: dict[str, ResolvedSoulFile] = {}
    for filename in SOUL_FILES:
        entry = resolve_profile_entry(
            cfg=cfg,
            profile=profile,
            filename=filename,
            active_profile_dir=active_dir,
            default_profile_dir=fallback_dir,
        )
        if entry is not None:
            files[filename] = entry

    return ProfileSnapshot(
        profile=profile,
        files=files,
        active_profile_dir=active_dir,
        default_profile_dir=fallback_dir,
    )


def create_profile(cfg: Config, name: str) -> Path:
    """Scaffold a new profile directory. Starts empty (inherits everything from default)."""
    profile_dir = cfg.profiles_dir / name
    profile_dir.mkdir(parents=True, exist_ok=True)
    (profile_dir / "modes").mkdir(exist_ok=True)
    return profile_dir
