from __future__ import annotations

import hashlib
import json
import shutil
from pathlib import Path
from types import SimpleNamespace

import pytest

import wepppy.nodb.mods.roads.roads as roads_module
from wepppy.nodb.mods.roads.roads import Roads

from ._support import _seed_prepared_state

pytestmark = [pytest.mark.unit, pytest.mark.nodb]


def test_parameterization_read_does_not_bind_and_save_roundtrips(tmp_path):
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    source = Path(controller._nodb)
    before = source.read_bytes()
    preview = controller.query_inputs()["parameterization"]
    assert preview["status"] == "unbound"
    assert preview["groups"][0]["roles"]["road"]["ki_kg_s_m4"]["adjusted"] == 500000
    assert source.read_bytes() == before
    overrides = roads_module.roads_parameterization.default_overrides()
    overrides["road"]["ki_kg_s_m4"] = {"mode": "multiply", "value": 2}
    result = controller.set_params({"parameterization": {"overrides": overrides}})
    assert "parameterization" not in result
    assert controller.query_parameterization()["status"] == "bound"
    restored = Roads.load_detached(str(tmp_path))
    assert restored._parameterization["overrides"] == overrides
    assert restored.query_parameterization()["groups"][0]["roles"]["road"]["ki_kg_s_m4"]["resolved"] == 1000000
    assert "parameterization" not in restored._roads_params
    assert list((tmp_path / "wepp/roads/history").glob("*/roads.nodb"))


def test_invalid_combined_parameterization_save_is_atomic(tmp_path, monkeypatch):
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    before = Path(controller._nodb).read_bytes()
    calls = []
    monkeypatch.setattr(roads_module.roads_lifecycle, "retain", lambda *args, **kwargs: calls.append(args))
    overrides = roads_module.roads_parameterization.default_overrides()
    overrides["fill"]["kr_s_m"] = {"mode": "absolute", "value": 0}
    with pytest.raises(ValueError):
        controller.set_params({"road_width_m_default": 8, "parameterization": {"overrides": overrides}})
    assert calls == []
    assert Path(controller._nodb).read_bytes() == before
    assert controller._roads_params["road_width_m_default"] == 4
    assert "_parameterization" not in controller.__dict__


def test_parameterization_repository_drift_is_read_only_and_retained_state_survives_missing_assets(tmp_path, monkeypatch):
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    controller.set_params({"parameterization": {"overrides": roads_module.roads_parameterization.default_overrides()}})
    repository = tmp_path / "repository-templates"
    shutil.copytree(controller.roads_legacy_templates_dir, repository)
    monkeypatch.setattr(Roads, "roads_legacy_templates_dir", property(lambda self: str(repository)))
    source = Path(controller._nodb)
    before = source.read_bytes()
    original = controller.query_parameterization()
    assert original["repository_baseline"] == {"status": "matching", "baseline_id": original["baseline_id"]}
    soil = repository / "soils/3gloam2.sol"
    soil.write_text("# Updated repository provenance\n" + soil.read_text())
    changed = controller.query_parameterization()
    assert changed["repository_baseline"]["status"] == "different"
    assert changed["repository_baseline"]["baseline_id"] != original["baseline_id"]
    soil.unlink()
    unavailable = controller.query_parameterization()
    assert unavailable["repository_baseline"]["status"] == "unavailable"
    assert unavailable["repository_baseline"]["reason"]
    for result in (changed, unavailable):
        assert result["status"] == "bound"
        assert result["baseline_id"] == original["baseline_id"]
        assert result["configuration_hash"] == original["configuration_hash"]
        assert result["groups"] == original["groups"]
    assert source.read_bytes() == before


