"""Logic for GPT-4o Mini TTS synthesis."""

from __future__ import annotations

from collections.abc import Iterable
from pathlib import Path

from pydub import AudioSegment

from ..models import AudioRenderTask, TranscriptSegment
from .openai_client import OpenAIClient


class TextToSpeechService:
    """Render transcript segments as speech audio."""

    def __init__(self, client: OpenAIClient, model: str, voice: str, instruction: str) -> None:
        self._client = client
        self._model = model
        self._voice = voice
        self._instruction = instruction

    async def create_render_tasks(
        self,
        segments: Iterable[TranscriptSegment],
        output_dir: Path,
    ) -> list[AudioRenderTask]:
        """Prepare AudioRenderTask definitions for later execution."""

        output_dir.mkdir(parents=True, exist_ok=True)

        tasks: list[AudioRenderTask] = []
        for index, segment in enumerate(segments):
            filename = f"{index:04d}_{segment.start:08.3f}.wav"
            output_path = output_dir / filename
            tasks.append(
                AudioRenderTask(
                    segment=segment,
                    instruction=self._instruction,
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
