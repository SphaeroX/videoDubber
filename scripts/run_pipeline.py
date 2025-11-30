"""Command line entry-point for the video dubbing pipeline."""

from __future__ import annotations

import argparse
import asyncio
from pathlib import Path

from video_dubber import Settings, VideoDubbingPipeline


def parse_args() -> argparse.Namespace:
    """Parse CLI arguments for the pipeline."""

    parser = argparse.ArgumentParser(
        description="Generate a dubbed version of a video using GPT-4o services."
    )
    parser.add_argument(
        "-i",
        "--input",
        required=True,
        type=Path,
        help="Path to the source video file.",
    )
    parser.add_argument(
        "-l",
        "--language",
        type=str,
        default=None,
        help="Optional language code for the synthesized narration.",
    )
    parser.add_argument(
        "--translation-instruction",
        type=str,
        default=None,
        help="Optional instruction for GPT-4o to refine or personalize transcript text before TTS.",
    )
    parser.add_argument(
        "-t",
        "--transcript",
        type=Path,
        default=None,
        help="Path to a custom transcript file (JSON) to use instead of generating one.",
    )
    parser.add_argument(
        "--noise-floor",
        type=int,
        default=None,
        help="Noise floor in dB for noise reduction (default: -25). Lower values mean less aggressive reduction.",
    )
    return parser.parse_args()


async def main(args: argparse.Namespace) -> None:
    settings = Settings.from_env()
    settings.target_language = args.language or settings.target_language
    settings.translation_instruction = (
        args.translation_instruction or settings.translation_instruction
    )
    if args.transcript:
        settings.transcript_path = args.transcript
    if args.noise_floor is not None:
        settings.noise_floor_db = args.noise_floor

    pipeline = VideoDubbingPipeline(settings)

    source_video = args.input
    lang_suffix = f".{settings.target_language}" if settings.target_language else ""
    output_video = source_video.with_name(
        f"{source_video.stem}.dubbed{lang_suffix}{source_video.suffix}"
    )

    await pipeline.run(source_video=source_video, output_video=output_video)


if __name__ == "__main__":
    asyncio.run(main(parse_args()))
