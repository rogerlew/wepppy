"""Precondition validation tests against real run-artifact fixtures.

Assembles run-directory layouts from tests/data/path_ce fixtures, then
degrades them to exercise each failure mode with its actionable message.
"""

from __future__ import annotations

import shutil
from pathlib import Path

import pytest

pd = pytest.importorskip("pandas")

from wepppy.nodb.mods.path_ce.preconditions import (
    OUTLET_SEDIMENT_KEY,
    validate_preconditions,
)
from wepppy.nodb.mods.path_ce.presets import default_treatments

FIXTURES = Path(__file__).resolve().parents[3] / "data" / "path_ce"

pytestmark = pytest.mark.unit


def _assemble_run_dir(tmp_path: Path, fixture: str, with_geojson: bool = False) -> Path:
    src = FIXTURES / fixture
    wd = tmp_path / fixture
    (wd / "omni").mkdir(parents=True)
    (wd / "watershed").mkdir()
    for name in (
        "scenarios.hillslope_summaries.parquet",
        "contrasts.out.parquet",
        "scenarios.out.parquet",
        "contrast_id_definitions.psv",
    ):
        if (src / name).exists():
            shutil.copy(src / name, wd / "omni" / name)
    shutil.copy(src / "hillslopes.parquet", wd / "watershed" / "hillslopes.parquet")
    if with_geojson:
        geo = wd / "dem" / "wbt"
        geo.mkdir(parents=True)
        (geo / "subcatchments.WGS.geojson").write_text("{}")
        (geo / "channels.WGS.geojson").write_text("{}")
    return wd


def test_austere_passes_with_all_three_treatments(tmp_path):
    wd = _assemble_run_dir(tmp_path, "austere_inaction", with_geojson=True)
    report = validate_preconditions(str(wd), default_treatments())
    assert report.ok, report.errors
    assert report.mode == "grouped"
    assert report.contrast_groups_path == "omni/contrast_id_definitions.psv"
    assert report.subcatchments_geojson == "dem/wbt/subcatchments.WGS.geojson"
    assert report.warnings == []


def test_missing_geojson_is_warning_not_error(tmp_path):
    wd = _assemble_run_dir(tmp_path, "austere_inaction", with_geojson=False)
    report = validate_preconditions(str(wd), default_treatments())
    assert report.ok
    assert any("WGS.geojson" in w for w in report.warnings)
    assert report.subcatchments_geojson is None


def test_honeyed_fails_partial_treatment_coverage(tmp_path):
    """honeyed-marathoner only has mulch_60 contrasts — 0.5/1 t/ac must be named."""
    wd = _assemble_run_dir(tmp_path, "honeyed_marathoner")
    report = validate_preconditions(str(wd), default_treatments())
    assert not report.ok
    joined = " ".join(report.errors)
    assert "mulch_15_sbs_map" in joined and "mulch_30_sbs_map" in joined
    assert "run Omni" in joined


def test_honeyed_passes_with_mulch60_only(tmp_path):
    wd = _assemble_run_dir(tmp_path, "honeyed_marathoner")
    treatments = [t for t in default_treatments() if t["scenario"] == "mulch_60_sbs_map"]
    report = validate_preconditions(str(wd), treatments)
    assert report.ok, report.errors
    assert report.mode == "grouped"  # psv present


def test_missing_contrasts_is_actionable(tmp_path):
    wd = _assemble_run_dir(tmp_path, "austere_inaction")
    (wd / "omni" / "contrasts.out.parquet").unlink()
    report = validate_preconditions(str(wd), default_treatments())
    assert not report.ok
    assert any("run Omni contrasts" in e for e in report.errors)


def test_missing_scenarios_is_actionable(tmp_path):
    wd = _assemble_run_dir(tmp_path, "austere_inaction")
    (wd / "omni" / "scenarios.hillslope_summaries.parquet").unlink()
    report = validate_preconditions(str(wd), default_treatments())
    assert not report.ok
    assert any("run Omni scenarios" in e for e in report.errors)


def test_no_psv_no_topaz_id_fails_schema_detection(tmp_path):
    wd = _assemble_run_dir(tmp_path, "austere_inaction")
    (wd / "omni" / "contrast_id_definitions.psv").unlink()
    # austere contrasts have no contrast_topaz_id column
    report = validate_preconditions(str(wd), default_treatments())
    assert not report.ok
    assert any("contrast schema" in e for e in report.errors)


def test_cumulative_mode_detected_from_contrast_topaz_id(tmp_path):
    wd = _assemble_run_dir(tmp_path, "austere_inaction")
    (wd / "omni" / "contrast_id_definitions.psv").unlink()
    co_path = wd / "omni" / "contrasts.out.parquet"
    contrasts = pd.read_parquet(co_path)
    contrasts["contrast_topaz_id"] = 22
    contrasts.to_parquet(co_path)
    report = validate_preconditions(str(wd), default_treatments())
    assert report.ok, report.errors
    assert report.mode == "cumulative"
    assert report.contrast_groups_path is None


def test_missing_hillslope_char_is_error(tmp_path):
    wd = _assemble_run_dir(tmp_path, "austere_inaction")
    (wd / "watershed" / "hillslopes.parquet").unlink()
    report = validate_preconditions(str(wd), default_treatments())
    assert not report.ok
    assert any("watershed" in e for e in report.errors)


def test_corrupt_artifact_becomes_report_error_not_exception(tmp_path):
    wd = _assemble_run_dir(tmp_path, "austere_inaction")
    (wd / "omni" / "contrasts.out.parquet").write_bytes(b"this is not parquet")
    report = validate_preconditions(str(wd), default_treatments())
    assert not report.ok
    assert any("unreadable" in e for e in report.errors)


def test_char_missing_centroids_is_error(tmp_path):
    wd = _assemble_run_dir(tmp_path, "austere_inaction")
    char_path = wd / "watershed" / "hillslopes.parquet"
    char = pd.read_parquet(char_path).drop(columns=["centroid_lon", "centroid_lat"])
    char.to_parquet(char_path)
    report = validate_preconditions(str(wd), default_treatments())
    assert not report.ok
    assert any("centroid_lon" in e for e in report.errors)


def test_non_baseline_control_contrasts_do_not_count_as_coverage(tmp_path):
    """A treatment-vs-undisturbed contrast must not satisfy per-treatment coverage."""
    wd = _assemble_run_dir(tmp_path, "austere_inaction")
    co_path = wd / "omni" / "contrasts.out.parquet"
    contrasts = pd.read_parquet(co_path)
    mask = contrasts["contrast"].astype(str).str.endswith("mulch_60_sbs_map")
    contrasts.loc[mask, "control_scenario"] = "undisturbed"
    contrasts.to_parquet(co_path)

    report = validate_preconditions(str(wd), default_treatments())
    assert not report.ok
    assert any("mulch_60_sbs_map" in e and "control" in e for e in report.errors)
    assert any("ignored for coverage" in w for w in report.warnings)


def test_missing_outlet_sediment_key_in_totals_is_warning(tmp_path):
    wd = _assemble_run_dir(tmp_path, "austere_inaction")
    so_path = wd / "omni" / "scenarios.out.parquet"
    totals = pd.read_parquet(so_path)
    totals = totals[totals["key"] != OUTLET_SEDIMENT_KEY]
    totals.to_parquet(so_path)
    report = validate_preconditions(str(wd), default_treatments())
    assert report.ok, report.errors
    assert any(OUTLET_SEDIMENT_KEY in w for w in report.warnings)
