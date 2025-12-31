from __future__ import annotations

import errno
import logging
import shutil
from pathlib import Path
from typing import Dict, List

import pyarrow as pa
import pyarrow.parquet as pq

from ._utils import _parse_float
from .schema_utils import pa_field
from .versioning import schema_with_version

TC_OUT_FILENAME = "tc_out.txt"
TC_OUT_PARQUET = "tc_out.parquet"
CHUNK_SIZE = 250_000

LOGGER = logging.getLogger(__name__)


SCHEMA = schema_with_version(
    pa.schema(
        [
            pa_field("day", pa.int16(), description="Julian day from tc_out.txt"),
            pa_field("year", pa.int16(), description="Calendar year"),
            pa_field(
                "Time of Conc (hr)",
                pa.float64(),
                units="hr",
                description="Event time of concentration at the outlet channel",
            ),
            pa_field(
                "Storm Duration (hr)",
                pa.float64(),
                units="hr",
                description="Storm duration for the event",
            ),
            pa_field(
                "Storm Peak (hr)",
                pa.float64(),
                units="hr",
                description="Time to storm peak for the event",
            ),
        ]
    )
)


def _init_column_store() -> Dict[str, List]:
    return {name: [] for name in SCHEMA.names}


def _flush_chunk(store: Dict[str, List], writer: pq.ParquetWriter) -> None:
    if not store["day"]:
        return
    table = pa.table(store, schema=SCHEMA)
    writer.write_table(table)
    store.clear()
    store.update(_init_column_store())


def _find_outlet_channel(source: Path) -> int | None:
    outlet_channel = None
    with source.open("r") as stream:
        for raw_line in stream:
            stripped = raw_line.strip()
            if not stripped or stripped.startswith("Element") or stripped.startswith("-"):
                continue

            tokens = stripped.split()
            if len(tokens) < 9 or tokens[1] != "C":
                continue

            try:
                channel_id = int(tokens[2])
            except ValueError:
                continue

            if outlet_channel is None or channel_id > outlet_channel:
                outlet_channel = channel_id

    return outlet_channel


def _write_tc_out_parquet(
    source: Path,
    target: Path,
    *,
    outlet_channel: int,
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
    row_counter = 0

    try:
        with source.open("r") as stream:
            for raw_line in stream:
                stripped = raw_line.strip()
                if not stripped or stripped.startswith("Element") or stripped.startswith("-"):
                    continue

                tokens = stripped.split()
                if len(tokens) < 9 or tokens[1] != "C":
                    continue

                try:
                    channel_id = int(tokens[2])
                except ValueError:
                    continue
                if channel_id != outlet_channel:
                    continue

                try:
                    day = int(tokens[3])
                    year = int(tokens[4])
                except ValueError:
                    continue

                store["day"].append(day)
                store["year"].append(year)
                store["Time of Conc (hr)"].append(_parse_float(tokens[6]))
                store["Storm Duration (hr)"].append(_parse_float(tokens[7]))
                store["Storm Peak (hr)"].append(_parse_float(tokens[8]))

                row_counter += 1
                if row_counter % chunk_size == 0:
                    _flush_chunk(store, writer)

        if store["day"]:
            _flush_chunk(store, writer)
        else:
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


def run_wepp_watershed_tc_out_interchange(wepp_output_dir: Path | str) -> Path | None:
    base = Path(wepp_output_dir)
    if not base.exists():
        raise FileNotFoundError(base)

    source = base / TC_OUT_FILENAME
    if not source.exists():
        LOGGER.info("tc_out.txt not found in %s; skipping tc_out parquet.", base)
        return None

    outlet_channel = _find_outlet_channel(source)
    if outlet_channel is None:
        LOGGER.info("tc_out.txt has no channel rows; skipping tc_out parquet.")
        return None

    target = base / TC_OUT_PARQUET
    _write_tc_out_parquet(source, target, outlet_channel=outlet_channel)
    return target
