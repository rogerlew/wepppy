from __future__ import annotations

from types import SimpleNamespace
from unittest.mock import Mock

import pytest

from wepppy.nodb.core import ClimateMode
from wepppy.runtime_paths.errors import NoDirError
from wepppy.rq import wepp_rq_stage_helpers
from wepppy.rq.wepp_rq_stage_helpers import (
    check_execution_climate,
    recover_mixed_nodir_roots,
    with_stage_read_projections,
)

pytestmark = pytest.mark.unit


@pytest.mark.parametrize('mode', [ClimateMode.SingleStorm, ClimateMode.UserDefinedSingleStorm])
def test_individual_single_storm_runs_with_an_advisory(mode, caplog, monkeypatch) -> None:
    parser = Mock(return_value=SimpleNamespace(is_single_storm=True))
    monkeypatch.setattr(wepp_rq_stage_helpers, 'ClimateFile', parser)
    check_execution_climate(SimpleNamespace(is_single_storm=True, climate_mode=mode, cli_path='active.cli'))
    assert 'Single-storm climates are deprecated.' in caplog.text


def test_continuous_upload_with_stale_single_storm_mode_is_not_run_as_an_event(monkeypatch) -> None:
    monkeypatch.setattr(wepp_rq_stage_helpers, 'ClimateFile', lambda _path: SimpleNamespace(is_single_storm=False))
    with pytest.raises(ValueError, match='active upload does not contain one event'):
        check_execution_climate(SimpleNamespace(is_single_storm=True, climate_mode=ClimateMode.UserDefinedSingleStorm,
                                                cli_path='active.cli'))


def test_batch_still_reports_the_postprocessing_limitation() -> None:
    with pytest.raises(ValueError, match='require per-event postprocessing'):
        check_execution_climate(SimpleNamespace(is_single_storm=True, climate_mode=ClimateMode.SingleStormBatch))


def test_prepared_single_storm_does_not_require_the_original_upload(caplog) -> None:
    check_execution_climate(SimpleNamespace(is_single_storm=True, climate_mode=ClimateMode.UserDefinedSingleStorm),
                            prepared_inputs=True)
    assert 'Single-storm climates are deprecated.' in caplog.text


def test_continuous_mode_does_not_emit_an_advisory(caplog) -> None:
    check_execution_climate(SimpleNamespace(is_single_storm=False))
    assert 'Single-storm' not in caplog.text


def test_recover_mixed_nodir_roots_returns_empty_when_directory_only(tmp_path) -> None:
    wd = tmp_path / "run"
    (wd / "watershed").mkdir(parents=True, exist_ok=True)

    assert recover_mixed_nodir_roots(str(wd), roots=("watershed",)) == tuple()


def test_recover_mixed_nodir_roots_raises_for_archive_only_root(tmp_path) -> None:
    wd = tmp_path / "run"
    wd.mkdir(parents=True, exist_ok=True)
    (wd / "watershed.nodir").write_bytes(b"archive")

    with pytest.raises(NoDirError) as exc_info:
        recover_mixed_nodir_roots(str(wd), roots=("watershed",))

    assert exc_info.value.code == "NODIR_ARCHIVE_RETIRED"


def test_recover_mixed_nodir_roots_raises_for_mixed_root(tmp_path) -> None:
    wd = tmp_path / "run"
    (wd / "watershed").mkdir(parents=True, exist_ok=True)
    (wd / "watershed.nodir").write_bytes(b"archive")

    with pytest.raises(NoDirError) as exc_info:
        recover_mixed_nodir_roots(str(wd), roots=("watershed",))

    assert exc_info.value.code == "NODIR_MIXED_STATE"


def test_with_stage_read_projections_allows_directory_only_roots(tmp_path) -> None:
    wd = tmp_path / "run"
    (wd / "watershed").mkdir(parents=True, exist_ok=True)

    with with_stage_read_projections(
        str(wd),
        roots=("watershed",),
        purpose="unit",
    ):
        pass


def test_with_stage_read_projections_raises_for_archive_only_root(tmp_path) -> None:
    wd = tmp_path / "run"
    wd.mkdir(parents=True, exist_ok=True)
    (wd / "watershed.nodir").write_bytes(b"archive")

    with pytest.raises(NoDirError) as exc_info:
        with with_stage_read_projections(
            str(wd),
            roots=("watershed",),
            purpose="unit",
        ):
            pass

    assert exc_info.value.code == "NODIR_ARCHIVE_RETIRED"


def test_with_stage_read_projections_raises_for_mixed_root(tmp_path) -> None:
    wd = tmp_path / "run"
    (wd / "watershed").mkdir(parents=True, exist_ok=True)
    (wd / "watershed.nodir").write_bytes(b"archive")

    with pytest.raises(NoDirError) as exc_info:
        with with_stage_read_projections(
            str(wd),
            roots=("watershed",),
            purpose="unit",
        ):
            pass

    assert exc_info.value.code == "NODIR_MIXED_STATE"