def test_parameterization_reset_preserves_baseline_and_repair_retains_invalid_bytes(tmp_path):
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    defaults = roads_module.roads_parameterization.default_overrides()
    controller.set_params({"parameterization": {"overrides": defaults}})
    identity = controller._parameterization["baseline"]["id"]
    controller.set_params({"parameterization": {"overrides": defaults}})
    assert controller._parameterization["baseline"]["id"] == identity
    with pytest.raises(ValueError):
        controller.set_params({"parameterization": {"repair": True, "overrides": defaults}})
    with controller.locked():
        controller._parameterization = None
    invalid_bytes = Path(controller._nodb).read_bytes()
    assert controller.query_parameterization()["status"] == "invalid"
    with pytest.raises(ValueError):
        controller.set_params({"road_width_m_default": 8})
    controller.set_params({"parameterization": {"repair": True, "overrides": defaults}})
    assert controller.query_parameterization()["status"] == "bound"
    assert invalid_bytes in [p.read_bytes() for p in (tmp_path / "wepp/roads/history").glob("*/roads.nodb")]


def test_parameterization_run_requires_bound_current_prepare(tmp_path):
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    with controller.locked():
        controller._uploaded_geojson_sha256 = "upload"
        controller._status = "prepared"
        controller._last_prepare_summary = {
            "uploaded_geojson_sha256": "upload",
            "roads_params_signature": controller._params_signature(controller._roads_params),
        }
    with pytest.raises(ValueError, match="unbound"):
        controller._require_prepare_state_current()
    _seed_prepared_state(controller)
    controller._require_prepare_state_current()
    with controller.locked():
        controller._parameterization["overrides"]["road"]["ksat_mm_h"] = {"mode": "multiply", "value": 2}
    with pytest.raises(ValueError, match="parameterization changed"):
        controller._require_prepare_state_current()


@pytest.mark.parametrize("writer,order", [
    ("_build_single_ofe_soil_file", (1,)),
    ("_build_routed_two_ofe_soil_file", (1, 3)),
    ("_build_routed_three_ofe_soil_file", (1, 2, 3)),
    ("_build_routed_mofe_soil_file", (3, 1, 2, 3)),
])
def test_parameterization_reaches_each_native_soil_writer(tmp_path, writer, order):
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    repository_template = Path(controller.roads_legacy_soils_dir) / "3gloam2.sol"
    baseline_path = tmp_path / "baseline.sol"
    kwargs = {"traffic": "low", "surface": "gravel", "rfg_pct": 20}
    if writer == "_build_routed_mofe_soil_file":
        kwargs["ofe_order"] = order
    getattr(controller, writer)(template_path=repository_template, output_path=baseline_path, **kwargs)
    controller.set_params({"parameterization": {"overrides": roads_module.roads_parameterization.default_overrides()}})
    default_path = tmp_path / "default.sol"
    retained_template = controller._resolve_legacy_soil_template_path(design="inslope_bd", surface="gravel", soil_texture="loam")
    getattr(controller, writer)(template_path=retained_template, output_path=default_path, **kwargs)
    assert default_path.read_bytes() == baseline_path.read_bytes()
    overrides = roads_module.roads_parameterization.default_overrides()
    for role, factor in zip(("road", "fill", "buffer"), (2, 3, 4)):
        for key in roads_module.roads_parameterization.PARAMETERS:
            overrides[role][key] = {"mode": "multiply", "value": factor}
    controller.set_params({"parameterization": {"overrides": overrides}})
    custom_path = tmp_path / "custom.sol"
    retained_template = controller._resolve_legacy_soil_template_path(design="inslope_bd", surface="gravel", soil_texture="loam")
    getattr(controller, writer)(template_path=retained_template, output_path=custom_path, **kwargs)
    record = controller._parameterization_runtime_readbacks[str(custom_path)]
    assert [r["role"] for r in record["ofes"]] == [{1: "road", 2: "fill", 3: "buffer"}[i] for i in order]
    for row in record["ofes"]:
        factor = {"road": 2, "fill": 3, "buffer": 4}[row["role"]]
        for key, value in row["adjusted"].items():
            assert row["emitted"][key] == pytest.approx(value * factor)
    with controller.locked():
        controller._timestamps["test"] = 1
    saved = json.loads(Path(controller._nodb).read_text())
    assert "_parameterization_runtime_templates" not in saved
    assert "_parameterization_runtime_readbacks" not in saved


