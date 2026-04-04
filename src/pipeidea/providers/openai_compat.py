"""OpenAI-compatible provider. Works with OpenAI, DeepSeek, and any OpenAI-compatible API."""

from typing import AsyncIterator

from openai import AsyncOpenAI


class OpenAICompatProvider:
    """Provider for any OpenAI-compatible API (OpenAI, DeepSeek, etc.)."""

    def __init__(
        self,
        api_key: str,
        model: str,
        base_url: str | None = None,
        temperature: float = 0.9,
        provider_name: str = "openai",
    ):
        kwargs = {"api_key": api_key}
        if base_url:
            kwargs["base_url"] = base_url
        self._client = AsyncOpenAI(**kwargs)
        self._model = model
        self._temperature = temperature
        self._name = provider_name

    @property
    def name(self) -> str:
        return self._name

    @property
    def model(self) -> str:
        return self._model

    async def generate(self, system: str, messages: list[dict]) -> str:
        full_messages = [{"role": "system", "content": system}] + messages
        response = await self._client.chat.completions.create(
            model=self._model,
            temperature=self._temperature,
            max_tokens=4096,
            messages=full_messages,
        )
        return response.choices[0].message.content

    async def stream(self, system: str, messages: list[dict]) -> AsyncIterator[str]:
        full_messages = [{"role": "system", "content": system}] + messages
        stream = await self._client.chat.completions.create(
            model=self._model,
            temperature=self._temperature,
            max_tokens=4096,
            messages=full_messages,
            stream=True,
        )
        async for chunk in stream:
            if chunk.choices and chunk.choices[0].delta.content:
                yield chunk.choices[0].delta.content
