from __future__ import annotations

import errno
import shutil
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List

import pyarrow as pa
import pyarrow.parquet as pq

from wepppy.all_your_base.hydro import determine_wateryear

SOIL_FILENAME = "soil_pw0.txt"
SOIL_PARQUET = "soil_pw0.parquet"
CHUNK_SIZE = 250_000


def _field(name: str, dtype: pa.DataType, units: str | None = None) -> pa.Field:
    if units is None:
        return pa.field(name, dtype)
    return pa.field(name, dtype).with_metadata({b"units": units.encode()})


SCHEMA = pa.schema(
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


def _julian_to_calendar(year: int, julian: int) -> tuple[int, int]:
    base = datetime(year, 1, 1) + timedelta(days=julian - 1)
    return base.month, base.day


def _init_column_store() -> Dict[str, List]:
    return {name: [] for name in SCHEMA.names}


def _flush_chunk(store: Dict[str, List], writer: pq.ParquetWriter) -> None:
    if not store["wepp_id"]:
        return
    table = pa.table(store, schema=SCHEMA)
    writer.write_table(table)
    store.clear()
    store.update(_init_column_store())


def _write_soil_parquet(
    source: Path,
    target: Path,
    *,
    chunk_size: int = CHUNK_SIZE,
) -> None:
    tmp_target = target.with_suffix(f"{target.suffix}.tmp")
    if tmp_target.exists():
        tmp_target.unlink()

    writer = pq.ParquetWriter(
        tmp_target,
        SCHEMA,
        compression="snappy",
        use_dictionary=True,
    )

    store = _init_column_store()
    header_found = False
    data_start = 0
    row_counter = 0

    try:
        with source.open("r") as stream:
            for idx, raw_line in enumerate(stream):
                stripped = raw_line.strip()
                if not header_found:
                    if stripped.startswith("OFE"):
                        header_found = True
                        data_start = idx + 2
                    continue

                if idx < data_start:
                    continue

                if not stripped or stripped.startswith("-"):
                    continue

                tokens = stripped.split()
                if not tokens or not tokens[0].isdigit():
                    continue
                if len(tokens) != 14:
                    raise ValueError(f"Unexpected token count in soil row: {raw_line}")

                ofe = int(tokens[0])
                julian = int(tokens[1])
                year = int(tokens[2])
                values = [float(tok) for tok in tokens[3:]]
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

                store["wepp_id"].append(ofe)
                store["ofe_id"].append(ofe)
                store["year"].append(year)
                store["day"].append(julian)
                store["julian"].append(julian)
                store["month"].append(month)
                store["day_of_month"].append(day_of_month)
                store["water_year"].append(water_year)
                store["OFE"].append(ofe)
                store["Day"].append(julian)
                store["Y"].append(year)
                store["Poros"].append(poros)
                store["Keff"].append(keff)
                store["Suct"].append(suct)
                store["FC"].append(fc)
                store["WP"].append(wp)
                store["Rough"].append(rough)
                store["Ki"].append(ki)
                store["Kr"].append(kr)
                store["Tauc"].append(tauc)
                store["Saturation"].append(saturation)
                store["TSW"].append(tsw)

                row_counter += 1
                if row_counter % chunk_size == 0:
                    _flush_chunk(store, writer)

        if store["wepp_id"]:
            _flush_chunk(store, writer)
        elif row_counter == 0:
            writer.write_table(pa.table(_init_column_store(), schema=SCHEMA))
    except Exception:
        writer.close()
        if tmp_target.exists():
            tmp_target.unlink()
        raise
    else:
        writer.close()
        try:
            tmp_target.replace(target)
        except OSError as exc:
            if exc.errno == errno.EXDEV:
                shutil.move(str(tmp_target), str(target))
            else:
                raise


def run_wepp_watershed_soil_interchange(wepp_output_dir: Path | str) -> Path:
    base = Path(wepp_output_dir)
    if not base.exists():
        raise FileNotFoundError(base)

    soil_path = base / SOIL_FILENAME
    if not soil_path.exists():
        raise FileNotFoundError(soil_path)

    interchange_dir = base / "interchange"
    interchange_dir.mkdir(parents=True, exist_ok=True)

    target = interchange_dir / SOIL_PARQUET
    _write_soil_parquet(soil_path, target)
    return target
