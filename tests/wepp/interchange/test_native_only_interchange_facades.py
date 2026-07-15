from __future__ import annotations

import shutil
from pathlib import Path
from types import SimpleNamespace

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
from wepppy.wepp.interchange.watershed_tc_out_interchange import (
    run_wepp_watershed_tc_out_interchange,
)


pytestmark = pytest.mark.unit

FIXTURE_OUTPUT = (
    Path(__file__).parent / "fixtures" / "decimal-pleasing" / "wepp" / "output"
)
PROJECT_OUTPUT = Path(__file__).parent / "test_project" / "output"


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

    expected = {
        "H.ebe.parquet",
        "H.element.parquet",
        "H.loss.parquet",
        "H.pass.parquet",
        "H.soil.parquet",
        "H.wat.parquet",
        "chan.out.parquet",
        "chanwb.parquet",
        "chnwb.parquet",
        "ebe_pw0.parquet",
        "loss_pw0.all_years.chn.parquet",
        "loss_pw0.all_years.class_data.parquet",
        "loss_pw0.all_years.hill.parquet",
        "loss_pw0.all_years.out.parquet",
        "loss_pw0.chn.parquet",
        "loss_pw0.class_data.parquet",
        "loss_pw0.hill.parquet",
        "loss_pw0.out.parquet",
        "pass_pw0.events.parquet",
        "pass_pw0.metadata.parquet",
        "soil_pw0.parquet",
        "tc_out.parquet",
    }
    observed = {path.name for path in interchange_dir.glob("*.parquet")}
    assert expected <= observed
    for name in expected:
        pq.ParquetFile(interchange_dir / name)

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
