"""Minimal stub of python-dotenv for test environments.

The full cli-agent-orchestrator stack depends on python-dotenv, but our CI
shim layers avoid pulling the entire dependency graph.  Only ``load_dotenv``
is required for NoDb modules, so provide a no-op implementation so imports
continue to succeed during unit tests.
"""

from __future__ import annotations

from typing import Any, Mapping, Optional


def load_dotenv(
    dotenv_path: Optional[str] = None,
    stream: Optional[Any] = None,
    verbose: bool = False,
    override: bool = False,
    interpolate: bool = True,
    encoding: Optional[str] = "utf-8",
) -> bool:
    """Drop-in replacement that simply returns False (no variables loaded)."""
    return False
