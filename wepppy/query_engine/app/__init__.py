"""Starlette application for the WEPPcloud query engine."""

from .server import create_app

__all__ = ["create_app"]
