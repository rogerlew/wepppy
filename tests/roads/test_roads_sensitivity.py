"""Artifact and paired-contrast safeguards for the Roads sensitivity harness."""
import math

import pytest

from tests.roads import roads_sensitivity as sensitivity



@pytest.mark.unit
def test_manifest_rejects_drift_and_path_escape(tmp_path):
    (tmp_path / "input").write_text("native input")
    manifest = sensitivity.inventory(tmp_path)
    sensitivity.verify(tmp_path, manifest)
    (tmp_path / "input").write_text("changed")
    with pytest.raises(ValueError, match="drift"):
        sensitivity.verify(tmp_path, manifest)
    with pytest.raises(ValueError, match="alias"):
        sensitivity.verify(tmp_path, {"../outside": "not-a-hash"})


@pytest.mark.unit
def test_inventory_rejects_symlinks(tmp_path):
    (tmp_path / "input").write_text("native input")
    (tmp_path / "alias").symlink_to(tmp_path / "input")
    with pytest.raises(ValueError, match="symlinks"):
        sensitivity.inventory(tmp_path)


@pytest.mark.unit
def test_interaction_preserves_signed_nonadditivity():
    assert sensitivity.interaction(10, 15, 7, 11) == -1
    assert sensitivity.interaction(10, 15, 7, 12) == 0
    with pytest.raises(ValueError, match="Nonfinite"):
        sensitivity.interaction(10, 15, 7, math.nan)


@pytest.mark.unit
def test_pair_readback_detects_noop_and_membership_change():
    baseline = {"input_sha256": {"p1.sol": "soil", "p1.slp": "slope"}}
    assert sensitivity.paired_input_changes(baseline, baseline) == []
    changed = {"input_sha256": {"p1.sol": "soil", "p1.slp": "new"}}
    assert sensitivity.paired_input_changes(baseline, changed) == ["p1.slp"]
    with pytest.raises(ValueError, match="membership"):
        sensitivity.paired_input_changes(baseline, {"input_sha256": {"p1.sol": "soil"}})


@pytest.mark.unit
def test_receipt_is_exclusive_and_finite(tmp_path):
    path = tmp_path / "receipt.json"
    sensitivity.save_new(path, {"passed": True})
    with pytest.raises(FileExistsError):
        sensitivity.save_new(path, {})
    with pytest.raises(ValueError):
        sensitivity.save_new(tmp_path / "nonfinite.json", {"value": math.nan})


@pytest.mark.integration
def test_canonical_geometry_pair_and_binary_override(tmp_path):
    from tests.roads.roads_matrix import Case
    case = Case("median", "loam", "gravel", "low", "rutted")
    base = sensitivity.prepare(tmp_path / "base", case)
    contrast = sensitivity.prepare(tmp_path / "contrast", case,
                                   geometry={"width_m": 8., "fill_length_m": 60.})
    assert base["emitted"]["width_m"] == 4.
    assert contrast["emitted"]["width_m"] == 8.
    assert contrast["emitted"]["lengths_m"][1] == 60.
    assert sensitivity.paired_input_changes(base, contrast) == ["wepp/roads/runs/p1.slp"]
    assert base["binary"] == "wepp_261029"
    assert base["binary_sha256"] == contrast["binary_sha256"]
    assert "wepp_ui.txt" in base["prepared_files"]


@pytest.mark.integration
def test_unrecorded_sidecar_blocks_execution_before_native_call(tmp_path):
    from tests.roads.roads_matrix import Case
    root = tmp_path / "capsule"
    record = sensitivity.prepare(root, Case("median", "loam", "gravel", "low", "rutted"))
    (root / "wepp/roads/runs/wepp_observe.on").touch()
    with pytest.raises(ValueError, match="Unrecorded"):
        sensitivity.execute(root, record)
    assert not (root / "execution-start.json").exists()


