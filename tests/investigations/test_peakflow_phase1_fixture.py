from __future__ import annotations

from pathlib import Path

import pytest

from tools.peakflow_phase1_fixture import assert_single_ksat_difference


pytestmark = pytest.mark.unit


FIXTURE = (
    Path(__file__).parents[2]
    / "docs/investigations/2026-08-08-wepp-peak-flow-discontinuity-multi-site-audit"
    / "artifacts/topanga-h106-1980-ksat"
)


def test_1980_fixture_changes_only_first_horizon_ksat() -> None:
    assert_single_ksat_difference(FIXTURE)


def test_1980_fixture_rejects_an_additional_input_change(tmp_path: Path) -> None:
    fixture = tmp_path / "fixture"
    for lane in ("baseline-ksat20", "mutant-ksat35"):
        (fixture / lane).mkdir(parents=True)
        source = FIXTURE / lane / "runs"
        target = fixture / lane / "runs"
        target.symlink_to(source, target_is_directory=True)
    replacement = tmp_path / "mutant-runs"
    replacement.mkdir()
    for path in (FIXTURE / "mutant-ksat35/runs").iterdir():
        (replacement / path.name).write_bytes(path.read_bytes())
    (fixture / "mutant-ksat35/runs").unlink()
    (fixture / "mutant-ksat35/runs").symlink_to(replacement, target_is_directory=True)
    (replacement / "p106.man").write_text((replacement / "p106.man").read_text() + "\n")
    with pytest.raises(AssertionError, match="unexpected differing input"):
        assert_single_ksat_difference(fixture)
