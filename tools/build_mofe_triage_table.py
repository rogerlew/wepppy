#!/usr/bin/env python3
"""Build run- and hillslope-level triage tables for MOFE flagged hillslopes."""

from __future__ import annotations

import argparse
import json
import math
import re
import sys
from pathlib import Path
from typing import Any

import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
INPUT_ARTIFACTS_DIR = (
    ROOT
    / "docs/mini-work-packages/20260502_rq_replay_mofe_260501_validation/artifacts"
)
DEFAULT_ROLLUP_CSV = INPUT_ARTIFACTS_DIR / "hillslope_audit_rollup.csv"
DEFAULT_DEFECT_SUMMARY_MD = INPUT_ARTIFACTS_DIR / "defect_summary.md"
DEFAULT_OUTPUT_DIR = (
    ROOT / "docs/work-packages/20260502_mofe_flagged_hillslope_triage/artifacts"
)


RUN_COLUMNS = [
    "runid",
    "config",
    "wepp_bin",
    "mods",
    "multi_ofe",
    "wd",
    "staged_runs_dir",
    "n_hillslopes_total",
    "n_hillslopes_flagged",
    "flag_rate_pct",
    "max_abs_closure_mm_run_max",
    "max_abs_ofe_closure_mm_run_max",
    "wepp_nodb_path",
    "wepp_nodb_source",
]

HILLSLOPE_COLUMNS = [
    "runid",
    "config",
    "wepp_id",
    "topaz_id",
    "summary_json_path",
    "top_days_csv_path",
    "late_max_abs_ofe_closure_residual_mm_max_abs",
    "late_max_abs_ofe_closure_residual_mm_p99",
    "late_max_abs_ofe_closure_residual_mm_p95",
    "late_max_abs_ofe_closure_residual_mm_p90",
    "late_max_surface_pulse_proxy_mm_max_abs",
    "late_max_surface_pulse_proxy_mm_p99",
    "late_max_qofe_to_q_ratio_max_abs",
    "late_max_qofe_to_q_ratio_p99",
    "closure_residual_pct_of_rm_total",
    "closure_residual_total_mm",
    "max_abs_ofe_closure_residual_mm_max_abs",
    "closure_residual_mm_max_abs",
    "closure_residual_mm_p99",
    "n_ofe_max",
    "n_ofe_min",
    "late_outlier_ofe_id",
    "outlier_is_outlet_ofe",
    "outlier_is_first_ofe",
    "outlier_is_interior_ofe",
    "chain_subsurface_transfer_residual_m3_max_abs",
    "chain_subsurface_transfer_residual_m3_p99",
    "chain_surface_transfer_residual_m3_max_abs",
    "chain_surface_transfer_residual_m3_p99",
    "runoff_pass_vs_outlet_qofe_residual_m3_max_abs",
    "runoff_pass_vs_outlet_qofe_residual_m3_p99",
    "first_ofe_nonzero_subrin_days",
    "first_ofe_nonzero_upstrmq_days",
    "strict_chain_invariants_applicable",
    "soilwater_to_porosity_fraction_max_abs",
    "soilwater_to_porosity_fraction_p99",
    "soilwater_minus_fc_mm_max_abs",
    "soilwater_minus_wp_mm_max_abs",
    "soilwater_gt_porositycap_days",
    "soilwater_lt_wpstore_days",
    "profile_order_fc_gt_porosity_days",
    "profile_order_wp_gt_fc_days",
    "precip_total_mm",
    "runoff_reported_total_mm",
    "lateral_reported_total_mm",
    "et_reported_total_mm",
    "storage_change_mm",
    "requires_scientific_review_days",
    "total_simulation_days",
    "flagged_day_fraction",
    "max_anomaly_year",
    "max_anomaly_month",
    "max_anomaly_julian",
    "worst_review_day_year",
    "worst_review_day_month",
    "worst_review_day_julian",
    "worst_review_day_reason",
    "worst_review_day_late_residual_mm",
    "worst_review_day_late_pulse_mm",
    "worst_review_day_qofe_to_q_ratio",
    "threshold_late_ofe_residual_mm",
    "threshold_late_pulse_mm",
    "threshold_late_qofe_to_q_ratio",
    "threshold_late_ofe_window",
]


