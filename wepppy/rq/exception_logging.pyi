from __future__ import annotations

from typing import Callable, ParamSpec, TypeVar

P = ParamSpec("P")
R = TypeVar("R")

def with_exception_logging(func: Callable[P, R]) -> Callable[P, R]: ...
