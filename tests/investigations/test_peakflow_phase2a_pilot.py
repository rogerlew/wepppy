from pathlib import Path

import pandas as pd
import pytest

from tools.peakflow_phase2a_pilot import (
    Trial,
    adapt_run_deck,
    apply_mutation,
    cover_fields,
    pair_events,
    parse_topology,
    soil_fields,
    storage_artifact,
    validate_storage_manifest,
)


@pytest.mark.unit
def test_adapt_run_deck_requires_exactly_one_legacy_pass() -> None:
    assert adapt_run_deck("before\n../output/H3.pass.dat\nafter\n") == "before\n../output/H3.hbp\nafter\n"
    with pytest.raises(ValueError, match="expected one"):
        adapt_run_deck("no pass here")


@pytest.mark.integration
def test_parse_topology_builds_complete_h106_closure() -> None:
    source = Path("/wc1/runs/ha/hand-to-mouth-drought/wepp/runs/pw0.str")
    if not source.exists():
        pytest.skip("Topanga authority is not mounted")
    rows, closures = parse_topology(source)
    assert len(rows) == 61
    assert closures[106][0] == 155
    assert closures[106][-1] == 201
    assert len(closures) == 140


@pytest.mark.integration
def test_mutations_change_only_declared_tokens(tmp_path: Path) -> None:
    source = Path("/wc1/runs/ha/hand-to-mouth-drought/wepp/runs")
    if not source.exists():
        pytest.skip("Topanga authority is not mounted")
    soil = tmp_path / "p106.sol"
    management = tmp_path / "p106.man"
    soil.write_bytes((source / soil.name).read_bytes())
    management.write_bytes((source / management.name).read_bytes())

    soil_before = soil_fields(soil)
    ksat = apply_mutation(tmp_path, Trial("burned", 106, "ksat", "plus"))
    soil_after = soil_fields(soil)
    assert ksat["parameter"] == "first_horizon_ksat_mm_h"
    assert soil_after["surface_ksat_mm_h"] == pytest.approx(soil_before["surface_ksat_mm_h"] * 1.01)

    cover_before = cover_fields(management)
    cover = apply_mutation(tmp_path, Trial("burned", 106, "cover", "minus"))
    cover_after = cover_fields(management)
    assert cover["parameter"] == "paired_inrcov_rilcov"
    assert cover_after["inrcov"] == pytest.approx(cover_before["inrcov"] - 0.01)
    assert cover_after["rilcov"] == pytest.approx(cover_before["rilcov"] - 0.01)


@pytest.mark.unit
def test_outer_join_keeps_absence_separate_from_zero() -> None:
    shared = {
        "scenario": "burned", "hillslope_id": 106, "ofe": 1, "ordinal": 1,
        "runoff_post_m": 0.0, "surdra_raw_m": 0.0, "surdra_realized_m": 0.0,
        "added_rate_m_s": 0.0,
        "forcing_mode": 0, "solver": "APPMTH", "peak_m_s": 0.0,
    }
    baseline = pd.DataFrame([{**shared, "year": 1980, "day": 1}, {**shared, "year": 1980, "day": 2}])
    mutant = pd.DataFrame([{**shared, "year": 1980, "day": 2}, {**shared, "year": 1980, "day": 3}])
    paired = pair_events(baseline, mutant, Trial("burned", 106, "ksat", "plus"))

    day1 = paired.loc[paired.day == 1].iloc[0]
    day2 = paired.loc[paired.day == 2].iloc[0]
    day3 = paired.loc[paired.day == 3].iloc[0]
    assert bool(day1.baseline_event_present) and not bool(day1.mutant_event_present)
    assert bool(day2.baseline_event_present) and bool(day2.mutant_event_present)
    assert not bool(day3.baseline_event_present) and bool(day3.mutant_event_present)
    assert pd.isna(day1.peak_m_s_mutant)
    assert day2.peak_m_s_mutant == 0.0


@pytest.mark.unit
def test_external_storage_manifest_detects_content_drift(tmp_path: Path) -> None:
    artifact = tmp_path / "routing" / "chan.out"
    artifact.parent.mkdir()
    artifact.write_text("original\n")
    manifest = {"artifacts": [storage_artifact(artifact, tmp_path)]}
    validate_storage_manifest(manifest)

    artifact.write_text("modified\n")
    with pytest.raises(ValueError, match="hash mismatch"):
        validate_storage_manifest(manifest)
