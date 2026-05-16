#!/usr/bin/env python3
"""Compare two MOFE hillslope-audit roots with day-level and cohort-level deltas."""

from __future__ import annotations

import argparse
import json
from collections import Counter
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import pandas as pd


SUMMARY_FILENAME = "hillslope_mofe_daily_closure_audit_summary.json"
DAILY_FILENAME = "hillslope_mofe_daily_closure_audit_daily.csv"
DEPRECATED_REASON = "late_ofe_residual_plus_surface_pulse_proxy_q_ratio_unavailable"

DAY_KEY_COLUMNS = [
    "wepp_id",
    "year",
    "sim_day_index",
    "julian",
    "month",
    "day_of_month",
]


@dataclass(frozen=True)
class TargetDay:
    wepp_id: int
    year: int
    month: int
    day_of_month: int


def _parse_hillslope_id(path: Path) -> int | None:
    name = path.name
    if not (name.startswith("H") and name[1:].isdigit()):
        return None
    return int(name[1:])


def _as_bool_series(series: pd.Series) -> pd.Series:
    if series.dtype == bool:
        return series
    normalized = series.astype(str).str.strip().str.lower()
    mapped = normalized.map({"true": True, "1": True, "false": False, "0": False, "nan": False})
    unknown = mapped.isna() & series.notna()
    if unknown.any():
        unknown_values = sorted({str(v) for v in series[unknown].tolist()})
        raise ValueError(
            "unsupported boolean values in audit_requires_scientific_review: "
            + ", ".join(unknown_values)
        )
    return mapped.fillna(False).astype(bool)


def _load_hillslope_summary(root: Path) -> dict[int, dict[str, Any]]:
    result: dict[int, dict[str, Any]] = {}
    for h_dir in sorted(root.glob("H*")):
        wepp_id = _parse_hillslope_id(h_dir)
        if wepp_id is None:
            continue
        summary_path = h_dir / SUMMARY_FILENAME
        if not summary_path.exists():
            continue
        payload = json.loads(summary_path.read_text(encoding="utf-8"))
        full = payload.get("full_physical_closure", {})
        flagged = bool(full.get("requires_scientific_review", False))
        flagged_days = int(full.get("requires_scientific_review_days", 0) or 0)
        max_day = full.get("max_requires_scientific_review_day") or {}
        reason = str(max_day.get("reason", "none")) if flagged else "none"
        result[wepp_id] = {
            "wepp_id": wepp_id,
            "flagged": flagged,
            "flagged_days": flagged_days,
            "reason": reason,
        }
    return result


def _load_daily_rows(root: Path, *, allow_missing_daily: bool) -> tuple[pd.DataFrame, list[int]]:
    frames: list[pd.DataFrame] = []
    missing_daily_ids: list[int] = []
    required_columns = DAY_KEY_COLUMNS[1:] + [
        "audit_requires_scientific_review",
        "audit_requires_scientific_review_reason",
        "audit_late_max_abs_ofe_closure_residual_mm",
        "audit_late_max_qofe_to_q_ratio",
        "audit_late_max_surface_pulse_proxy_mm",
    ]

    for h_dir in sorted(root.glob("H*")):
        wepp_id = _parse_hillslope_id(h_dir)
        if wepp_id is None:
            continue
        daily_path = h_dir / DAILY_FILENAME
        if not daily_path.exists():
            missing_daily_ids.append(wepp_id)
            continue
        frame = pd.read_csv(daily_path)
        if "wepp_id" not in frame.columns:
            frame.insert(0, "wepp_id", wepp_id)

        missing = [column for column in required_columns if column not in frame.columns]
        if missing:
            raise KeyError(
                f"{daily_path} is missing required columns: {', '.join(sorted(missing))}"
            )

        frame = frame.copy()
        frame["wepp_id"] = frame["wepp_id"].astype(int)
        frame["audit_requires_scientific_review"] = _as_bool_series(frame["audit_requires_scientific_review"])
        frame["audit_requires_scientific_review_reason"] = (
            frame["audit_requires_scientific_review_reason"].fillna("none").astype(str)
        )
        frames.append(
            frame[
                DAY_KEY_COLUMNS
                + [
                    "audit_requires_scientific_review",
                    "audit_requires_scientific_review_reason",
                    "audit_late_max_abs_ofe_closure_residual_mm",
                    "audit_late_max_qofe_to_q_ratio",
                    "audit_late_max_surface_pulse_proxy_mm",
                ]
            ].copy()
        )

    if missing_daily_ids and not allow_missing_daily:
        raise FileNotFoundError(
            f"{root} is missing {DAILY_FILENAME} for hillslopes: {missing_daily_ids[:20]}"
            + ("..." if len(missing_daily_ids) > 20 else "")
        )

    if not frames:
        empty = pd.DataFrame(
            columns=DAY_KEY_COLUMNS
            + [
                "audit_requires_scientific_review",
                "audit_requires_scientific_review_reason",
                "audit_late_max_abs_ofe_closure_residual_mm",
                "audit_late_max_qofe_to_q_ratio",
                "audit_late_max_surface_pulse_proxy_mm",
            ]
        )
        return empty, missing_daily_ids

    daily = pd.concat(frames, ignore_index=True)
    daily = daily.sort_values(DAY_KEY_COLUMNS, kind="mergesort").reset_index(drop=True)
    return daily, missing_daily_ids


