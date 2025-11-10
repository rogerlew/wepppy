from __future__ import annotations

import enum

class AshType(enum.IntEnum):
    BLACK = ...
    WHITE = ...

    def __str__(self) -> str: ...

__all__ = ["AshType"]
