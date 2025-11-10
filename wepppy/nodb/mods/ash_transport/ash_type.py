"""Enumerations describing modeled ash compositions."""

from __future__ import annotations

import enum

__all__ = ["AshType"]


class AshType(enum.IntEnum):
    """Ash composition used by the multi-year transport models."""

    BLACK = 0
    WHITE = 1

    def __str__(self) -> str:
        if self == AshType.BLACK:
            return "Black"
        if self == AshType.WHITE:
            return "White"
        raise ValueError(f"Unknown ash type {self}")
