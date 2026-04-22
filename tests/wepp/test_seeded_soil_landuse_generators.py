from __future__ import annotations

from collections import Counter
import json
from random import Random
from pathlib import Path
import sys
import types

import pytest

from wepppy.wepp.fuzzing.seeded_soil_landuse_generators import (
    DEFAULT_MUTATION_PROFILE,
    SeedTuple,
    SeededSoilLanduseGenerator,
    _ensure_rosetta3_available,
    _mutate_management,
    _mutate_soil,
    discover_seed_tuples,
    evaluate_soft_invariants,
    sample_seed_tuples,
)
from wepppy.wepp.management.managements import read_management
from wepppy.wepp.soils.utils import WeppSoilUtil

pytestmark = pytest.mark.integration

FIXTURE_RUNS_DIR = (
    Path(__file__).resolve().parents[1]
    / "wepp"
    / "interchange"
    / "fixtures"
    / "deductive-futurist"
    / "wepp"
    / "runs"
)


def _make_seed_tuple(*, seed_id: str, run_id: str, stem: str) -> SeedTuple:
    runs_dir = f"/wc1/runs/{run_id}/wepp/runs"
    return SeedTuple(
        seed_id=seed_id,
        run_id=run_id,
        runs_dir=runs_dir,
        stem=stem,
        sol_path=f"{runs_dir}/{stem}.sol",
        man_path=f"{runs_dir}/{stem}.man",
        slp_path=f"{runs_dir}/{stem}.slp",
        cli_path=f"{runs_dir}/{stem}.cli",
        run_path=f"{runs_dir}/{stem}.run",
    )


def test_discover_seed_tuples_filters_to_complete_file_sets(tmp_path: Path) -> None:
    runs_dir = tmp_path / "aa" / "demo-run" / "wepp" / "runs"
    runs_dir.mkdir(parents=True)

    for ext in ("sol", "man", "slp", "cli"):
        (runs_dir / f"p1.{ext}").write_text("x\n", encoding="utf-8")

    for ext in ("sol", "man", "slp"):
        (runs_dir / f"p2.{ext}").write_text("x\n", encoding="utf-8")

    discovered = discover_seed_tuples(tmp_path)
    assert len(discovered) == 1
    assert discovered[0].run_id == "aa/demo-run"
    assert discovered[0].stem == "p1"


def test_sample_seed_tuples_is_deterministic_and_run_capped() -> None:
    seeds = [
        _make_seed_tuple(seed_id="seed-a1", run_id="aa/run-a", stem="p1"),
        _make_seed_tuple(seed_id="seed-a2", run_id="aa/run-a", stem="p2"),
        _make_seed_tuple(seed_id="seed-b1", run_id="bb/run-b", stem="p1"),
        _make_seed_tuple(seed_id="seed-b2", run_id="bb/run-b", stem="p2"),
        _make_seed_tuple(seed_id="seed-c1", run_id="cc/run-c", stem="p1"),
    ]

    sample_one = sample_seed_tuples(
        seeds, sample_size=3, random_seed=20260421, per_run_cap=1
    )
    sample_two = sample_seed_tuples(
        seeds, sample_size=3, random_seed=20260421, per_run_cap=1
    )

    assert [seed.seed_id for seed in sample_one] == [seed.seed_id for seed in sample_two]

    counts = Counter(seed.run_id for seed in sample_one)
    assert max(counts.values()) == 1


def test_sample_seed_tuples_varies_with_random_seed_when_bucket_limited() -> None:
    seeds = [
        _make_seed_tuple(seed_id=f"seed-{bucket}", run_id=f"{bucket}/run", stem="p1")
        for bucket in ("aa", "bb", "cc", "dd", "ee", "ff", "gg", "hh", "ii", "jj")
    ]

    sample_a = sample_seed_tuples(
        seeds, sample_size=5, random_seed=111, per_run_cap=1
    )
    sample_b = sample_seed_tuples(
        seeds, sample_size=5, random_seed=222, per_run_cap=1
    )

    assert [seed.seed_id for seed in sample_a] != [seed.seed_id for seed in sample_b]


