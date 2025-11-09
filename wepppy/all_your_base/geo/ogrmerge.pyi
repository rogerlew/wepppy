from __future__ import annotations

from collections.abc import Callable, Sequence
from typing import Any


def Usage() -> int: ...


def process(
    argv: Sequence[str],
    progress: Callable[[float], None] | None = ...,
    progress_arg: Any | None = ...,
) -> int: ...