NON_NULLABLE_RUN_COLUMNS = [
    "runid",
    "config",
    "n_hillslopes_total",
    "n_hillslopes_flagged",
    "flag_rate_pct",
    "max_abs_closure_mm_run_max",
    "max_abs_ofe_closure_mm_run_max",
    "wepp_nodb_source",
]

NON_NULLABLE_HILLSLOPE_COLUMNS = [
    "runid",
    "config",
    "wepp_id",
    "summary_json_path",
    "top_days_csv_path",
    "late_max_abs_ofe_closure_residual_mm_max_abs",
    "late_max_abs_ofe_closure_residual_mm_p99",
    "late_max_abs_ofe_closure_residual_mm_p95",
    "late_max_abs_ofe_closure_residual_mm_p90",
    "late_max_surface_pulse_proxy_mm_max_abs",
    "late_max_surface_pulse_proxy_mm_p99",
    "closure_residual_pct_of_rm_total",
    "closure_residual_total_mm",
    "max_abs_ofe_closure_residual_mm_max_abs",
    "closure_residual_mm_max_abs",
    "closure_residual_mm_p99",
    "n_ofe_max",
    "n_ofe_min",
    "outlier_is_outlet_ofe",
    "outlier_is_first_ofe",
    "outlier_is_interior_ofe",
    "requires_scientific_review_days",
    "total_simulation_days",
    "flagged_day_fraction",
    "max_anomaly_year",
    "max_anomaly_month",
    "max_anomaly_julian",
    "threshold_late_ofe_residual_mm",
    "threshold_late_pulse_mm",
    "threshold_late_qofe_to_q_ratio",
    "threshold_late_ofe_window",
]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description=(
            "Build triage tables from hillslope audit artifacts and per-hillslope summary JSONs."
        )
    )
    parser.add_argument(
        "--rollup-csv",
        type=Path,
        default=DEFAULT_ROLLUP_CSV,
        help="Path to hillslope_audit_rollup.csv",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_OUTPUT_DIR,
        help="Directory where triage_table_*.csv files are written",
    )
    parser.add_argument(
        "--defect-summary-md",
        type=Path,
        default=DEFAULT_DEFECT_SUMMARY_MD,
        help="Path to defect_summary.md used as fallback for run metadata",
    )
    parser.add_argument(
        "--include-passing",
        dest="include_passing",
        action="store_true",
        help=(
            "Include passing hillslopes in triage_table_hillslopes.csv "
            "(triage_table_hillslopes_all.csv is always emitted)."
        ),
    )
    parser.add_argument(
        "--no-include-passing",
        dest="include_passing",
        action="store_false",
        help="Exclude passing hillslopes from triage_table_hillslopes.csv (default).",
    )
    parser.set_defaults(include_passing=False)
    return parser.parse_args()


def normalize_bool(value: Any) -> bool:
    if isinstance(value, bool):
        return value
    if value is None:
        return False
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if isinstance(value, float) and math.isnan(value):
            return False
        return bool(value)
    text = str(value).strip().lower()
    return text in {"1", "true", "t", "yes", "y"}


def maybe_int(value: Any) -> int | None:
    if value is None:
        return None
    if isinstance(value, float) and math.isnan(value):
        return None
    if isinstance(value, str) and not value.strip():
        return None
    return int(value)


def get_nested(data: dict[str, Any], *parts: str) -> Any:
    cur: Any = data
    for part in parts:
        if not isinstance(cur, dict) or part not in cur:
            return None
        cur = cur[part]
    return cur