def test_evaluate_soft_invariants_reports_warnings_without_structural_reject() -> None:
    soil = WeppSoilUtil(str(FIXTURE_RUNS_DIR / "p1.sol"))
    management = read_management(str(FIXTURE_RUNS_DIR / "p1.man"))

    soil.obj["ofes"][0]["sat"] = 1.8
    soil.obj["ofes"][0]["horizons"][0]["sand"] = 90.0
    soil.obj["ofes"][0]["horizons"][0]["clay"] = 25.0
    soil.obj["ofes"][0]["horizons"][0]["bd"] = 3.4

    management["ini.data.cancov"] = 1.25
    management["plant.data.rdmax"] = -0.3

    checks = evaluate_soft_invariants(soil, management)
    warns = [check for check in checks if check["outcome"] == "warn"]

    assert warns
    assert any("texture_sum" in check["name"] for check in warns)
    assert any("cancov_range" in check["name"] for check in warns)
    assert any("rdmax_positive" in check["name"] for check in warns)


def test_p2_event_edge_management_mutations_stay_within_safe_bounds() -> None:
    management = read_management(str(FIXTURE_RUNS_DIR / "p1.man"))
    _mutate_management(
        management,
        Random(20260421),
        mutation_profile_id="P2_EVENT_EDGE",
    )

    ini_data = management.inis[0].data
    plant_data = management.plants[0].data
    assert 0.05 <= float(ini_data.cancov) <= 0.2
    assert 0.75 <= float(ini_data.inrcov) <= 0.95
    assert 0.05 <= float(ini_data.rilcov) <= 0.25
    assert 0.15 <= float(plant_data.rdmax) <= 0.7
    assert 0.2 <= float(plant_data.xmxlai) <= 1.2


def test_p4_texture_discontinuity_mutations_keep_texture_sum_bounded() -> None:
    soil = WeppSoilUtil(str(FIXTURE_RUNS_DIR / "p1.sol"))
    _mutate_soil(
        soil,
        Random(20260421),
        mutation_profile_id="P4_TEXTURE_DENSITY_DISCONTINUITY",
    )

    for ofe in soil.obj.get("ofes", []):
        for horizon in ofe.get("horizons", []):
            sand = float(horizon["sand"])
            clay = float(horizon["clay"])
            assert 1.0 <= sand <= 85.0
            assert 1.0 <= clay <= 85.0
            assert sand + clay <= 92.0 + 1.0e-6
            assert float(horizon["wp"]) <= float(horizon["fc"]) + 1.0e-6


def test_p5_slope_amplification_mutations_clamp_sat_texture_and_bd() -> None:
    soil = WeppSoilUtil(str(FIXTURE_RUNS_DIR / "p1.sol"))
    _mutate_soil(
        soil,
        Random(20260421),
        mutation_profile_id="P5_SLOPE_RESPONSE_AMPLIFICATION",
    )

    for ofe in soil.obj.get("ofes", []):
        sat = float(ofe["sat"])
        assert 0.08 <= sat <= 0.92
        for horizon in ofe.get("horizons", []):
            sand = float(horizon["sand"])
            clay = float(horizon["clay"])
            bd = float(horizon["bd"])
            assert 1.0 <= sand <= 85.0
            assert 1.0 <= clay <= 85.0
            assert sand + clay <= 92.0 + 1.0e-6
            assert 0.8 <= bd <= 1.9
            assert float(horizon["wp"]) <= float(horizon["fc"]) + 1.0e-6


def test_p5_slope_amplification_management_window_is_stabilized() -> None:
    management = read_management(str(FIXTURE_RUNS_DIR / "p1.man"))
    _mutate_management(
        management,
        Random(20260421),
        mutation_profile_id="P5_SLOPE_RESPONSE_AMPLIFICATION",
    )

    ini_data = management.inis[0].data
    plant_data = management.plants[0].data
    assert 0.1 <= float(ini_data.rilcov) <= 0.4
    assert 1.0 <= float(plant_data.rdmax) <= 3.0
    assert 2.0 <= float(plant_data.xmxlai) <= 7.0


