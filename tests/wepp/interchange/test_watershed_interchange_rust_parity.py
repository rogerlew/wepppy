from __future__ import annotations

import importlib
import os
import shutil
from functools import partial
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from .module_loader import PROJECT_OUTPUT, cleanup_import_state, load_module
from .schema_snapshot import (
    assert_schema_matches_snapshot,
    assert_version_metadata,
    schema_from_parquet,
)


pytestmark = pytest.mark.integration


if os.getenv("WEPPPY_RUST_INTERCHANGE_TESTS") != "1":
    pytest.skip(
        "Rust parity tests disabled; set WEPPPY_RUST_INTERCHANGE_TESTS=1 to enable.",
        allow_module_level=True,
    )

try:
    rust_interchange = importlib.import_module("wepppyo3.wepp_interchange")
except Exception:
    pytest.skip("wepppyo3.wepp_interchange not available in this environment.", allow_module_level=True)

load_module("wepppy.all_your_base", "wepppy/all_your_base/__init__.py")
load_module("wepppy.all_your_base.hydro", "wepppy/all_your_base/hydro/hydro.py")
rust_helpers = load_module("wepppy.wepp.interchange._rust_interchange", "wepppy/wepp/interchange/_rust_interchange.py")

pass_mod = load_module(
    "wepppy.wepp.interchange.watershed_pass_interchange",
    "wepppy/wepp/interchange/watershed_pass_interchange.py",
)
soil_mod = load_module(
    "wepppy.wepp.interchange.watershed_soil_interchange",
    "wepppy/wepp/interchange/watershed_soil_interchange.py",
)
loss_mod = load_module(
    "wepppy.wepp.interchange.watershed_loss_interchange",
    "wepppy/wepp/interchange/watershed_loss_interchange.py",
)
chan_mod = load_module(
    "wepppy.wepp.interchange.watershed_chan_peak_interchange",
    "wepppy/wepp/interchange/watershed_chan_peak_interchange.py",
)
ebe_mod = load_module(
    "wepppy.wepp.interchange.watershed_ebe_interchange",
    "wepppy/wepp/interchange/watershed_ebe_interchange.py",
)
chanwb_mod = load_module(
    "wepppy.wepp.interchange.watershed_chanwb_interchange",
    "wepppy/wepp/interchange/watershed_chanwb_interchange.py",
)
chnwb_mod = load_module(
    "wepppy.wepp.interchange.watershed_chnwb_interchange",
    "wepppy/wepp/interchange/watershed_chnwb_interchange.py",
)
hill_pass_mod = load_module(
    "wepppy.wepp.interchange.hill_pass_interchange",
    "wepppy/wepp/interchange/hill_pass_interchange.py",
)
hill_ebe_mod = load_module(
    "wepppy.wepp.interchange.hill_ebe_interchange",
    "wepppy/wepp/interchange/hill_ebe_interchange.py",
)
hill_element_mod = load_module(
    "wepppy.wepp.interchange.hill_element_interchange",
    "wepppy/wepp/interchange/hill_element_interchange.py",
)
hill_loss_mod = load_module(
    "wepppy.wepp.interchange.hill_loss_interchange",
    "wepppy/wepp/interchange/hill_loss_interchange.py",
)
hill_soil_mod = load_module(
    "wepppy.wepp.interchange.hill_soil_interchange",
    "wepppy/wepp/interchange/hill_soil_interchange.py",
)
hill_wat_mod = load_module(
    "wepppy.wepp.interchange.hill_wat_interchange",
    "wepppy/wepp/interchange/hill_wat_interchange.py",
)
cleanup_import_state()


def _resolve_source(base: Path, filename: str) -> Path | None:
    path = base / filename
    if path.exists():
        return path
    gz_path = path.with_suffix(path.suffix + ".gz")
    if gz_path.exists():
        return gz_path
    return None


def _compare_parquet(py_path: Path, rust_path: Path) -> None:
    py_table = pq.read_table(py_path)
    rust_table = pq.read_table(rust_path)

    assert py_table.schema.equals(rust_table.schema, check_metadata=True)
    assert py_table.num_rows == rust_table.num_rows

    py_df = py_table.to_pandas(strings_to_categorical=False)
    rust_df = rust_table.to_pandas(strings_to_categorical=False)
    pd.testing.assert_frame_equal(py_df, rust_df, check_dtype=False, check_exact=False)


