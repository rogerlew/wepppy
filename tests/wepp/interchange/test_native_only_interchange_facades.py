from __future__ import annotations

import shutil
from pathlib import Path
from types import SimpleNamespace

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from wepppy.wepp.interchange import _rust_interchange as native
from wepppy.wepp.interchange.hill_interchange import run_wepp_hillslope_interchange
from wepppy.wepp.interchange.hill_loss_interchange import (
    run_wepp_hillslope_loss_interchange,
)
from wepppy.wepp.interchange.watershed_interchange import (
    run_wepp_watershed_interchange,
)
from wepppy.wepp.interchange.watershed_soil_interchange import (
    run_wepp_watershed_soil_interchange,
)
from wepppy.wepp.interchange.watershed_tc_out_interchange import (
    run_wepp_watershed_tc_out_interchange,
)

from .schema_snapshot import (
    SNAPSHOT_TARGETS,
    assert_schema_matches_snapshot,
    assert_version_metadata,
    schema_from_parquet,
)


pytestmark = pytest.mark.unit

FIXTURE_OUTPUT = (
    Path(__file__).parent / "fixtures" / "decimal-pleasing" / "wepp" / "output"
)
PROJECT_OUTPUT = Path(__file__).parent / "test_project" / "output"
DYNAMIC_SCHEMA_METADATA_KEYS = frozenset(
    {"average_years", "begin_year", "max_years", "nhill"}
)


def _copy_compact_project(target: Path) -> None:
    target.mkdir(parents=True)
    for pattern in ("H1.*", "H2.*", "H3.*"):
        for source in FIXTURE_OUTPUT.glob(pattern):
            shutil.copy2(source, target / source.name)
    for name in (
        "chanwb.out",
        "chnwb.txt",
        "loss_pw0.txt",
        "pass_pw0.txt",
        "soil_pw0.txt",
        "tc_out.txt",
    ):
        shutil.copy2(FIXTURE_OUTPUT / name, target / name)
    for name in ("chan.out", "ebe_pw0.txt"):
        shutil.copy2(PROJECT_OUTPUT / name, target / name)


def test_public_facades_generate_complete_native_interchange(tmp_path: Path) -> None:
    output = tmp_path / "wepp" / "output"
    _copy_compact_project(output)

    interchange_dir = run_wepp_hillslope_interchange(output, max_workers=1)
    assert interchange_dir == output / "interchange"

    assert run_wepp_watershed_interchange(output, start_year=2000) == interchange_dir
    assert run_wepp_watershed_tc_out_interchange(output) == (
        interchange_dir / "tc_out.parquet"
    )

    expected = set(SNAPSHOT_TARGETS.values())
    observed = {path.name for path in interchange_dir.glob("*.parquet")}
    assert observed == expected
    for snapshot_name, name in SNAPSHOT_TARGETS.items():
        schema = schema_from_parquet(interchange_dir / name)
        assert_version_metadata(schema)
        assert_schema_matches_snapshot(
            schema,
            snapshot_name,
            ignored_metadata_keys=DYNAMIC_SCHEMA_METADATA_KEYS,
        )

    for name in (
        "H.ebe.parquet",
        "H.element.parquet",
        "H.loss.parquet",
        "H.pass.parquet",
        "H.soil.parquet",
        "H.wat.parquet",
    ):
        assert pq.ParquetFile(interchange_dir / name).num_row_groups == 3


def test_missing_native_writer_fails_without_publishing_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "H1.loss.dat").write_text("native writer must own parsing\n")
    monkeypatch.setattr(
        native,
        "_import_wepppyo3_interchange",
        lambda: SimpleNamespace(),
    )

    with pytest.raises(
        native.WeppInterchangeUnavailableError,
        match="hillslope_loss_files_to_parquet",
    ):
        run_wepp_hillslope_loss_interchange(tmp_path)

    assert not (tmp_path / "interchange" / "H.loss.parquet").exists()


def test_native_writer_failure_retains_cause_without_publishing_target(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "H1.loss.dat").write_text("native writer must own parsing\n")
    cause = ValueError("malformed native record")

    def fail_writer(*_args, **_kwargs) -> None:
        raise cause

    monkeypatch.setattr(
        native,
        "_import_wepppyo3_interchange",
        lambda: SimpleNamespace(hillslope_loss_files_to_parquet=fail_writer),
    )

    with pytest.raises(native.WeppInterchangeExecutionError) as raised:
        run_wepp_hillslope_loss_interchange(tmp_path)

    assert raised.value.__cause__ is cause
    assert not (tmp_path / "interchange" / "H.loss.parquet").exists()


def test_soil_schema_failure_preserves_previous_target_and_retains_cause(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    (tmp_path / "soil_pw0.txt").write_text("native writer owns parsing\n")
    interchange_dir = tmp_path / "interchange"
    interchange_dir.mkdir()
    target = interchange_dir / "soil_pw0.parquet"
    target.write_bytes(b"previous generation")

    def write_wrong_schema(
        _source: str,
        staged_target: str,
        *_args,
        **_kwargs,
    ) -> None:
        pq.write_table(pa.table({"wrong": [1]}), staged_target)

    monkeypatch.setattr(
        native,
        "_import_wepppyo3_interchange",
        lambda: SimpleNamespace(watershed_soil_to_parquet=write_wrong_schema),
    )

    with pytest.raises(native.WeppInterchangeExecutionError) as raised:
        run_wepp_watershed_soil_interchange(tmp_path)

    assert isinstance(raised.value.__cause__, ValueError)
    assert target.read_bytes() == b"previous generation"
    assert list(interchange_dir.glob(".soil_pw0.parquet.*.stage")) == []
