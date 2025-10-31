"""Compatibility bridge for the CLI Agent Orchestrator package.

Tests and legacy scripts import ``wepppy.cli_agent_orchestrator`` while the
real implementation lives in ``services/cao/src`` (or an installed wheel).
This module proxies those imports so both environments work without modifying
``PYTHONPATH``.
"""

from __future__ import annotations

from importlib import import_module
from pathlib import Path
import sys

_PACKAGE_NAME = "cli_agent_orchestrator"


def _ensure_src_on_path() -> None:
    """Ensure the editable source tree is importable during dev runs."""
    src_root = Path(__file__).resolve().parents[2] / "services" / "cao" / "src"
    if not src_root.exists():
        return

    src_str = str(src_root)
    if src_str not in sys.path:
        sys.path.append(src_str)


def _load_package():
    try:
        return import_module(_PACKAGE_NAME)
    except ModuleNotFoundError as exc:
        if exc.name != _PACKAGE_NAME:
            raise

        _ensure_src_on_path()
        return import_module(_PACKAGE_NAME)


_package = _load_package()

# Mirror the real package metadata and submodule search path.
__all__ = getattr(_package, "__all__", [])
__doc__ = getattr(_package, "__doc__", __doc__)
__path__ = list(getattr(_package, "__path__", []))


def __getattr__(name: str):
    return getattr(_package, name)


def __dir__():
    return sorted(set(globals()) | set(dir(_package)))
