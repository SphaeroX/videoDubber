"""Logic for GPT-4o transcription requests."""

from __future__ import annotations

import json
import re
from pathlib import Path
from typing import Iterable, List, Sequence
import logging
import asyncio

import ffmpeg

from ..models import TranscriptSegment
from ..utils import save_prompt
from .openai_client import OpenAIClient


class TranscriptionService:
    """Handle audio transcription via OpenAI."""

    SENTENCE_BOUNDARY = re.compile(r"(?<=[.!?])\s+")

    def __init__(self, client: OpenAIClient, model: str) -> None:
        self._client = client
        self._model = model

    async def transcribe(self, audio_path: Path) -> list[TranscriptSegment]:
        """Submit the audio file and parse the resulting segments."""

        if not audio_path.exists():
            raise FileNotFoundError(f"Audio file not found: {audio_path}")

        # Idempotency: Check for existing transcript
        transcript_cache_path = audio_path.with_suffix(".transcript.json")
        if transcript_cache_path.exists():
            try:
                with transcript_cache_path.open("r", encoding="utf-8") as f:
                    data = json.load(f)
                    return [TranscriptSegment(**item) for item in data]
            except Exception as e:
                logging.warning(f"Failed to load cached transcript: {e}")

        response_format = self._response_format_for_model(self._model)

        save_prompt(
            audio_path.parent,
            category="transcription",
            name=audio_path.stem or "request",
            content=json.dumps(
                {
                    "model": self._model,
                    "response_format": response_format,
                    "file": audio_path.name,
                },
                indent=2,
                ensure_ascii=False,
            ),
            suffix="json",
        )

        with audio_path.open("rb") as handle:
            # Retry logic for 500 errors
            max_retries = 3
            for attempt in range(max_retries):
                try:
                    response = await self._client.client.audio.transcriptions.create(
                        model=self._model,
                        file=handle,
                        response_format=response_format,
                    )
                    break
                except Exception as e:
                    is_server_error = "500" in str(e) or (hasattr(e, "status_code") and e.status_code >= 500)
                    if is_server_error and attempt < max_retries - 1:
                        wait_time = 2 ** attempt
                        logging.warning(f"OpenAI 500 error: {e}. Retrying in {wait_time}s...")
                        await asyncio.sleep(wait_time)
                        # Re-open file handle for retry as it might be consumed
                        handle.seek(0)
                        continue
                    raise

        raw_segments: Sequence[dict[str, object]] = []
        transcript_text = ""

        if hasattr(response, "segments"):
            raw_segments = getattr(response, "segments") or []
            transcript_text = getattr(response, "text", "") or ""
        else:
            model_dump = getattr(response, "model_dump", None)
            if callable(model_dump):
                payload = model_dump()
                raw_segments = payload.get("segments") or []
                transcript_text = payload.get("text", "") or ""
            elif isinstance(response, dict):
                raw_segments = response.get("segments") or []
                transcript_text = response.get("text", "") or ""

        segments = self._parse_segments(raw_segments)

        if not segments and transcript_text:
            segments = self._approximate_segments(audio_path, transcript_text)

        # Cache the result
        try:
            with transcript_cache_path.open("w", encoding="utf-8") as f:
                json.dump([{"start": s.start, "end": s.end, "text": s.text} for s in segments], f, indent=2)
        except Exception as e:
            logging.warning(f"Failed to cache transcript: {e}")

        return segments

    def _parse_segments(self, raw_segments: Iterable[dict[str, object]]) -> list[TranscriptSegment]:
        """Convert API payloads into TranscriptSegment instances."""

        parsed: List[TranscriptSegment] = []

        for item in raw_segments:
            try:
                start = float(item.get("start", 0.0))  # type: ignore[arg-type]
                end = float(item.get("end", start))  # type: ignore[arg-type]
                text = str(item.get("text", "")).strip()
            except (TypeError, ValueError):
                continue

            if not text:
                continue

            parsed.append(TranscriptSegment(start=start, end=end, text=text))

        return parsed

    def _approximate_segments(self, audio_path: Path, transcript_text: str) -> list[TranscriptSegment]:
        """Fallback segmentation when the API does not provide timestamps."""

        sentences = [
            sentence.strip()
            for sentence in self.SENTENCE_BOUNDARY.split(transcript_text.strip())
            if sentence.strip()
        ]

        if not sentences:
            cleaned = transcript_text.strip()
            duration = self._probe_audio_duration(audio_path)
            return [TranscriptSegment(start=0.0, end=max(duration, 0.0), text=cleaned)] if cleaned else []

        duration = max(self._probe_audio_duration(audio_path), 0.0)
        if duration <= 0.0:
            duration = float(len(sentences)) * 2.5

        total_chars = sum(len(sentence) for sentence in sentences) or len(sentences)
        segments: list[TranscriptSegment] = []
        cursor = 0.0

        for index, sentence in enumerate(sentences):
            cursor = min(cursor, duration)

            if index == len(sentences) - 1:
                end = duration
            else:
                share = len(sentence) / total_chars
                segment_duration = duration * share
                min_slice = duration / (len(sentences) * 2.0)
                segment_duration = max(segment_duration, min_slice)
                end = min(duration, cursor + segment_duration)
                if end <= cursor and duration > cursor:
                    end = min(duration, cursor + min_slice)

            segments.append(TranscriptSegment(start=cursor, end=end, text=sentence))
            cursor = end

        return segments

    def _response_format_for_model(self, model: str) -> str:
        """Choose the appropriate response_format for the selected model."""

        model_lc = model.lower()
        if "gpt-4o-transcribe" in model_lc:
            return "json"
        return "verbose_json"

    def _probe_audio_duration(self, audio_path: Path) -> float:
        """Read the audio duration via ffprobe."""

        try:
            probe = ffmpeg.probe(str(audio_path))
        except ffmpeg.Error:
            return 0.0

        format_info = probe.get("format") or {}
        try:
            return max(0.0, float(format_info.get("duration", 0.0)))
        except (TypeError, ValueError):
            return 0.0
