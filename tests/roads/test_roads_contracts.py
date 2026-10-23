"""Fast fixture, matrix and failure contracts, independent of local project data."""
from collections import Counter
import json
from pathlib import Path
import pytest

from tests.roads.extract_fixture import DATA, climate_dates, digest, extract
from tests.roads.roads_matrix import CASES, ARRANGEMENTS, CONTROLS, site
from tests.roads.roads_analysis import records

pytestmark = pytest.mark.unit


def test_all_four_textures_and_factor_coverage():
    core = [c for c in CASES if c.control == "core"]
    assert len(core) == 504 and len(CASES) == 516
    assert len({c.name for c in CASES}) == 516
    assert Counter(c.texture for c in core) == dict.fromkeys(("clay", "loam", "sand", "silt"), 126)
    assert Counter(c.arrangement for c in core) == dict.fromkeys(ARRANGEMENTS, 72)
    assert {c.control for c in CASES if c.control != "core"} == set(CONTROLS)


def test_fixture_dates_and_identity():
    fixture = site()
    dates = climate_dates(DATA / "site.cli")
    assert len(dates) == fixture["daily_records"] == 5844
    assert len({d.year for d in dates}) == fixture["simulation_years"] == 16
    for name, expected in fixture["fixture_sha256"].items():
        assert digest(DATA / name) == expected
    lengths = sorted(fixture["source_lengths_m"])
    assert [fixture["geometry"][g]["segment_length_m"] for g in ("short", "median", "long")] == [lengths[0], lengths[(len(lengths)-1)//2], lengths[-1]]


def test_reject_empty_source(tmp_path):
    folder = tmp_path / "wepp/roads/segments"
    folder.mkdir(parents=True)
    (folder / "roads.segment.pass.manifest.json").write_text("[]")
    with pytest.raises(ValueError, match="no completed"):
        extract(tmp_path)


@pytest.mark.parametrize("change", ["missing", "duplicate", "nonfinite"])
def test_reject_broken_climate(tmp_path, change):
    lines = (DATA / "site.cli").read_text().splitlines()
    if change == "missing":
        del lines[-1]
    elif change == "duplicate":
        lines[-1] = lines[-2]
    else:
        values = lines[-1].split()
        values[3] = "nan"
        lines[-1] = " ".join(values)
    path = tmp_path / "broken.cli"
    path.write_text("\n".join(lines))
    with pytest.raises(ValueError):
        climate_dates(path)


def test_reject_partial_matrix(tmp_path):
    with pytest.raises(ValueError, match="case identities"):
        records(tmp_path)
    (tmp_path / "case-1.json").write_text(json.dumps(dict(name=CASES[0].name, segment_run_id=1)))
    with pytest.raises(ValueError, match="case identities"):
        records(tmp_path)


@pytest.mark.parametrize("mutation", ["missing_input", "missing_output", "changed_output", "metadata"])
def test_reject_incomplete_or_changed_execution_evidence(tmp_path, mutation):
    from dataclasses import asdict
    record = dict(name=CASES[0].name, case=asdict(CASES[0]), segment_run_id=1,
                  status="completed", input_sha256={}, output_sha256={},
                  template_sha256={"tests/roads/data/site.cli":digest(DATA / "site.cli")})
    for kind, folder, names in (("input_sha256", "runs", [f"p1.{e}" for e in ("run","slp","sol","man","cli")]),
                                ("output_sha256", "output", ["H1.pass.dat", "H1.wat.dat"])):
        for name in names:
            relative = f"wepp/roads/{folder}/{name}"
            path = tmp_path / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("unit-test evidence")
            record[kind][relative] = digest(path)
    if mutation == "missing_input":
        del record["input_sha256"]["wepp/roads/runs/p1.man"]
    elif mutation == "missing_output":
        del record["output_sha256"]["wepp/roads/output/H1.pass.dat"]
    elif mutation == "changed_output":
        (tmp_path / "wepp/roads/output/H1.wat.dat").write_text("tampered")
    else:
        record["case"]["texture"] = "sand"
    (tmp_path / "case-1.json").write_text(json.dumps(record))
    with pytest.raises(ValueError):
        records(tmp_path, expected=CASES[:1])
