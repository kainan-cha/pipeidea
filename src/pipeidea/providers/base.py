"""AI provider protocol — the interface all providers implement."""

from typing import AsyncIterator, Protocol, runtime_checkable


@runtime_checkable
class Provider(Protocol):
    """Minimal interface for AI text generation."""

    @property
    def name(self) -> str:
        """Provider name (e.g., 'claude', 'openai')."""
        ...

    @property
    def model(self) -> str:
        """Provider model identifier."""
        ...

    async def generate(self, system: str, messages: list[dict]) -> str:
        """Single completion. Returns the full response text."""
        ...

    async def stream(self, system: str, messages: list[dict]) -> AsyncIterator[str]:
        """Streaming completion. Yields text chunks as they arrive."""
        ...
