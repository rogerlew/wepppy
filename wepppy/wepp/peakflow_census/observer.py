"""Parser for the accepted observer-enabled WEPP trace."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Any

import pandas as pd


def parse_trace(path: Path, scenario: str, hillslope_id: int) -> pd.DataFrame:
    scalars: dict[tuple[int, int, int, int], dict[str, Any]] = {}
    rows: list[dict[str, Any]] = []
    with path.open(newline="") as stream:
        for fields in csv.reader(stream):
            if not fields:
                continue
            if fields[0] == "SCALAR":
                key = tuple(int(value) for value in fields[1:5])
                numeric = [float(value) for value in fields[5:18]]
                scalars[key] = {"scenario": scenario, "hillslope_id": hillslope_id,
                                "year": key[0], "day": key[1], "ofe": key[2], "ordinal": key[3],
                                **dict(zip(["runoff_pre_m", "runoff_post_m", "surdra_raw_m",
                                           "surdra_realized_m", "positive_excess_duration_s",
                                           "assignment_duration_s", "remax_m_s", "postmax_m_s",
                                           "added_rate_m_s", "tp2_s", "alpha", "m", "length_m"],
                                          numeric, strict=True)),
                                "forcing_steps": int(fields[18]), "forcing_mode": int(fields[19])}
            elif fields[0] == "RESULT":
                key = tuple(int(value) for value in fields[1:5])
                try:
                    row = scalars.pop(key)
                except KeyError as error:
                    raise ValueError(f"result without scalar in {path}: {key}") from error
                row.update({"solver": fields[5], "peak_m_s": float(fields[6])})
                rows.append(row)
    if scalars:
        raise ValueError(f"trace has {len(scalars)} unterminated solver calls: {path}")
    if not rows:
        raise ValueError(f"trace contains no solver results: {path}")
    return pd.DataFrame(rows)
