"""Actual-file comparisons must not conflate climate, geometry or stale outputs."""
import copy
import json
from pathlib import Path
import shutil

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from wepppy.nodb.mods.roads import _parameterization_comparisons as comparisons
from wepppy.wepp.interchange import _roads_lifecycle as lifecycle

pytestmark = pytest.mark.integration


def _inputs(root, *, custom=False, runoff=10., sediment=2., climate="climate A", width=4., ids=(901, 902)):
    overrides = {role: {key: {"mode": "default"} for key in comparisons.PARAMETERS} for role in comparisons.ROLES}
    if custom:
        overrides["road"]["ki_kg_s_m4"] = {"mode": "multiply", "value": 2.}
    state = {"baseline": {"id": "roads-baseline"}, "overrides": overrides}
    config_hash = "b" * 64 if custom else "a" * 64
    records = []
    sources = []
    folder = root / comparisons.SUMMARY.parent
    folder.mkdir(parents=True, exist_ok=True)
    runs = root / "wepp/roads/runs"
    runs.mkdir(parents=True, exist_ok=True)
    for identifier in ids:
        records.append({"segment_run_id": identifier, "summary_policy": "roads_segment_pass_v1",
                        "simulation_years": 2, "profile_scope": "mixed_profile",
                        "modeled_area_m2": 100., "runoff_volume_m3": runoff, "sediment_yield_kg": sediment})
        sources.append({"segment_run_id": identifier, "status": "completed",
                        "parameterization": {"configuration_hash": config_hash}})
        (runs / f"p{identifier}.cli").write_text(climate)
        (runs / f"p{identifier}.run").write_text(f"m\n../output/H{identifier}.pass.dat\np{identifier}.cli\n16\n")
        (runs / f"p{identifier}.slp").write_text(f"slope with width {width}")
        (runs / f"p{identifier}.man").write_text("management")
        ki = "1000000" if custom else "500000"
        (runs / f"p{identifier}.sol").write_text(f"98.4\n'Road' 'loam' 1 0.6 0.5 {ki} 0.000075 2 8.1\n200 45 20 .01 16 65\n")
    pq.write_table(pa.Table.from_pylist(records), root / comparisons.SUMMARY)
    pq.write_table(pa.table({"wepp_id": [i for i in ids for _ in (2001, 2002)],
                            "year": [year for _ in ids for year in (2001, 2002)]}), root / comparisons.PASS)
    manifest = root / comparisons.MANIFEST
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps(sources))
    return state, config_hash


def _write(root, monkeypatch, *, completed_at=1, **kwargs):
    state, config_hash = _inputs(root, **kwargs)
    monkeypatch.setattr(comparisons, "_engine_identity", lambda _: {"watershed_sha256": "w", "hillslope_sha256": "h"})
    result = comparisons.write_comparison_snapshot(root, parameterization=state,
                                                  configuration_hash=config_hash, completed_at=completed_at)
    required = sorted(lifecycle.mandatory_paths(False) | {str(comparisons.SNAPSHOT)})
    for relative in required:
        path = root / relative
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("published resource fixture")
    (root / comparisons.RECEIPT).write_text(json.dumps({"policy": "roads_current_v1",
        "parameterization_hash": config_hash, "is_single_storm": False,
        "parameterization_snapshot_sha256": comparisons._digest(root / comparisons.SNAPSHOT),
        "required_relpaths": required}))
    # This suite verifies receipt/resource boundaries; real NoDb identity admission
    # is covered by test_roads_lifecycle with actual parameterization state.
    monkeypatch.setattr(lifecycle, "require_current", lambda _: None)
    return result


def _retain(root):
    history = root / comparisons.HISTORY / "retained"
    for name in ("runs", "output", "segments"):
        target = history / "wepp/roads" / name
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.move(root / "wepp/roads" / name, target)
    return history


def test_actual_profiles_compared_once_with_units_and_historical_identity(tmp_path, monkeypatch):
    baseline = _write(tmp_path, monkeypatch)
    _retain(tmp_path)
    custom = _write(tmp_path, monkeypatch, custom=True, runoff=12., sediment=5., completed_at=2)
    result = comparisons.query_comparisons(tmp_path)
    assert result["status"] == "available"
    assert result["baseline"]["run_id"] == baseline["run_id"]
    assert result["custom"]["run_id"] == custom["run_id"]
    assert result["baseline"]["historical"] is True
    assert result["custom"]["metrics"] == {"modeled_area_m2": 200., "annual_runoff_m3": 24.,
        "annual_sediment_kg": 10., "annual_runoff_mm": 120., "annual_sediment_kg_m2": .05,
        "simulation_years": 2}
    assert result["difference"]["annual_sediment_kg"] == 6.
    assert result["custom"]["calendar_years"] == [2001, 2002]


@pytest.mark.parametrize("change", [{"climate": "different"}, {"width": 8.}])
def test_incompatible_actual_inputs_are_not_compared(tmp_path, monkeypatch, change):
    _write(tmp_path, monkeypatch)
    _retain(tmp_path)
    _write(tmp_path, monkeypatch, custom=True, **change)
    result = comparisons.query_comparisons(tmp_path)
    assert result["status"] == "unavailable"
    assert "No compatible" in result["reason"]


def test_preparation_local_ids_do_not_define_compatibility(tmp_path, monkeypatch):
    _write(tmp_path, monkeypatch)
    _retain(tmp_path)
    _write(tmp_path, monkeypatch, custom=True, ids=(991, 992))
    assert comparisons.query_comparisons(tmp_path)["status"] == "available"


