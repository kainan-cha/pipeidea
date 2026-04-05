"""Configuration loader for pipeidea."""

import os
from dataclasses import dataclass, field
from pathlib import Path


def _pipeidea_home() -> Path:
    """Return ~/.pipeidea, creating it if needed."""
    home = Path(os.environ.get("PIPEIDEA_HOME", Path.home() / ".pipeidea"))
    home.mkdir(parents=True, exist_ok=True)
    return home


@dataclass
class Config:
    home: Path = field(default_factory=_pipeidea_home)

    # AI provider
    default_provider: str = "deepseek"
    anthropic_api_key: str = ""
    openai_api_key: str = ""
    google_api_key: str = ""
    deepseek_api_key: str = ""
    deepseek_base_url: str = "https://api.deepseek.com/v1"
    deepseek_model: str = "deepseek-chat"

    # Profile
    default_profile: str = "default"

    # Generation
    temperature: float = 0.9

    # Calibration
    default_realist_provider: str = ""

    @property
    def profiles_dir(self) -> Path:
        d = self.home / "profiles"
        d.mkdir(parents=True, exist_ok=True)
        return d

    @property
    def calibration_dir(self) -> Path:
        raw = os.environ.get("PIPEIDEA_CALIBRATION_DIR")
        directory = Path(raw) if raw else self.home / "calibration"
        directory.mkdir(parents=True, exist_ok=True)
        return directory

    @property
    def calibration_runs_dir(self) -> Path:
        directory = self.calibration_dir / "runs"
        directory.mkdir(parents=True, exist_ok=True)
        return directory


def load_config() -> Config:
    """Load config from environment variables.

    Env vars:
        PIPEIDEA_HOME         — override ~/.pipeidea
        PIPEIDEA_PROVIDER     — default AI provider
        ANTHROPIC_API_KEY     — Anthropic API key
        OPENAI_API_KEY        — OpenAI API key
        GOOGLE_API_KEY        — Google AI API key
        DEEPSEEK_API_KEY      — DeepSeek API key
        DEEPSEEK_BASE_URL     — DeepSeek base URL (default: https://api.deepseek.com/v1)
        DEEPSEEK_MODEL        — DeepSeek model name (default: deepseek-chat)
        AI_PROVIDER           — alias for PIPEIDEA_PROVIDER
        PIPEIDEA_PROFILE      — default profile name
        PIPEIDEA_TEMPERATURE  — generation temperature (0.0-2.0)
        PIPEIDEA_REALIST_PROVIDER — default evaluator provider
        PIPEIDEA_CALIBRATION_DIR  — location for calibration run artifacts
    """
    cfg = Config()
    cfg.default_provider = os.environ.get(
        "PIPEIDEA_PROVIDER",
        os.environ.get("AI_PROVIDER", cfg.default_provider),
    )
    cfg.anthropic_api_key = os.environ.get("ANTHROPIC_API_KEY", "")
    cfg.openai_api_key = os.environ.get("OPENAI_API_KEY", "")
    cfg.google_api_key = os.environ.get("GOOGLE_API_KEY", "")
    cfg.deepseek_api_key = os.environ.get("DEEPSEEK_API_KEY", "")
    cfg.deepseek_base_url = os.environ.get("DEEPSEEK_BASE_URL", cfg.deepseek_base_url)
    cfg.deepseek_model = os.environ.get("DEEPSEEK_MODEL", cfg.deepseek_model)
    cfg.default_profile = os.environ.get("PIPEIDEA_PROFILE", cfg.default_profile)
    cfg.default_realist_provider = os.environ.get(
        "PIPEIDEA_REALIST_PROVIDER",
        cfg.default_realist_provider,
    )

    temp = os.environ.get("PIPEIDEA_TEMPERATURE")
    if temp:
        cfg.temperature = float(temp)

    return cfg
