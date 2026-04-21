"""RQ package exports.

Avoid importing heavy worker dependencies at package import-time so tools like
the scheduler can import task modules without requiring worker-only optional
secrets or integrations.
"""

from __future__ import annotations

import importlib
from typing import Any

__all__ = ["WepppyRqWorker", "rq_worker"]


def __getattr__(name: str) -> Any:
    if name == "rq_worker":
        return importlib.import_module(".rq_worker", __name__)
    if name == "WepppyRqWorker":
        from .rq_worker import WepppyRqWorker

        return WepppyRqWorker
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
