"""Helpers for reading the curated WEPP soil database bundled with the repo."""

from __future__ import annotations

import os
from glob import glob
from os.path import exists as _exists
from os.path import join as _join
from typing import Any, Dict, List, Tuple

from wepppy.wepp.soils.utils import WeppSoilUtil

__all__ = ["load_db", "get_soil", "read_disturbed_wepp_soil_fire_pars"]

_THIS_DIR = os.path.dirname(__file__)
_DATA_DIR = _join(_THIS_DIR, "data")
_DISTURBED_LOOKUP: Dict[Tuple[str, str], str] = {
    ("silt loam", "high"): _join("Forest", "High sev fire-silt loam.sol"),
    ("silt loam", "low"): _join("Forest", "Low sev fire-silt loam.sol"),
    ("loam", "high"): _join("Forest", "High sev fire-loam.sol"),
    ("loam", "low"): _join("Forest", "Low sev fire-loam.sol"),
    ("sand loam", "high"): _join("Forest", "High sev fire-sandy loam.sol"),
    ("sand loam", "low"): _join("Forest", "Low sev fire-sandy loam.sol"),
    ("clay loam", "high"): _join("Forest", "High sev fire-clay loam.sol"),
    ("clay loam", "low"): _join("Forest", "Low sev fire-clay loam.sol"),
}


def load_db() -> List[str]:
    """Return a list of soil files relative to the soilsdb ``data`` directory."""
    sols = glob(_join(_DATA_DIR, "*/*.sol"))
    return [os.path.relpath(sol, _DATA_DIR) for sol in sols]


def get_soil(sol: str) -> str:
    """Return the absolute path to a soil file stored within the database."""
    path = _join(os.path.abspath(_DATA_DIR), sol)
    if not _exists(path):
        raise FileNotFoundError(path)
    return path


def read_disturbed_wepp_soil_fire_pars(simple_texture: str, fire_severity: str) -> Dict[str, Any]:
    """Return the baseline fire parameters for a disturbed soil.

    Args:
        simple_texture: Texture label such as ``"silt loam"``.
        fire_severity: Severity classification (``"high"`` or ``"low"``).

    Returns:
        The dictionary describing the first OFE in the matching soil file.

    Raises:
        ValueError: If the texture or severity values are unsupported.
        FileNotFoundError: If the expected soil file does not exist.
    """
    key = (simple_texture.lower(), fire_severity.lower())
    relative = _DISTURBED_LOOKUP.get(key)
    if relative is None:
        raise ValueError(f"Unsupported texture/severity combination: {simple_texture}/{fire_severity}")

    fn = _join(_DATA_DIR, relative)
    if not _exists(fn):
        raise FileNotFoundError(fn)

    soil = WeppSoilUtil(fn)
    return soil.obj["ofes"][0]


if __name__ == "__main__":  # pragma: no cover - manual inspection helper
    print(load_db())
