"""Async helpers for throttling concurrent tasks."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Iterable
from typing import TypeVar

T = TypeVar("T")


async def bounded_gather(limit: int, tasks: Iterable[Awaitable[T]]) -> list[T]:
    """Run awaitables with a concurrency limit."""

    semaphore = asyncio.Semaphore(limit)
    results: list[T] = []

    async def _run(coro: Awaitable[T]) -> None:
        async with semaphore:
            results.append(await coro)

    await asyncio.gather(*(_run(task) for task in tasks))
    return results
