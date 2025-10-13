"""Logic for GPT-4o Mini TTS synthesis."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

from pydub import AudioSegment

from ..models import AudioRenderTask, TranscriptSegment
from ..utils import save_prompt
from .openai_client import OpenAIClient


class TextToSpeechService:
    """Render transcript segments as speech audio."""

    _DEFAULT_INSTRUCTION = "Sprich klar, freundlich und ohne Hintergrundgeraeusche."

    def __init__(
        self,
        client: OpenAIClient,
        model: str,
        voice: str,
        instruction: str | None,
    ) -> None:
        self._client = client
        self._model = model
        self._voice = voice
        self._instruction = instruction.strip() if instruction else None

    async def create_render_tasks(
        self,
        segments: Iterable[TranscriptSegment],
        output_dir: Path,
        instruction_override: str | None = None,
    ) -> list[AudioRenderTask]:
        """Prepare AudioRenderTask definitions for later execution."""

        output_dir.mkdir(parents=True, exist_ok=True)

        applied_instruction = (instruction_override or "").strip() or self._instruction
        if not applied_instruction:
            applied_instruction = self._DEFAULT_INSTRUCTION

        tasks: list[AudioRenderTask] = []
        for index, segment in enumerate(segments):
            filename = f"{index:04d}_{segment.start:08.3f}.wav"
            output_path = output_dir / filename

            prompt_payload = {
                "model": self._model,
                "voice": self._voice,
                "instruction": applied_instruction,
                "segment": {
                    "index": index,
                    "start": segment.start,
                    "end": segment.end,
                    "text": segment.text,
                },
            }
            save_prompt(
                output_dir.parent,
                category="tts",
                name=filename,
                content=json.dumps(prompt_payload, indent=2, ensure_ascii=False),
                suffix="json",
            )

            tasks.append(
                AudioRenderTask(
                    segment=segment,
                    instruction=applied_instruction,
                    voice=self._voice,
                    output_path=output_path,
                )
            )

        return tasks

    async def synthesize(self, task: AudioRenderTask) -> Path:
        """Generate audio data for a single transcript segment."""

        text = task.segment.text.strip()
        task.output_path.parent.mkdir(parents=True, exist_ok=True)

        if not text:
            duration_ms = max(1, int((task.segment.end - task.segment.start) * 1000))
            AudioSegment.silent(duration=duration_ms).export(str(task.output_path), format="wav")
            return task.output_path

        async with self._client.client.audio.speech.with_streaming_response.create(
            model=self._model,
            voice=task.voice,
            input=text,
            instructions=task.instruction,
        ) as response:
            await response.stream_to_file(task.output_path)

        return task.output_path
