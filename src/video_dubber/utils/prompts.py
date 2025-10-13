"""Helpers for persisting prompt payloads alongside artifacts."""

from __future__ import annotations

from pathlib import Path


def save_prompt(
    base_dir: Path | None,
    category: str,
    name: str,
    content: str,
    suffix: str = "txt",
) -> Path | None:
    """Persist prompt content inside the artifacts directory structure.

    Args:
        base_dir: Root directory for the current run. When None, logging is skipped.
        category: Folder name under ``prompts`` (e.g. ``translation`` or ``tts``).
        name: Base filename for the prompt snapshot.
        content: Text to write to disk.
        suffix: Optional file extension (defaults to ``txt``).

    Returns:
        Path to the written file when logging is performed, otherwise ``None``.
    """

    if base_dir is None:
        return None

    safe_category = _sanitize_token(category) if category else "general"
    safe_name = _sanitize_token(name) or "prompt"
    safe_suffix = suffix.lstrip(".") or "txt"

    target_dir = base_dir / "prompts" / safe_category
    target_dir.mkdir(parents=True, exist_ok=True)

    candidate = target_dir / f"{safe_name}.{safe_suffix}"
    counter = 2
    while candidate.exists():
        candidate = target_dir / f"{safe_name}_{counter}.{safe_suffix}"
        counter += 1

    candidate.write_text(content, encoding="utf-8")
    return candidate


def _sanitize_token(token: str) -> str:
    """Replace characters that are unsafe for filesystem use."""

    cleaned = "".join(ch if ch.isalnum() or ch in {"-", "_"} else "_" for ch in token)
    cleaned = cleaned.strip("_")
    return cleaned or "prompt"