def _assert_schema_snapshot(parquet_path: Path, snapshot_name: str) -> None:
    schema = schema_from_parquet(parquet_path)
    assert_version_metadata(schema)
    assert_schema_matches_snapshot(schema, snapshot_name)


def _populate_output_dir(dest: Path, filenames: list[str]) -> None:
    dest.mkdir(parents=True, exist_ok=True)
    for filename in filenames:
        src = _resolve_source(PROJECT_OUTPUT, filename)
        if src is None:
            raise FileNotFoundError(f"Missing required fixture {filename} in {PROJECT_OUTPUT}")
        shutil.copy2(src, dest / src.name)


def _resolve_cli_source() -> Path | None:
    cli_root = PROJECT_OUTPUT.parent / "runs"
    candidates = sorted(cli_root.glob("*.cli"))
    if not candidates:
        return None
    return candidates[0]


def _install_cli_calendar(dest: Path) -> bool:
    cli_source = _resolve_cli_source()
    if cli_source is None:
        return False
    cli_dir = dest / "climate"
    cli_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(cli_source, cli_dir / cli_source.name)
    return True


def _select_hillslope_ids(sample_count: int) -> list[str]:
    candidates = sorted(PROJECT_OUTPUT.glob("H*.pass.dat"))
    if not candidates:
        return []
    ids: list[str] = []
    for path in candidates[:sample_count]:
        stem = path.name.split(".")[0]
        ids.append(stem)
    return ids


def _populate_hillslope_subset(dest: Path, ids: list[str], suffix: str) -> list[Path]:
    dest.mkdir(parents=True, exist_ok=True)
    paths: list[Path] = []
    for hid in ids:
        src = PROJECT_OUTPUT / f"{hid}.{suffix}.dat"
        if not src.exists():
            continue
        target = dest / src.name
        shutil.copy2(src, target)
        paths.append(target)
    return paths


def test_watershed_pass_interchange_rust_parity(tmp_path: Path) -> None:
    if not _resolve_source(PROJECT_OUTPUT, "pass_pw0.txt"):
        pytest.skip("pass_pw0 dataset not available in test fixture")

    py_dir = tmp_path / "pass_py"
    rust_dir = tmp_path / "pass_rust"
    _populate_output_dir(py_dir, ["pass_pw0.txt"])
    _populate_output_dir(rust_dir, ["pass_pw0.txt"])

    py_result = pass_mod._run_wepp_watershed_pass_interchange_python(py_dir)

    pass_path = _resolve_source(rust_dir, "pass_pw0.txt")
    assert pass_path is not None
    events_path = rust_dir / "interchange" / pass_mod.EVENTS_PARQUET
    metadata_path = rust_dir / "interchange" / pass_mod.METADATA_PARQUET
    events_path.parent.mkdir(parents=True, exist_ok=True)

    major, minor = rust_helpers.version_args()
    cli_calendar_path = rust_helpers.resolve_cli_calendar_path(rust_dir)

    rust_interchange.watershed_pass_to_parquet(
        str(pass_path),
        str(events_path),
        str(metadata_path),
        major,
        minor,
        cli_calendar_path=str(cli_calendar_path) if cli_calendar_path else None,
        chunk_rows=pass_mod.EVENT_CHUNK_SIZE,
    )

    _compare_parquet(py_result["events"], events_path)
    _compare_parquet(py_result["metadata"], metadata_path)
    _assert_schema_snapshot(py_result["events"], "pass_events")
    _assert_schema_snapshot(py_result["metadata"], "pass_metadata")
    _assert_schema_snapshot(events_path, "pass_events")
    _assert_schema_snapshot(metadata_path, "pass_metadata")


