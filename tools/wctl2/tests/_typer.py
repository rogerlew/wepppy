"""Detect whether Typer is available for CLI tests."""

from __future__ import annotations

try:  # pragma: no cover - depends on optional dependency
    import typer  # type: ignore import-not-found
    from typer.testing import CliRunner  # type: ignore import-not-found
except ModuleNotFoundError:  # pragma: no cover - depends on optional dependency
    typer = None  # type: ignore[assignment]
    CliRunner = None  # type: ignore[assignment]
    TYPER_AVAILABLE = False
else:  # pragma: no cover - trivial branch
    TYPER_AVAILABLE = True

__all__ = ["CliRunner", "TYPER_AVAILABLE", "typer"]
