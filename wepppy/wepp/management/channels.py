# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

"""Helpers for loading and customising WEPP channel management templates."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Dict, List, Optional, TypedDict

__all__ = ["ChannelDefinition", "load_channel_d50_cs", "load_channels", "get_channel"]

_DATA_DIRECTORY = Path(__file__).resolve().parent / "data"


class ChannelDefinition(TypedDict):
    """Parsable structure describing a WEPP channel management entry."""

    key: str
    desc: str
    contents: str
    rot: str


def load_channel_d50_cs() -> List[Dict[str, float | str]]:
    """Load channel D50/Cs coefficient lookup table.

    Returns:
        Rows from ``channel_d50_cs.csv`` with numeric fields coerced to ``float``.
    """
    rows: List[Dict[str, float | str]] = []
    with (_DATA_DIRECTORY / "channel_d50_cs.csv").open("r", encoding="utf-8") as stream:
        reader = csv.DictReader(stream)
        for row in reader:
            coerced_row: Dict[str, float | str] = {}
            for key, value in row.items():
                if value is None:
                    coerced_row[key] = ""
                    continue
                try:
                    coerced_row[key] = float(value)
                except ValueError:
                    coerced_row[key] = value
            rows.append(coerced_row)
    return rows


def _format_value(value: str) -> str:
    """Format numeric tokens using scientific notation where appropriate."""
    formatted = f"{float(value):0.5f}"
    if formatted == "0.00000":
        # fall back to scientific notation to avoid losing tiny magnitudes
        formatted = f"{float(value):1.1e}"
    return formatted


def load_channels() -> Dict[str, ChannelDefinition]:
    """Load canonical channel management templates from ``channels.defs``.

    Returns:
        Mapping of channel template name to structured definition.
    """
    with (_DATA_DIRECTORY / "channels.defs").open("r", encoding="utf-8") as stream:
        blocks = stream.read().split("\n\n")

    definitions: Dict[str, ChannelDefinition] = {}
    for block in blocks:
        lines = block.strip().split("\n")
        if len(lines) < 9:
            continue
        key = lines[0]
        desc = lines[1]
        contents = lines[2:-2]
        contents[3] = "\n".join(contents[3].split())
        contents[4] = " ".join(_format_value(token) for token in contents[4].split())
        contents[5] = " ".join(_format_value(token) for token in contents[5].split())
        contents[6] = " ".join(_format_value(token) for token in contents[6].split())
        # contents[7] retains the original formatting for readability.
        contents_blob = "\n".join(contents)
        rot = lines[-1]
        definitions[key] = ChannelDefinition(key=key, desc=desc, contents=contents_blob, rot=rot)
    return definitions


def get_channel(
    key: str,
    erodibility: Optional[float] = None,
    critical_shear: Optional[float] = None,
    chnnbr: Optional[int] = None,
    chnn: Optional[int] = None,
) -> ChannelDefinition:
    """Retrieve a channel template and optionally inject calibration values.

    Args:
        key: Name of the channel template to load.
        erodibility: Optional override for the erodibility parameter.
        critical_shear: Optional override for the critical shear parameter.
        chnnbr: Optional override for the Manning roughness break number.
        chnn: Optional override for the Manning roughness coefficient.

    Returns:
        Channel definition dictionary with formatted ``contents``.

    Raises:
        KeyError: If ``key`` does not correspond to a known channel template.
    """
    definitions = load_channels()
    channel = definitions[key].copy()

    if any(value is not None for value in (erodibility, critical_shear, chnnbr, chnn)):
        contents = channel["contents"].split("\n")

        line7_tokens = contents[7].split()
        if chnnbr is not None:
            line7_tokens[1] = str(chnnbr)
        contents[7] = " ".join(line7_tokens)

        line8_tokens = contents[8].split()
        if chnn is not None:
            line8_tokens[0] = str(chnn)
        if erodibility is not None:
            line8_tokens[1] = str(erodibility)
        if critical_shear is not None:
            line8_tokens[2] = str(critical_shear)
        contents[8] = " ".join(line8_tokens)

        channel["contents"] = "\n".join(contents)

    return channel


if __name__ == "__main__":  # pragma: no cover
    from pprint import pprint

    pprint(get_channel("OnRock 2", erodibility=99, critical_shear=110))