@pytest.mark.integration
def test_native_failure_retains_real_capsule_receipt(tmp_path, monkeypatch):
    from types import SimpleNamespace
    from tests.roads.roads_matrix import Case
    root = tmp_path / "capsule"
    record = sensitivity.prepare(root, Case("median", "loam", "gravel", "low", "rutted"))
    before = sensitivity.inventory(root / "wepp/roads/runs")
    monkeypatch.setattr(sensitivity.subprocess, "run", lambda *args, **kwargs: SimpleNamespace(returncode=1))
    with pytest.raises(RuntimeError, match="did not complete"):
        sensitivity.execute(root, record)
    assert (root / "failure.json").is_file()
    assert (root / "wepp/roads/runs/stdout").is_file()
    sensitivity.verify(root / "wepp/roads/runs", before)


@pytest.mark.unit
def test_event_comparison_keeps_zero_days_and_checks_calendar(tmp_path):
    import pyarrow as pa
    import pyarrow.parquet as pq
    for name, volumes in (("baseline", [2., 0.]), ("contrast", [3., 1.])):
        path = tmp_path / name / "wepp/roads/output/interchange"
        path.mkdir(parents=True)
        values = dict(year=[2000, 2000], julian=[1, 2], runvol=volumes,
                      sedcon_1=[1., 1.], **{f"sedcon_{i}": [0., 0.] for i in range(2, 6)})
        pq.write_table(pa.table(values), path / "H.pass.parquet")
    response = sensitivity.paired_events(tmp_path / "baseline", tmp_path / "contrast")
    assert response["changed_days"] == 2
    assert response["annual"] == [dict(year=2000, runoff_delta_m3=2., sediment_delta_kg=2.)]
    path = tmp_path / "contrast/wepp/roads/output/interchange/H.pass.parquet"
    pq.write_table(pq.read_table(path).slice(0, 1), path)
    with pytest.raises(ValueError, match="calendars"):
        sensitivity.paired_events(tmp_path / "baseline", tmp_path / "contrast")
    one = pq.read_table(path)
    pq.write_table(pa.concat_tables([one, one]), path)
    with pytest.raises(ValueError, match="Duplicate"):
        sensitivity.paired_events(tmp_path / "baseline", tmp_path / "contrast")


@pytest.mark.integration
def test_calendar_context_rejects_stale_cli_cache_and_nearer_ancestor(tmp_path):
    import pyarrow as pa
    import pyarrow.parquet as pq
    from tests.roads.roads_matrix import Case
    root = tmp_path / "capsule"
    record = sensitivity.prepare(root, Case("median", "loam", "gravel", "low", "rutted"))
    climate = root / "climate/site.cli"
    original = climate.read_bytes()
    climate.write_bytes(original + b"\n")
    with pytest.raises(ValueError, match="Reader climate differs"):
        sensitivity.execute(root, record)
    assert not (root / "execution-start.json").exists()
    climate.write_bytes(original)
    cached = root / "climate/wepp_cli.parquet"
    pq.write_table(pa.table(dict(year=[1999], month=[1], day_of_month=[1])), cached)
    with pytest.raises(ValueError, match="Cached reader calendar differs"):
        sensitivity.execute(root, record)
    assert not (root / "execution-start.json").exists()
    with pytest.raises(ValueError, match="Cached reader calendar differs"):
        sensitivity.summarize(root, record, start_year=2000, years=16)
    (root / "wepp/climate").mkdir()
    with pytest.raises(ValueError, match="Unexpected ancestor"):
        sensitivity.validate_calendar_context(root, record["prepared_files"]["p1.cli"])
    (root / "wepp/climate").rmdir()
    cached.unlink()  # Remove only this test's deliberately malformed cache.
    valid = sensitivity.validate_calendar_context(root, record["prepared_files"]["p1.cli"])
    assert valid["days"] == 5844 and valid["first"] == "2000-01-01"
    native = root / "wepp/roads/runs/p1.cli"
    native.write_bytes(original + b"\n")
    climate.write_bytes(original + b"\n")
    with pytest.raises(ValueError, match="differs from prepared receipt"):
        sensitivity.summarize(root, record, start_year=2000, years=16)
