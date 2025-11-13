from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from tests.profile_recorder.stubdeps import load_profile_module

_EXPECTATIONS_MODULE = load_profile_module(
    "expectations.py",
    "tests.profile_recorder.expectations_module",
    package="wepppy.profile_recorder",
)
evaluate_job_expectations = getattr(_EXPECTATIONS_MODULE, "evaluate_job_expectations")
ProfileExpectationError = getattr(_EXPECTATIONS_MODULE, "ProfileExpectationError")


def _write_single_value_parquet(path: Path, column: str, value: float) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with duckdb.connect(database=":memory:") as con:
        con.execute(f"CREATE TABLE data({column} DOUBLE)")
        con.execute(f"INSERT INTO data ({column}) VALUES (?)", [value])
        con.execute("COPY data TO ? (FORMAT 'parquet')", [str(path)])


@pytest.mark.unit
def test_expectations_pass_for_rattlesnake_profile(tmp_path: Path) -> None:
    slug = "rattlesnake-gridmet-interp-watar10mm-dss_export"
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    _write_single_value_parquet(run_dir / "ash" / "H10_ash.parquet", "remaining_ash", 22.0)
    export_dir = run_dir / "export" / "dss"
    export_dir.mkdir(parents=True, exist_ok=True)
    for name in ("totalwatsed3_chan_144.dss", "totalwatsed3_chan_204.dss"):
        (export_dir / name).write_text("demo", encoding="utf-8")

    ash_messages = evaluate_job_expectations(slug, run_dir, "/runs/demo/cfg/rq/api/run_ash")
    assert ash_messages == ["H10 remaining_ash equals 22.0 after run_ash"]

    dss_messages = evaluate_job_expectations(
        slug,
        run_dir,
        "/runs/demo/cfg/rq/api/post_dss_export_rq",
    )
    assert dss_messages == ["totalwatsed3 channel 144/204 DSS exports exist"]


@pytest.mark.unit
def test_expectations_raise_when_artifacts_missing(tmp_path: Path) -> None:
    slug = "rattlesnake-gridmet-interp-watar10mm-dss_export"
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    # Parquet exists but contains wrong value to trigger expectation failure.
    _write_single_value_parquet(run_dir / "ash" / "H10_ash.parquet", "remaining_ash", 25.0)

    with pytest.raises(ProfileExpectationError) as excinfo:
        evaluate_job_expectations(slug, run_dir, "/runs/demo/cfg/rq/api/run_ash")
    assert "remaining_ash" in str(excinfo.value)

    # Ensure missing DSS export raises as well.
    (run_dir / "export" / "dss").mkdir(parents=True, exist_ok=True)
    (run_dir / "export" / "dss" / "totalwatsed3_chan_144.dss").write_text("demo", encoding="utf-8")
    with pytest.raises(ProfileExpectationError) as excinfo:
        evaluate_job_expectations(slug, run_dir, "/runs/demo/cfg/rq/api/post_dss_export_rq")
    assert "Missing DSS export" in str(excinfo.value)
