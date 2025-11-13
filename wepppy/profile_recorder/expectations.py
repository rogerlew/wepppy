from __future__ import annotations

"""Profile-specific validation hooks executed during playback."""

import math
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Dict, List

import duckdb


class ProfileExpectationError(RuntimeError):
    """Raised when a playback expectation fails."""


CheckFunc = Callable[[Path, str, str], None]


@dataclass(frozen=True)
class JobExpectation:
    """Expectation triggered after a specific playback endpoint completes."""

    endpoint_suffix: str
    description: str
    check: CheckFunc


def evaluate_job_expectations(profile_slug: str, run_dir: Path, task_path: str) -> List[str]:
    """Execute any expectations registered for the given slug/task combination."""
    expectations = _PROFILE_EXPECTATIONS.get(profile_slug)
    if not expectations:
        return []

    normalized_task = task_path.rstrip("/")
    results: List[str] = []

    for expectation in expectations:
        suffix = expectation.endpoint_suffix.rstrip("/")
        if not suffix:
            continue
        if not normalized_task.endswith(suffix):
            continue
        try:
            expectation.check(run_dir, profile_slug, normalized_task)
        except ProfileExpectationError:
            raise
        except Exception as exc:  # pragma: no cover - defensive; re-wrap unexpected errors
            raise ProfileExpectationError(
                f"{profile_slug} expectation '{expectation.description}' failed: {exc}"
            ) from exc
        results.append(expectation.description)

    return results


def _check_ash_remaining_ash(run_dir: Path, profile_slug: str, task_path: str) -> None:
    """Ensure the ash parquet contains the expected remaining_ash value."""
    parquet_path = run_dir / "ash" / "H10_ash.parquet"
    _assert_file_exists(parquet_path)
    value = _read_first_value(parquet_path, "remaining_ash (tonne/ha)")
    if value is None:
        raise ProfileExpectationError(f"{parquet_path} is empty; expected at least one row")
    numeric_value = float(value)
    if not math.isclose(numeric_value, 22.0, rel_tol=0.0, abs_tol=1e-6):
        raise ProfileExpectationError(
            f"{parquet_path} remaining_ash expected 22.0 but found {numeric_value}"
        )


def _check_dss_exports_exist(run_dir: Path, profile_slug: str, task_path: str) -> None:
    """Ensure required DSS exports exist after the export job completes."""
    required = [
        run_dir / "export" / "dss" / "totalwatsed3_chan_144.dss",
        run_dir / "export" / "dss" / "totalwatsed3_chan_204.dss",
    ]
    missing = [path for path in required if not path.exists()]
    if missing:
        joined = ", ".join(str(path) for path in missing)
        raise ProfileExpectationError(f"Missing DSS export artifacts: {joined}")


def _read_first_value(parquet_path: Path, column: str):
    """Return the first column value from a parquet file using DuckDB."""
    with duckdb.connect(database=":memory:") as con:
        row = con.execute(f"SELECT {column} FROM read_parquet(?) LIMIT 1", [str(parquet_path)]).fetchone()
    if not row:
        return None
    return row[0]


def _assert_file_exists(path: Path) -> None:
    if not path.exists():
        raise ProfileExpectationError(f"Required file missing: {path}")


_PROFILE_EXPECTATIONS: Dict[str, List[JobExpectation]] = {
    "rattlesnake-gridmet-interp-watar10mm-dss_export": [
        JobExpectation(
            endpoint_suffix="rq/api/run_ash",
            description="H10 remaining_ash equals 22.0 after run_ash",
            check=_check_ash_remaining_ash,
        ),
        JobExpectation(
            endpoint_suffix="rq/api/post_dss_export_rq",
            description="totalwatsed3 channel 144/204 DSS exports exist",
            check=_check_dss_exports_exist,
        ),
    ],
}


__all__ = ["ProfileExpectationError", "evaluate_job_expectations"]
