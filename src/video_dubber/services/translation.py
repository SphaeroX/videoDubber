"""Helpers for translating transcript segments to a target language."""

from __future__ import annotations

import json
import re
from collections.abc import Iterable
from typing import Any

from ..models import TranscriptSegment
from .openai_client import OpenAIClient


class TranslationService:
    """Translate transcript segments using a GPT-4o chat model."""

    def __init__(self, client: OpenAIClient, model: str) -> None:
        self._client = client
        self._model = model

    async def translate_segments(
        self,
        segments: Iterable[TranscriptSegment],
        target_language: str,
    ) -> list[TranscriptSegment]:
        """Translate each segment text into the desired language."""

        segment_list = list(segments)
        if not segment_list:
            return []

        target_language = target_language.strip()
        if not target_language:
            return segment_list

        payload = {
            "target_language": target_language,
            "segments": [
                {"index": index, "text": segment.text}
                for index, segment in enumerate(segment_list)
            ],
        }

        response = await self._client.client.responses.create(
            model=self._model,
            input=[
                {
                    "role": "system",
                    "content": [
                        {
                            "type": "input_text",
                            "text": (
                                "You translate text snippets into the requested language. "
                                "Return a JSON array of objects with keys 'index' and 'translation', "
                                "preserving the order of the provided segments and avoiding additional commentary."
                            ),
                        }
                    ],
                },
                {
                    "role": "user",
                    "content": [
                        {
                            "type": "input_text",
                            "text": json.dumps(payload, ensure_ascii=False),
                        }
                    ],
                },
            ],
            temperature=0.0,
        )

        translated = self._parse_response(response)

        by_index = {item["index"]: item["translation"] for item in translated if "index" in item and "translation" in item}

        result: list[TranscriptSegment] = []
        for index, segment in enumerate(segment_list):
            translated_text = by_index.get(index, segment.text)
            result.append(
                TranscriptSegment(start=segment.start, end=segment.end, text=translated_text)
            )

        return result

    def _parse_response(self, response: Any) -> list[dict[str, Any]]:
        """Extract and parse JSON output from the model response."""

        text = self._extract_text(response)
        if not text:
            return []

        text = text.strip()

        candidates = [text]
        if "```" in text:
            code_blocks = re.findall(r"```(?:json)?\s*(.+?)```", text, re.DOTALL)
            candidates.extend(code_blocks)

        for candidate in candidates:
            cleaned = candidate.strip()
            try:
                parsed = json.loads(cleaned)
                if isinstance(parsed, dict) and "segments" in parsed:
                    payload = parsed.get("segments")
                    if isinstance(payload, list):
                        return [item for item in payload if isinstance(item, dict)]
                if isinstance(parsed, list):
                    return [item for item in parsed if isinstance(item, dict)]
            except json.JSONDecodeError:
                continue

        return []

    def _extract_text(self, response: Any) -> str:
        """Flatten the response object into plain text."""

        if hasattr(response, "output_text") and response.output_text:
            return str(response.output_text)

        output = getattr(response, "output", None)
        if output:
            chunks: list[str] = []
            for message in output:
                content = getattr(message, "content", None)
                if not content:
                    continue
                for block in content:
                    text = getattr(block, "text", None)
                    if text:
                        chunks.append(str(text))
            if chunks:
                return "".join(chunks)

        choices = getattr(response, "choices", None)
        if choices:
            pieces: list[str] = []
            for choice in choices:
                message = getattr(choice, "message", None)
                if not message:
                    continue
                text = getattr(message, "content", None)
                if text:
                    pieces.append(str(text))
            if pieces:
                return "".join(pieces)

        if isinstance(response, dict):
            return str(response.get("output_text") or response)

        return ""
