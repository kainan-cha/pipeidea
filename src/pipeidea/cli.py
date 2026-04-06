"""pipeidea CLI — the entry point."""

import asyncio
from typing import Optional

import typer
from rich.console import Console
from rich.markdown import Markdown

from pipeidea.realist.artifacts import find_run_dir, write_json
from pipeidea.realist.compare import compare_runs, render_comparison_markdown
from pipeidea.realist.runner import (
    DEFAULT_RUBRIC_NAME,
    run_calibration,
    summarize_run_artifacts,
    write_promotion_record,
)
from pipeidea.config import load_config
from pipeidea.core import run_creative
from pipeidea.soul.profiles import ensure_defaults, list_profiles, create_profile, load_full_profile
from pipeidea.web import serve_web_ui

app = typer.Typer(
    name="pipeidea",
    help="AI-powered wild idea generator. Pipe dream + idea.",
    no_args_is_help=True,
)
console = Console()

# --- Profile subcommand ---

profile_app = typer.Typer(help="Manage agent profiles.")
app.add_typer(profile_app, name="profile")

calibrate_app = typer.Typer(help="Run internal calibration and comparison flows.")
app.add_typer(calibrate_app, name="calibrate")


@profile_app.command("list")
def profile_list():
    """List available profiles."""
    cfg = load_config()
    ensure_defaults(cfg)
    profiles = list_profiles(cfg)
    for p in profiles:
        marker = " (default)" if p == cfg.default_profile else ""
        console.print(f"  {p}{marker}")


@profile_app.command("create")
def profile_create(name: str):
    """Scaffold a new profile (inherits everything from default)."""
    cfg = load_config()
    ensure_defaults(cfg)
    path = create_profile(cfg, name)
    console.print(f"Created profile '{name}' at {path}")
    console.print("Edit markdown files to override default behavior. Missing files inherit from default/.")


@profile_app.command("show")
def profile_show(name: str):
    """Show the merged soul for a profile (resolved inheritance)."""
    cfg = load_config()
    ensure_defaults(cfg)
    files = load_full_profile(cfg, name)
    if not files:
        console.print(f"Profile '{name}' not found.", style="red")
        raise typer.Exit(1)
    for filename, content in sorted(files.items()):
        console.rule(filename)
        console.print(Markdown(content))


# --- Creative commands ---


async def _run_creative(
    seeds: list[str],
    mode: str,
    profile: str,
    provider_name: str | None,
    wild: bool,
    single_pass: bool = False,
):
    """Core creative flow: compose prompt, call provider, stream output."""
    console.print()
    try:
        await run_creative(
            seeds=seeds,
            mode=mode,
            profile=profile,
            provider_name=provider_name,
            wild=wild,
            on_chunk=lambda chunk: console.print(chunk, end="", highlight=False),
            single_pass=single_pass,
        )
    except Exception as e:
        console.print(f"\n\nError: {e}", style="red")
        raise typer.Exit(1)
    console.print("\n")


@app.command()
def bloom(
    seed: str = typer.Argument(help="The seed to bloom from — a word, phrase, concept, or question."),
    profile: Optional[str] = typer.Option(None, "-P", "--profile", help="Agent profile to use."),
    provider: Optional[str] = typer.Option(None, "-p", "--provider", help="AI provider."),
    wild: bool = typer.Option(False, "-w", "--wild", help="Maximum chaos. Drop all restraint."),
    forage: bool = typer.Option(False, "--forage", help="Also forage the web for stimuli."),
    single_pass: bool = typer.Option(False, "--single-pass", help="Skip 3-stage pipeline, use single-pass generation."),
):
    """Bloom mode: give a seed, get wild ideas."""
    cfg = load_config()
    mode = "forage" if forage else "bloom"
    asyncio.run(_run_creative([seed], mode, profile or cfg.default_profile, provider, wild, single_pass))


@app.command()
def collide(
    seed1: str = typer.Argument(help="First input."),
    seed2: str = typer.Argument(help="Second input."),
    profile: Optional[str] = typer.Option(None, "-P", "--profile", help="Agent profile to use."),
    provider: Optional[str] = typer.Option(None, "-p", "--provider", help="AI provider."),
    wild: bool = typer.Option(False, "-w", "--wild", help="Maximum chaos."),
    single_pass: bool = typer.Option(False, "--single-pass", help="Skip 3-stage pipeline, use single-pass generation."),
):
    """Collision mode: smash two unrelated inputs together."""
    cfg = load_config()
    asyncio.run(
        _run_creative([seed1, seed2], "collision", profile or cfg.default_profile, provider, wild, single_pass)
    )


@app.command()
def web(
    host: str = typer.Option("127.0.0.1", "--host", help="Host interface to bind."),
    port: int = typer.Option(8000, "--port", help="Port to listen on."),
):
    """Run the keyboard-driven web UI."""
    try:
        serve_web_ui(host=host, port=port)
    except KeyboardInterrupt:
        console.print("\nShutting down web UI.")


