"""Public package namespace for WEPP utilities."""

from __future__ import annotations

import importlib

from . import reports


def __getattr__(name: str):
    if name == "interchange":
        module = importlib.import_module(f"{__name__}.interchange")
        globals()[name] = module
        return module
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


__all__ = ["reports", "interchange"]
