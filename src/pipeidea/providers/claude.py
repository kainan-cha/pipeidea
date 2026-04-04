"""Anthropic Claude provider."""

from typing import AsyncIterator

import anthropic


class ClaudeProvider:
    """Claude provider using the Anthropic SDK."""

    def __init__(self, api_key: str, model: str = "claude-sonnet-4-20250514", temperature: float = 0.9):
        self._client = anthropic.AsyncAnthropic(api_key=api_key)
        self._model = model
        self._temperature = temperature

    @property
    def name(self) -> str:
        return "claude"

    @property
    def model(self) -> str:
        return self._model

    async def generate(self, system: str, messages: list[dict]) -> str:
        response = await self._client.messages.create(
            model=self._model,
            max_tokens=4096,
            temperature=self._temperature,
            system=system,
            messages=messages,
        )
        return response.content[0].text

    async def stream(self, system: str, messages: list[dict]) -> AsyncIterator[str]:
        async with self._client.messages.stream(
            model=self._model,
            max_tokens=4096,
            temperature=self._temperature,
            system=system,
            messages=messages,
        ) as stream:
            async for text in stream.text_stream:
                yield text
