from __future__ import annotations

import json
from pathlib import Path
import runpy

import pandas as pd
import pytest

pytestmark = pytest.mark.unit


def _module() -> dict[str, object]:
    repo_root = Path(__file__).resolve().parents[2]
    return runpy.run_path(str(repo_root / "tools/hillslope_mofe_scireview_compare.py"))


def _summary_payload(*, flagged: bool, flagged_days: int, reason: str) -> dict[str, object]:
    return {
        "full_physical_closure": {
            "requires_scientific_review": flagged,
            "requires_scientific_review_days": flagged_days,
            "max_requires_scientific_review_day": {"reason": reason} if flagged else None,
        }
    }


def _write_hillslope_artifacts(
    root: Path,
    *,
    wepp_id: int,
    summary: dict[str, object],
    daily_rows: list[dict[str, object]],
) -> None:
    h_dir = root / f"H{wepp_id}"
    h_dir.mkdir(parents=True, exist_ok=True)
    (h_dir / "hillslope_mofe_daily_closure_audit_summary.json").write_text(
        json.dumps(summary, indent=2, sort_keys=True),
        encoding="utf-8",
    )
    pd.DataFrame.from_records(daily_rows).to_csv(
        h_dir / "hillslope_mofe_daily_closure_audit_daily.csv",
        index=False,
    )


def _row(
    *,
    wepp_id: int,
    year: int,
    month: int,
    day_of_month: int,
    sim_day_index: int,
    julian: int,
    flagged: bool,
    reason: str,
    residual: float,
    ratio: float | None,
    pulse: float | None,
) -> dict[str, object]:
    return {
        "wepp_id": wepp_id,
        "year": year,
        "month": month,
        "day_of_month": day_of_month,
        "water_year": year,
        "sim_day_index": sim_day_index,
        "julian": julian,
        "n_ofe": 3,
        "audit_requires_scientific_review": flagged,
        "audit_requires_scientific_review_reason": reason,
        "audit_late_max_abs_ofe_closure_residual_mm": residual,
        "audit_late_max_qofe_to_q_ratio": ratio,
        "audit_late_max_surface_pulse_proxy_mm": pulse,
        "audit_late_outlier_ofe_id": 3,
        "audit_full_physical_closure_residual_mm": residual,
        "audit_full_implied_unresolved_term_mm": residual,
        "audit_full_outlier_ofe_id": 3,
        "audit_full_outlier_ofe_closure_residual_mm": residual,
    }