def parse_defect_summary_fallback(
    defect_summary_path: Path,
) -> dict[tuple[str, str], dict[str, Any]]:
    result: dict[tuple[str, str], dict[str, Any]] = {}
    if not defect_summary_path.exists():
        return result

    heading_re = re.compile(r"^##\s+(.+?)\s*/\s*(.+?)\s*$")
    snippet_re = re.compile(r"^- binary evidence B \(run artifact snippet\): `([^`]+)`$")
    current_key: tuple[str, str] | None = None

    with defect_summary_path.open("r", encoding="utf-8") as handle:
        for raw_line in handle:
            line = raw_line.rstrip("\n")
            heading_match = heading_re.match(line)
            if heading_match:
                runid = heading_match.group(1).strip()
                config = heading_match.group(2).strip()
                current_key = (runid, config)
                continue

            if current_key is None:
                continue

            snippet_match = snippet_re.match(line)
            if not snippet_match:
                continue
            snippet_payload = snippet_match.group(1)
            if ":1:" not in snippet_payload:
                continue
            json_payload = snippet_payload.split(":1:", 1)[1]
            try:
                parsed = json.loads(json_payload)
            except json.JSONDecodeError:
                continue
            state = get_nested(parsed, "py/state")
            if isinstance(state, dict):
                result[current_key] = state
    return result


def load_run_state(
    runid: str,
    config: str,
    fallback_states: dict[tuple[str, str], dict[str, Any]],
) -> tuple[str, Path, dict[str, Any] | None]:
    wepp_nodb_path = Path("/wc1/runs") / runid[:2] / runid / "wepp.nodb"
    try:
        with wepp_nodb_path.open("r", encoding="utf-8") as handle:
            parsed = json.load(handle)
        state = get_nested(parsed, "py/state")
        if isinstance(state, dict):
            return "live_wc1", wepp_nodb_path, state
    except (OSError, json.JSONDecodeError):
        pass

    fallback_state = fallback_states.get((runid, config))
    if isinstance(fallback_state, dict):
        return "defect_summary_md", wepp_nodb_path, fallback_state

    return "unavailable", wepp_nodb_path, None


def build_run_table(
    rollup_df: pd.DataFrame,
    fallback_states: dict[tuple[str, str], dict[str, Any]],
) -> tuple[pd.DataFrame, list[str]]:
    run_records: list[dict[str, Any]] = []
    warnings: list[str] = []

    grouped = rollup_df.groupby(["runid", "config"], sort=False, dropna=False)
    for (runid, config), group in grouped:
        source, wepp_nodb_path, state = load_run_state(str(runid), str(config), fallback_states)
        if source == "unavailable":
            warnings.append(
                f"warning: missing run metadata for {runid}/{config} at {wepp_nodb_path}"
            )

        wepp_bin = None
        mods = None
        multi_ofe = None
        wd = None
        staged_runs_dir = None
        if state is not None:
            wepp_bin = state.get("_wepp_bin")
            mods_value = state.get("_mods")
            if isinstance(mods_value, list):
                mods = ";".join(str(item) for item in mods_value)
            elif mods_value is not None:
                mods = str(mods_value)
            multi_ofe = state.get("_multi_ofe")
            wd = state.get("wd")
            if wd:
                staged_runs_dir = f"{wd}/wepp/runs"

        n_total = int(len(group))
        flagged_mask = group["requires_scientific_review_bool"]
        n_flagged = int(flagged_mask.sum())
        flag_rate_pct = round((100.0 * n_flagged / n_total), 1) if n_total else 0.0

        run_records.append(
            {
                "runid": str(runid),
                "config": str(config),
                "wepp_bin": wepp_bin,
                "mods": mods,
                "multi_ofe": multi_ofe,
                "wd": wd,
                "staged_runs_dir": staged_runs_dir,
                "n_hillslopes_total": n_total,
                "n_hillslopes_flagged": n_flagged,
                "flag_rate_pct": flag_rate_pct,
                "max_abs_closure_mm_run_max": float(group["max_abs_closure_mm"].max()),
                "max_abs_ofe_closure_mm_run_max": float(group["max_abs_ofe_closure_mm"].max()),
                "wepp_nodb_path": str(wepp_nodb_path),
                "wepp_nodb_source": source,
            }
        )

    run_df = pd.DataFrame(run_records, columns=RUN_COLUMNS)
    return run_df, warnings