def test_watershed_soil_interchange_rust_parity(tmp_path: Path) -> None:
    if not _resolve_source(PROJECT_OUTPUT, "soil_pw0.txt"):
        pytest.skip("soil_pw0 dataset not available in test fixture")

    py_dir = tmp_path / "soil_py"
    rust_dir = tmp_path / "soil_rust"
    _populate_output_dir(py_dir, ["soil_pw0.txt"])
    _populate_output_dir(rust_dir, ["soil_pw0.txt"])

    py_path = soil_mod._run_wepp_watershed_soil_interchange_python(py_dir)

    soil_path = _resolve_source(rust_dir, "soil_pw0.txt")
    assert soil_path is not None
    rust_path = rust_dir / "interchange" / soil_mod.SOIL_PARQUET
    rust_path.parent.mkdir(parents=True, exist_ok=True)

    major, minor = rust_helpers.version_args()
    cli_calendar_path = rust_helpers.resolve_cli_calendar_path(rust_dir)

    rust_interchange.watershed_soil_to_parquet(
        str(soil_path),
        str(rust_path),
        major,
        minor,
        cli_calendar_path=str(cli_calendar_path) if cli_calendar_path else None,
        chunk_rows=soil_mod.CHUNK_SIZE,
    )

    _compare_parquet(py_path, rust_path)
    _assert_schema_snapshot(py_path, "soil")
    _assert_schema_snapshot(rust_path, "soil")


def test_watershed_loss_interchange_rust_parity(tmp_path: Path) -> None:
    if not (PROJECT_OUTPUT / "loss_pw0.txt").exists():
        pytest.skip("loss_pw0 dataset not available in test fixture")

    py_dir = tmp_path / "loss_py"
    rust_dir = tmp_path / "loss_rust"
    _populate_output_dir(py_dir, ["loss_pw0.txt"])
    _populate_output_dir(rust_dir, ["loss_pw0.txt"])

    py_outputs = loss_mod._run_wepp_watershed_loss_interchange_python(py_dir)

    major, minor = rust_helpers.version_args()
    rust_interchange.watershed_loss_to_parquet(
        str(rust_dir / "loss_pw0.txt"),
        str(rust_dir / "interchange"),
        major,
        minor,
    )

    for key, py_path in py_outputs.items():
        rust_path = rust_dir / "interchange" / py_path.name
        _compare_parquet(py_path, rust_path)
        snapshot_key = f"loss_{key}"
        _assert_schema_snapshot(py_path, snapshot_key)
        _assert_schema_snapshot(rust_path, snapshot_key)


def test_watershed_chan_peak_interchange_rust_parity(tmp_path: Path) -> None:
    if not (PROJECT_OUTPUT / "chan.out").exists():
        pytest.skip("chan.out dataset not available in test fixture")

    py_dir = tmp_path / "chan_py"
    rust_dir = tmp_path / "chan_rust"
    _populate_output_dir(py_dir, ["chan.out"])
    _populate_output_dir(rust_dir, ["chan.out"])

    py_path = chan_mod._run_wepp_watershed_chan_peak_interchange_python(py_dir)

    chan_path = rust_dir / "chan.out"
    rust_path = rust_dir / "interchange" / chan_mod.CHAN_PEAK_PARQUET
    rust_path.parent.mkdir(parents=True, exist_ok=True)

    major, minor = rust_helpers.version_args()
    cli_calendar_path = rust_helpers.resolve_cli_calendar_path(rust_dir)

    rust_interchange.watershed_chan_peak_to_parquet(
        str(chan_path),
        str(rust_path),
        major,
        minor,
        cli_calendar_path=str(cli_calendar_path) if cli_calendar_path else None,
        start_year=None,
        chunk_rows=chan_mod.CHUNK_SIZE,
    )

    _compare_parquet(py_path, rust_path)
    _assert_schema_snapshot(py_path, "chan_peak")
    _assert_schema_snapshot(rust_path, "chan_peak")


def test_watershed_ebe_interchange_rust_parity(tmp_path: Path) -> None:
    if not _resolve_source(PROJECT_OUTPUT, "ebe_pw0.txt"):
        pytest.skip("ebe_pw0 dataset not available in test fixture")

    py_dir = tmp_path / "ebe_py"
    rust_dir = tmp_path / "ebe_rust"
    _populate_output_dir(py_dir, ["ebe_pw0.txt", "chan.out"])
    _populate_output_dir(rust_dir, ["ebe_pw0.txt", "chan.out"])
    if not (_install_cli_calendar(py_dir) and _install_cli_calendar(rust_dir)):
        pytest.skip("CLI fixture unavailable for EBE parity test")

    py_path = ebe_mod._run_wepp_watershed_ebe_interchange_python(py_dir, start_year=None)

    ebe_path = rust_dir / "ebe_pw0.txt"
    rust_path = rust_dir / "interchange" / ebe_mod.EBE_PARQUET
    rust_path.parent.mkdir(parents=True, exist_ok=True)

    major, minor = rust_helpers.version_args()
    cli_calendar_path = rust_helpers.resolve_cli_calendar_path(rust_dir)
    legacy_element_id = ebe_mod._infer_outlet_element_id(rust_dir)

    rust_interchange.watershed_ebe_to_parquet(
        str(ebe_path),
        str(rust_path),
        major,
        minor,
        cli_calendar_path=str(cli_calendar_path) if cli_calendar_path else None,
        start_year=None,
        legacy_element_id=legacy_element_id,
        chunk_rows=ebe_mod.CHUNK_SIZE,
    )

    _compare_parquet(py_path, rust_path)
    _assert_schema_snapshot(py_path, "ebe")
    _assert_schema_snapshot(rust_path, "ebe")