def test_generator_rosetta_guard_fails_when_missing(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delitem(sys.modules, "rosetta", raising=False)
    rosetta_stub = types.ModuleType("rosetta")
    monkeypatch.setitem(sys.modules, "rosetta", rosetta_stub)

    with pytest.raises(RuntimeError, match="Rosetta3 dependency unavailable"):
        _ensure_rosetta3_available()


def test_generator_rosetta_guard_passes_when_available() -> None:
    _ensure_rosetta3_available()


def test_generate_batch_fails_fast_when_rosetta_missing(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    seed = SeedTuple(
        seed_id="seed-fixture-p1-rosetta",
        run_id="fx/deductive-futurist",
        runs_dir=str(FIXTURE_RUNS_DIR),
        stem="p1",
        sol_path=str(FIXTURE_RUNS_DIR / "p1.sol"),
        man_path=str(FIXTURE_RUNS_DIR / "p1.man"),
        slp_path=str(FIXTURE_RUNS_DIR / "p1.slp"),
        cli_path=str(FIXTURE_RUNS_DIR / "p1.cli"),
        run_path=str(FIXTURE_RUNS_DIR / "p1.run"),
    )
    monkeypatch.delitem(sys.modules, "rosetta", raising=False)
    rosetta_stub = types.ModuleType("rosetta")
    monkeypatch.setitem(sys.modules, "rosetta", rosetta_stub)

    generator = SeededSoilLanduseGenerator(random_seed=20260421)
    with pytest.raises(RuntimeError, match="Rosetta3 dependency unavailable"):
        generator.generate_batch(seeds=[seed], output_root=tmp_path)


def test_generate_case_writes_valid_artifacts_and_metadata(tmp_path: Path) -> None:
    stem = "p1"
    seed = SeedTuple(
        seed_id="seed-fixture-p1",
        run_id="fx/deductive-futurist",
        runs_dir=str(FIXTURE_RUNS_DIR),
        stem=stem,
        sol_path=str(FIXTURE_RUNS_DIR / f"{stem}.sol"),
        man_path=str(FIXTURE_RUNS_DIR / f"{stem}.man"),
        slp_path=str(FIXTURE_RUNS_DIR / f"{stem}.slp"),
        cli_path=str(FIXTURE_RUNS_DIR / f"{stem}.cli"),
        run_path=str(FIXTURE_RUNS_DIR / f"{stem}.run"),
    )

    generator = SeededSoilLanduseGenerator(random_seed=20260421)
    metadata = generator.generate_case(seed=seed, case_index=1, output_root=tmp_path)

    assert metadata["status"] == "ok"
    assert metadata["seed_id"] == seed.seed_id
    assert metadata["mutation_profile_id"] == DEFAULT_MUTATION_PROFILE
    assert metadata["hard_failures"] == []
    assert metadata["soft_invariants"]

    generated_sol = Path(metadata["generated_paths"]["sol"])
    generated_man = Path(metadata["generated_paths"]["man"])
    metadata_path = generated_sol.parent / "case_metadata.json"

    assert generated_sol.exists()
    assert generated_man.exists()
    assert metadata_path.exists()

    WeppSoilUtil(str(generated_sol))
    read_management(str(generated_man))


def test_generate_case_records_mutation_profile_attribution(tmp_path: Path) -> None:
    seed = SeedTuple(
        seed_id="seed-fixture-p1-p2",
        run_id="fx/deductive-futurist",
        runs_dir=str(FIXTURE_RUNS_DIR),
        stem="p1",
        sol_path=str(FIXTURE_RUNS_DIR / "p1.sol"),
        man_path=str(FIXTURE_RUNS_DIR / "p1.man"),
        slp_path=str(FIXTURE_RUNS_DIR / "p1.slp"),
        cli_path=str(FIXTURE_RUNS_DIR / "p1.cli"),
        run_path=str(FIXTURE_RUNS_DIR / "p1.run"),
    )
    generator = SeededSoilLanduseGenerator(random_seed=20260421)
    metadata = generator.generate_case(
        seed=seed,
        case_index=1,
        output_root=tmp_path,
        case_config={
            "mutation_profile_id": "P2_EVENT_EDGE",
            "mutation_profile_attribution": {"adaptive_score": 3.5, "lane": "test"},
        },
    )

    assert metadata["mutation_profile_id"] == "P2_EVENT_EDGE"
    assert metadata["lineage"]["mutation_profile_id"] == "P2_EVENT_EDGE"
    assert metadata["lineage"]["mutation_profile_attribution"]["lane"] == "test"


def test_generate_case_preserves_multi_ofe_soil_structure(tmp_path: Path) -> None:
    stem = "pw0"
    seed = SeedTuple(
        seed_id="seed-fixture-pw0",
        run_id="fx/deductive-futurist",
        runs_dir=str(FIXTURE_RUNS_DIR),
        stem=stem,
        sol_path=str(FIXTURE_RUNS_DIR / f"{stem}.sol"),
        man_path=str(FIXTURE_RUNS_DIR / f"{stem}.man"),
        slp_path=str(FIXTURE_RUNS_DIR / f"{stem}.slp"),
        cli_path=str(FIXTURE_RUNS_DIR / f"{stem}.cli"),
        run_path=str(FIXTURE_RUNS_DIR / f"{stem}.run"),
    )

    source_soil = WeppSoilUtil(seed.sol_path)
    source_ntemp = int(source_soil.obj["ntemp"])
    assert source_ntemp > 1

    generator = SeededSoilLanduseGenerator(random_seed=20260421)
    metadata = generator.generate_case(seed=seed, case_index=2, output_root=tmp_path)

    generated_soil = WeppSoilUtil(metadata["generated_paths"]["sol"])
    assert int(generated_soil.obj["ntemp"]) == source_ntemp
    assert len(generated_soil.obj["ofes"]) == len(source_soil.obj["ofes"])


def test_generate_batch_writes_case_metadata_for_hard_failures(tmp_path: Path) -> None:
    seed = SeedTuple(
        seed_id="seed-bad-man",
        run_id="fx/deductive-futurist",
        runs_dir=str(FIXTURE_RUNS_DIR),
        stem="p1",
        sol_path=str(FIXTURE_RUNS_DIR / "p1.sol"),
        man_path=str(FIXTURE_RUNS_DIR / "missing.man"),
        slp_path=str(FIXTURE_RUNS_DIR / "p1.slp"),
        cli_path=str(FIXTURE_RUNS_DIR / "p1.cli"),
        run_path=str(FIXTURE_RUNS_DIR / "p1.run"),
    )

    generator = SeededSoilLanduseGenerator(random_seed=20260421)
    manifest = generator.generate_batch(seeds=[seed], output_root=tmp_path)

    assert manifest["hard_fail_cases"] == 1
    assert manifest["ok_cases"] == 0

    case = manifest["cases"][0]
    assert case["status"] == "hard_fail"

    case_dir = tmp_path / case["case_id"]
    metadata_path = case_dir / "case_metadata.json"
    assert metadata_path.exists()

    with metadata_path.open(encoding="utf-8") as handle:
        persisted = json.load(handle)

    assert persisted["status"] == "hard_fail"
    assert persisted["hard_failures"]


def test_generate_batch_validates_case_config_cardinality(tmp_path: Path) -> None:
    seed = SeedTuple(
        seed_id="seed-fixture-p1",
        run_id="fx/deductive-futurist",
        runs_dir=str(FIXTURE_RUNS_DIR),
        stem="p1",
        sol_path=str(FIXTURE_RUNS_DIR / "p1.sol"),
        man_path=str(FIXTURE_RUNS_DIR / "p1.man"),
        slp_path=str(FIXTURE_RUNS_DIR / "p1.slp"),
        cli_path=str(FIXTURE_RUNS_DIR / "p1.cli"),
        run_path=str(FIXTURE_RUNS_DIR / "p1.run"),
    )
    generator = SeededSoilLanduseGenerator(random_seed=20260421)
    with pytest.raises(ValueError, match="case_configs length must match seeds length"):
        generator.generate_batch(
            seeds=[seed],
            output_root=tmp_path,
            case_configs=[],
        )
