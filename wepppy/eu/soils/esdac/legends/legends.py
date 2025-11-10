"""Load the ESDAC PTRDB/SGDPE legend tables into friendly dictionaries."""

from __future__ import annotations

import os
from os.path import join as _join
from typing import Final

# https://esdac.jrc.ec.europa.eu/content/european-soil-database-v2-raster-library-1kmx1km
# https://esdac.jrc.ec.europa.eu/content/sgdbe-attributes
# https://esdac.jrc.ec.europa.eu/content/ptrdb-attributes
# https://esdac.jrc.ec.europa.eu/content/legend-files


from ..esdac import _attr_fmt


_thisdir: Final[str] = os.path.dirname(__file__)

def _load_ptrdb_legends() -> dict[str, dict[str, object]]:
    """Parse the PTRDB legend dump bundled alongside this module."""
    with open(_join(_thisdir, "ptrdb.dat"), "r", encoding="utf-8") as fp:
        lines = fp.readlines()

    breaks = []
    for i, line in enumerate(lines):
        if line.strip().startswith("-"):
            breaks.append(i)

    data: dict[str, dict[str, object]] = {}
    i0 = 0
    for _, iend in enumerate(breaks):
        subset = lines[i0:iend]

        attr, desc = subset[0].split("=")
        attr, desc = attr.strip(), desc.strip()
        attr = _attr_fmt(attr)
        data[attr] = dict(description=desc, table={})

        for line in subset[1:]:
            key, value = line.split("=")
            key, value = key.strip(), value.strip()
            data[attr]["table"][key] = value

        i0 = iend + 1

    return data


def _load_sgdpe_legends() -> dict[str, dict[str, object]]:
    """Parse the SGDPE legend dump bundled alongside this module."""
    with open(_join(_thisdir, "sgdpe.dat"), "r", encoding="utf-8") as fp:
        lines = fp.readlines()

    breaks = []
    for i, line in enumerate(lines):
        if line.startswith("-") and len(line.strip()) > 70:
            breaks.append(i)

    data: dict[str, dict[str, object]] = {}
    i0 = 0
    for i, iend in enumerate(breaks):
        subset = lines[i0:iend]
        if not subset:
            continue

        attr = _attr_fmt(subset[0].strip())
        data[attr] = dict(description=None, table={})

        assert subset[1].strip().startswith("-"), (attr, subset[1])

        tbl_lines = []
        for j, line in enumerate(subset[2:]):
            if (
                len(line[:4].strip()) == 0
                and "no information" not in line.lower()
                and j > 0
            ):
                tbl_lines[-1] = f"{tbl_lines[-1].rstrip()} {line.lstrip()}"
            else:
                tbl_lines.append(line)

        for line in tbl_lines:
            if len(line[:4].strip()) == 0:
                key = ""
                value = line.strip()
            else:
                tokens = line.split()
                key = tokens[0]
                value = " ".join(tokens[1:])

            data[attr]["table"][key] = value

        i0 = iend + 1

    return data


ptrdb = _load_ptrdb_legends()
sgdpe = _load_sgdpe_legends()


def get_legend(attr: str) -> dict[str, object]:
    """Return the PTRDB/SGDPE legend dictionary for ``attr``."""
    _attr = _attr_fmt(attr)

    for key, value in ptrdb.items():
        if _attr == _attr_fmt(key):
            return value

    for key, value in sgdpe.items():
        if _attr == _attr_fmt(key):
            return value

    raise KeyError(attr)