def _parse_target_day(text: str) -> TargetDay:
    # Expected format: <wepp_id>:YYYY-MM-DD
    if ":" not in text:
        raise ValueError(f"invalid target-day format '{text}'")
    wepp_raw, day_raw = text.split(":", 1)
    year_raw, month_raw, dom_raw = day_raw.split("-", 2)
    return TargetDay(
        wepp_id=int(wepp_raw),
        year=int(year_raw),
        month=int(month_raw),
        day_of_month=int(dom_raw),
    )


def _build_hillslope_delta(
    baseline_summary: dict[int, dict[str, Any]],
    candidate_summary: dict[int, dict[str, Any]],
) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for wepp_id in sorted(set(baseline_summary) | set(candidate_summary)):
        baseline = baseline_summary.get(wepp_id)
        candidate = candidate_summary.get(wepp_id)
        baseline_flagged = bool(baseline["flagged"]) if baseline is not None else False
        candidate_flagged = bool(candidate["flagged"]) if candidate is not None else False
        if baseline_flagged and not candidate_flagged:
            state_delta = "cleared"
        elif not baseline_flagged and candidate_flagged:
            state_delta = "newly_flagged"
        else:
            state_delta = "unchanged"

        rows.append(
            {
                "wepp_id": wepp_id,
                "baseline_flagged": baseline_flagged,
                "baseline_reason": baseline["reason"] if baseline is not None else "missing",
                "baseline_flagged_days": baseline["flagged_days"] if baseline is not None else 0,
                "candidate_flagged": candidate_flagged,
                "candidate_reason": candidate["reason"] if candidate is not None else "missing",
                "candidate_flagged_days": candidate["flagged_days"] if candidate is not None else 0,
                "flagged_days_delta": (candidate["flagged_days"] if candidate is not None else 0)
                - (baseline["flagged_days"] if baseline is not None else 0),
                "state_delta": state_delta,
            }
        )
    return pd.DataFrame.from_records(rows).sort_values("wepp_id", kind="mergesort").reset_index(drop=True)


def _build_day_delta(baseline_daily: pd.DataFrame, candidate_daily: pd.DataFrame) -> pd.DataFrame:
    baseline = baseline_daily.rename(
        columns={
            "audit_requires_scientific_review": "baseline_flagged_day",
            "audit_requires_scientific_review_reason": "baseline_reason_day",
            "audit_late_max_abs_ofe_closure_residual_mm": "baseline_late_residual_mm",
            "audit_late_max_qofe_to_q_ratio": "baseline_late_ratio",
            "audit_late_max_surface_pulse_proxy_mm": "baseline_late_pulse_mm",
        }
    )
    candidate = candidate_daily.rename(
        columns={
            "audit_requires_scientific_review": "candidate_flagged_day",
            "audit_requires_scientific_review_reason": "candidate_reason_day",
            "audit_late_max_abs_ofe_closure_residual_mm": "candidate_late_residual_mm",
            "audit_late_max_qofe_to_q_ratio": "candidate_late_ratio",
            "audit_late_max_surface_pulse_proxy_mm": "candidate_late_pulse_mm",
        }
    )

    merged = baseline.merge(candidate, on=DAY_KEY_COLUMNS, how="outer", validate="one_to_one")
    merged["baseline_flagged_day"] = _as_bool_series(merged["baseline_flagged_day"].fillna(False))
    merged["candidate_flagged_day"] = _as_bool_series(merged["candidate_flagged_day"].fillna(False))
    merged["baseline_reason_day"] = merged["baseline_reason_day"].fillna("none").astype(str)
    merged["candidate_reason_day"] = merged["candidate_reason_day"].fillna("none").astype(str)

    state = []
    for baseline_flagged, candidate_flagged in zip(
        merged["baseline_flagged_day"].tolist(),
        merged["candidate_flagged_day"].tolist(),
    ):
        if baseline_flagged and not candidate_flagged:
            state.append("cleared_day")
        elif not baseline_flagged and candidate_flagged:
            state.append("newly_flagged_day")
        else:
            state.append("unchanged_day")
    merged["day_state_delta"] = state
    return merged.sort_values(DAY_KEY_COLUMNS, kind="mergesort").reset_index(drop=True)


