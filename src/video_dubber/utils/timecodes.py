"""Helpers for working with timestamps."""

from __future__ import annotations


def seconds_to_timestamp(value: float) -> str:
    """Convert seconds to HH:MM:SS.mmm format."""

    hours = int(value // 3600)
    minutes = int((value % 3600) // 60)
    seconds = value % 60
    return f"{hours:02d}:{minutes:02d}:{seconds:06.3f}"
