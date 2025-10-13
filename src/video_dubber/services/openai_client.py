"""Thin async wrapper around the OpenAI Python SDK."""

from __future__ import annotations

from typing import Any, AsyncIterator

from openai import AsyncOpenAI

from ..config import Settings


class OpenAIClient:
    """Provide shared AsyncOpenAI client access."""

    def __init__(self, settings: Settings) -> None:
        self._client = AsyncOpenAI(api_key=settings.openai_api_key)

    @property
    def client(self) -> AsyncOpenAI:
        """Expose the underlying SDK client."""

        return self._client

    async def stream_tts(self, **kwargs: Any) -> AsyncIterator[bytes]:
        """Stream audio bytes produced by a TTS request."""

        async with self._client.audio.speech.with_streaming_response.create(**kwargs) as response:
            async for chunk in response.iter_bytes():
                yield chunk
