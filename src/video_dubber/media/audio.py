"""Audio related file operations."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any

from moviepy import VideoFileClip
from pydub import AudioSegment


class AudioWorkspace:
    """Manage intermediate audio assets."""

    def __init__(self, temp_dir: Path) -> None:
        self._temp_dir = temp_dir

    def ensure_workspace(self) -> None:
        """Create workspace folders if missing."""

        self._temp_dir.mkdir(parents=True, exist_ok=True)

    def _video_root(self, video_path: Path) -> Path:
        root = self._temp_dir / video_path.stem
        root.mkdir(parents=True, exist_ok=True)
        return root

    def extract(self, video_path: Path) -> Path:
        """Extract raw audio from a video file."""

        root = self._video_root(video_path)
        audio_path = root / f"{video_path.stem}.wav"

        clip = VideoFileClip(str(video_path))
        try:
            audio = clip.audio
            if audio is None:
                raise ValueError(f"No audio track found in {video_path}")
            audio.write_audiofile(str(audio_path), codec="pcm_s16le", fps=44100, logger=None)
        finally:
            clip.close()

        return audio_path

    def segment(self, transcript_path: Path) -> list[Path]:
        """Split audio into segments according to a transcript."""

        if not transcript_path.exists():
            raise FileNotFoundError(f"Transcript file not found: {transcript_path}")

        if transcript_path.suffix.lower() != ".json":
            return []

        with transcript_path.open("r", encoding="utf-8") as handle:
            payload: dict[str, Any] = json.load(handle)

        raw_segments = payload.get("segments") or []
        if not raw_segments:
            return []

        audio_source = transcript_path.with_suffix(".wav")
        if not audio_source.exists():
            return []

        audio = AudioSegment.from_file(audio_source)
        segment_dir = transcript_path.parent / "segments"
        segment_dir.mkdir(parents=True, exist_ok=True)

        exported: list[Path] = []
        for index, segment in enumerate(raw_segments):
            start = max(0.0, float(segment.get("start", 0.0)))
            end = max(start, float(segment.get("end", start)))

            start_ms = int(start * 1000)
            end_ms = int(end * 1000)
            chunk = audio[start_ms:end_ms] if end_ms > start_ms else AudioSegment.silent(duration=1)

            output_path = segment_dir / f"{index:04d}.wav"
            chunk.export(output_path, format="wav")
            exported.append(output_path)

        return exported
