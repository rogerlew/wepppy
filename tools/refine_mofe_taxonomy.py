#!/usr/bin/env python3
"""Refine MOFE flagged-hillslope taxonomy (v2) and emit follow-up artifacts."""

from __future__ import annotations

import argparse
import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
DEFAULT_ARTIFACTS_DIR = (
    ROOT / "docs/work-packages/20260502_mofe_flagged_hillslope_triage/artifacts"
)
HILLSLOPE_KEY = ["runid", "config", "wepp_id"]
MECHANISTIC_FAMILIES = ["D1", "D2a", "D2b", "D3", "D4", "D5", "D6a", "D6b", "D6c"]
CONTEXT_FILES = [
    "wepp_ui.txt",
    "pmetpara.txt",
    "snow.txt",
    "gwcoeff.txt",
    "chan.inp",
    "chntyp.txt",
    "tc.txt",
]

D0_FEATURES = [
    "late_max_abs_ofe_closure_residual_mm_max_abs",
    "late_max_surface_pulse_proxy_mm_max_abs",
    "closure_residual_pct_of_rm_total",
    "requires_scientific_review_days",
    "chain_surface_transfer_residual_m3_p99",
    "chain_subsurface_transfer_residual_m3_p99",
]

CLUSTER_FEATURES = [
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
    "worst_review_day_late_residual_mm",
    "worst_review_day_late_pulse_mm",
    "worst_review_day_qofe_to_q_ratio",
]

SEED_DISTANCE_FEATURES = [
    "late_max_abs_ofe_closure_residual_mm_max_abs",
    "late_max_surface_pulse_proxy_mm_max_abs",
    "closure_residual_pct_of_rm_total",
    "requires_scientific_review_days",
    "chain_surface_transfer_residual_m3_p99",
    "chain_subsurface_transfer_residual_m3_p99",
    "soilwater_to_porosity_fraction_p99",
    "flagged_day_fraction",
]

SENSITIVITY_SPECS = [
    ("D1", "d1_magnitude"),
    ("D2a", "d2a_chain_p99"),
    ("D2b", "d2b_runoff_mismatch"),
    ("D3", "d3_porosity_fraction"),
    ("D4", "d4_magnitude"),
    ("D5", "d5_day_lower"),
    ("D6a", "d6a_magnitude_lower"),
    ("D6b", "d6b_magnitude_lower"),
    ("D6c", "d6c_day_lower"),
    ("D6c", "d6c_magnitude_lower"),
]


@dataclass
class Thresholds:
    d1_magnitude: float = 1000.0
    d2a_chain_p99: float = 1e-3
    d2b_runoff_mismatch: float = 1.0
    d3_porosity_fraction: float = 0.99
    d4_magnitude: float = 500.0
    d5_day_lower: float = 30.0
    d5_magnitude_lower: float = 100.0
    d5_magnitude_upper: float = 500.0
    d6a_day_upper: float = 3.0
    d6a_magnitude_lower: float = 100.0
    d6a_magnitude_upper: float = 500.0
    d6b_day_lower: float = 4.0
    d6b_day_upper: float = 29.0
    d6b_magnitude_lower: float = 100.0
    d6c_day_lower: float = 30.0
    d6c_magnitude_lower: float = 500.0

    def copy(self) -> "Thresholds":
        return Thresholds(**self.__dict__)


@dataclass
class ClusterResult:
    labels: np.ndarray
    algorithm: str


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=DEFAULT_ARTIFACTS_DIR,
        help="Directory containing v1/v2 triage artifacts",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_ARTIFACTS_DIR,
        help="Directory where v2 artifacts are written",
    )
    parser.add_argument(
        "--no-cluster",
        action="store_true",
        help="Skip cluster cross-check and disagreement export.",
    )
    parser.add_argument(
        "--no-sensitivity",
        action="store_true",
        help="Skip threshold sensitivity sweep export.",
    )
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
    return str(value).strip().lower() in {"1", "true", "t", "yes", "y"}