def test_watershed_chanwb_interchange_rust_parity(tmp_path: Path) -> None:
    if not (PROJECT_OUTPUT / "chanwb.out").exists():
        pytest.skip("chanwb.out dataset not available in test fixture")

    py_dir = tmp_path / "chanwb_py"
    rust_dir = tmp_path / "chanwb_rust"
    _populate_output_dir(py_dir, ["chanwb.out"])
    _populate_output_dir(rust_dir, ["chanwb.out"])

    py_path = chanwb_mod._run_wepp_watershed_chanwb_interchange_python(py_dir, start_year=None)

    chanwb_path = rust_dir / "chanwb.out"
    rust_path = rust_dir / "interchange" / chanwb_mod.CHAN_PARQUET
    rust_path.parent.mkdir(parents=True, exist_ok=True)

    major, minor = rust_helpers.version_args()
    cli_calendar_path = rust_helpers.resolve_cli_calendar_path(rust_dir)

    rust_interchange.watershed_chanwb_to_parquet(
        str(chanwb_path),
        str(rust_path),
        major,
        minor,
        cli_calendar_path=str(cli_calendar_path) if cli_calendar_path else None,
        start_year=None,
        chunk_rows=500_000,
    )

    _compare_parquet(py_path, rust_path)
    _assert_schema_snapshot(py_path, "chanwb")
    _assert_schema_snapshot(rust_path, "chanwb")


def test_watershed_chnwb_interchange_rust_parity(tmp_path: Path) -> None:
    if not (PROJECT_OUTPUT / "chnwb.txt").exists():
        pytest.skip("chnwb.txt dataset not available in test fixture")

    py_dir = tmp_path / "chnwb_py"
    rust_dir = tmp_path / "chnwb_rust"
    _populate_output_dir(py_dir, ["chnwb.txt"])
    _populate_output_dir(rust_dir, ["chnwb.txt"])

    py_path = chnwb_mod._run_wepp_watershed_chnwb_interchange_python(py_dir, start_year=None)

    chnwb_path = rust_dir / "chnwb.txt"
    rust_path = rust_dir / "interchange" / chnwb_mod.CHANWB_PARQUET
    rust_path.parent.mkdir(parents=True, exist_ok=True)

    major, minor = rust_helpers.version_args()
    cli_calendar_path = rust_helpers.resolve_cli_calendar_path(rust_dir)

    rust_interchange.watershed_chnwb_to_parquet(
        str(chnwb_path),
        str(rust_path),
        major,
        minor,
        cli_calendar_path=str(cli_calendar_path) if cli_calendar_path else None,
        start_year=None,
        chunk_rows=250_000,
    )

    _compare_parquet(py_path, rust_path)
    _assert_schema_snapshot(py_path, "chnwb")
    _assert_schema_snapshot(rust_path, "chnwb")


