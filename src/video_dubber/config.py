"""Configuration models for the video dubber pipeline."""

from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass(slots=True)
class Settings:
    """Runtime configuration for the pipeline."""

    openai_api_key: str
    transcription_model: str = "gpt-4o-transcribe"
    translation_model: str = "gpt-4o"
    tts_model: str = "gpt-4o-mini-tts"
    tts_voice: str = "alloy"
    tts_instruction: str = "Sprich klar, freundlich und ohne Hintergrundgeraeusche."
    target_language: str | None = None
    max_concurrency: int = 10
    temp_dir: Path = Path("artifacts")

    @classmethod
    def from_env(cls) -> "Settings":
        """Create settings using environment defaults."""

        return cls(
            openai_api_key=os.getenv("OPENAI_API_KEY", ""),
            tts_instruction=os.getenv(
                "TTS_INSTRUCTION",
                "Sprich klar, freundlich und ohne Hintergrundgeraeusche.",
            ),
            translation_model=os.getenv("TRANSLATION_MODEL", "gpt-4o"),
            tts_voice=os.getenv("TTS_VOICE", "alloy"),
            target_language=os.getenv("TARGET_LANGUAGE") or None,
            max_concurrency=int(os.getenv("MAX_CONCURRENCY", "10")),
            temp_dir=Path(os.getenv("TEMP_DIR", "artifacts")),
        )
