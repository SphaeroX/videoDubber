"""Video editing helpers."""

from __future__ import annotations

import math
from pathlib import Path
from typing import Iterable, List, Tuple

import ffmpeg
from pydub import AudioSegment


class VideoEditor:
    """Apply audio edits to a video file."""

    def remove_audio_track(self, video_path: Path) -> Path:
        """Produce a muted version of the input video."""

        muted_path = video_path.with_name(f"{video_path.stem}.muted{video_path.suffix}")
        stream = ffmpeg.input(str(video_path))
        output = ffmpeg.output(stream, str(muted_path), c="copy", an=None)
        ffmpeg.run(output, overwrite_output=True, quiet=True)
        return muted_path

    def attach_audio_segments(
        self,
        video_path: Path,
        audio_segments: Iterable[tuple[Path, float, float]],
        output_path: Path,
    ) -> Path:
        """Merge synthesized audio segments back into the video."""

        output_path.parent.mkdir(parents=True, exist_ok=True)
        segment_list: List[Tuple[Path, float, float]] = sorted(
            ((Path(path), float(start), float(end)) for path, start, end in audio_segments),
            key=lambda item: item[1],
        )

        max_segment_end = max((end for _, _, end in segment_list), default=0.0)
        duration_seconds = max(self._probe_duration(video_path), max_segment_end)
        total_duration_ms = max(1000, math.ceil(duration_seconds * 1000))

        target_sample_width = 2  # 16-bit PCM
        target_channels = 2
        target_frame_rate = 44100

        mixdown = AudioSegment.silent(duration=total_duration_ms, frame_rate=target_frame_rate)
        mixdown = mixdown.set_sample_width(target_sample_width).set_channels(target_channels)

        for audio_path, start, _ in segment_list:
            if not audio_path.exists():
                continue

            segment_audio = AudioSegment.from_file(audio_path)
            segment_audio = (
                segment_audio.set_sample_width(target_sample_width)
                .set_channels(target_channels)
                .set_frame_rate(target_frame_rate)
            )

            position_ms = max(0, int(start * 1000))
            mixdown = mixdown.overlay(segment_audio, position=position_ms)

        temp_audio = output_path.with_suffix(".temp.wav")

        try:
            mixdown.export(str(temp_audio), format="wav")

            video_input = ffmpeg.input(str(video_path))
            audio_input = ffmpeg.input(str(temp_audio))

            output = ffmpeg.output(
                video_input.video,
                audio_input.audio,
                str(output_path),
                vcodec="copy",
                acodec="aac",
                audio_bitrate="192k",
            )
            ffmpeg.run(output, overwrite_output=True, quiet=True)
        finally:
            if temp_audio.exists():
                temp_audio.unlink()

        return output_path

    def _probe_duration(self, video_path: Path) -> float:
        """Read the media duration via ffprobe."""

        try:
            probe = ffmpeg.probe(str(video_path))
        except ffmpeg.Error:
            return 0.0

        format_info = probe.get("format") or {}
        try:
            return max(0.0, float(format_info.get("duration", 0.0)))
        except (TypeError, ValueError):
            return 0.0