def test_hillslope_pass_interchange_rust_parity(tmp_path: Path) -> None:
    ids = _select_hillslope_ids(3)
    if not ids:
        pytest.skip("No hillslope pass files available in test fixture")

    py_dir = tmp_path / "hill_pass_py"
    rust_dir = tmp_path / "hill_pass_rust"
    py_files = _populate_hillslope_subset(py_dir, ids, "pass")
    rust_files = _populate_hillslope_subset(rust_dir, ids, "pass")
    if not py_files or not rust_files:
        pytest.skip("Hillslope pass subset unavailable in test fixture")
    _install_cli_calendar(py_dir)
    _install_cli_calendar(rust_dir)

    py_target = py_dir / "interchange" / "H.pass.parquet"
    py_target.parent.mkdir(parents=True, exist_ok=True)
    calendar_lookup = hill_pass_mod._build_cli_calendar_lookup(py_dir)
    py_parser = partial(hill_pass_mod._parse_pass_file, calendar_lookup=calendar_lookup)
    hill_pass_mod.write_parquet_with_pool(
        py_files,
        py_parser,
        hill_pass_mod.SCHEMA,
        py_target,
        empty_table=hill_pass_mod.EMPTY_TABLE,
        max_workers=0,
    )

    rust_target = rust_dir / "interchange" / "H.pass.parquet"
    rust_target.parent.mkdir(parents=True, exist_ok=True)
    major, minor = rust_helpers.version_args()
    cli_calendar_path = rust_helpers.resolve_cli_calendar_path(rust_dir)

    def _rust_pass_parser(path: Path) -> pa.Table:
        columns = rust_interchange.hillslope_pass_to_columns(
            str(path),
            major,
            minor,
            cli_calendar_path=str(cli_calendar_path) if cli_calendar_path else None,
        )
        return pa.table(columns, schema=hill_pass_mod.SCHEMA)

    hill_pass_mod.write_parquet_with_pool(
        rust_files,
        _rust_pass_parser,
        hill_pass_mod.SCHEMA,
        rust_target,
        empty_table=hill_pass_mod.EMPTY_TABLE,
        max_workers=0,
    )

    _compare_parquet(py_target, rust_target)
    _assert_schema_snapshot(py_target, "hill_pass")
    _assert_schema_snapshot(rust_target, "hill_pass")


def test_hillslope_ebe_interchange_rust_parity(tmp_path: Path) -> None:
    ids = _select_hillslope_ids(3)
    if not ids:
        pytest.skip("No hillslope ebe files available in test fixture")

    py_dir = tmp_path / "hill_ebe_py"
    rust_dir = tmp_path / "hill_ebe_rust"
    py_files = _populate_hillslope_subset(py_dir, ids, "ebe")
    rust_files = _populate_hillslope_subset(rust_dir, ids, "ebe")
    if not py_files or not rust_files:
        pytest.skip("Hillslope ebe subset unavailable in test fixture")
    if not (_install_cli_calendar(py_dir) and _install_cli_calendar(rust_dir)):
        pytest.skip("CLI fixture unavailable for hillslope EBE parity test")

    py_target = py_dir / "interchange" / "H.ebe.parquet"
    py_target.parent.mkdir(parents=True, exist_ok=True)
    calendar_lookup = hill_ebe_mod._build_cli_calendar_lookup(py_dir)
    py_parser = partial(
        hill_ebe_mod._parse_ebe_file,
        start_year=None,
        calendar_lookup=calendar_lookup,
    )
    hill_ebe_mod.write_parquet_with_pool(
        py_files,
        py_parser,
        hill_ebe_mod.SCHEMA,
        py_target,
        empty_table=hill_ebe_mod.EMPTY_TABLE,
        max_workers=0,
    )

    rust_target = rust_dir / "interchange" / "H.ebe.parquet"
    rust_target.parent.mkdir(parents=True, exist_ok=True)
    major, minor = rust_helpers.version_args()
    cli_calendar_path = rust_helpers.resolve_cli_calendar_path(rust_dir)

    def _rust_ebe_parser(path: Path) -> pa.Table:
        columns = rust_interchange.hillslope_ebe_to_columns(
            str(path),
            major,
            minor,
            cli_calendar_path=str(cli_calendar_path) if cli_calendar_path else None,
            start_year=None,
        )
        return pa.table(columns, schema=hill_ebe_mod.SCHEMA)

    hill_ebe_mod.write_parquet_with_pool(
        rust_files,
        _rust_ebe_parser,
        hill_ebe_mod.SCHEMA,
        rust_target,
        empty_table=hill_ebe_mod.EMPTY_TABLE,
        max_workers=0,
    )

    _compare_parquet(py_target, rust_target)
    _assert_schema_snapshot(py_target, "hill_ebe")
    _assert_schema_snapshot(rust_target, "hill_ebe")