def test_parameterization_initial_preview_and_invalid_request_do_not_create_state(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    assert Roads.initial_parameterization_preview()["status"] == "unbound"
    with pytest.raises(ValueError):
        Roads.validate_initial_params({"road_width_m_default": 0.01})
    assert list(tmp_path.iterdir()) == []


def test_parameterization_completed_provenance_requires_actual_executed_inputs(tmp_path, monkeypatch):
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    controller.set_params({"parameterization": {"overrides": roads_module.roads_parameterization.default_overrides()}})
    with pytest.raises(ValueError, match="lacks native parameterization readback"):
        controller._attach_parameterization_records([{"segment_run_id": 900001, "status": "completed"}])
    baseline = tmp_path / "wepp/runs"
    baseline.mkdir(parents=True)
    (baseline / "p1.cli").write_text("climate")
    monkeypatch.setattr(Roads, "wepp_instance", property(lambda self: SimpleNamespace(
        runs_dir=str(baseline), pass_family="legacy_ascii",
    )))
    monkeypatch.setattr(roads_module, "make_hillslope_run", lambda *args, **kwargs: None)
    monkeypatch.setattr(roads_module, "run_hillslope", lambda *args, **kwargs: None)
    root = Path(controller.roads_runs_dir)
    template = controller._resolve_legacy_soil_template_path(design="inslope_bd", surface="gravel", soil_texture="loam")
    soil = root / "p900001.single_ofe.sol"
    controller._build_single_ofe_soil_file(template_path=template, output_path=soil, traffic="low", surface="gravel", rfg_pct=20)
    slope = root / "p900001.slp"
    controller._write_single_ofe_slope_file(slope, width_m=4, length_m=20, slope_pct=10)
    management = controller._materialize_single_ofe_management_template(traffic="low")
    controller._run_segment_hillslope(segment_run_id=900001, climate_wepp_id=1, sim_years=1,
                                     wepp_bin=None, single_ofe_management_path=management,
                                     single_ofe_soil_path=soil, single_ofe_slope_path=slope)
    rows = [{"segment_run_id": 900001, "status": "completed"}]
    controller._attach_parameterization_records(rows)
    files = rows[0]["parameterization"]["input_files"]
    assert {Path(row["relpath"]).name for row in files} == {"p900001.sol", "p900001.slp", "p900001.man"}
    assert (root / "p900001.parameterization.json").is_file()
    (root / "p900001.man").unlink()
    with pytest.raises(ValueError, match="inputs changed"):
        controller._attach_parameterization_records(rows)


def _write_historical_parameterization_snapshot(controller, snapshot):
    signature = roads_module.roads_parameterization.configuration_hash(controller._parameterization)
    baseline_id = controller._parameterization["baseline"]["id"]
    required = roads_module.roads_lifecycle.mandatory_paths(False)
    required.add("wepp/roads/output/roads.parameterization.comparison.json")
    for name in required:
        path = snapshot / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("retained artifact")
    files = []
    for suffix in ("sol", "slp", "man"):
        path = snapshot / f"wepp/roads/runs/p900001.{suffix}"
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(f"actual {suffix}")
        files.append({"relpath": str(path.relative_to(snapshot)), "sha256": hashlib.sha256(path.read_bytes()).hexdigest()})
    manifest = snapshot / "wepp/roads/segments/roads.segment.pass.manifest.json"
    manifest.parent.mkdir(parents=True, exist_ok=True)
    manifest.write_text(json.dumps([{
        "segment_id": "old-segment", "segment_run_id": 900001, "status": "completed",
        "parameterization": {"configuration_hash": signature, "baseline_id": baseline_id,
                             "input_files": files, "ofes": [{"role": "road", "emitted": {"ki_kg_s_m4": 500000}}]},
    }]))
    comparison = snapshot / "wepp/roads/output/roads.parameterization.comparison.json"
    comparison.write_text(json.dumps({"configuration_hash": signature, "baseline_id": baseline_id,
                                     "sources": {str(manifest.relative_to(snapshot)): hashlib.sha256(manifest.read_bytes()).hexdigest()}}))
    receipt = snapshot / "wepp/roads/output/roads.current.json"
    receipt.write_text(json.dumps({
        "policy": roads_module.roads_lifecycle.POLICY, "is_single_storm": False,
        "parameterization_hash": signature, "required_relpaths": sorted(required),
        "parameterization_snapshot_sha256": hashlib.sha256(comparison.read_bytes()).hexdigest(),
    }))
    return receipt


def test_parameterization_historical_readback_stays_historical_after_edit(tmp_path):
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    defaults = roads_module.roads_parameterization.default_overrides()
    controller.set_params({"parameterization": {"overrides": defaults}})
    signature = roads_module.roads_parameterization.configuration_hash(controller._parameterization)
    snapshot = tmp_path / "wepp/roads/history/retained"
    _write_historical_parameterization_snapshot(controller, snapshot)
    controller.set_params({"road_width_m_default": 8})
    record = controller.query_parameterization()["last_completed_run"]
    assert record["historical"] and not record["current"]
    assert record["records"][0]["segment_id"] == "old-segment"
    assert record["configuration_hash"] == signature


@pytest.mark.parametrize("aliased", ["history", "snapshot", "receipt", "manifest", "input"])
def test_parameterization_historical_readback_rejects_symlink_alias(tmp_path, aliased):
    import shutil
    project = tmp_path / "project"
    project.mkdir()
    controller = Roads(str(project), "disturbed9002-wbt-mofe.cfg")
    controller.set_params({"parameterization": {"overrides": roads_module.roads_parameterization.default_overrides()}})
    snapshot = project / "wepp/roads/history/retained"
    receipt = _write_historical_parameterization_snapshot(controller, snapshot)
    path = {"history": snapshot.parent, "snapshot": snapshot, "receipt": receipt,
            "manifest": snapshot / "wepp/roads/segments/roads.segment.pass.manifest.json",
            "input": snapshot / "wepp/roads/runs/p900001.sol"}[aliased]
    outside = tmp_path / "outside"
    shutil.move(str(path), outside)
    path.symlink_to(outside, target_is_directory=outside.is_dir())
    diagnostics = []
    assert controller._last_parameterization_readback(diagnostics) is None
    assert any("aliased" in message for message in diagnostics)


@pytest.mark.parametrize("corruption", ["policy", "incomplete", "snapshot_hash", "input_hash"])
def test_parameterization_historical_readback_rejects_incomplete_or_changed_publication(tmp_path, corruption):
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    controller.set_params({"parameterization": {"overrides": roads_module.roads_parameterization.default_overrides()}})
    snapshot = tmp_path / "wepp/roads/history/retained"
    receipt_path = _write_historical_parameterization_snapshot(controller, snapshot)
    receipt = json.loads(receipt_path.read_text())
    if corruption == "policy":
        receipt.pop("policy")
    elif corruption == "incomplete":
        receipt["required_relpaths"] = ["wepp/roads/output/roads.parameterization.comparison.json"]
    elif corruption == "snapshot_hash":
        receipt["parameterization_snapshot_sha256"] = "0" * 64
    else:
        (snapshot / "wepp/roads/runs/p900001.man").write_text("changed")
    receipt_path.write_text(json.dumps(receipt))
    diagnostics = []
    assert controller._last_parameterization_readback(diagnostics) is None
    assert diagnostics


def test_parameterization_does_not_change_ordinary_params_roundtrip(tmp_path):
    controller = Roads(str(tmp_path), "disturbed9002-wbt-mofe.cfg")
    overrides = roads_module.roads_parameterization.default_overrides()
    overrides["road"]["ki_kg_s_m4"] = {"mode": "multiply", "value": 2}
    params = controller.set_params({"road_width_m_default": 8, "parameterization": {"overrides": overrides}})
    assert params == controller.query_inputs()["roads_params"]
    assert "parameterization" not in params
    assert controller.set_params(params) == params
    assert controller._parameterization["overrides"] == overrides
