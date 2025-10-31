"""CLI Agent Orchestrator package metadata."""

from __future__ import annotations

from importlib import metadata
from pathlib import Path

try:
    __version__ = metadata.version("cli-agent-orchestrator")
except metadata.PackageNotFoundError:  # pragma: no cover - editable installs
    _root = Path(__file__).resolve().parent.parent.parent
    _version_file = _root / "VERSION"
    if _version_file.exists():
        __version__ = _version_file.read_text(encoding="utf-8").strip()
    else:  # pragma: no cover - fallback for dev checkouts
        __version__ = "0.0.0"

__all__ = ["__version__"]