def extract_hillslope_row(row: pd.Series, summary: dict[str, Any]) -> dict[str, Any]:
    full = summary.get("full_physical_closure", {})
    mofe = summary.get("mofe_chain", {})
    whole = summary.get("whole_run_closure", {})
    thresholds = full.get("requires_scientific_review_thresholds", {})
    max_abs_day = full.get("max_abs_day", {})
    max_review_day = full.get("max_requires_scientific_review_day", {})

    n_ofe_max = maybe_int(summary.get("n_ofe_max"))
    n_ofe_min = maybe_int(summary.get("n_ofe_min"))
    late_outlier_ofe_id = maybe_int(get_nested(max_review_day, "late_outlier_ofe_id"))

    outlier_is_outlet_ofe = bool(
        late_outlier_ofe_id is not None and n_ofe_max is not None and late_outlier_ofe_id == n_ofe_max
    )
    outlier_is_first_ofe = bool(late_outlier_ofe_id is not None and late_outlier_ofe_id == 1)
    outlier_is_interior_ofe = bool(
        late_outlier_ofe_id is not None
        and n_ofe_max is not None
        and 1 < late_outlier_ofe_id < n_ofe_max
    )

    requires_days = maybe_int(full.get("requires_scientific_review_days"))
    total_days = maybe_int(summary.get("rows"))
    if requires_days is None:
        requires_days = maybe_int(row["requires_scientific_review_days"])
    if requires_days is None:
        requires_days = 0
    if total_days is None:
        total_days = 0
    flagged_day_fraction = round((requires_days / total_days), 4) if total_days else 0.0

    return {
        "runid": str(row["runid"]),
        "config": str(row["config"]),
        "wepp_id": maybe_int(row["wepp_id"]),
        "topaz_id": maybe_int(row["topaz_id"]),
        "summary_json_path": str(row["summary_json_path"]),
        "top_days_csv_path": str(row["top_days_csv_path"]),
        "late_max_abs_ofe_closure_residual_mm_max_abs": get_nested(
            full, "late_max_abs_ofe_closure_residual_mm", "max_abs"
        ),
        "late_max_abs_ofe_closure_residual_mm_p99": get_nested(
            full, "late_max_abs_ofe_closure_residual_mm", "p99"
        ),
        "late_max_abs_ofe_closure_residual_mm_p95": get_nested(
            full, "late_max_abs_ofe_closure_residual_mm", "p95"
        ),
        "late_max_abs_ofe_closure_residual_mm_p90": get_nested(
            full, "late_max_abs_ofe_closure_residual_mm", "p90"
        ),
        "late_max_surface_pulse_proxy_mm_max_abs": get_nested(
            full, "late_max_surface_pulse_proxy_mm", "max_abs"
        ),
        "late_max_surface_pulse_proxy_mm_p99": get_nested(
            full, "late_max_surface_pulse_proxy_mm", "p99"
        ),
        "late_max_qofe_to_q_ratio_max_abs": get_nested(
            full, "late_max_qofe_to_q_ratio", "max_abs"
        ),
        "late_max_qofe_to_q_ratio_p99": get_nested(full, "late_max_qofe_to_q_ratio", "p99"),
        "closure_residual_pct_of_rm_total": get_nested(full, "closure_residual_pct_of_rm_total"),
        "closure_residual_total_mm": get_nested(full, "closure_residual_total_mm"),
        "max_abs_ofe_closure_residual_mm_max_abs": get_nested(
            full, "max_abs_ofe_closure_residual_mm", "max_abs"
        ),
        "closure_residual_mm_max_abs": get_nested(full, "closure_residual_mm", "max_abs"),
        "closure_residual_mm_p99": get_nested(full, "closure_residual_mm", "p99"),
        "n_ofe_max": n_ofe_max,
        "n_ofe_min": n_ofe_min,
        "late_outlier_ofe_id": late_outlier_ofe_id,
        "outlier_is_outlet_ofe": outlier_is_outlet_ofe,
        "outlier_is_first_ofe": outlier_is_first_ofe,
        "outlier_is_interior_ofe": outlier_is_interior_ofe,
        "chain_subsurface_transfer_residual_m3_max_abs": get_nested(
            mofe, "subsurface_transfer_residual_m3", "max_abs"
        ),
        "chain_subsurface_transfer_residual_m3_p99": get_nested(
            mofe, "subsurface_transfer_residual_m3", "p99"
        ),
        "chain_surface_transfer_residual_m3_max_abs": get_nested(
            mofe, "surface_transfer_residual_m3_geometry_sensitive", "max_abs"
        ),
        "chain_surface_transfer_residual_m3_p99": get_nested(
            mofe, "surface_transfer_residual_m3_geometry_sensitive", "p99"
        ),
        "runoff_pass_vs_outlet_qofe_residual_m3_max_abs": get_nested(
            mofe, "runoff_pass_vs_outlet_qofe_residual_m3", "max_abs"
        ),
        "runoff_pass_vs_outlet_qofe_residual_m3_p99": get_nested(
            mofe, "runoff_pass_vs_outlet_qofe_residual_m3", "p99"
        ),
        "first_ofe_nonzero_subrin_days": maybe_int(get_nested(mofe, "first_ofe_nonzero_subrin_days")),
        "first_ofe_nonzero_upstrmq_days": maybe_int(
            get_nested(mofe, "first_ofe_nonzero_upstrmq_days")
        ),
        "strict_chain_invariants_applicable": (
            get_nested(mofe, "strict_chain_invariants_applicability")
            or get_nested(mofe, "strict_chain_invariants_applicable")
        ),
        "soilwater_to_porosity_fraction_max_abs": get_nested(
            summary, "soilwater_to_porosity_fraction", "max_abs"
        ),
        "soilwater_to_porosity_fraction_p99": get_nested(
            summary, "soilwater_to_porosity_fraction", "p99"
        ),
        "soilwater_minus_fc_mm_max_abs": get_nested(summary, "soilwater_minus_fc_mm", "max_abs"),
        "soilwater_minus_wp_mm_max_abs": get_nested(summary, "soilwater_minus_wp_mm", "max_abs"),
        "soilwater_gt_porositycap_days": maybe_int(get_nested(whole, "soilwater_gt_porositycap_days")),
        "soilwater_lt_wpstore_days": maybe_int(get_nested(whole, "soilwater_lt_wpstore_days")),
        "profile_order_fc_gt_porosity_days": maybe_int(
            get_nested(whole, "profile_order_fc_gt_porosity_days")
        ),
        "profile_order_wp_gt_fc_days": maybe_int(get_nested(whole, "profile_order_wp_gt_fc_days")),
        "precip_total_mm": get_nested(whole, "precip_total_mm"),
        "runoff_reported_total_mm": get_nested(whole, "runoff_reported_total_mm"),
        "lateral_reported_total_mm": get_nested(whole, "lateral_reported_total_mm"),
        "et_reported_total_mm": get_nested(whole, "et_reported_total_mm"),
        "storage_change_mm": get_nested(whole, "storage_change_mm"),
        "requires_scientific_review_days": requires_days,
        "total_simulation_days": total_days,
        "flagged_day_fraction": flagged_day_fraction,
        "max_anomaly_year": maybe_int(get_nested(max_abs_day, "year")),
        "max_anomaly_month": maybe_int(get_nested(max_abs_day, "month")),
        "max_anomaly_julian": maybe_int(get_nested(max_abs_day, "julian")),
        "worst_review_day_year": maybe_int(get_nested(max_review_day, "year")),
        "worst_review_day_month": maybe_int(get_nested(max_review_day, "month")),
        "worst_review_day_julian": maybe_int(get_nested(max_review_day, "julian")),
        "worst_review_day_reason": get_nested(max_review_day, "reason"),
        "worst_review_day_late_residual_mm": get_nested(
            max_review_day, "late_max_abs_ofe_closure_residual_mm"
        ),
        "worst_review_day_late_pulse_mm": get_nested(
            max_review_day, "late_max_surface_pulse_proxy_mm"
        ),
        "worst_review_day_qofe_to_q_ratio": get_nested(max_review_day, "late_max_qofe_to_q_ratio"),
        "threshold_late_ofe_residual_mm": get_nested(
            thresholds, "late_max_abs_ofe_closure_residual_mm"
        ),
        "threshold_late_pulse_mm": get_nested(thresholds, "late_max_surface_pulse_proxy_mm"),
        "threshold_late_qofe_to_q_ratio": get_nested(thresholds, "late_max_qofe_to_q_ratio"),
        "threshold_late_ofe_window": maybe_int(get_nested(thresholds, "late_ofe_window")),
    }


