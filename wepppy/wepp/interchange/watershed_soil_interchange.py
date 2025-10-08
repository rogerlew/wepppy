from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

import pyarrow as pa
import pyarrow.parquet as pq

from wepppy.all_your_base.hydro import determine_wateryear

SOIL_FILENAME = "soil_pw0.txt"
SOIL_PARQUET = "soil_pw0.parquet"


def _julian_to_calendar(year: int, julian: int) -> tuple[int, int]:
    base = datetime(year, 1, 1) + timedelta(days=julian - 1)
    return base.month, base.day


def _parse_soil_file(path: Path) -> pa.Table:
    with path.open("r") as stream:
        lines = stream.readlines()

    header_idx = None
    for idx, line in enumerate(lines):
        if line.strip().startswith("OFE"):
            header_idx = idx
            break

    if header_idx is None:
        raise ValueError("Unable to locate soil header line in soil_pw0.txt")

    data_lines = lines[header_idx + 2 :]  # skip units line

    column_store: Dict[str, List] = {
        "wepp_id": [],
        "ofe_id": [],
        "year": [],
        "day": [],
        "julian": [],
        "month": [],
        "day_of_month": [],
        "water_year": [],
        "OFE": [],
        "Day": [],
        "Y": [],
        "Poros": [],
        "Keff": [],
        "Suct": [],
        "FC": [],
        "WP": [],
        "Rough": [],
        "Ki": [],
        "Kr": [],
        "Tauc": [],
        "Saturation": [],
        "TSW": [],
    }

    for raw_line in data_lines:
        stripped = raw_line.strip()
        if not stripped or stripped.startswith("-"):
            continue
        tokens = stripped.split()
        if not tokens[0].isdigit():
            continue
        if len(tokens) != 14:
            raise ValueError(f"Unexpected token count in soil row: {raw_line}")

        ofe = int(tokens[0])
        julian = int(tokens[1])
        year = int(tokens[2])
        values = list(map(float, tokens[3:]))
        (
            poros,
            keff,
            suct,
            fc,
            wp,
            rough,
            ki,
            kr,
            tauc,
            saturation,
            tsw,
        ) = values

        month, day_of_month = _julian_to_calendar(year, julian)
        water_year = int(determine_wateryear(year, julian))

        column_store["wepp_id"].append(ofe)
        column_store["ofe_id"].append(ofe)
        column_store["year"].append(year)
        column_store["day"].append(julian)
        column_store["julian"].append(julian)
        column_store["month"].append(month)
        column_store["day_of_month"].append(day_of_month)
        column_store["water_year"].append(water_year)
        column_store["OFE"].append(ofe)
        column_store["Day"].append(julian)
        column_store["Y"].append(year)
        column_store["Poros"].append(poros)
        column_store["Keff"].append(keff)
        column_store["Suct"].append(suct)
        column_store["FC"].append(fc)
        column_store["WP"].append(wp)
        column_store["Rough"].append(rough)
        column_store["Ki"].append(ki)
        column_store["Kr"].append(kr)
        column_store["Tauc"].append(tauc)
        column_store["Saturation"].append(saturation)
        column_store["TSW"].append(tsw)

    def _field(name: str, dtype: pa.DataType, units: str | None = None) -> pa.Field:
        if units is None:
            return pa.field(name, dtype)
        return pa.field(name, dtype).with_metadata({b"units": units.encode()})

    schema = pa.schema(
        [
            _field("wepp_id", pa.int32()),
            _field("ofe_id", pa.int16()),
            _field("year", pa.int16()),
            _field("day", pa.int16()),
            _field("julian", pa.int16()),
            _field("month", pa.int8()),
            _field("day_of_month", pa.int8()),
            _field("water_year", pa.int16()),
            _field("OFE", pa.int16()),
            _field("Day", pa.int16()),
            _field("Y", pa.int16()),
            _field("Poros", pa.float64(), "%"),
            _field("Keff", pa.float64(), "mm/hr"),
            _field("Suct", pa.float64(), "mm"),
            _field("FC", pa.float64(), "mm/mm"),
            _field("WP", pa.float64(), "mm/mm"),
            _field("Rough", pa.float64(), "mm"),
            _field("Ki", pa.float64(), "adjsmt"),
            _field("Kr", pa.float64(), "adjsmt"),
            _field("Tauc", pa.float64(), "adjsmt"),
            _field("Saturation", pa.float64(), "frac"),
            _field("TSW", pa.float64(), "mm"),
        ]
    )

    return pa.table(column_store, schema=schema)


def run_wepp_watershed_soil_interchange(wepp_output_dir: Path | str) -> Path:
    base = Path(wepp_output_dir)
    if not base.exists():
        raise FileNotFoundError(base)

    soil_path = base / SOIL_FILENAME
    if not soil_path.exists():
        raise FileNotFoundError(soil_path)

    table = _parse_soil_file(soil_path)

    interchange_dir = base / "interchange"
    interchange_dir.mkdir(parents=True, exist_ok=True)

    target = interchange_dir / SOIL_PARQUET
    pq.write_table(table, target, compression="snappy", use_dictionary=True)
    return target

