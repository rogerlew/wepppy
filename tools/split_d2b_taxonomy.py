#!/usr/bin/env python3
"""Split v2 D2b family into v3 D2b1-D2b5 and emit v3 artifacts."""

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
D2B_SPLIT_FAMILIES = ["D2b1", "D2b2", "D2b3", "D2b4", "D2b5"]
CARRY_FAMILIES = ["D1", "D3", "D4", "D6b", "D6c"]
CONTEXT_FILES = [
    "wepp_ui.txt",
    "pmetpara.txt",
    "snow.txt",
    "gwcoeff.txt",
    "chan.inp",
    "chntyp.txt",
    "tc.txt",
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

SENSITIVITY_THRESHOLDS = [
    "severity_lower_100",
    "severity_split_300",
    "severity_split_500",
    "severity_upper_1000",
    "persistence_split_3",
    "persistence_split_29",
]


@dataclass
class ClusterResult:
    labels: np.ndarray
    algorithm: str


@dataclass
class SplitThresholds:
    severity_lower_100: float = 100.0
    severity_split_300: float = 300.0
    severity_split_500: float = 500.0
    severity_upper_1000: float = 1000.0
    persistence_split_3: float = 3.0
    persistence_split_29: float = 29.0

    def copy(self) -> "SplitThresholds":
        return SplitThresholds(**self.__dict__)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--input-dir",
        type=Path,
        default=DEFAULT_ARTIFACTS_DIR,
        help="Directory containing v1/v2 artifacts",
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=DEFAULT_ARTIFACTS_DIR,
        help="Directory where v3 artifacts are written",
    )
    parser.add_argument(
        "--no-cluster",
        action="store_true",
        help="Skip cluster cross-check and emit blank disagreement file.",
    )
    parser.add_argument(
        "--no-sensitivity",
        action="store_true",
        help="Skip threshold sensitivity sweep output.",
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


def load_inputs(input_dir: Path) -> tuple[pd.DataFrame, ...]:
    flagged = pd.read_csv(input_dir / "triage_table_hillslopes.csv")
    all_hillslopes = pd.read_csv(input_dir / "triage_table_hillslopes_all.csv")
    runs = pd.read_csv(input_dir / "triage_table_runs.csv")
    tax_v2 = pd.read_csv(input_dir / "taxonomy_assignments_v2.csv")
    seeds_v2 = pd.read_csv(input_dir / "representative_seeds_v2.csv")
    matrix_v2 = pd.read_csv(input_dir / "campaign_matrix_v2.csv")
    defect_v2_text = (input_dir / "defect_families_v2.md").read_text(encoding="utf-8")

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

    tax_v2["wepp_id"] = pd.to_numeric(tax_v2["wepp_id"], errors="coerce").fillna(-1).astype(int)
    seeds_v2["wepp_id"] = pd.to_numeric(seeds_v2["wepp_id"], errors="coerce").fillna(-1).astype(int)
    return flagged, all_hillslopes, runs, tax_v2, seeds_v2, matrix_v2, defect_v2_text


def assign_d2b_split_family(row: pd.Series, th: SplitThresholds) -> str:
    days = int(row["requires_scientific_review_days"])
    severity = float(row["late_max_abs_ofe_closure_residual_mm_max_abs"])
    m1_low = th.severity_lower_100
    m1_high = th.severity_split_300
    m2_high = th.severity_split_500
    m3_high = th.severity_upper_1000
    t1 = th.persistence_split_3
    t2 = th.persistence_split_29

    if days <= t1 and m1_low <= severity < m1_high:
        return "D2b1"
    if days <= t1 and m1_high <= severity < m2_high:
        return "D2b2"
    if t1 < days <= t2 and m1_low <= severity < m1_high:
        return "D2b3"
    if t1 < days <= t2 and m1_high <= severity < m2_high:
        return "D2b4"
    if t1 < days <= t2 and m2_high <= severity <= m3_high:
        return "D2b5"
    return "D_UNRESOLVED_D2B_SPLIT"


def split_taxonomy(
    flagged: pd.DataFrame,
    tax_v2: pd.DataFrame,
    th: SplitThresholds,
) -> tuple[pd.DataFrame, dict[str, int], pd.DataFrame]:
    merged = tax_v2.merge(
        flagged[
            HILLSLOPE_KEY
            + [
                "late_max_abs_ofe_closure_residual_mm_max_abs",
                "requires_scientific_review_days",
                "soilwater_to_porosity_fraction_p99",
            ]
        ],
        on=HILLSLOPE_KEY,
        how="left",
        validate="one_to_one",
    )
    out = tax_v2.copy()
    # Ensure string assignments on split rows do not trigger dtype warnings
    # when v2 carried-forward columns are numeric.
    for col in ["family_secondary", "family_tertiary", "family_rationale", "cluster_label", "rule_cluster_agreement"]:
        if col in out.columns:
            out[col] = out[col].astype(object)
    out["storage_saturation_observed"] = (
        pd.to_numeric(merged["soilwater_to_porosity_fraction_p99"], errors="coerce").fillna(-1) >= 0.99
    )

    split_counts = {fam: 0 for fam in D2B_SPLIT_FAMILIES}
    unresolved_rows: list[dict[str, Any]] = []
    d2b_mask = merged["family_primary"] == "D2b"
    d2b_indices = merged[d2b_mask].index.tolist()

    for idx in d2b_indices:
        r = merged.loc[idx]
        fam = assign_d2b_split_family(r, th)
        out.at[idx, "family_primary"] = fam
        out.at[idx, "family_secondary"] = ""
        out.at[idx, "family_tertiary"] = ""
        out.at[idx, "cluster_label"] = ""
        out.at[idx, "rule_cluster_agreement"] = ""

        severity = float(r["late_max_abs_ofe_closure_residual_mm_max_abs"])
        days = int(r["requires_scientific_review_days"])
        if fam == "D2b1":
            rationale = (
                f"D2b1: cell (M1,T1) with severity={severity:.3f} in [100,300) and "
                f"requires_scientific_review_days={days}<=3."
            )
        elif fam == "D2b2":
            rationale = (
                f"D2b2: cell (M2,T1) with severity={severity:.3f} in [300,500) and "
                f"requires_scientific_review_days={days}<=3."
            )
        elif fam == "D2b3":
            rationale = (
                f"D2b3: cell (M1,T2) with severity={severity:.3f} in [100,300) and "
                f"requires_scientific_review_days={days} in [4,29]."
            )
        elif fam == "D2b4":
            rationale = (
                f"D2b4: cell (M2,T2) with severity={severity:.3f} in [300,500) and "
                f"requires_scientific_review_days={days} in [4,29]."
            )
        elif fam == "D2b5":
            rationale = (
                f"D2b5: cell (M3,T2) with severity={severity:.3f} in [500,1000] and "
                f"requires_scientific_review_days={days} in [4,29]."
            )
        else:
            rationale = (
                "D_UNRESOLVED_D2B_SPLIT: row outside configured severity/persistence split grid."
            )
            unresolved_rows.append(
                {
                    "runid": r["runid"],
                    "config": r["config"],
                    "wepp_id": int(r["wepp_id"]),
                    "severity": severity,
                    "requires_scientific_review_days": days,
                }
            )
        out.at[idx, "family_rationale"] = rationale

        if fam in split_counts:
            split_counts[fam] += 1

    unresolved_df = pd.DataFrame(unresolved_rows)
    return out, split_counts, unresolved_df


def validate_m1_gates(tax_v3: pd.DataFrame, split_counts: dict[str, int], d2b_count_v2: int) -> None:
    if len(tax_v3) != 132:
        raise RuntimeError(f"M1 gate failed: taxonomy_assignments_v3 rows={len(tax_v3)} (expected 132)")

    counts = tax_v3["family_primary"].value_counts()
    if int(counts.get("D2b", 0)) != 0:
        raise RuntimeError("M1 gate failed: D2b parent label still present in v3 output.")
    if int(counts.get("D_UNRESOLVED_D2B_SPLIT", 0)) != 0:
        raise RuntimeError("M1 gate failed: D_UNRESOLVED_D2B_SPLIT rows present.")
    if int(counts.get("D_UNCLASSIFIED", 0)) != 0:
        raise RuntimeError("M1 gate failed: D_UNCLASSIFIED rows present.")

    for fam, count in counts.items():
        if fam == "D4":
            continue
        if int(count) < 5:
            raise RuntimeError(
                f"M1 gate failed: family {fam} has {int(count)} rows (<5, D4 only exempt)."
            )
    if int(counts.max()) > 53:
        raise RuntimeError(
            f"M1 gate failed: largest family has {int(counts.max())} rows (>53)."
        )

    d2b_split_total = sum(split_counts.values())
    if d2b_split_total != d2b_count_v2:
        raise RuntimeError(
            f"M1 sanity failed: split row total {d2b_split_total} does not match v2 D2b count {d2b_count_v2}."
        )


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
            HILLSLOPE_KEY
            + [
                "family_primary",
                "storage_saturation_observed",
                "cluster_label",
                "rule_cluster_agreement",
            ]
        ],
        on=HILLSLOPE_KEY,
        how="left",
    )
    return joined[joined["rule_cluster_agreement"] == "disagree"].copy()