@calibrate_app.command("run")
def calibrate_run_command(
    pack: str = typer.Argument(help="Seed pack name or path."),
    profile: Optional[str] = typer.Option(None, "-P", "--profile", help="Profile to evaluate."),
    provider: Optional[str] = typer.Option(None, "-p", "--provider", help="Generation provider."),
    evaluator_provider: Optional[str] = typer.Option(
        None,
        "--evaluator-provider",
        help="Optional provider for `realist`. Defaults to PIPEIDEA_REALIST_PROVIDER or the generation provider.",
    ),
    rubric: str = typer.Option(DEFAULT_RUBRIC_NAME, "--rubric", help="Rubric name or path."),
    profile_dir: Optional[str] = typer.Option(
        None,
        "--profile-dir",
        help="Optional explicit profile directory to read instead of ~/.pipeidea.",
    ),
    default_dir: Optional[str] = typer.Option(
        None,
        "--default-dir",
        help="Optional explicit fallback default profile directory.",
    ),
    output_dir: Optional[str] = typer.Option(
        None,
        "--output-dir",
        help="Optional explicit directory for this run's artifacts.",
    ),
    candidate_label: Optional[str] = typer.Option(
        None,
        "--candidate-label",
        help="Label used in the run id and manifest.",
    ),
    temperature: Optional[float] = typer.Option(
        None,
        "--temperature",
        help="Override generation temperature for this run.",
    ),
    wild: bool = typer.Option(False, "--wild", help="Raise temperature like the creative CLI."),
    realist: bool = typer.Option(
        True,
        "--realist/--no-realist",
        help="Enable or disable evaluator scoring.",
    ),
):
    """Run a calibration pack and write artifacts."""
    cfg = load_config()
    selected_profile = profile or cfg.default_profile
    try:
        manifest, run_dir = asyncio.run(
            run_calibration(
                pack=pack,
                profile=selected_profile,
                provider_name=provider,
                evaluator_provider_name=evaluator_provider,
                rubric=rubric,
                profile_dir=profile_dir,
                default_dir=default_dir,
                output_dir=output_dir,
                candidate_label=candidate_label,
                temperature=temperature,
                realist_enabled=realist,
                wild=wild,
                progress=lambda message: console.print(message),
            )
        )
    except Exception as exc:
        console.print(f"Calibration failed: {exc}", style="red")
        raise typer.Exit(1)

    console.print(f"Run: {manifest.run_id}")
    console.print(f"Artifacts: {run_dir}")
    console.print(Markdown((run_dir / "summary.md").read_text()))


@calibrate_app.command("summarize")
def calibrate_summarize_command(
    run_ref: str = typer.Argument(help="Run id or explicit run directory."),
):
    """Render the summary for an existing run."""
    cfg = load_config()
    try:
        run_dir = find_run_dir(cfg, run_ref)
        summary = summarize_run_artifacts(run_dir)
    except Exception as exc:
        console.print(f"Unable to summarize run: {exc}", style="red")
        raise typer.Exit(1)

    console.print(Markdown(summary))


@calibrate_app.command("compare")
def calibrate_compare_command(
    baseline: str = typer.Argument(help="Baseline run id or directory."),
    candidate: str = typer.Argument(help="Candidate run id or directory."),
):
    """Compare two completed runs."""
    cfg = load_config()
    try:
        baseline_dir = find_run_dir(cfg, baseline)
        candidate_dir = find_run_dir(cfg, candidate)
        report = compare_runs(baseline_dir, candidate_dir)
        compare_dir = candidate_dir / "compare"
        compare_dir.mkdir(parents=True, exist_ok=True)
        report_path = compare_dir / f"{report.baseline_run_id}.json"
        summary_path = compare_dir / f"{report.baseline_run_id}.md"
        write_json(report_path, report)
        summary_path.write_text(render_comparison_markdown(report))
    except Exception as exc:
        console.print(f"Unable to compare runs: {exc}", style="red")
        raise typer.Exit(1)

    console.print(f"Comparison report: {report_path}")
    console.print(Markdown(summary_path.read_text()))


@calibrate_app.command("promote")
def calibrate_promote_command(
    run_ref: str = typer.Argument(help="Run id or directory to promote."),
    version: str = typer.Argument(help="Version tag for the record, e.g. 0.3.1."),
    hypothesis: str = typer.Option(..., "--hypothesis", help="One-line tuning hypothesis."),
    touched_file: Optional[list[str]] = typer.Option(
        None,
        "--touched-file",
        help="Repeat to record which profile files were intentionally edited.",
    ),
    accept: bool = typer.Option(
        True,
        "--accept/--reject",
        help="Whether this promotion record represents an accepted or rejected candidate.",
    ),
):
    """Write a promotion record into calibration/versions and calibration/decisions."""
    cfg = load_config()
    try:
        run_dir = find_run_dir(cfg, run_ref)
        record_path = write_promotion_record(
            run_dir=run_dir,
            version=version,
            hypothesis=hypothesis,
            touched_files=touched_file or [],
            accepted=accept,
        )
    except Exception as exc:
        console.print(f"Unable to write promotion record: {exc}", style="red")
        raise typer.Exit(1)

    console.print(f"Promotion record: {record_path}")


if __name__ == "__main__":
    app()
