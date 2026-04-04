"""Provider discovery and instantiation."""

from pipeidea.config import Config
from pipeidea.providers.base import Provider

AVAILABLE_PROVIDERS = ["claude", "openai", "deepseek"]


def get_provider(cfg: Config, name: str | None = None) -> Provider:
    """Get an AI provider by name, defaulting to config.default_provider."""
    name = name or cfg.default_provider

    match name:
        case "claude":
            from pipeidea.providers.claude import ClaudeProvider

            if not cfg.anthropic_api_key:
                raise ValueError(
                    "ANTHROPIC_API_KEY not set. "
                    "Export it: export ANTHROPIC_API_KEY=sk-ant-..."
                )
            return ClaudeProvider(
                api_key=cfg.anthropic_api_key,
                temperature=cfg.temperature,
            )
        case "openai":
            from pipeidea.providers.openai_compat import OpenAICompatProvider

            if not cfg.openai_api_key:
                raise ValueError(
                    "OPENAI_API_KEY not set. "
                    "Export it: export OPENAI_API_KEY=sk-..."
                )
            return OpenAICompatProvider(
                api_key=cfg.openai_api_key,
                model="gpt-4o",
                temperature=cfg.temperature,
                provider_name="openai",
            )
        case "deepseek":
            from pipeidea.providers.openai_compat import OpenAICompatProvider

            if not cfg.deepseek_api_key:
                raise ValueError(
                    "DEEPSEEK_API_KEY not set. "
                    "Export it: export DEEPSEEK_API_KEY=sk-..."
                )
            return OpenAICompatProvider(
                api_key=cfg.deepseek_api_key,
                model=cfg.deepseek_model,
                base_url=cfg.deepseek_base_url,
                temperature=cfg.temperature,
                provider_name="deepseek",
            )
        case _:
            raise ValueError(
                f"Unknown provider: {name}. "
                f"Available: {', '.join(AVAILABLE_PROVIDERS)}"
            )