def test_hillslope_element_interchange_rust_parity(tmp_path: Path) -> None:
    ids = _select_hillslope_ids(3)
    if not ids:
        pytest.skip("No hillslope element files available in test fixture")

    py_dir = tmp_path / "hill_element_py"
    rust_dir = tmp_path / "hill_element_rust"
    py_files = _populate_hillslope_subset(py_dir, ids, "element")
    rust_files = _populate_hillslope_subset(rust_dir, ids, "element")
    if not py_files or not rust_files:
        pytest.skip("Hillslope element subset unavailable in test fixture")
    _install_cli_calendar(py_dir)
    _install_cli_calendar(rust_dir)

    py_target = py_dir / "interchange" / "H.element.parquet"
    py_target.parent.mkdir(parents=True, exist_ok=True)
    py_parser = partial(hill_element_mod._parse_element_file, start_year=None)
    hill_element_mod.write_parquet_with_pool(
        py_files,
        py_parser,
        hill_element_mod.SCHEMA,
        py_target,
        empty_table=hill_element_mod.EMPTY_TABLE,
        max_workers=0,
    )

    rust_target = rust_dir / "interchange" / "H.element.parquet"
    rust_target.parent.mkdir(parents=True, exist_ok=True)
    major, minor = rust_helpers.version_args()

    def _rust_element_parser(path: Path) -> pa.Table:
        columns = rust_interchange.hillslope_element_to_columns(
            str(path),
            major,
            minor,
            start_year=None,
        )
        return pa.table(columns, schema=hill_element_mod.SCHEMA)

    hill_element_mod.write_parquet_with_pool(
        rust_files,
        _rust_element_parser,
        hill_element_mod.SCHEMA,
        rust_target,
        empty_table=hill_element_mod.EMPTY_TABLE,
        max_workers=0,
    )

    _compare_parquet(py_target, rust_target)
    _assert_schema_snapshot(py_target, "hill_element")
    _assert_schema_snapshot(rust_target, "hill_element")


def test_hillslope_loss_interchange_rust_parity(tmp_path: Path) -> None:
    ids = _select_hillslope_ids(3)
    if not ids:
        pytest.skip("No hillslope loss files available in test fixture")

    py_dir = tmp_path / "hill_loss_py"
    rust_dir = tmp_path / "hill_loss_rust"
    py_files = _populate_hillslope_subset(py_dir, ids, "loss")
    rust_files = _populate_hillslope_subset(rust_dir, ids, "loss")
    if not py_files or not rust_files:
        pytest.skip("Hillslope loss subset unavailable in test fixture")
    _install_cli_calendar(py_dir)
    _install_cli_calendar(rust_dir)

    py_target = py_dir / "interchange" / "H.loss.parquet"
    py_target.parent.mkdir(parents=True, exist_ok=True)
    hill_loss_mod.write_parquet_with_pool(
        py_files,
        hill_loss_mod._parse_loss_file,
        hill_loss_mod.SCHEMA,
        py_target,
        empty_table=hill_loss_mod.EMPTY_TABLE,
        max_workers=0,
    )

    rust_target = rust_dir / "interchange" / "H.loss.parquet"
    rust_target.parent.mkdir(parents=True, exist_ok=True)
    major, minor = rust_helpers.version_args()

    def _rust_loss_parser(path: Path) -> pa.Table:
        columns = rust_interchange.hillslope_loss_to_columns(str(path), major, minor)
        return pa.table(columns, schema=hill_loss_mod.SCHEMA)

    hill_loss_mod.write_parquet_with_pool(
        rust_files,
        _rust_loss_parser,
        hill_loss_mod.SCHEMA,
        rust_target,
        empty_table=hill_loss_mod.EMPTY_TABLE,
        max_workers=0,
    )

    _compare_parquet(py_target, rust_target)
    _assert_schema_snapshot(py_target, "hill_loss")
    _assert_schema_snapshot(rust_target, "hill_loss")


