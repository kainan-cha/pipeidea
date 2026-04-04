"""Shared application logic for CLI and web entry points."""

from dataclasses import dataclass, replace
from hashlib import sha256
from pathlib import Path
from collections.abc import Callable

from pipeidea.config import Config, load_config
from pipeidea.providers.registry import get_provider
from pipeidea.soul.composer import compose_prompt, compose_user_message
from pipeidea.soul.profiles import ensure_defaults
from pipeidea.soul.random_stimulus import get_random_stimulus


@dataclass(frozen=True)
class CreativeRunTrace:
    """Structured trace for a creative run."""

    requested_profile: str
    resolved_profile: str
    mode: str
    seeds: list[str]
    random_stimulus: str | None
    garden_echo_count: int
    web_stimulus_count: int
    user_message: str
    system_prompt_hash: str
    prompt_sections: list[dict[str, str | None]]
    provider_name: str
    provider_model: str | None
    temperature: float
    active_profile_dir: str | None
    default_profile_dir: str | None


@dataclass(frozen=True)
class CreativeRunResult:
    """Output plus trace metadata for calibration and debugging."""

    output: str
    trace: CreativeRunTrace


async def run_creative_with_trace(
    seeds: list[str],
    mode: str,
    profile: str,
    provider_name: str | None,
    wild: bool,
    on_chunk: Callable[[str], None] | None = None,
    cfg: Config | None = None,
    random_stimulus_override: str | None = None,
    garden_echoes: list[str] | None = None,
    web_stimuli: list[str] | None = None,
    active_profile_dir: Path | None = None,
    default_profile_dir: Path | None = None,
    temperature_override: float | None = None,
) -> CreativeRunResult:
    """Run the core creative flow and return output plus trace metadata."""
    cfg = cfg or load_config()
    if active_profile_dir is None and default_profile_dir is None:
        ensure_defaults(cfg)

    runtime_cfg = replace(cfg)
    if temperature_override is not None:
        runtime_cfg.temperature = temperature_override
    elif wild:
        runtime_cfg.temperature = min(runtime_cfg.temperature + 0.3, 1.5)

    provider = get_provider(runtime_cfg, provider_name)

    stimulus = random_stimulus_override
    if stimulus is None:
        try:
            stimulus = get_random_stimulus()
        except Exception:
            stimulus = None

    prompt = compose_prompt(
        cfg=cfg,
        profile=profile,
        mode=mode,
        random_stimulus=stimulus,
        garden_echoes=garden_echoes,
        web_stimuli=web_stimuli,
        active_profile_dir=active_profile_dir,
        default_profile_dir=default_profile_dir,
    )
    user_message = compose_user_message(seeds, mode)
    messages = [{"role": "user", "content": user_message}]

    trace = CreativeRunTrace(
        requested_profile=profile,
        resolved_profile=profile,
        mode=mode,
        seeds=list(seeds),
        random_stimulus=stimulus,
        garden_echo_count=len(garden_echoes or []),
        web_stimulus_count=len(web_stimuli or []),
        user_message=user_message,
        system_prompt_hash=sha256(prompt.system_prompt.encode("utf-8")).hexdigest(),
        prompt_sections=[
            {
                "key": section.key,
                "title": section.title,
                "kind": section.kind,
                "source_profile": section.source_profile,
                "source_path": section.source_path,
                "content": section.content,
            }
            for section in prompt.sections
        ],
        provider_name=provider.name,
        provider_model=getattr(provider, "model", None),
        temperature=runtime_cfg.temperature,
        active_profile_dir=prompt.active_profile_dir,
        default_profile_dir=prompt.default_profile_dir,
    )

    chunks: list[str] = []
    async for chunk in provider.stream(prompt.system_prompt, messages):
        chunks.append(chunk)
        if on_chunk is not None:
            on_chunk(chunk)

    return CreativeRunResult(output="".join(chunks), trace=trace)


async def run_creative(
    seeds: list[str],
    mode: str,
    profile: str,
    provider_name: str | None,
    wild: bool,
    on_chunk: Callable[[str], None] | None = None,
) -> str:
    """Run the core creative flow and optionally stream chunks to a callback."""
    result = await run_creative_with_trace(
        seeds=seeds,
        mode=mode,
        profile=profile,
        provider_name=provider_name,
        wild=wild,
        on_chunk=on_chunk,
    )
    return result.output
