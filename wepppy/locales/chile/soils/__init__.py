"""Utilities for resolving Chilean soil ids to WEPP-ready `.sol` files."""

from __future__ import annotations

import os
from os.path import exists as _exists
from os.path import join as _join
from typing import Final

_thisdir: Final[str] = os.path.dirname(__file__)

_MAP: dict[int, str] = {}
with open(_join(_thisdir, "map.psv"), encoding="utf-8") as fp:
    for line in fp:
        line = line.strip()
        if not line:
            continue
        k, v = line.split("|")
        _MAP[int(k)] = v

__all__ = ("get_soil_fn",)


def get_soil_fn(soil_id: int | str) -> tuple[str, str]:
    """Return the absolute `.sol` file path and mukey for ``soil_id``.

    Args:
        soil_id: Integer identifier provided by the Chile locale datasets.

    Returns:
        Tuple of (absolute soil-file path, mukey/string key).

    Raises:
        ValueError: If the soil id cannot be found in `map.psv`.
        FileNotFoundError: If the mapped `.sol` file is missing on disk.
    """
    try:
        key = int(soil_id)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Invalid soil id: {soil_id!r}") from exc

    if key not in _MAP:
        raise ValueError(f"Unknown soil ID: {soil_id}")

    mukey = _MAP[key]
    soil_path = os.path.abspath(_join(_thisdir, f"{mukey}.sol"))
    if not _exists(soil_path):
        raise FileNotFoundError(f"File not found: {soil_path}")

    return soil_path, mukey


if __name__ == "__main__":
    for soil_id in range(1, 4):
        print(soil_id)
        print(get_soil_fn(soil_id))