@pytest.mark.parametrize("source", [comparisons.SUMMARY, Path("wepp/roads/runs/p901.cli")])
def test_changed_source_bytes_withhold_comparison(tmp_path, monkeypatch, source):
    _write(tmp_path, monkeypatch)
    history = _retain(tmp_path)
    _write(tmp_path, monkeypatch, custom=True)
    with (history / source).open("ab") as stream:
        stream.write(b"changed")
    result = comparisons.query_comparisons(tmp_path)
    assert result["status"] == "unavailable"
    assert result["diagnostics"]


def test_snapshot_before_publication_is_not_a_completed_run(tmp_path, monkeypatch):
    _write(tmp_path, monkeypatch)
    _retain(tmp_path)
    _write(tmp_path, monkeypatch, custom=True)
    (tmp_path / comparisons.RECEIPT).unlink()
    assert comparisons.query_comparisons(tmp_path)["status"] == "unavailable"


def test_duplicate_summary_profiles_fail_before_snapshot(tmp_path, monkeypatch):
    state, config_hash = _inputs(tmp_path)
    path = tmp_path / comparisons.SUMMARY
    rows = pq.read_table(path).to_pylist()
    rows.append(copy.deepcopy(rows[0]))
    pq.write_table(pa.Table.from_pylist(rows), path)
    with pytest.raises(ValueError, match="Duplicate"):
        comparisons.write_comparison_snapshot(tmp_path, parameterization=state,
                                             configuration_hash=config_hash, completed_at=1)
    assert not (tmp_path / comparisons.SNAPSHOT).exists()


def test_absent_continuous_summary_is_explicit_not_zero(tmp_path):
    state, config_hash = _inputs(tmp_path)
    (tmp_path / comparisons.SUMMARY).unlink()
    result = comparisons.write_comparison_snapshot(tmp_path, parameterization=state,
                                                  configuration_hash=config_hash, completed_at=1)
    assert result["status"] == "unavailable"
    assert "metrics" not in result
    assert result["sources"] == {str(comparisons.MANIFEST): comparisons._digest(tmp_path / comparisons.MANIFEST)}
    assert result["configuration_hash"] == config_hash
    assert (tmp_path / comparisons.SNAPSHOT).is_file()


def test_changed_runtime_sidecar_prevents_comparison(tmp_path, monkeypatch):
    _write(tmp_path, monkeypatch)
    _retain(tmp_path)
    state, config_hash = _inputs(tmp_path, custom=True)
    (tmp_path / "wepp/roads/runs/wepp_ui.txt").write_text("changed evaporation model")
    comparisons.write_comparison_snapshot(tmp_path, parameterization=state,
                                         configuration_hash=config_hash, completed_at=2)
    # Recreate matching publication receipt only; preserve the changed control.
    receipt = json.loads(next((tmp_path / comparisons.HISTORY).glob("*/wepp/roads/output/roads.current.json")).read_text())
    receipt["parameterization_hash"] = config_hash
    receipt["parameterization_snapshot_sha256"] = comparisons._digest(tmp_path / comparisons.SNAPSHOT)
    for relative in receipt["required_relpaths"]:
        path = tmp_path / relative
        if not path.exists():
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("published resource fixture")
    (tmp_path / comparisons.RECEIPT).write_text(json.dumps(receipt))
    assert comparisons.query_comparisons(tmp_path)["status"] == "unavailable"


def test_malicious_snapshot_source_cannot_escape_history(tmp_path, monkeypatch):
    _write(tmp_path, monkeypatch)
    history = _retain(tmp_path)
    _write(tmp_path, monkeypatch, custom=True)
    path = history / comparisons.SNAPSHOT
    snapshot = json.loads(path.read_text())
    snapshot["sources"]["../../outside"] = "bad"
    path.write_text(json.dumps(snapshot))
    receipt_path = history / comparisons.RECEIPT
    receipt = json.loads(receipt_path.read_text())
    receipt["parameterization_snapshot_sha256"] = comparisons._digest(path)
    receipt_path.write_text(json.dumps(receipt))
    result = comparisons.query_comparisons(tmp_path)
    assert result["status"] == "unavailable"
    assert "escapes project" in result["diagnostics"][0]["reason"]


def test_snapshot_write_refuses_alias_to_baseline_output(tmp_path):
    baseline = tmp_path / "wepp/output"
    baseline.mkdir(parents=True)
    (tmp_path / "wepp/roads").mkdir()
    (tmp_path / "wepp/roads/output").symlink_to(baseline, target_is_directory=True)
    state = {"baseline": {"id": "baseline"}, "overrides": {
        role: {key: {"mode": "default"} for key in comparisons.PARAMETERS} for role in comparisons.ROLES}}
    with pytest.raises(ValueError, match="must not alias"):
        comparisons.write_comparison_snapshot(tmp_path, parameterization=state,
                                             configuration_hash="a" * 64, completed_at=1)
    assert list(baseline.iterdir()) == []


def test_historical_metadata_tamper_rejected_by_published_snapshot_hash(tmp_path, monkeypatch):
    _write(tmp_path, monkeypatch)
    history = _retain(tmp_path)
    _write(tmp_path, monkeypatch, custom=True)
    path = history / comparisons.SNAPSHOT
    snapshot = json.loads(path.read_text())
    snapshot["completed_at"] = 999999
    path.write_text(json.dumps(snapshot))
    result = comparisons.query_comparisons(tmp_path)
    assert result["status"] == "unavailable"
    assert "matching completed publication" in result["diagnostics"][0]["reason"]
