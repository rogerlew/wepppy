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
    cancelled = False
    while not task.done():
        try:
            await asyncio.shield(task)
        except asyncio.CancelledError:
            # Threads cannot be killed safely. Every cancellation is deferred
            # until the bounded thread ends so admission and scratch stay owned.
            cancelled = True
    if cancelled:
        # Retrieve any worker exception so cancellation does not leave an
        # unobserved-task warning; cancellation remains the request contract.
        task.exception()
        raise asyncio.CancelledError
    return task.result()