def test_hillslope_soil_interchange_rust_parity(tmp_path: Path) -> None:
    ids = _select_hillslope_ids(3)
    if not ids:
        pytest.skip("No hillslope soil files available in test fixture")

    py_dir = tmp_path / "hill_soil_py"
    rust_dir = tmp_path / "hill_soil_rust"
    py_files = _populate_hillslope_subset(py_dir, ids, "soil")
    rust_files = _populate_hillslope_subset(rust_dir, ids, "soil")
    if not py_files or not rust_files:
        pytest.skip("Hillslope soil subset unavailable in test fixture")
    if not (_install_cli_calendar(py_dir) and _install_cli_calendar(rust_dir)):
        pytest.skip("CLI fixture unavailable for hillslope soil parity test")

    py_target = py_dir / "interchange" / "H.soil.parquet"
    py_target.parent.mkdir(parents=True, exist_ok=True)
    calendar_lookup = hill_soil_mod._build_cli_calendar_lookup(py_dir)
    py_parser = partial(
        hill_soil_mod._parse_soil_file,
        calendar_lookup=calendar_lookup,
        start_year=None,
    )
    hill_soil_mod.write_parquet_with_pool(
        py_files,
        py_parser,
        hill_soil_mod.SCHEMA,
        py_target,
        empty_table=hill_soil_mod.EMPTY_TABLE,
        max_workers=0,
    )

    rust_target = rust_dir / "interchange" / "H.soil.parquet"
    rust_target.parent.mkdir(parents=True, exist_ok=True)
    major, minor = rust_helpers.version_args()
    cli_calendar_path = rust_helpers.resolve_cli_calendar_path(rust_dir)

    def _rust_soil_parser(path: Path) -> pa.Table:
        columns = rust_interchange.hillslope_soil_to_columns(
            str(path),
            major,
            minor,
            cli_calendar_path=str(cli_calendar_path) if cli_calendar_path else None,
            start_year=None,
        )
        return pa.table(columns, schema=hill_soil_mod.SCHEMA)

    hill_soil_mod.write_parquet_with_pool(
        rust_files,
        _rust_soil_parser,
        hill_soil_mod.SCHEMA,
        rust_target,
        empty_table=hill_soil_mod.EMPTY_TABLE,
        max_workers=0,
    )

    _compare_parquet(py_target, rust_target)
    _assert_schema_snapshot(py_target, "hill_soil")
    _assert_schema_snapshot(rust_target, "hill_soil")


def test_hillslope_wat_interchange_rust_parity(tmp_path: Path) -> None:
    ids = _select_hillslope_ids(3)
    if not ids:
        pytest.skip("No hillslope wat files available in test fixture")

    py_dir = tmp_path / "hill_wat_py"
    rust_dir = tmp_path / "hill_wat_rust"
    py_files = _populate_hillslope_subset(py_dir, ids, "wat")
    rust_files = _populate_hillslope_subset(rust_dir, ids, "wat")
    if not py_files or not rust_files:
        pytest.skip("Hillslope wat subset unavailable in test fixture")
    if not (_install_cli_calendar(py_dir) and _install_cli_calendar(rust_dir)):
        pytest.skip("CLI fixture unavailable for hillslope wat parity test")

    py_target = py_dir / "interchange" / "H.wat.parquet"
    py_target.parent.mkdir(parents=True, exist_ok=True)
    calendar_lookup = hill_wat_mod._build_cli_calendar_lookup(py_dir)
    py_parser = partial(hill_wat_mod._parse_wat_file, calendar_lookup=calendar_lookup)
    hill_wat_mod.write_parquet_with_pool(
        py_files,
        py_parser,
        hill_wat_mod.SCHEMA,
        py_target,
        empty_table=hill_wat_mod.EMPTY_TABLE,
        max_workers=0,
    )

    rust_target = rust_dir / "interchange" / "H.wat.parquet"
    rust_target.parent.mkdir(parents=True, exist_ok=True)
    major, minor = rust_helpers.version_args()
    cli_calendar_path = rust_helpers.resolve_cli_calendar_path(rust_dir)

    def _rust_wat_parser(path: Path) -> pa.Table:
        columns = rust_interchange.hillslope_wat_to_columns(
            str(path),
            major,
            minor,
            cli_calendar_path=str(cli_calendar_path) if cli_calendar_path else None,
        )
        return pa.table(columns, schema=hill_wat_mod.SCHEMA)

    hill_wat_mod.write_parquet_with_pool(
        rust_files,
        _rust_wat_parser,
        hill_wat_mod.SCHEMA,
        rust_target,
        empty_table=hill_wat_mod.EMPTY_TABLE,
        max_workers=0,
    )

    _compare_parquet(py_target, rust_target)
    _assert_schema_snapshot(py_target, "hill_wat")
    _assert_schema_snapshot(rust_target, "hill_wat")