def build_hillslope_table(rollup_df: pd.DataFrame) -> pd.DataFrame:
    records: list[dict[str, Any]] = []
    for row in rollup_df.itertuples(index=False):
        row_series = pd.Series(row._asdict())
        summary_path = Path(str(row_series["summary_json_path"]))
        with summary_path.open("r", encoding="utf-8") as handle:
            summary = json.load(handle)
        records.append(extract_hillslope_row(row_series, summary))

    return pd.DataFrame(records, columns=HILLSLOPE_COLUMNS)


def validate_non_nullable(df: pd.DataFrame, columns: list[str], table_name: str) -> None:
    missing = {}
    for col in columns:
        if col not in df.columns:
            missing[col] = "column_missing"
            continue
        null_count = int(df[col].isna().sum())
        if null_count:
            missing[col] = f"{null_count} nulls"
    if missing:
        details = ", ".join(f"{col}={issue}" for col, issue in missing.items())
        raise ValueError(f"{table_name} non-null validation failed: {details}")


def main() -> int:
    args = parse_args()
    output_dir = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    rollup_df = pd.read_csv(args.rollup_csv)
    required_rollup_columns = [
        "runid",
        "config",
        "wepp_id",
        "topaz_id",
        "requires_scientific_review",
        "requires_scientific_review_days",
        "max_abs_closure_mm",
        "max_abs_ofe_closure_mm",
        "summary_json_path",
        "top_days_csv_path",
    ]
    missing_rollup = [c for c in required_rollup_columns if c not in rollup_df.columns]
    if missing_rollup:
        raise ValueError(f"rollup CSV missing required columns: {missing_rollup}")

    rollup_df["requires_scientific_review_bool"] = rollup_df["requires_scientific_review"].map(
        normalize_bool
    )

    fallback_states = parse_defect_summary_fallback(args.defect_summary_md)
    run_df, warnings = build_run_table(rollup_df, fallback_states)
    for warning in warnings:
        print(warning, file=sys.stderr)

    hillslopes_all_df = build_hillslope_table(rollup_df)
    if args.include_passing:
        hillslopes_df = hillslopes_all_df.copy()
    else:
        flagged_mask = rollup_df["requires_scientific_review_bool"].to_numpy()
        hillslopes_df = hillslopes_all_df.loc[flagged_mask].reset_index(drop=True)

    validate_non_nullable(run_df, NON_NULLABLE_RUN_COLUMNS, "triage_table_runs.csv")
    validate_non_nullable(
        hillslopes_df, NON_NULLABLE_HILLSLOPE_COLUMNS, "triage_table_hillslopes.csv"
    )
    validate_non_nullable(
        hillslopes_all_df, NON_NULLABLE_HILLSLOPE_COLUMNS, "triage_table_hillslopes_all.csv"
    )

    run_path = output_dir / "triage_table_runs.csv"
    hillslope_path = output_dir / "triage_table_hillslopes.csv"
    hillslope_all_path = output_dir / "triage_table_hillslopes_all.csv"
    run_df.to_csv(run_path, index=False)
    hillslopes_df.to_csv(hillslope_path, index=False)
    hillslopes_all_df.to_csv(hillslope_all_path, index=False)

    flagged_count = int(rollup_df["requires_scientific_review_bool"].sum())
    total_count = int(len(rollup_df))
    print(
        f"triage_table built: {len(run_df)} runs, {flagged_count} flagged hillslopes, {total_count} total hillslopes"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
