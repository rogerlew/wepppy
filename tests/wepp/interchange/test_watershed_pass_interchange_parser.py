from __future__ import annotations

import pytest
import pyarrow.parquet as pq

from .module_loader import cleanup_import_state, load_module


_watershed_pass = load_module(
    "wepppy.wepp.interchange.watershed_pass_interchange",
    "wepppy/wepp/interchange/watershed_pass_interchange.py",
)
cleanup_import_state()

_ValueCollector = _watershed_pass._ValueCollector
_write_events_parquet = _watershed_pass._write_events_parquet


@pytest.mark.unit
def test_value_collector_handles_joined_tokens() -> None:
    reader = _ValueCollector(iter(["0.97059-100 1.5", " -2.5"]))
    assert reader.read(4) == [0.97059, -100.0, 1.5, -2.5]


@pytest.mark.unit
def test_write_events_parquet_absorbs_stray_numeric_lines(tmp_path) -> None:
    out_path = tmp_path / "events.parquet"
    lines = iter(
        [
            "EVENT 1 1",
            "1",
            "2",
            "3",
            "4",
            "5",
            "6",
            "7",
            "8",
            "9",
            "10",
            "11",
            "12",
            "13",
            "14",
            "0.5 0.6",  # stray numeric line should be buffered
            "NO EVENT 1 2",
        ]
    )
    global_meta = {"version": 1, "nhill": 1, "max_years": 1, "begin_year": 1, "npart": 0}

    _write_events_parquet(
        lines,
        hillslope_ids=[1],
        nhill=1,
        npart=0,
        global_meta=global_meta,
        target=out_path,
        calendar_lookup=None,
        chunk_size=10,
    )

    table = pq.read_table(out_path)
    assert table.num_rows == 2
    assert list(table.column("event")) == ["EVENT", "NO EVENT"]
    assert table.column("gwbfv").to_pylist()[-1] == 0.5
    assert table.column("gwdsv").to_pylist()[-1] == 0.6
