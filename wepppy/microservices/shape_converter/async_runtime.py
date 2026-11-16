"""Cancellation-safe helpers for bounded blocking service work."""

from __future__ import annotations

import asyncio
import collections.abc as cabc
from typing import ParamSpec, TypeVar

_P = ParamSpec("_P")
_T = TypeVar("_T")


async def run_blocking_phase(
    function: cabc.Callable[_P, _T],
    /,
    *args: _P.args,
    **kwargs: _P.kwargs,
) -> _T:
    """Run blocking work and retain ownership through repeated cancellation."""

    task = asyncio.create_task(asyncio.to_thread(function, *args, **kwargs))
    drained = asyncio.gather(task, return_exceptions=True)
    cancelled = False
    while not drained.done():
        try:
            await asyncio.shield(drained)
        except asyncio.CancelledError:
            # Threads cannot be killed safely. Every cancellation is deferred
            # until the bounded thread ends so admission and scratch stay owned.
            cancelled = True
    if cancelled:
        raise asyncio.CancelledError
    return task.result()
