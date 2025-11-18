from __future__ import annotations

import errno
import shutil
import logging
from pathlib import Path
from typing import Dict, List

import pyarrow as pa
import pyarrow.parquet as pq

from .schema_utils import pa_field
from ._utils import _build_cli_calendar_lookup, _julian_to_calendar, _parse_float, _wait_for_path
from .versioning import schema_with_version

from wepppy.all_your_base.hydro import determine_wateryear

CHANWB_FILENAME = "chnwb.txt"
CHANWB_PARQUET = "chnwb.parquet"

LOGGER = logging.getLogger(__name__)

MEASUREMENT_COLUMNS: List[tuple[str, str | None, str | None]] = [
    ("P (mm)", "mm", "precipitation"),
    ("RM (mm)", "mm", "rainfall + irrigation + snowmelt"),
    ("Q (mm)", "mm", "daily runoff over effective length"),
    ("Ep (mm)", "mm", "plant transpiration"),
    ("Es (mm)", "mm", "soil evaporation"),
    ("Er (mm)", "mm", "residue evaporation"),
    ("Dp (mm)", "mm", "deep percolation"),
    ("UpStrmQ (mm)", "mm", "Runon added to OFE"),
    ("SubRIn (mm)", "mm", "Subsurface runon added to OFE"),
    ("latqcc (mm)", "mm", "lateral subsurface flow"),
    ("Total Soil Water (mm)", "mm", "Unfrozen water in soil profile"),
    ("frozwt (mm)", "mm", "Frozen water in soil profile"),
    ("Snow Water (mm)", "mm", "Water in surface snow"),
    ("QOFE (mm)", "mm", "Daily runoff scaled to single OFE"),
    ("Tile (mm)", "mm", "Tile drainage"),
    ("Irr (mm)", "mm", "Irrigation"),
    ("Surf (mm)", "mm", "Surface storage"),
    ("Base (mm)", "mm", "Portion of runon from external baseflow"),
    ("Area (m^2)", "m^2", "Area that depths apply over"),
]


SCHEMA = schema_with_version(
    pa.schema(
        [
            pa_field("wepp_id", pa.int32(), description="Channel (OFE) identifier"),
            pa_field("julian", pa.int16(), description="Julian day"),
            pa_field("year", pa.int16(), description="Calendar year"),
            pa_field("simulation_year", pa.int16(), description="Simulation year value from input file"),
            pa_field("month", pa.int8(), description="Calendar month"),
            pa_field("day_of_month", pa.int8(), description="Calendar day of month"),
            pa_field("water_year", pa.int16(), description="Computed water year"),
            pa_field("OFE", pa.int16(), description="Channel OFE index"),
            pa_field("J", pa.int16(), description="Julian day as reported"),
            pa_field("Y", pa.int16(), description="Simulation year as reported"),
        ]
        + [
            pa_field(name, pa.float64(), units=units, description=description)
            for name, units, description in MEASUREMENT_COLUMNS
        ]
    )
)


def _init_column_store() -> Dict[str, List]:
    return {name: [] for name in SCHEMA.names}


def _flush_chunk(store: Dict[str, List], writer: pq.ParquetWriter) -> None:
    if not store["wepp_id"]:
        return
    table = pa.table(store, schema=SCHEMA)
    writer.write_table(table)
    store.clear()
    store.update(_init_column_store())


def _write_chanwb_parquet(
    source: Path,
    target: Path,
    *,
    start_year: int | None = None,
    calendar_lookup: dict[int, list[tuple[int, int]]] | None = None,
    chunk_size: int = 250_000,
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
    row_counter = 0
    header_found = False
    data_offset = 0

    try:
        with source.open("r") as stream:
            for idx, raw_line in enumerate(stream):
                stripped = raw_line.strip()
                if not header_found:
                    if stripped.startswith("OFE"):
                        header_found = True
                        data_offset = idx + 3
                    continue
                if idx < data_offset:
                    continue

                if not stripped or stripped.startswith("-"):
                    continue

                tokens = stripped.split()
                if len(tokens) != 22:
                    continue

                ofe = int(tokens[0])
                julian = int(tokens[1])
                sim_year = int(tokens[2])

                if start_year is not None and sim_year < 1000:
                    year = start_year + sim_year - 1
                else:
                    year = sim_year

                month, day_of_month = _julian_to_calendar(year, julian, calendar_lookup=calendar_lookup)
                store["wepp_id"].append(ofe)
                store["julian"].append(julian)
                store["year"].append(year)
                store["simulation_year"].append(sim_year)
                store["month"].append(month)
                store["day_of_month"].append(day_of_month)
                store["water_year"].append(int(determine_wateryear(year, julian)))
                store["OFE"].append(ofe)
                store["J"].append(julian)
                store["Y"].append(sim_year)

                measurement_values = tokens[3:]
                for (key, _units, _description), token in zip(MEASUREMENT_COLUMNS, measurement_values):
                    store[key].append(_parse_float(token))

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


def run_wepp_watershed_chnwb_interchange(
    wepp_output_dir: Path | str, *, start_year: int | None = None
) -> Path:
    base = Path(wepp_output_dir)
    if not base.exists():
        raise FileNotFoundError(base)

    try:
        start_year = int(start_year)  # type: ignore
    except (TypeError, ValueError):
        start_year = None

    source = base / CHANWB_FILENAME
    _wait_for_path(source)

    interchange_dir = base / "interchange"
    interchange_dir.mkdir(parents=True, exist_ok=True)
    target = interchange_dir / CHANWB_PARQUET
    calendar_lookup = _build_cli_calendar_lookup(base, log=LOGGER)
    _write_chanwb_parquet(source, target, start_year=start_year, calendar_lookup=calendar_lookup)
    return target