def _check_target_days(day_delta: pd.DataFrame, targets: list[TargetDay]) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    for target in targets:
        subset = day_delta[
            (day_delta["wepp_id"] == target.wepp_id)
            & (day_delta["year"] == target.year)
            & (day_delta["month"] == target.month)
            & (day_delta["day_of_month"] == target.day_of_month)
        ]
        if subset.empty:
            rows.append(
                {
                    "wepp_id": target.wepp_id,
                    "year": target.year,
                    "month": target.month,
                    "day_of_month": target.day_of_month,
                    "found": False,
                    "baseline_flagged_day": False,
                    "candidate_flagged_day": False,
                    "target_cleared": False,
                }
            )
            continue
        row = subset.iloc[0]
        baseline_flagged = bool(row["baseline_flagged_day"])
        candidate_flagged = bool(row["candidate_flagged_day"])
        rows.append(
            {
                "wepp_id": target.wepp_id,
                "year": target.year,
                "month": target.month,
                "day_of_month": target.day_of_month,
                "found": True,
                "baseline_flagged_day": baseline_flagged,
                "candidate_flagged_day": candidate_flagged,
                "target_cleared": bool(baseline_flagged and not candidate_flagged),
            }
        )
    return pd.DataFrame.from_records(rows)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("baseline_root", help="Path to baseline audit_hillslope_mofe_daily_closure_all_* root")
    parser.add_argument("candidate_root", help="Path to candidate audit_hillslope_mofe_daily_closure_all_* root")
    parser.add_argument("--output-dir", required=True, help="Directory for comparison outputs")
    parser.add_argument(
        "--require-target-day-cleared",
        action="append",
        default=[],
        metavar="WEPP:YYYY-MM-DD",
        help="Assert a specific day transitions from flagged to unflagged",
    )
    parser.add_argument(
        "--deprecated-reason",
        action="append",
        default=[DEPRECATED_REASON],
        help="Reason string that must not appear in candidate flagged days/hillslopes",
    )
    parser.add_argument(
        "--max-hillslope-flag-increase",
        type=int,
        default=0,
        help="Fail if candidate flagged hillslopes exceed baseline by more than this value",
    )
    parser.add_argument(
        "--max-flagged-day-increase",
        type=int,
        default=None,
        help="Optional drift budget on flagged-day increase (candidate-baseline)",
    )
    parser.add_argument(
        "--allow-new-reason-classes",
        action="store_true",
        help="Allow candidate-only reason classes among flagged hillslopes/days",
    )
    parser.add_argument(
        "--allow-missing-daily",
        action="store_true",
        help=f"Allow missing {DAILY_FILENAME} in either root (day-level deltas may be partial)",
    )
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    baseline_root = Path(args.baseline_root).expanduser().resolve()
    candidate_root = Path(args.candidate_root).expanduser().resolve()
    output_dir = Path(args.output_dir).expanduser().resolve()
    output_dir.mkdir(parents=True, exist_ok=True)

    baseline_summary = _load_hillslope_summary(baseline_root)
    candidate_summary = _load_hillslope_summary(candidate_root)

    baseline_daily, baseline_missing_daily = _load_daily_rows(
        baseline_root, allow_missing_daily=bool(args.allow_missing_daily)
    )
    candidate_daily, candidate_missing_daily = _load_daily_rows(
        candidate_root, allow_missing_daily=bool(args.allow_missing_daily)
    )

    hillslope_delta = _build_hillslope_delta(baseline_summary, candidate_summary)
    day_delta = _build_day_delta(baseline_daily, candidate_daily)

    baseline_flagged_hillslopes = int(hillslope_delta["baseline_flagged"].sum())
    candidate_flagged_hillslopes = int(hillslope_delta["candidate_flagged"].sum())
    hillslope_flagged_delta = candidate_flagged_hillslopes - baseline_flagged_hillslopes

    baseline_flagged_days = int(day_delta["baseline_flagged_day"].sum())
    candidate_flagged_days = int(day_delta["candidate_flagged_day"].sum())
    flagged_days_delta = candidate_flagged_days - baseline_flagged_days

    baseline_hillslope_reasons = Counter(
        hillslope_delta.loc[hillslope_delta["baseline_flagged"], "baseline_reason"].tolist()
    )
    candidate_hillslope_reasons = Counter(
        hillslope_delta.loc[hillslope_delta["candidate_flagged"], "candidate_reason"].tolist()
    )
    baseline_day_reasons = Counter(
        day_delta.loc[day_delta["baseline_flagged_day"], "baseline_reason_day"].tolist()
    )
    candidate_day_reasons = Counter(
        day_delta.loc[day_delta["candidate_flagged_day"], "candidate_reason_day"].tolist()
    )

    baseline_reason_classes = {k for k in baseline_day_reasons if k != "none"} | {
        k for k in baseline_hillslope_reasons if k != "none"
    }
    candidate_reason_classes = {k for k in candidate_day_reasons if k != "none"} | {
        k for k in candidate_hillslope_reasons if k != "none"
    }
    new_reason_classes = sorted(candidate_reason_classes - baseline_reason_classes)

    deprecated_reasons = {str(reason) for reason in args.deprecated_reason if str(reason).strip()}
    candidate_deprecated_hillslope_count = int(
        sum(candidate_hillslope_reasons.get(reason, 0) for reason in deprecated_reasons)
    )
    candidate_deprecated_day_count = int(
        sum(candidate_day_reasons.get(reason, 0) for reason in deprecated_reasons)
    )

    target_days = [_parse_target_day(raw) for raw in args.require_target_day_cleared]
    target_checks = _check_target_days(day_delta, target_days) if target_days else pd.DataFrame()
    missing_targets = int((~target_checks["found"]).sum()) if not target_checks.empty else 0
    uncleared_targets = int((~target_checks["target_cleared"]).sum()) if not target_checks.empty else 0

    failure_reasons: list[str] = []
    if hillslope_flagged_delta > int(args.max_hillslope_flag_increase):
        failure_reasons.append(
            f"hillslope_flagged_delta={hillslope_flagged_delta} exceeded max_hillslope_flag_increase={args.max_hillslope_flag_increase}"
        )
    if args.max_flagged_day_increase is not None and flagged_days_delta > int(args.max_flagged_day_increase):
        failure_reasons.append(
            f"flagged_days_delta={flagged_days_delta} exceeded max_flagged_day_increase={args.max_flagged_day_increase}"
        )
    if (candidate_deprecated_hillslope_count + candidate_deprecated_day_count) > 0:
        failure_reasons.append(
            "candidate still contains deprecated reasons in flagged outputs"
        )
    if not args.allow_new_reason_classes and new_reason_classes:
        failure_reasons.append(f"candidate introduced new reason classes: {new_reason_classes}")
    if missing_targets > 0:
        failure_reasons.append(f"missing target-day rows: {missing_targets}")
    if uncleared_targets > 0:
        failure_reasons.append(f"target days not cleared: {uncleared_targets}")
    if baseline_missing_daily and not args.allow_missing_daily:
        failure_reasons.append(
            f"baseline missing {DAILY_FILENAME} for hillslopes: {baseline_missing_daily[:20]}"
        )
    if candidate_missing_daily and not args.allow_missing_daily:
        failure_reasons.append(
            f"candidate missing {DAILY_FILENAME} for hillslopes: {candidate_missing_daily[:20]}"
        )

    pass_or_fail = "pass" if not failure_reasons else "fail"

    hillslope_path = output_dir / "scireview_compare_hillslope_summary.csv"
    day_path = output_dir / "scireview_compare_day_deltas.csv"
    reason_path = output_dir / "scireview_compare_reason_counts.csv"
    target_path = output_dir / "scireview_compare_target_day_checks.csv"
    summary_path = output_dir / "scireview_compare_summary.json"

    hillslope_delta.to_csv(hillslope_path, index=False)
    day_delta.to_csv(day_path, index=False)

    reason_rows: list[dict[str, Any]] = []
    for reason in sorted(set(baseline_day_reasons) | set(candidate_day_reasons) | set(baseline_hillslope_reasons) | set(candidate_hillslope_reasons)):
        reason_rows.append(
            {
                "reason": reason,
                "baseline_flagged_hillslopes": int(baseline_hillslope_reasons.get(reason, 0)),
                "candidate_flagged_hillslopes": int(candidate_hillslope_reasons.get(reason, 0)),
                "baseline_flagged_days": int(baseline_day_reasons.get(reason, 0)),
                "candidate_flagged_days": int(candidate_day_reasons.get(reason, 0)),
            }
        )
    pd.DataFrame.from_records(reason_rows).to_csv(reason_path, index=False)
    if not target_checks.empty:
        target_checks.to_csv(target_path, index=False)
    else:
        pd.DataFrame(
            columns=[
                "wepp_id",
                "year",
                "month",
                "day_of_month",
                "found",
                "baseline_flagged_day",
                "candidate_flagged_day",
                "target_cleared",
            ]
        ).to_csv(target_path, index=False)

    summary = {
        "baseline_root": str(baseline_root),
        "candidate_root": str(candidate_root),
        "hillslopes_scanned_baseline": len(baseline_summary),
        "hillslopes_scanned_candidate": len(candidate_summary),
        "baseline_flagged_hillslopes": baseline_flagged_hillslopes,
        "candidate_flagged_hillslopes": candidate_flagged_hillslopes,
        "hillslope_flagged_delta": hillslope_flagged_delta,
        "baseline_flagged_days": baseline_flagged_days,
        "candidate_flagged_days": candidate_flagged_days,
        "flagged_days_delta": flagged_days_delta,
        "new_reason_classes": new_reason_classes,
        "candidate_deprecated_reason_hillslope_count": candidate_deprecated_hillslope_count,
        "candidate_deprecated_reason_day_count": candidate_deprecated_day_count,
        "target_days_requested": [target.__dict__ for target in target_days],
        "target_days_missing": missing_targets,
        "target_days_uncleared": uncleared_targets,
        "baseline_missing_daily_hillslopes": baseline_missing_daily,
        "candidate_missing_daily_hillslopes": candidate_missing_daily,
        "pass_or_fail": pass_or_fail,
        "failure_reasons": failure_reasons,
        "artifacts": {
            "hillslope_summary_csv": str(hillslope_path),
            "day_delta_csv": str(day_path),
            "reason_counts_csv": str(reason_path),
            "target_checks_csv": str(target_path),
        },
    }
    summary_path.write_text(json.dumps(summary, indent=2, sort_keys=True), encoding="utf-8")

    print(f"baseline_root={baseline_root}")
    print(f"candidate_root={candidate_root}")
    print(f"baseline_flagged_hillslopes={baseline_flagged_hillslopes}")
    print(f"candidate_flagged_hillslopes={candidate_flagged_hillslopes}")
    print(f"hillslope_flagged_delta={hillslope_flagged_delta}")
    print(f"baseline_flagged_days={baseline_flagged_days}")
    print(f"candidate_flagged_days={candidate_flagged_days}")
    print(f"flagged_days_delta={flagged_days_delta}")
    print(f"new_reason_classes={new_reason_classes}")
    print(f"target_days_missing={missing_targets}")
    print(f"target_days_uncleared={uncleared_targets}")
    print(f"candidate_deprecated_reason_hillslope_count={candidate_deprecated_hillslope_count}")
    print(f"candidate_deprecated_reason_day_count={candidate_deprecated_day_count}")
    print(f"pass_or_fail={pass_or_fail}")
    print(f"summary_json={summary_path}")

    return 0 if pass_or_fail == "pass" else 1


if __name__ == "__main__":
    raise SystemExit(main())
