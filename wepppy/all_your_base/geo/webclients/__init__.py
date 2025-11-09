"""Proxy functions for remote raster/elevation microservices."""

from __future__ import annotations

from .elevation import elevationquery
from .wmesque import wmesque_retrieve

__all__: list[str] = ["elevationquery", "wmesque_retrieve"]
