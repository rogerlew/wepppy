"""Australian Geoscience Data Cube (AGDC) helpers.

Only a single entry point—:func:`agdc_mod`—is exported today, but packaging the
adapter keeps the surface area tidy and mirrors the structure used by other
regional climate integrations.
"""

from __future__ import annotations

from .agdc import agdc_mod

__all__ = ["agdc_mod"]
