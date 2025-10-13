"""High level orchestration for the video dubbing workflow."""

from __future__ import annotations

import asyncio
from pathlib import Path
from typing import Iterable

from .config import Settings
from .media.audio import AudioWorkspace
from .media.video import VideoEditor
from .models import (
    AudioRenderTask,
    RenderedAudioSegment,
    TranscriptSegment,
    VideoAssemblyPlan,
)
from .services.openai_client import OpenAIClient
from .services.transcription import TranscriptionService
from .services.translation import TranslationService
from .services.tts import TextToSpeechService
from .utils.concurrency import bounded_gather


class VideoDubbingPipeline:
    """Coordinate the end-to-end dubbing process for a single video."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings
        self._workspace = AudioWorkspace(settings.temp_dir)
        self._video_editor = VideoEditor()
        self._client = OpenAIClient(settings)
        self._transcription = TranscriptionService(self._client, settings.transcription_model)
        self._translation = TranslationService(self._client, settings.translation_model)
        self._tts = TextToSpeechService(
            self._client,
            settings.tts_model,
            settings.tts_voice,
            settings.tts_instruction,
        )
        self._run_root: Path | None = None

    async def run(self, source_video: Path, output_video: Path) -> None:
        """Execute the full pipeline for a single video.

        Steps:
            1. Extract audio track.
            2. Transcribe audio into segments.
            3. Render TTS audio clips for each segment.
            4. Assemble video with the new audio.
        """

        self._workspace.ensure_workspace()

        source_video = source_video.resolve()
        output_video = output_video.resolve()

        if not source_video.exists():
            raise FileNotFoundError(f"Source video not found: {source_video}")

        extracted_audio = await self.extract_audio(source_video)
        segments = await self.transcribe_audio(extracted_audio)
        segments = await self.translate_segments_if_needed(segments)
        render_tasks = await self.render_audio_segments(segments)

        rendered_segments = [
            RenderedAudioSegment(
                audio_path=task.output_path,
                start=task.segment.start,
                end=task.segment.end,
            )
            for task in render_tasks
        ]

        plan = VideoAssemblyPlan(
            source_video=source_video,
            rendered_segments=rendered_segments,
            output_video=output_video,
        )

        await self.assemble_video(plan)

    async def extract_audio(self, source_video: Path) -> Path:
        """Extract the audio track from the source video."""

        audio_path = await asyncio.to_thread(self._workspace.extract, source_video)
        self._run_root = audio_path.parent
        return audio_path

    async def transcribe_audio(self, audio_path: Path) -> list[TranscriptSegment]:
        """Generate transcript segments using GPT-4o Transcribe."""

        return await self._transcription.transcribe(audio_path)

    async def translate_segments_if_needed(self, segments: Iterable[TranscriptSegment]) -> list[TranscriptSegment]:
        """Translate transcript segments when a target language is configured."""

        segment_list = list(segments)
        target_language = (self._settings.target_language or "").strip()

        if not segment_list or not target_language:
            return segment_list

        return await self._translation.translate_segments(segment_list, target_language)

    async def render_audio_segments(self, segments: Iterable[TranscriptSegment]) -> list[AudioRenderTask]:
        """Render each transcript segment using GPT-4o Mini TTS."""

        segment_list = list(segments)
        if not segment_list:
            return []

        output_root = self._run_root or (self._settings.temp_dir / "renders")
        render_tasks = await self._tts.create_render_tasks(segment_list, output_root / "tts")

        await bounded_gather(
            self._settings.max_concurrency,
            [self._tts.synthesize(task) for task in render_tasks],
        )
        return render_tasks

    async def assemble_video(self, plan: VideoAssemblyPlan) -> None:
        """Replace the original audio track with rendered clips."""

        segments = [
            (segment.audio_path, segment.start, segment.end)
            for segment in plan.rendered_segments
        ]

        muted_video = await asyncio.to_thread(self._video_editor.remove_audio_track, plan.source_video)

        try:
            await asyncio.to_thread(
                self._video_editor.attach_audio_segments,
                muted_video,
                segments,
                plan.output_video,
            )
        finally:
            if muted_video.exists() and muted_video != plan.output_video:
                muted_video.unlink(missing_ok=True)