def select_split_family_seeds(
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
    rows: list[dict[str, Any]] = []
    missing_alerts: list[dict[str, Any]] = []

    for family in D2B_SPLIT_FAMILIES:
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
                f"No unflagged contrast candidates for {family} under config {target_config}"
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
            rep_row = {
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
            rows.append(rep_row)
            if role in {"worst", "median"} and missing:
                missing_alerts.append(rep_row)
    return pd.DataFrame(rows), missing_alerts


def build_representative_seeds_v3(
    split_seeds: pd.DataFrame, seeds_v2: pd.DataFrame
) -> pd.DataFrame:
    carried = seeds_v2[seeds_v2["family"].isin(CARRY_FAMILIES)].copy()
    out = pd.concat([split_seeds, carried], ignore_index=True)
    out = out.sort_values(["family", "role", "runid", "wepp_id"]).reset_index(drop=True)
    return out


def build_campaign_matrix_v3(
    taxonomy: pd.DataFrame,
    seeds_v3: pd.DataFrame,
    matrix_v2: pd.DataFrame,
    d2b2_extend: bool,
) -> pd.DataFrame:
    cm_rows: list[dict[str, Any]] = []
    carry_rows = matrix_v2[matrix_v2["family"].isin(CARRY_FAMILIES)].copy()
    for row in carry_rows.to_dict(orient="records"):
        cm_rows.append(row)

    split_hypothesis = {
        "D2b1": "Outlet sub-severe single-day mild (100-300 mm, <=3 days): threshold-adjacent outlet surge likely dominated by low-magnitude numerical noise.",
        "D2b2": "Outlet sub-severe single-day moderate (300-500 mm, <=3 days): D4-adjacent spike below severe bar, candidate H2637-lane generalization target.",
        "D2b3": "Outlet sub-severe multi-day mild (100-300 mm, 4-29 days): low-magnitude multi-day regime suggesting parameter/boundary mismatch.",
        "D2b4": "Outlet sub-severe multi-day moderate (300-500 mm, 4-29 days): same persistence as D2b3 but with stronger severity signal requiring separate lane.",
        "D2b5": "Outlet sub-severe multi-day severe (500-1000 mm, 4-29 days): sustained severe outlet residual below D1 ceiling, likely structural model gap.",
    }
    split_observable = {
        "D2b1": "Lower late_max_abs_ofe_closure_residual_mm_max_abs below 100 and reduce requires_scientific_review_days to 0 while keeping runoff_pass_vs_outlet_qofe_residual_m3_max_abs below the D2b activation regime.",
        "D2b2": "Lower late_max_abs_ofe_closure_residual_mm_max_abs below 300 and remove <=3-day outlet spikes; monitor runoff_pass_vs_outlet_qofe_residual_m3_max_abs reduction.",
        "D2b3": "Collapse 4-29 day mild regime by reducing requires_scientific_review_days below 4 and late_max_abs_ofe_closure_residual_mm_max_abs below 100.",
        "D2b4": "Collapse 4-29 day moderate regime and reduce late_max_abs_ofe_closure_residual_mm_max_abs below 300.",
        "D2b5": "Reduce late_max_abs_ofe_closure_residual_mm_max_abs below 500 and break sustained 4-29 day severe outlet pattern.",
    }
    split_pass_fail = {
        "D2b1": "PASS if representative seeds no longer exceed 100 mm and review-day count is 0.",
        "D2b2": "PASS if <=3-day 300-500 mm spikes are removed without shifting into D4/D1 predicates.",
        "D2b3": "PASS if 4-29 day mild persistence resolves and severity falls below 100 mm.",
        "D2b4": "PASS if 4-29 day moderate persistence resolves and severity falls below 300 mm.",
        "D2b5": "PASS if multi-day severe band (>500 mm) clears or transitions into bounded non-severe families.",
    }
    signatures = {
        "D2b1": "d2b1-single-day-mild",
        "D2b2": "d2b2-single-day-moderate",
        "D2b3": "d2b3-multi-day-mild",
        "D2b4": "d2b4-multi-day-moderate",
        "D2b5": "d2b5-multi-day-severe",
    }

    today = datetime.now(tz=timezone.utc).strftime("%Y%m%d")
    for family in D2B_SPLIT_FAMILIES:
        fam = taxonomy[taxonomy["family_primary"] == family]
        if fam.empty:
            continue
        reps = seeds_v3[seeds_v3["family"] == family]

        def rep(role: str) -> str:
            r = reps[reps["role"] == role]
            if r.empty:
                return ""
            row = r.iloc[0]
            return f"{row['runid']}/H{int(row['wepp_id'])}"

        mode_run = fam["runid"].mode().iloc[0]
        recommendation = "new_incident"
        if family == "D2b2" and d2b2_extend:
            recommendation = "extend_20260430_uncapped-spectacular_h2637_hillslope_closure-spike"

        cm_rows.append(
            {
                "family": family,
                "hypothesis": split_hypothesis[family],
                "representative_worst": rep("worst"),
                "representative_median": rep("median"),
                "representative_contrast": rep("contrast"),
                "expected_observable": split_observable[family],
                "pass_fail_criterion": split_pass_fail[family],
                "suggested_lane_type": "G*",
                "candidate_incident_id": f"{today}_{mode_run}_hillslope_{signatures[family]}",
                "recommendation": recommendation,
            }
        )

    out = pd.DataFrame(cm_rows)
    out = out.sort_values("family").reset_index(drop=True)
    return out


def build_defect_families_v3(
    flagged: pd.DataFrame,
    taxonomy: pd.DataFrame,
    defect_v2_text: str,
    matrix_v3: pd.DataFrame,
) -> str:
    merged = flagged.merge(taxonomy[HILLSLOPE_KEY + ["family_primary", "storage_saturation_observed"]], on=HILLSLOPE_KEY, how="inner")
    total = len(merged)

    lines = ["# Defect Families v3", ""]
    recommendation_map = matrix_v3.set_index("family")["recommendation"].to_dict()

    # Parse v2 paragraphs for carry-forward families.
    v2_sections: dict[str, str] = {}
    current_family = None
    current_lines: list[str] = []
    for raw in defect_v2_text.splitlines():
        line = raw.rstrip()
        if line.startswith("## "):
            if current_family and current_lines:
                v2_sections[current_family] = "\n".join(current_lines).strip()
            current_family = line.replace("## ", "", 1).strip()
            current_lines = []
            continue
        if current_family is not None:
            current_lines.append(line)
    if current_family and current_lines:
        v2_sections[current_family] = "\n".join(current_lines).strip()

    for family in sorted(merged["family_primary"].unique()):
        fam = merged[merged["family_primary"] == family].copy()
        n = len(fam)
        pct = 100.0 * n / total
        rec = recommendation_map.get(family, "new_incident")

        if family in D2B_SPLIT_FAMILIES:
            sev = pd.to_numeric(fam["late_max_abs_ofe_closure_residual_mm_max_abs"], errors="coerce")
            day = pd.to_numeric(fam["requires_scientific_review_days"], errors="coerce")
            sat = fam["storage_saturation_observed"].map(normalize_bool)
            sat_frac = 100.0 * sat.mean() if len(sat) else 0.0
            paragraph = (
                f"## {family}\n"
                f"{family} contains {n} of {total} flagged hillslopes ({pct:.1f}%). "
                f"Severity spans {sev.min():.3f}-{sev.max():.3f} mm and persistence spans {int(day.min())}-{int(day.max())} review days "
                f"within its severity×persistence cell definition. "
                f"Storage saturation (`storage_saturation_observed`) is present in {sat.sum()}/{len(sat)} rows ({sat_frac:.1f}%). "
                f"Recommended next step: `{rec}`."
            )
            lines.extend([paragraph, ""])
        elif family in CARRY_FAMILIES:
            v2_para = v2_sections.get(family, "").strip()
            paragraph = (
                f"## {family}\n"
                f"{family} is unchanged from v2; v3 only split D2b. "
                f"{v2_para}"
            )
            lines.extend([paragraph, ""])
        else:
            sev = pd.to_numeric(fam["late_max_abs_ofe_closure_residual_mm_max_abs"], errors="coerce")
            day = pd.to_numeric(fam["requires_scientific_review_days"], errors="coerce")
            paragraph = (
                f"## {family}\n"
                f"{family} contains {n} of {total} flagged hillslopes ({pct:.1f}%), severity {sev.min():.3f}-{sev.max():.3f} mm, "
                f"persistence {int(day.min())}-{int(day.max())} days. Recommended next step: `{rec}`."
            )
            lines.extend([paragraph, ""])
    return "\n".join(lines)


def build_taxonomy_evolution_v3(tax_v2: pd.DataFrame, tax_v3: pd.DataFrame) -> str:
    v2_counts = tax_v2["family_primary"].value_counts()
    v3_counts = tax_v3["family_primary"].value_counts()
    families = sorted(set(v2_counts.index).union(set(v3_counts.index)))

    coverage_rows = [
        "| family | v2 count | v3 count |",
        "|---|---:|---:|",
    ]
    for fam in families:
        coverage_rows.append(f"| {fam} | {int(v2_counts.get(fam, 0))} | {int(v3_counts.get(fam, 0))} |")

    merged = tax_v2[HILLSLOPE_KEY + ["family_primary"]].merge(
        tax_v3[HILLSLOPE_KEY + ["family_primary"]],
        on=HILLSLOPE_KEY,
        suffixes=("_v2", "_v3"),
        how="inner",
    )
    d2b = merged[merged["family_primary_v2"] == "D2b"]
    counts = d2b["family_primary_v3"].value_counts()
    disposition_rows = [
        "| v2 family | v3 family | cell | row count |",
        "|---|---|---|---:|",
    ]
    cell_map = {
        "D2b1": "(M1,T1)",
        "D2b2": "(M2,T1)",
        "D2b3": "(M1,T2)",
        "D2b4": "(M2,T2)",
        "D2b5": "(M3,T2)",
    }
    for fam in D2B_SPLIT_FAMILIES:
        disposition_rows.append(
            f"| D2b | {fam} | {cell_map[fam]} | {int(counts.get(fam, 0))} |"
        )

    text = (
        "# Taxonomy Evolution v3 (v2 to v3)\n\n"
        "## What changed\n"
        "v3 retires `D2b` and replaces it with `D2b1`-`D2b5` using a deterministic severity×persistence split, while `D1`, `D3`, `D4`, `D6b`, and `D6c` are carried forward unchanged.\n\n"
        "## Coverage delta\n"
        + "\n".join(coverage_rows)
        + "\n\n## Disposition of v2 D2b\n"
        + "\n".join(disposition_rows)
        + "\n"
    )
    return text


def jaccard(a: set[tuple[str, str, int]], b: set[tuple[str, str, int]]) -> float:
    if not a and not b:
        return 1.0
    union = a | b
    if not union:
        return 1.0
    return len(a & b) / len(union)


def split_family_with_perturbed_thresholds(
    flagged_d2b: pd.DataFrame,
    th: SplitThresholds,
) -> pd.DataFrame:
    rows = []
    for row in flagged_d2b.to_dict(orient="records"):
        fam = assign_d2b_split_family(pd.Series(row), th)
        rows.append(
            {
                "runid": row["runid"],
                "config": row["config"],
                "wepp_id": int(row["wepp_id"]),
                "family_primary": fam,
            }
        )
    return pd.DataFrame(rows)


def threshold_sensitivity_v3(
    flagged: pd.DataFrame,
    tax_v2: pd.DataFrame,
    tax_v3: pd.DataFrame,
    base_th: SplitThresholds,
) -> pd.DataFrame:
    d2b_keys = tax_v2[tax_v2["family_primary"] == "D2b"][HILLSLOPE_KEY]
    flagged_d2b = flagged.merge(d2b_keys, on=HILLSLOPE_KEY, how="inner")
    base_sets = {
        fam: set(
            (str(r["runid"]), str(r["config"]), int(r["wepp_id"]))
            for r in tax_v3[tax_v3["family_primary"] == fam].to_dict(orient="records")
        )
        for fam in D2B_SPLIT_FAMILIES
    }

    rows: list[dict[str, Any]] = []
    for threshold_name in SENSITIVITY_THRESHOLDS:
        base_value = float(getattr(base_th, threshold_name))
        for label, factor in [("-25%", 0.75), ("-10%", 0.90), ("+10%", 1.10), ("+25%", 1.25)]:
            th = base_th.copy()
            setattr(th, threshold_name, base_value * factor)
            perturbed = split_family_with_perturbed_thresholds(flagged_d2b, th)
            for fam in D2B_SPLIT_FAMILIES:
                pert_set = set(
                    (str(r["runid"]), str(r["config"]), int(r["wepp_id"]))
                    for r in perturbed[perturbed["family_primary"] == fam].to_dict(orient="records")
                )
                score = jaccard(base_sets[fam], pert_set)
                rows.append(
                    {
                        "rule_id": fam,
                        "threshold_name": threshold_name,
                        "perturbation": label,
                        "jaccard_with_baseline": round(float(score), 6),
                        "stability": "stable" if score >= 0.7 else "unstable",
                    }
                )
    return pd.DataFrame(rows)


def write_taxonomy_v3(path: Path, taxonomy: pd.DataFrame) -> None:
    cols = [
        "runid",
        "config",
        "wepp_id",
        "family_primary",
        "family_secondary",
        "family_tertiary",
        "family_rationale",
        "storage_saturation_observed",
        "cluster_label",
        "rule_cluster_agreement",
    ]
    out = taxonomy.copy()
    for col in cols:
        if col not in out.columns:
            out[col] = ""
    out = out[cols]
    out.to_csv(path, index=False)


def main() -> int:
    args = parse_args()
    input_dir: Path = args.input_dir
    output_dir: Path = args.output_dir
    output_dir.mkdir(parents=True, exist_ok=True)

    flagged, all_hillslopes, runs, tax_v2, seeds_v2, matrix_v2, defect_v2_text = load_inputs(input_dir)
    thresholds = SplitThresholds()

    tax_v3, split_counts, unresolved_df = split_taxonomy(flagged, tax_v2, thresholds)
    d2b_count_v2 = int((tax_v2["family_primary"] == "D2b").sum())
    validate_m1_gates(tax_v3, split_counts, d2b_count_v2)

    cluster_algo = "skipped(--no-cluster)"
    disagreements = pd.DataFrame()
    if args.no_cluster:
        tax_v3["cluster_label"] = ""
        tax_v3["rule_cluster_agreement"] = ""
    else:
        z = standardize(flagged, CLUSTER_FEATURES)
        cluster = cluster_rows(z)
        cluster_algo = cluster.algorithm
        mapping = flagged[HILLSLOPE_KEY].copy()
        mapping["cluster_label"] = cluster.labels
        tax_v3 = tax_v3.drop(columns=["cluster_label"], errors="ignore").merge(
            mapping,
            on=HILLSLOPE_KEY,
            how="left",
            validate="one_to_one",
        )
        tax_v3 = compute_rule_cluster_agreement(tax_v3)
        disagreements = build_disagreements(flagged, tax_v3)
        disagreements.to_csv(output_dir / "taxonomy_disagreements_v3.csv", index=False)

    write_taxonomy_v3(output_dir / "taxonomy_assignments_v3.csv", tax_v3)

    split_seeds, missing_alerts = select_split_family_seeds(flagged, all_hillslopes, runs, tax_v3)
    seeds_v3 = build_representative_seeds_v3(split_seeds, seeds_v2)
    seeds_v3.to_csv(output_dir / "representative_seeds_v3.csv", index=False)

    d2b2_extend = True
    matrix_v3 = build_campaign_matrix_v3(tax_v3, seeds_v3, matrix_v2, d2b2_extend=d2b2_extend)
    matrix_v3.to_csv(output_dir / "campaign_matrix_v3.csv", index=False)

    defect_v3 = build_defect_families_v3(flagged, tax_v3, defect_v2_text, matrix_v3)
    (output_dir / "defect_families_v3.md").write_text(defect_v3, encoding="utf-8")

    evolution = build_taxonomy_evolution_v3(tax_v2, tax_v3)
    (output_dir / "taxonomy_evolution_v3.md").write_text(evolution, encoding="utf-8")

    sens_rows = 0
    sensitivity_df = pd.DataFrame()
    if not args.no_sensitivity:
        sensitivity_df = threshold_sensitivity_v3(flagged, tax_v2, tax_v3, thresholds)
        sensitivity_df.to_csv(output_dir / "threshold_sensitivity_v3.csv", index=False)
        sens_rows = len(sensitivity_df)

    if args.no_cluster:
        # Keep contract: file exists even when clustering skipped.
        pd.DataFrame(columns=list(flagged.columns) + ["family_primary", "cluster_label", "rule_cluster_agreement"]).to_csv(
            output_dir / "taxonomy_disagreements_v3.csv",
            index=False,
        )

    carried_forward = len(tax_v3) - sum(split_counts.values())
    print(
        "split_d2b: "
        f"D2b1={split_counts['D2b1']} D2b2={split_counts['D2b2']} D2b3={split_counts['D2b3']} "
        f"D2b4={split_counts['D2b4']} D2b5={split_counts['D2b5']}; "
        f"carried_forward={carried_forward} total={len(tax_v3)}"
    )

    metadata = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "split_thresholds": thresholds.__dict__,
        "split_counts": split_counts,
        "carried_forward": int(carried_forward),
        "v2_d2b_count": d2b_count_v2,
        "cluster_algorithm": cluster_algo,
        "disagreement_count": int(len(disagreements)),
        "missing_seed_context_alerts": missing_alerts,
        "d2b2_recommendation": (
            "extend_20260430_uncapped-spectacular_h2637_hillslope_closure-spike"
            if d2b2_extend
            else "new_incident"
        ),
        "unresolved_rows": unresolved_df.to_dict(orient="records"),
        "sensitivity_rows": int(sens_rows),
        "no_cluster": bool(args.no_cluster),
        "no_sensitivity": bool(args.no_sensitivity),
        "family_counts_v3": {k: int(v) for k, v in tax_v3["family_primary"].value_counts().items()},
    }
    (output_dir / "split_d2b_taxonomy_metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8"
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
