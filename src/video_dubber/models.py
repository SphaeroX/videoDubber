"""Core datamodels for the transcription workflow."""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable


@dataclass(slots=True)
class TranscriptSegment:
    """Represents a single transcription chunk."""

    start: float
    end: float
    text: str

    def as_timecode(self) -> tuple[float, float]:
        """Return the segment start and end as a tuple."""

        return self.start, self.end


@dataclass(slots=True)
class AudioRenderTask:
    """Describes an audio clip that needs to be synthesized."""

    segment: TranscriptSegment
    instruction: str
    voice: str
    output_path: Path


@dataclass(slots=True)
class RenderedAudioSegment:
    """Represents a synthesized audio clip and its placement."""

    audio_path: Path
    start: float
    end: float


@dataclass(slots=True)
class VideoAssemblyPlan:
    """Contains the mapping of rendered audio clips to the target video."""

    source_video: Path
    rendered_segments: Iterable[RenderedAudioSegment]
    output_video: Path
