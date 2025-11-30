"""Logic for GPT-4o Mini TTS synthesis."""

from __future__ import annotations

import json
from collections.abc import Iterable
from pathlib import Path

from pydub import AudioSegment

from ..models import AudioRenderTask, TranscriptSegment
from ..utils import save_prompt
from .openai_client import OpenAIClient
import ffmpeg


class TextToSpeechService:
    """Render transcript segments as speech audio."""

    def __init__(
        self,
        client: OpenAIClient,
        model: str,
        voice: str,
        instruction: str | None,
        max_speedup_factor: float = 1.3,
    ) -> None:
        self._client = client
        self._model = model
        self._voice = voice
        self._instruction = instruction.strip() if instruction else None
        self._max_speedup_factor = max_speedup_factor

    async def create_render_tasks(
        self,
        segments: Iterable[TranscriptSegment],
        output_dir: Path,
        instruction_override: str | None = None,
    ) -> list[AudioRenderTask]:
        """Prepare AudioRenderTask definitions for later execution."""

        output_dir.mkdir(parents=True, exist_ok=True)

        applied_instruction = (instruction_override or "").strip() or self._instruction
        applied_instruction = applied_instruction.strip() if applied_instruction else None

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

        # Idempotency: Check if output already exists
        if task.output_path.exists() and task.output_path.stat().st_size > 0:
            return task.output_path

        if not text:
            duration_ms = max(1, int((task.segment.end - task.segment.start) * 1000))
            AudioSegment.silent(duration=duration_ms).export(str(task.output_path), format="wav")
            return task.output_path

        request_args = {
            "model": self._model,
            "voice": task.voice,
            "input": text,
        }
        if task.instruction:
            request_args["instructions"] = task.instruction

        async with self._client.client.audio.speech.with_streaming_response.create(
            **request_args
        ) as response:
            await response.stream_to_file(task.output_path)

        # Check duration and adjust speed if necessary
        try:
            probe = ffmpeg.probe(str(task.output_path))
            current_duration = float(probe["format"]["duration"])
            target_duration = task.segment.end - task.segment.start

            if current_duration > target_duration:
                speedup_factor = current_duration / target_duration
                # Limit the speedup factor
                effective_speedup = min(speedup_factor, self._max_speedup_factor)
                
                if effective_speedup > 1.01: # Only adjust if significant difference
                    temp_path = task.output_path.with_suffix(".tmp.wav")
                    
                    # atempo filter for speed adjustment (pitch preservation)
                    # For factors > 2.0, multiple atempo filters might be needed, 
                    # but here we assume reasonable factors < 2.0 usually.
                    # If effective_speedup is e.g. 1.5, we want to speed up, so we use atempo=1.5
                    
                    stream = ffmpeg.input(str(task.output_path))
                    stream = ffmpeg.filter(stream, "atempo", effective_speedup)
                    stream = ffmpeg.output(stream, str(temp_path))
                    ffmpeg.run(stream, overwrite_output=True, quiet=True)
                    
                    temp_path.replace(task.output_path)
                    
        except Exception as e:
            print(f"Warning: Failed to adjust audio speed for {task.output_path}: {e}")

        return task.output_path
