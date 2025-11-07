from __future__ import annotations

import typer

from . import doc, maintenance, npm, playback, playwright, python_tasks

__all__ = ["register"]


def register(app: typer.Typer) -> None:
    """
    Register all Typer commands on the provided application instance.
    """

    doc.register(app)
    maintenance.register(app)
    npm.register(app)
    python_tasks.register(app)
    playback.register(app)
    playwright.register(app)