def test_compare_passes_with_target_day_cleared_and_no_new_classes(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _module()
    main = module["main"]

    baseline_root = tmp_path / "baseline"
    candidate_root = tmp_path / "candidate"
    out_dir = tmp_path / "out"

    triad = "late_ofe_residual_plus_qofe_to_q_ratio_plus_surface_pulse_proxy"

    _write_hillslope_artifacts(
        baseline_root,
        wepp_id=1,
        summary=_summary_payload(flagged=True, flagged_days=1, reason=triad),
        daily_rows=[
            _row(
                wepp_id=1,
                year=2024,
                month=11,
                day_of_month=21,
                sim_day_index=1,
                julian=326,
                flagged=True,
                reason=triad,
                residual=120.0,
                ratio=3.0,
                pulse=120.0,
            ),
            _row(
                wepp_id=1,
                year=2024,
                month=11,
                day_of_month=22,
                sim_day_index=2,
                julian=327,
                flagged=False,
                reason="none",
                residual=20.0,
                ratio=1.0,
                pulse=10.0,
            ),
        ],
    )
    _write_hillslope_artifacts(
        baseline_root,
        wepp_id=2,
        summary=_summary_payload(flagged=False, flagged_days=0, reason="none"),
        daily_rows=[
            _row(
                wepp_id=2,
                year=2024,
                month=11,
                day_of_month=21,
                sim_day_index=1,
                julian=326,
                flagged=False,
                reason="none",
                residual=5.0,
                ratio=1.0,
                pulse=5.0,
            )
        ],
    )

    _write_hillslope_artifacts(
        candidate_root,
        wepp_id=1,
        summary=_summary_payload(flagged=True, flagged_days=1, reason=triad),
        daily_rows=[
            _row(
                wepp_id=1,
                year=2024,
                month=11,
                day_of_month=21,
                sim_day_index=1,
                julian=326,
                flagged=False,
                reason="none",
                residual=110.0,
                ratio=None,
                pulse=None,
            ),
            _row(
                wepp_id=1,
                year=2024,
                month=11,
                day_of_month=22,
                sim_day_index=2,
                julian=327,
                flagged=True,
                reason=triad,
                residual=130.0,
                ratio=2.5,
                pulse=140.0,
            ),
        ],
    )
    _write_hillslope_artifacts(
        candidate_root,
        wepp_id=2,
        summary=_summary_payload(flagged=False, flagged_days=0, reason="none"),
        daily_rows=[
            _row(
                wepp_id=2,
                year=2024,
                month=11,
                day_of_month=21,
                sim_day_index=1,
                julian=326,
                flagged=False,
                reason="none",
                residual=4.0,
                ratio=1.0,
                pulse=4.0,
            )
        ],
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "hillslope_mofe_scireview_compare.py",
            str(baseline_root),
            str(candidate_root),
            "--output-dir",
            str(out_dir),
            "--require-target-day-cleared",
            "1:2024-11-21",
        ],
    )

    result = main()
    assert result == 0

    summary = json.loads((out_dir / "scireview_compare_summary.json").read_text(encoding="utf-8"))
    assert summary["pass_or_fail"] == "pass"
    assert summary["hillslope_flagged_delta"] == 0
    assert summary["target_days_uncleared"] == 0

    day_delta = pd.read_csv(out_dir / "scireview_compare_day_deltas.csv")
    target = day_delta[
        (day_delta["wepp_id"] == 1)
        & (day_delta["year"] == 2024)
        & (day_delta["month"] == 11)
        & (day_delta["day_of_month"] == 21)
    ].iloc[0]
    assert target["day_state_delta"] == "cleared_day"


def test_compare_fails_on_new_reason_class(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    module = _module()
    main = module["main"]

    baseline_root = tmp_path / "baseline"
    candidate_root = tmp_path / "candidate"
    out_dir = tmp_path / "out"
    triad = "late_ofe_residual_plus_qofe_to_q_ratio_plus_surface_pulse_proxy"

    _write_hillslope_artifacts(
        baseline_root,
        wepp_id=10,
        summary=_summary_payload(flagged=True, flagged_days=1, reason=triad),
        daily_rows=[
            _row(
                wepp_id=10,
                year=2025,
                month=1,
                day_of_month=2,
                sim_day_index=1,
                julian=2,
                flagged=True,
                reason=triad,
                residual=120.0,
                ratio=3.0,
                pulse=125.0,
            )
        ],
    )
    _write_hillslope_artifacts(
        candidate_root,
        wepp_id=10,
        summary=_summary_payload(flagged=True, flagged_days=1, reason="brand_new_reason"),
        daily_rows=[
            _row(
                wepp_id=10,
                year=2025,
                month=1,
                day_of_month=2,
                sim_day_index=1,
                julian=2,
                flagged=True,
                reason="brand_new_reason",
                residual=121.0,
                ratio=3.1,
                pulse=126.0,
            )
        ],
    )

    monkeypatch.setattr(
        "sys.argv",
        [
            "hillslope_mofe_scireview_compare.py",
            str(baseline_root),
            str(candidate_root),
            "--output-dir",
            str(out_dir),
            "--max-hillslope-flag-increase",
            "10",
        ],
    )

    result = main()
    assert result == 1

    summary = json.loads((out_dir / "scireview_compare_summary.json").read_text(encoding="utf-8"))
    assert summary["pass_or_fail"] == "fail"
    assert any("new reason classes" in reason for reason in summary["failure_reasons"])