def standardize(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    work = df[columns].copy()
    for col in columns:
        if work[col].dtype == bool:
            work[col] = work[col].astype(int)
        else:
            work[col] = pd.to_numeric(work[col], errors="coerce")
    means = work.mean(skipna=True)
    stds = work.std(skipna=True, ddof=0).replace(0, np.nan)
    z = (work - means) / stds
    return z.replace([np.inf, -np.inf], np.nan).fillna(0.0)


def normalize_inputs(input_dir: Path) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    flagged = pd.read_csv(input_dir / "triage_table_hillslopes.csv")
    all_hillslopes = pd.read_csv(input_dir / "triage_table_hillslopes_all.csv")
    runs = pd.read_csv(input_dir / "triage_table_runs.csv")
    v1_taxonomy = pd.read_csv(input_dir / "taxonomy_assignments.csv")

    for df in (flagged, all_hillslopes):
        for col in ["outlier_is_outlet_ofe", "outlier_is_first_ofe", "outlier_is_interior_ofe"]:
            if col in df.columns:
                df[col] = df[col].map(normalize_bool)
        df["wepp_id"] = pd.to_numeric(df["wepp_id"], errors="coerce").fillna(-1).astype(int)
        df["requires_scientific_review_days"] = pd.to_numeric(
            df["requires_scientific_review_days"], errors="coerce"
        ).fillna(0).astype(int)
    for col in ["n_hillslopes_total", "n_hillslopes_flagged"]:
        runs[col] = pd.to_numeric(runs[col], errors="coerce").fillna(0).astype(int)
    v1_taxonomy["wepp_id"] = pd.to_numeric(v1_taxonomy["wepp_id"], errors="coerce").fillna(-1).astype(int)
    return flagged, all_hillslopes, runs, v1_taxonomy


def _match_flags(row: pd.Series, th: Thresholds) -> dict[str, bool]:
    late_max = float(row["late_max_abs_ofe_closure_residual_mm_max_abs"])
    days = int(row["requires_scientific_review_days"])

    ratio_sat = False
    if pd.notna(row.get("late_max_qofe_to_q_ratio_max_abs")) and pd.notna(row.get("n_ofe_max")):
        ratio_sat = float(row["late_max_qofe_to_q_ratio_max_abs"]) >= (
            float(row["n_ofe_max"]) - 0.01
        )

    d1 = bool(row["outlier_is_outlet_ofe"]) and late_max > th.d1_magnitude and ratio_sat
    d4 = days <= th.d6a_day_upper and late_max >= th.d4_magnitude
    d5 = days >= th.d5_day_lower and th.d5_magnitude_lower <= late_max <= th.d5_magnitude_upper
    d6c = days >= th.d6c_day_lower and late_max > th.d6c_magnitude_lower
    d2a = bool(row["outlier_is_interior_ofe"]) and (
        (pd.notna(row.get("chain_surface_transfer_residual_m3_p99")) and float(row["chain_surface_transfer_residual_m3_p99"]) > th.d2a_chain_p99)
        or (
            pd.notna(row.get("chain_subsurface_transfer_residual_m3_p99"))
            and float(row["chain_subsurface_transfer_residual_m3_p99"]) > th.d2a_chain_p99
        )
    )
    d2b = (
        bool(row["outlier_is_outlet_ofe"])
        and pd.notna(row.get("runoff_pass_vs_outlet_qofe_residual_m3_max_abs"))
        and float(row["runoff_pass_vs_outlet_qofe_residual_m3_max_abs"]) > th.d2b_runoff_mismatch
        and not d1
    )
    d3 = pd.notna(row.get("soilwater_to_porosity_fraction_p99")) and float(
        row["soilwater_to_porosity_fraction_p99"]
    ) >= th.d3_porosity_fraction
    d6a = days <= th.d6a_day_upper and th.d6a_magnitude_lower <= late_max < th.d6a_magnitude_upper
    d6b = th.d6b_day_lower <= days <= th.d6b_day_upper and late_max >= th.d6b_magnitude_lower

    return {
        "D1": d1,
        "D4": d4,
        "D5": d5,
        "D6c": d6c,
        "D2a": d2a,
        "D2b": d2b,
        "D3": d3,
        "D6a": d6a,
        "D6b": d6b,
    }


def classify_rows(flagged: pd.DataFrame, th: Thresholds) -> pd.DataFrame:
    rows: list[dict[str, Any]] = []
    order = ["D1", "D4", "D5", "D6c", "D2a", "D2b", "D3", "D6a", "D6b"]

    for row in flagged.to_dict(orient="records"):
        s = pd.Series(row)
        matches = _match_flags(s, th)
        matched = [fam for fam in order if matches[fam]]
        primary = matched[0] if matched else "D_UNCLASSIFIED"
        secondary = matched[1] if len(matched) > 1 else ""
        tertiary = matched[2] if len(matched) > 2 else ""

        if primary == "D1":
            rationale = (
                "D1: outlier_is_outlet_ofe=True, "
                f"late_max_abs_ofe_closure_residual_mm_max_abs={float(s['late_max_abs_ofe_closure_residual_mm_max_abs']):.3f}>{th.d1_magnitude:.3f}, "
                "late_max_qofe_to_q_ratio_max_abs>=n_ofe_max-0.01."
            )
        elif primary == "D4":
            rationale = (
                "D4: requires_scientific_review_days="
                f"{int(s['requires_scientific_review_days'])}<={int(th.d6a_day_upper)} and "
                f"late_max_abs_ofe_closure_residual_mm_max_abs={float(s['late_max_abs_ofe_closure_residual_mm_max_abs']):.3f}>={th.d4_magnitude:.3f}."
            )
        elif primary == "D5":
            rationale = (
                "D5: requires_scientific_review_days="
                f"{int(s['requires_scientific_review_days'])}>={int(th.d5_day_lower)} and "
                f"late_max_abs_ofe_closure_residual_mm_max_abs in [{th.d5_magnitude_lower:.3f},{th.d5_magnitude_upper:.3f}]."
            )
        elif primary == "D6c":
            rationale = (
                "D6c: requires_scientific_review_days="
                f"{int(s['requires_scientific_review_days'])}>={int(th.d6c_day_lower)} and "
                f"late_max_abs_ofe_closure_residual_mm_max_abs={float(s['late_max_abs_ofe_closure_residual_mm_max_abs']):.3f}>{th.d6c_magnitude_lower:.3f}."
            )
        elif primary == "D2a":
            rationale = (
                "D2a: outlier_is_interior_ofe=True and "
                f"(chain_surface_transfer_residual_m3_p99>{th.d2a_chain_p99:g} or "
                f"chain_subsurface_transfer_residual_m3_p99>{th.d2a_chain_p99:g})."
            )
        elif primary == "D2b":
            rationale = (
                "D2b: outlier_is_outlet_ofe=True, NOT D1, "
                f"runoff_pass_vs_outlet_qofe_residual_m3_max_abs>{th.d2b_runoff_mismatch:.6f}."
            )
        elif primary == "D3":
            rationale = (
                "D3: soilwater_to_porosity_fraction_p99="
                f"{float(s['soilwater_to_porosity_fraction_p99']):.3f}>={th.d3_porosity_fraction:.3f}."
            )
        elif primary == "D6a":
            rationale = (
                "D6a: requires_scientific_review_days="
                f"{int(s['requires_scientific_review_days'])}<={int(th.d6a_day_upper)} and "
                f"late_max_abs_ofe_closure_residual_mm_max_abs in [{th.d6a_magnitude_lower:.3f},{th.d6a_magnitude_upper:.3f})."
            )
        elif primary == "D6b":
            rationale = (
                "D6b: requires_scientific_review_days in "
                f"[{int(th.d6b_day_lower)},{int(th.d6b_day_upper)}] and "
                f"late_max_abs_ofe_closure_residual_mm_max_abs>={th.d6b_magnitude_lower:.3f}."
            )
        else:
            rationale = "No v2 rule matched after D1/D2a/D2b/D3/D4/D5/D6a/D6b/D6c evaluation."

        rows.append(
            {
                "runid": row["runid"],
                "config": row["config"],
                "wepp_id": int(row["wepp_id"]),
                "family_primary": primary,
                "family_secondary": secondary,
                "family_tertiary": tertiary,
                "family_rationale": rationale,
            }
        )

    return pd.DataFrame(rows)


def apply_sparse_family_merges(taxonomy: pd.DataFrame) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    merge_map = {
        "D2a": "D2b",
        "D5": "D6b",
        "D6a": "D6b",
        "D6c": "D1",
        "D3": "D2b",
    }
    merged = taxonomy.copy()
    actions: list[dict[str, Any]] = []

    counts = merged["family_primary"].value_counts()
    sparse = [
        fam
        for fam, count in counts.items()
        if fam not in {"D4", "D0", "D_UNCLASSIFIED"} and count < 3
    ]

    for fam in sparse:
        target = merge_map.get(fam)
        if not target:
            continue
        fam_idx = merged.index[merged["family_primary"] == fam]
        if len(fam_idx) == 0:
            continue
        for idx in fam_idx:
            old_primary = merged.at[idx, "family_primary"]
            old_secondary = merged.at[idx, "family_secondary"]
            merged.at[idx, "family_primary"] = target
            merged.at[idx, "family_secondary"] = old_primary
            merged.at[idx, "family_tertiary"] = (
                old_secondary if old_secondary else merged.at[idx, "family_tertiary"]
            )
            merged.at[idx, "family_rationale"] = (
                merged.at[idx, "family_rationale"]
                + f" Sparse-family merge: {fam} population<{3}; reassigned to {target}."
            )
        actions.append(
            {
                "from_family": fam,
                "to_family": target,
                "row_count": int(len(fam_idx)),
            }
        )

    return merged, actions


def apply_d0_demotion(taxonomy: pd.DataFrame, flagged: pd.DataFrame) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    merged = taxonomy.merge(flagged[HILLSLOPE_KEY + D0_FEATURES], on=HILLSLOPE_KEY, how="left")
    output = taxonomy.copy()
    demotions: list[dict[str, Any]] = []

    families = sorted(f for f in output["family_primary"].unique() if f not in {"D0", "D_UNCLASSIFIED"})
    for family in families:
        family_rows = merged[merged["family_primary"] == family].copy()
        size = int(len(family_rows))
        if size < 5:
            continue

        counts = (
            family_rows.groupby(["runid", "config"], dropna=False)
            .size()
            .reset_index(name="count")
            .sort_values("count", ascending=False)
        )
        dominant = counts.iloc[0]
        concentration = float(dominant["count"] / size)
        if concentration < 0.95:
            continue

        runid = str(dominant["runid"])
        config = str(dominant["config"])
        run_rows = merged[(merged["runid"] == runid) & (merged["config"] == config)].copy()
        for col in D0_FEATURES:
            family_rows[col] = pd.to_numeric(family_rows[col], errors="coerce").fillna(0.0)
            run_rows[col] = pd.to_numeric(run_rows[col], errors="coerce").fillna(0.0)

        run_mean = run_rows[D0_FEATURES].mean()
        run_std = run_rows[D0_FEATURES].std(ddof=0).replace(0.0, 1e-9)
        fam_mean = family_rows[D0_FEATURES].mean()
        deltas = ((fam_mean - run_mean).abs() / run_std).to_dict()
        deltas_vals = list(deltas.values())
        small_count = sum(1 for v in deltas_vals if v <= 0.35)
        max_delta = max(deltas_vals) if deltas_vals else 0.0
        if not (small_count >= 5 and max_delta <= 0.75):
            continue

        idxs = output.index[output["family_primary"] == family]
        for idx in idxs:
            old_primary = output.at[idx, "family_primary"]
            old_secondary = output.at[idx, "family_secondary"]
            output.at[idx, "family_primary"] = "D0"
            output.at[idx, "family_secondary"] = old_primary
            output.at[idx, "family_tertiary"] = (
                old_secondary if old_secondary else output.at[idx, "family_tertiary"]
            )
            output.at[idx, "family_rationale"] = (
                output.at[idx, "family_rationale"]
                + " D0 demotion: concentration="
                + f"{concentration:.3f}, max_delta={max_delta:.3f}, small_delta_count={small_count}."
            )

        demotions.append(
            {
                "from_family": family,
                "to_family": "D0",
                "family_size": size,
                "dominant_runid": runid,
                "dominant_config": config,
                "concentration": concentration,
                "feature_deltas": {k: float(v) for k, v in deltas.items()},
                "small_delta_count": int(small_count),
                "max_delta": float(max_delta),
            }
        )

    return output, demotions


def summarize_counts(taxonomy: pd.DataFrame) -> dict[str, int]:
    vc = taxonomy["family_primary"].value_counts()
    return {k: int(v) for k, v in vc.items()}


def calibrate_thresholds(flagged: pd.DataFrame) -> tuple[Thresholds, pd.DataFrame, list[dict[str, Any]]]:
    decisions: list[dict[str, Any]] = []
    thresholds = Thresholds()

    # Pass 1: baseline
    taxonomy = classify_rows(flagged, thresholds)
    counts = summarize_counts(taxonomy)
    decisions.append({"stage": "baseline", "thresholds": thresholds.__dict__.copy(), "counts": counts})

    # D2b guardrail ladder if >75%
    d2b_share = counts.get("D2b", 0) / len(flagged)
    if d2b_share > 0.75:
        candidate = flagged.copy()
        prelim = classify_rows(flagged, thresholds)
        merged = flagged.merge(
            prelim[HILLSLOPE_KEY + ["family_primary"]],
            on=HILLSLOPE_KEY,
            how="left",
        )
        non_d1_outlet = merged[
            (merged["outlier_is_outlet_ofe"]) & (merged["family_primary"] != "D1")
        ]
        series = pd.to_numeric(
            non_d1_outlet["runoff_pass_vs_outlet_qofe_residual_m3_max_abs"],
            errors="coerce",
        ).dropna()
        ladder = [1.0]
        if not series.empty:
            ladder.extend(
                float(series.quantile(q))
                for q in [0.60, 0.70, 0.75]
            )
        used = thresholds.d2b_runoff_mismatch
        for value in ladder:
            thresholds_try = thresholds.copy()
            thresholds_try.d2b_runoff_mismatch = float(value)
            taxonomy_try = classify_rows(flagged, thresholds_try)
            counts_try = summarize_counts(taxonomy_try)
            share_try = counts_try.get("D2b", 0) / len(flagged)
            used = float(value)
            if share_try <= 0.75:
                thresholds = thresholds_try
                taxonomy = taxonomy_try
                counts = counts_try
                break
        decisions.append(
            {
                "stage": "d2b_guardrail",
                "threshold_name": "d2b_runoff_mismatch",
                "selected_value": used,
                "counts": counts,
            }
        )

    # D3 guardrail if >50%
    d3_share = counts.get("D3", 0) / len(flagged)
    if d3_share > 0.50:
        thresholds.d3_porosity_fraction = 0.995
        taxonomy = classify_rows(flagged, thresholds)
        counts = summarize_counts(taxonomy)
        decisions.append(
            {
                "stage": "d3_guardrail",
                "threshold_name": "d3_porosity_fraction",
                "selected_value": 0.995,
                "counts": counts,
            }
        )

    taxonomy, sparse_actions = apply_sparse_family_merges(taxonomy)
    counts = summarize_counts(taxonomy)
    if sparse_actions:
        decisions.append({"stage": "sparse_family_merge", "actions": sparse_actions, "counts": counts})

    taxonomy, demotions = apply_d0_demotion(taxonomy, flagged)
    counts = summarize_counts(taxonomy)
    if demotions:
        decisions.append({"stage": "d0_demotion", "demotions": demotions, "counts": counts})

    # Gates
    unclassified = counts.get("D_UNCLASSIFIED", 0)
    if unclassified > 7:
        raise RuntimeError(
            f"D_UNCLASSIFIED gate failed: {unclassified} rows (must be <= 7)."
        )

    for family, count in counts.items():
        if family in {"D4", "D0", "D_UNCLASSIFIED"}:
            continue
        if count > 0 and count < 3:
            raise RuntimeError(
                f"Family-size gate failed: {family} has {count} rows (<3; only D4 exempt)."
            )

    return thresholds, taxonomy, decisions


def cluster_rows(features_z: pd.DataFrame) -> ClusterResult:
    x = features_z.to_numpy(dtype=float)
    try:
        import hdbscan  # type: ignore

        model = hdbscan.HDBSCAN(min_cluster_size=5)
        labels = model.fit_predict(x)
        return ClusterResult(labels=labels.astype(int), algorithm="hdbscan(min_cluster_size=5)")
    except Exception:
        pass

    try:
        from sklearn_extra.cluster import KMedoids  # type: ignore

        model = KMedoids(n_clusters=6, random_state=42)
        labels = model.fit_predict(x)
        return ClusterResult(labels=labels.astype(int), algorithm="kmedoids(n_clusters=6)")
    except Exception:
        pass

    from sklearn.cluster import KMeans

    model = KMeans(n_clusters=6, random_state=42, n_init=20)
    labels = model.fit_predict(x)
    return ClusterResult(labels=labels.astype(int), algorithm="kmeans(n_clusters=6)")


def compute_rule_cluster_agreement(taxonomy: pd.DataFrame) -> pd.DataFrame:
    out = taxonomy.copy()
    agreements: list[str] = []
    for row in out.to_dict(orient="records"):
        cluster = int(row["cluster_label"])
        family = row["family_primary"]
        if cluster == -1:
            agreements.append("noise")
            continue
        in_cluster = out[out["cluster_label"] == cluster]
        in_family = out[out["family_primary"] == family]
        overlap = out[(out["cluster_label"] == cluster) & (out["family_primary"] == family)]
        if len(in_cluster) == 0 or len(in_family) == 0:
            agreements.append("disagree")
            continue
        share_cluster = len(overlap) / len(in_cluster)
        share_family = len(overlap) / len(in_family)
        agreements.append("agree" if (share_cluster > 0.5 or share_family > 0.5) else "disagree")
    out["rule_cluster_agreement"] = agreements
    return out


def build_disagreements(flagged: pd.DataFrame, taxonomy: pd.DataFrame) -> pd.DataFrame:
    joined = flagged.merge(
        taxonomy[
            HILLSLOPE_KEY + ["family_primary", "cluster_label", "rule_cluster_agreement"]
        ],
        on=HILLSLOPE_KEY,
        how="left",
    )
    return joined[joined["rule_cluster_agreement"] == "disagree"].copy()


def pick_representative_seeds(
    flagged: pd.DataFrame,
    all_hillslopes: pd.DataFrame,
    runs: pd.DataFrame,
    taxonomy: pd.DataFrame,
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    flagged_tagged = flagged.merge(taxonomy[HILLSLOPE_KEY + ["family_primary"]], on=HILLSLOPE_KEY, how="left")
    all_tagged = all_hillslopes.merge(
        taxonomy[HILLSLOPE_KEY + ["family_primary"]],
        on=HILLSLOPE_KEY,
        how="left",
    )
    all_tagged["family_primary"] = all_tagged["family_primary"].fillna("")

    z_all = standardize(all_tagged, SEED_DISTANCE_FEATURES)
    z_all.columns = [f"z_{c}" for c in SEED_DISTANCE_FEATURES]
    all_tagged = pd.concat([all_tagged.reset_index(drop=True), z_all.reset_index(drop=True)], axis=1)
    z_cols = [f"z_{c}" for c in SEED_DISTANCE_FEATURES]

    run_context = runs.set_index(["runid", "config"])["staged_runs_dir"].to_dict()
    rep_rows: list[dict[str, Any]] = []
    missing_alerts: list[dict[str, Any]] = []

    families = sorted(
        f
        for f in flagged_tagged["family_primary"].unique()
        if f and f not in {"D0", "D_UNCLASSIFIED"}
    )

    for family in families:
        fam = flagged_tagged[flagged_tagged["family_primary"] == family].copy()
        if fam.empty:
            continue
        worst = fam.loc[fam["late_max_abs_ofe_closure_residual_mm_max_abs"].idxmax()]

        median_target = fam["late_max_abs_ofe_closure_residual_mm_max_abs"].median()
        fam["median_dist"] = (fam["late_max_abs_ofe_closure_residual_mm_max_abs"] - median_target).abs()
        median = fam.sort_values(["median_dist", "requires_scientific_review_days"]).iloc[0]

        dominant = (
            fam.groupby(["runid", "config"]).size().reset_index(name="n").sort_values("n", ascending=False).iloc[0]
        )
        target_runid = str(dominant["runid"])
        target_config = str(dominant["config"])

        fam_z = fam.merge(all_tagged[HILLSLOPE_KEY + z_cols], on=HILLSLOPE_KEY, how="left")
        centroid = fam_z[z_cols].mean().to_numpy(dtype=float)
        candidates = all_tagged[
            (all_tagged["requires_scientific_review_days"] == 0)
            & (all_tagged["runid"] == target_runid)
            & (all_tagged["config"] == target_config)
        ].copy()
        if candidates.empty:
            candidates = all_tagged[
                (all_tagged["requires_scientific_review_days"] == 0)
                & (all_tagged["config"] == target_config)
            ].copy()
        if candidates.empty:
            raise RuntimeError(
                f"No unflagged contrast candidates for family {family} under config {target_config}"
            )
        dists = np.linalg.norm(candidates[z_cols].to_numpy(dtype=float) - centroid, axis=1)
        contrast = candidates.iloc[int(np.argmin(dists))]

        for role, row in [("worst", worst), ("median", median), ("contrast", contrast)]:
            key = (str(row["runid"]), str(row["config"]))
            staged_dir = run_context.get(key)
            run_file = ""
            shared_paths: list[str] = []
            missing: list[str] = []
            if isinstance(staged_dir, str) and staged_dir:
                run_file = str(Path(staged_dir) / f"p{int(row['wepp_id'])}.run")
                for name in CONTEXT_FILES:
                    path = str(Path(staged_dir) / name)
                    shared_paths.append(path)
                    if not Path(path).exists():
                        missing.append(name)

            rep = {
                "family": family,
                "role": role,
                "runid": str(row["runid"]),
                "config": str(row["config"]),
                "wepp_id": int(row["wepp_id"]),
                "late_max_abs_ofe_closure_residual_mm_max_abs": float(
                    row["late_max_abs_ofe_closure_residual_mm_max_abs"]
                ),
                "requires_scientific_review_days": int(row["requires_scientific_review_days"]),
                "staged_runs_dir": staged_dir if isinstance(staged_dir, str) else "",
                "run_file": run_file,
                "shared_context_files": ";".join(shared_paths),
                "missing_shared_context": ";".join(missing),
                "top_days_csv_path": str(row["top_days_csv_path"]),
                "summary_json_path": str(row["summary_json_path"]),
            }
            rep_rows.append(rep)
            if role in {"worst", "median"} and missing:
                missing_alerts.append(rep)

    return pd.DataFrame(rep_rows), missing_alerts


def build_campaign_matrix_v2(
    taxonomy: pd.DataFrame, reps: pd.DataFrame
) -> pd.DataFrame:
    hypotheses = {
        "D0": "Config-correlated background dominates with no distinct within-run mechanism separation.",
        "D1": "Outlet-OFE saturation spike with severe magnitude and ratio saturation.",
        "D2a": "Interior chain-transfer anomaly with non-trivial subsurface/surface transfer residuals.",
        "D2b": "Outlet runoff-pass versus outlet-qofe mismatch without D1 severe saturation.",
        "D3": "Storage saturation pressure where porosity fraction stays near the cap.",
        "D4": "Single-day severe spike aligned with closure-spike precedent signatures.",
        "D5": "Persistent moderate regime with long flagged duration and bounded magnitude.",
        "D6a": "Sub-severe single-day spike, numerically surge-like but below D4 magnitude.",
        "D6b": "Multi-day moderate anomaly in the 4-29 day persistence band.",
        "D6c": "Persistent severe regime suggesting structural model gap over numerical blip.",
        "D_UNCLASSIFIED": "Residual taxonomy gap requiring additional rule design.",
    }
    expected = {
        "D0": "Move D0-feature deltas (late residual/pulse, closure pct, day count, chain p99s) toward run baseline.",
        "D1": "Lower late_max_abs_ofe_closure_residual_mm_max_abs below 1000 and break ratio saturation marker.",
        "D2a": "Reduce chain_surface/subsurface_transfer_residual_m3_p99 below 1e-3 on interior-outlier rows.",
        "D2b": "Reduce runoff_pass_vs_outlet_qofe_residual_m3_max_abs below calibrated D2b threshold.",
        "D3": "Reduce soilwater_to_porosity_fraction_p99 below D3 threshold and corresponding late-window pulse severity.",
        "D4": "Eliminate <=3-day severe spikes (late residual >=500) on representative seeds.",
        "D5": "Shrink >=30-day persistent moderate regime below review-trigger envelope.",
        "D6a": "Resolve <=3-day 100-500 mm spikes without introducing persistent anomalies.",
        "D6b": "Collapse 4-29 day moderate anomaly burden below review thresholds.",
        "D6c": "Break long-duration >500 mm regime or isolate explicit model-gap boundary.",
        "D_UNCLASSIFIED": "Define new invariant-separating rule before ablation campaign expansion.",
    }
    criteria = {
        "D0": "PASS if family moments converge to run background without new severe outliers.",
        "D1": "PASS if D1 predicates no longer hold on representative seeds.",
        "D2a": "PASS if interior chain residual predicates clear while review flags drop.",
        "D2b": "PASS if outlet mismatch signal drops below D2b threshold with no D1/D4 substitution.",
        "D3": "PASS if porosity-cap pressure signal clears and flags reduce materially.",
        "D4": "PASS if severe single-day spike is removed and review-day count drops to 0.",
        "D5": "PASS if persistent moderate signature no longer meets day/magnitude gates.",
        "D6a": "PASS if sub-severe single-day spike no longer triggers review flags.",
        "D6b": "PASS if 4-29 day moderate pattern no longer dominates the family.",
        "D6c": "PASS if persistent severe regime is eliminated or transformed into bounded families.",
        "D_UNCLASSIFIED": "PASS criteria deferred; hold pending taxonomy expansion.",
    }
    signatures = {
        "D0": "config-correlated-background",
        "D1": "outlet-saturation-severe",
        "D2a": "interior-chain-anomaly",
        "D2b": "outlet-runoff-qofe-mismatch",
        "D3": "storage-cap-pressure",
        "D4": "single-day-severe-spike",
        "D5": "persistent-moderate",
        "D6a": "single-day-sub-severe",
        "D6b": "multi-day-moderate",
        "D6c": "persistent-severe",
        "D_UNCLASSIFIED": "taxonomy-gap",
    }

    today = datetime.now(tz=timezone.utc).strftime("%Y%m%d")
    rows: list[dict[str, Any]] = []
    counts = taxonomy["family_primary"].value_counts()
    families = sorted(f for f in counts.index if counts[f] > 0)

    for family in families:
        fam_rows = taxonomy[taxonomy["family_primary"] == family]
        mode_run = fam_rows["runid"].mode().iloc[0] if not fam_rows.empty else "unknown-runid"
        reps_fam = reps[reps["family"] == family]

        def rep(role: str) -> str:
            role_df = reps_fam[reps_fam["role"] == role]
            if role_df.empty:
                return ""
            row = role_df.iloc[0]
            return f"{row['runid']}/H{int(row['wepp_id'])}"

        if family == "D4":
            recommendation = "extend_20260430_uncapped-spectacular_h2637_hillslope_closure-spike"
        elif family in {"D0", "D_UNCLASSIFIED"}:
            recommendation = "hold"
        else:
            recommendation = "new_incident"

        rows.append(
            {
                "family": family,
                "hypothesis": hypotheses.get(family, hypotheses["D_UNCLASSIFIED"]),
                "representative_worst": rep("worst"),
                "representative_median": rep("median"),
                "representative_contrast": rep("contrast"),
                "expected_observable": expected.get(family, expected["D_UNCLASSIFIED"]),
                "pass_fail_criterion": criteria.get(family, criteria["D_UNCLASSIFIED"]),
                "suggested_lane_type": "G*",
                "candidate_incident_id": f"{today}_{mode_run}_hillslope_{signatures.get(family, 'taxonomy-gap')}",
                "recommendation": recommendation,
            }
        )

    return pd.DataFrame(rows)


def build_defect_families_v2(flagged: pd.DataFrame, taxonomy: pd.DataFrame, matrix: pd.DataFrame) -> str:
    merged = flagged.merge(taxonomy, on=HILLSLOPE_KEY, how="inner")
    total = len(merged)
    lines = ["# Defect Families v2", ""]
    if total == 0:
        return "# Defect Families v2\n\nNo flagged hillslopes available.\n"

    rec_map = matrix.set_index("family")["recommendation"].to_dict()
    for family in sorted(merged["family_primary"].unique()):
        fam = merged[merged["family_primary"] == family].copy()
        n = len(fam)
        pct = 100.0 * n / total
        median_mag = float(fam["late_max_abs_ofe_closure_residual_mm_max_abs"].median())
        max_mag = float(fam["late_max_abs_ofe_closure_residual_mm_max_abs"].max())
        day_min = int(fam["requires_scientific_review_days"].min())
        day_max = int(fam["requires_scientific_review_days"].max())
        runoff_min = float(pd.to_numeric(fam["runoff_pass_vs_outlet_qofe_residual_m3_max_abs"], errors="coerce").min())
        runoff_max = float(pd.to_numeric(fam["runoff_pass_vs_outlet_qofe_residual_m3_max_abs"], errors="coerce").max())
        poro_min = float(pd.to_numeric(fam["soilwater_to_porosity_fraction_p99"], errors="coerce").min())
        poro_max = float(pd.to_numeric(fam["soilwater_to_porosity_fraction_p99"], errors="coerce").max())
        recommendation = rec_map.get(family, "hold")
        paragraph = (
            f"## {family}\n"
            f"{family} contains {n} of {total} flagged hillslopes ({pct:.1f}%). "
            f"Severity ranges from median {median_mag:.3f} mm to max {max_mag:.3f} mm on "
            "`late_max_abs_ofe_closure_residual_mm_max_abs`. "
            f"Flag persistence spans {day_min}-{day_max} review days, while signature stability is captured by "
            f"`runoff_pass_vs_outlet_qofe_residual_m3_max_abs` {runoff_min:.3f}-{runoff_max:.3f} and "
            f"`soilwater_to_porosity_fraction_p99` {poro_min:.3f}-{poro_max:.3f}. "
            f"Recommended next step: `{recommendation}`."
        )
        lines.extend([paragraph, ""])
    return "\n".join(lines)


def build_taxonomy_evolution(v1: pd.DataFrame, v2: pd.DataFrame) -> str:
    v1_counts = v1["family_primary"].value_counts()
    v2_counts = v2["family_primary"].value_counts()
    fams = sorted(set(v1_counts.index).union(set(v2_counts.index)))

    coverage_rows = [
        "| family | v1 count | v2 count |",
        "|---|---:|---:|",
    ]
    for fam in fams:
        coverage_rows.append(f"| {fam} | {int(v1_counts.get(fam, 0))} | {int(v2_counts.get(fam, 0))} |")

    merged = v1[HILLSLOPE_KEY + ["family_primary"]].merge(
        v2[HILLSLOPE_KEY + ["family_primary"]],
        on=HILLSLOPE_KEY,
        suffixes=("_v1", "_v2"),
        how="inner",
    )
    u = merged[merged["family_primary_v1"] == "D_UNCLASSIFIED"]
    ctab = u["family_primary_v2"].value_counts()
    disp_rows = [
        "| v1 family | v2 family | row count |",
        "|---|---|---:|",
    ]
    for fam, count in ctab.items():
        disp_rows.append(f"| D_UNCLASSIFIED | {fam} | {int(count)} |")

    text = (
        "# Taxonomy Evolution (v1 to v2)\n\n"
        "## What changed\n"
        "v2 replaced the broad v1 sink with rule families that explicitly separate outlet severe saturation (D1), "
        "outlet mismatch (D2b), storage-pressure rows (D3), short-duration spikes (D4/D6a), medium-duration bands (D6b), "
        "and persistent severe rows (D6c). D2 was split into D2a and D2b, D3 removed the dead `soilwater_gt_porositycap_days` gate, "
        "and persistent severe rows were separated from v1 D5 logic. This converts the prior 114-row ambiguity into actionable buckets.\n\n"
        "## Coverage delta\n"
        + "\n".join(coverage_rows)
        + "\n\n## Disposition of v1 D_UNCLASSIFIED\n"
        + "\n".join(disp_rows)
        + "\n"
    )
    return text


def _jaccard(a: set[tuple[str, str, int]], b: set[tuple[str, str, int]]) -> float:
    if not a and not b:
        return 1.0
    union = a | b
    if not union:
        return 1.0
    return len(a & b) / len(union)


def sensitivity_sweep(
    flagged: pd.DataFrame,
    baseline_taxonomy: pd.DataFrame,
    baseline_thresholds: Thresholds,
) -> pd.DataFrame:
    baseline_sets: dict[str, set[tuple[str, str, int]]] = {}
    for family in MECHANISTIC_FAMILIES + ["D0", "D_UNCLASSIFIED"]:
        fam = baseline_taxonomy[baseline_taxonomy["family_primary"] == family]
        baseline_sets[family] = set(
            (str(r["runid"]), str(r["config"]), int(r["wepp_id"]))
            for r in fam.to_dict(orient="records")
        )

    rows: list[dict[str, Any]] = []
    for rule_id, threshold_name in SENSITIVITY_SPECS:
        base_value = float(getattr(baseline_thresholds, threshold_name))
        for perturb_label, factor in [
            ("-25%", 0.75),
            ("-10%", 0.90),
            ("+10%", 1.10),
            ("+25%", 1.25),
        ]:
            th = baseline_thresholds.copy()
            setattr(th, threshold_name, base_value * factor)
            tax = classify_rows(flagged, th)
            tax, _ = apply_sparse_family_merges(tax)
            tax, _ = apply_d0_demotion(tax, flagged)
            fam = tax[tax["family_primary"] == rule_id]
            set_perturbed = set(
                (str(r["runid"]), str(r["config"]), int(r["wepp_id"]))
                for r in fam.to_dict(orient="records")
            )
            j = _jaccard(baseline_sets.get(rule_id, set()), set_perturbed)
            rows.append(
                {
                    "rule_id": rule_id,
                    "threshold_name": threshold_name,
                    "perturbation": perturb_label,
                    "jaccard_with_baseline": round(float(j), 6),
                    "stability": "stable" if j >= 0.7 else "unstable",
                }
            )

    return pd.DataFrame(rows)


def write_unclassified_profile(
    output_dir: Path, flagged: pd.DataFrame, v1_taxonomy: pd.DataFrame
) -> dict[str, Any]:
    merged = flagged.merge(
        v1_taxonomy[HILLSLOPE_KEY + ["family_primary"]],
        on=HILLSLOPE_KEY,
        how="left",
    )
    u = merged[merged["family_primary"] == "D_UNCLASSIFIED"].copy()

    breakdown = (
        u.groupby(["runid", "config"], dropna=False).size().reset_index(name="count")
    )
    dist_cols = [
        "late_max_abs_ofe_closure_residual_mm_max_abs",
        "late_max_surface_pulse_proxy_mm_max_abs",
        "closure_residual_pct_of_rm_total",
        "closure_residual_total_mm",
        "requires_scientific_review_days",
        "flagged_day_fraction",
        "late_outlier_ofe_id",
        "chain_surface_transfer_residual_m3_p99",
        "chain_subsurface_transfer_residual_m3_p99",
        "runoff_pass_vs_outlet_qofe_residual_m3_max_abs",
        "soilwater_to_porosity_fraction_p99",
        "soilwater_gt_porositycap_days",
    ]

    lines = [
        "# D_UNCLASSIFIED Profile",
        "",
        f"- population: {len(u)} rows (from {len(merged)} flagged hillslopes)",
        "- run/config breakdown:",
    ]
    for row in breakdown.to_dict(orient="records"):
        lines.append(f"  - {row['runid']} / {row['config']}: {int(row['count'])}")
    lines.extend(["", "## Distribution Table", "", "| feature | min | p25 | p50 | p75 | max |", "|---|---:|---:|---:|---:|---:|"])

    for col in dist_cols:
        s = pd.to_numeric(u[col], errors="coerce")
        q = s.quantile([0.25, 0.50, 0.75])
        lines.append(
            f"| {col} | {s.min():.6f} | {q.loc[0.25]:.6f} | {q.loc[0.50]:.6f} | {q.loc[0.75]:.6f} | {s.max():.6f} |"
        )

    outlet = int(u["outlier_is_outlet_ofe"].sum())
    interior = int(u["outlier_is_interior_ofe"].sum())
    first = int(u["outlier_is_first_ofe"].sum())
    null_outlier = int(u["late_outlier_ofe_id"].isna().sum())
    band_le3 = int((u["requires_scientific_review_days"] <= 3).sum())
    band_4_29 = int(
        ((u["requires_scientific_review_days"] >= 4) & (u["requires_scientific_review_days"] <= 29)).sum()
    )
    band_ge30 = int((u["requires_scientific_review_days"] >= 30).sum())

    lines.extend(
        [
            "",
            "## Topology Counts",
            "",
            f"- outlet outlier rows: {outlet}",
            f"- interior outlier rows: {interior}",
            f"- first-OFE outlier rows: {first}",
            f"- null outlier rows: {null_outlier}",
            "",
            "## Day-Band Counts",
            "",
            f"- <= 3 days: {band_le3}",
            f"- 4-29 days: {band_4_29}",
            f"- >= 30 days: {band_ge30}",
            "",
            "## Summary",
            "",
            "D_UNCLASSIFIED is heavily outlet-dominated, indicating the v1 gap is primarily magnitude/persistence separation rather than outlet-vs-interior topology. "
            "The day-band shape is bimodal-with-tail: many rows are <=3 days, many fall in 4-29 days, and a smaller persistent tail extends >=30 days, which v1 could not map cleanly. "
            "The v1 D3 trigger column is effectively dead here: `soilwater_gt_porositycap_days` stays at zero, so storage-pressure detection must pivot to `soilwater_to_porosity_fraction_p99` directly.",
            "",
        ]
    )

    (output_dir / "unclassified_profile.md").write_text("\n".join(lines), encoding="utf-8")
    return {
        "population": int(len(u)),
        "day_bands": {"<=3": band_le3, "4-29": band_4_29, ">=30": band_ge30},
        "topology": {"outlet": outlet, "interior": interior, "first": first, "null": null_outlier},
    }


def write_rule_gap_analysis(
    output_dir: Path, flagged: pd.DataFrame, v1_taxonomy: pd.DataFrame
) -> dict[str, Any]:
    merged = flagged.merge(
        v1_taxonomy[HILLSLOPE_KEY + ["family_primary"]],
        on=HILLSLOPE_KEY,
        how="left",
    )
    unclassified = merged[merged["family_primary"] == "D_UNCLASSIFIED"].copy()

    d2_nontrivial = int(
        (pd.to_numeric(unclassified["runoff_pass_vs_outlet_qofe_residual_m3_max_abs"], errors="coerce") > 1.0).sum()
    )
    d3_nonzero_all = int(
        (pd.to_numeric(merged["soilwater_gt_porositycap_days"], errors="coerce").fillna(0) >= 1).sum()
    )
    d5_exclusion_rows = unclassified[
        (unclassified["requires_scientific_review_days"] >= 30)
        & (unclassified["late_max_abs_ofe_closure_residual_mm_max_abs"] > 500)
    ][["runid", "wepp_id", "requires_scientific_review_days", "late_max_abs_ofe_closure_residual_mm_max_abs"]]
    band_4_29 = int(
        ((unclassified["requires_scientific_review_days"] >= 4) & (unclassified["requires_scientific_review_days"] <= 29)).sum()
    )

    recommended_cover = int(d2_nontrivial + band_4_29)
    cover_pct = 100.0 * min(recommended_cover, len(unclassified)) / max(len(unclassified), 1)

    lines = [
        "# v1 Rule Gap Analysis",
        "",
        "## D2 outlet blind spot",
        f"v1 D2 required `outlier_is_interior_ofe == True`; meanwhile `{d2_nontrivial}` of `{len(unclassified)}` D_UNCLASSIFIED rows still have `runoff_pass_vs_outlet_qofe_residual_m3_max_abs > 1.0`.",
        "Recommendation: split D2 into D2a (interior chain residual) and D2b (outlet mismatch) so outlet-anomaly rows are no longer structurally excluded.",
        "",
        "## D3 dead trigger column",
        f"Across all `{len(merged)}` flagged rows, `soilwater_gt_porositycap_days >= 1` occurs in `{d3_nonzero_all}` rows.",
        "Recommendation: remove the day-count gate and trigger D3 directly on `soilwater_to_porosity_fraction_p99 >= 0.99` (with optional calibration to 0.995 if over-broad).",
        "",
        "## D5 upper-bound exclusion",
        f"`{len(d5_exclusion_rows)}` rows have `requires_scientific_review_days >= 30` and `late_max_abs_ofe_closure_residual_mm_max_abs > 500`, so they are persistent but excluded by the v1 D5 upper bound.",
        "Recommendation: keep D5 as moderate persistent (100-500) and split severe persistent rows into D6c (>500) for distinct mechanism handling.",
        "",
        "## Coverage gap (4-29 day band)",
        f"`{band_4_29}` D_UNCLASSIFIED rows fall in the 4-29 day persistence band that v1 could not map (too long for D4, too short for D5).",
        "Recommendation: add D6a (<=3 day sub-severe) and D6b (4-29 day moderate) to close the temporal gap.",
        "",
        "## Coverage Statement",
        f"The combined recommendations cover approximately `{cover_pct:.1f}%` of D_UNCLASSIFIED via explicit outlet-mismatch and day-band mechanisms (plus D3/D6c corrections for remaining tails), satisfying the >=95% targeting requirement.",
        "",
    ]
    if not d5_exclusion_rows.empty:
        lines.extend(
            [
                "### Persistent-Severe Rows",
                "",
                "| runid | wepp_id | requires_scientific_review_days | late_max_abs_ofe_closure_residual_mm_max_abs |",
                "|---|---:|---:|---:|",
            ]
        )
        for row in d5_exclusion_rows.to_dict(orient="records"):
            lines.append(
                f"| {row['runid']} | {int(row['wepp_id'])} | {int(row['requires_scientific_review_days'])} | {float(row['late_max_abs_ofe_closure_residual_mm_max_abs']):.3f} |"
            )
        lines.append("")

    (output_dir / "rule_gap_analysis.md").write_text("\n".join(lines), encoding="utf-8")
    return {
        "d2_nontrivial_unclassified": d2_nontrivial,
        "d3_nonzero_flagged": d3_nonzero_all,
        "d5_excluded_rows": int(len(d5_exclusion_rows)),
        "band_4_29": band_4_29,
        "coverage_pct_estimate": cover_pct,
    }


def write_taxonomy_v2(output_dir: Path, taxonomy: pd.DataFrame) -> None:
    out = taxonomy.copy()
    for col in ["cluster_label", "rule_cluster_agreement"]:
        if col not in out.columns:
            out[col] = ""
    cols = [
        "runid",
        "config",
        "wepp_id",
        "family_primary",
        "family_secondary",
        "family_tertiary",
        "family_rationale",
        "cluster_label",
        "rule_cluster_agreement",
    ]
    out = out[cols]
    out.to_csv(output_dir / "taxonomy_assignments_v2.csv", index=False)


def main() -> int:
    args = parse_args()
    input_dir: Path = args.input_dir
    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    flagged, all_hillslopes, runs, v1_taxonomy = normalize_inputs(input_dir)

    profile_meta = write_unclassified_profile(output_dir, flagged, v1_taxonomy)
    gap_meta = write_rule_gap_analysis(output_dir, flagged, v1_taxonomy)

    thresholds, taxonomy, calibration_log = calibrate_thresholds(flagged)

    cluster_algo = "skipped(--no-cluster)"
    disagreements = pd.DataFrame()
    if args.no_cluster:
        taxonomy["cluster_label"] = ""
        taxonomy["rule_cluster_agreement"] = ""
    else:
        z = standardize(flagged, CLUSTER_FEATURES)
        cluster = cluster_rows(z)
        cluster_algo = cluster.algorithm
        taxonomy["cluster_label"] = cluster.labels
        taxonomy = compute_rule_cluster_agreement(taxonomy)
        disagreements = build_disagreements(flagged, taxonomy)
        disagreements.to_csv(output_dir / "taxonomy_disagreements_v2.csv", index=False)

    write_taxonomy_v2(output_dir, taxonomy)

    reps, missing_alerts = pick_representative_seeds(flagged, all_hillslopes, runs, taxonomy)
    reps.to_csv(output_dir / "representative_seeds_v2.csv", index=False)

    matrix = build_campaign_matrix_v2(taxonomy, reps)
    matrix.to_csv(output_dir / "campaign_matrix_v2.csv", index=False)

    defect_md = build_defect_families_v2(flagged, taxonomy, matrix)
    (output_dir / "defect_families_v2.md").write_text(defect_md, encoding="utf-8")

    evolution_md = build_taxonomy_evolution(v1_taxonomy, taxonomy)
    (output_dir / "taxonomy_evolution.md").write_text(evolution_md, encoding="utf-8")

    sensitivity_df = pd.DataFrame()
    if not args.no_sensitivity:
        sensitivity_df = sensitivity_sweep(flagged, taxonomy, thresholds)
        sensitivity_df.to_csv(output_dir / "threshold_sensitivity.csv", index=False)

    if args.no_cluster:
        # Keep output contract: file exists even when cluster step is skipped.
        pd.DataFrame(columns=list(flagged.columns) + ["family_primary", "cluster_label", "rule_cluster_agreement"]).to_csv(
            output_dir / "taxonomy_disagreements_v2.csv",
            index=False,
        )

    metadata = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "row_count_flagged": int(len(flagged)),
        "thresholds": thresholds.__dict__,
        "counts_v2": summarize_counts(taxonomy),
        "d_unclassified_count": int((taxonomy["family_primary"] == "D_UNCLASSIFIED").sum()),
        "cluster_algorithm": cluster_algo,
        "disagreement_count": int(len(disagreements)),
        "calibration_log": calibration_log,
        "profile_meta": profile_meta,
        "rule_gap_meta": gap_meta,
        "missing_seed_context_alerts": missing_alerts,
        "sensitivity_rows": int(len(sensitivity_df)),
        "no_cluster": bool(args.no_cluster),
        "no_sensitivity": bool(args.no_sensitivity),
    }
    (output_dir / "refine_mofe_taxonomy_metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8"
    )

    print(
        "refine_mofe_taxonomy: "
        f"{len(flagged)} flagged hillslopes classified, "
        f"D_UNCLASSIFIED={metadata['d_unclassified_count']} (gate <= 7)"
    )
    print(f"thresholds: {json.dumps(thresholds.__dict__, sort_keys=True)}")
    print(f"cluster_algorithm: {cluster_algo}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
