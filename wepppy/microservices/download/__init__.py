"""Dedicated download microservice for critical run artifacts."""

from .app import app, create_app

__all__ = ["app", "create_app"]
