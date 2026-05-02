#!/usr/bin/env python3
"""Run MOFE flagged hillslope triage milestones M2-M6."""

from __future__ import annotations

import json
import math
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

import numpy as np
import pandas as pd


ROOT = Path(__file__).resolve().parents[1]
ARTIFACTS_DIR = (
    ROOT / "docs/work-packages/20260502_mofe_flagged_hillslope_triage/artifacts"
)
ABLATION_DIR = Path("/workdir/wepp-forest/docs/ablation")

HILLSLOPE_KEY = ["runid", "config", "wepp_id"]
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


@dataclass
class ClusterResult:
    labels: np.ndarray
    algorithm: str


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


def normalize_tables() -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame]:
    flagged = pd.read_csv(ARTIFACTS_DIR / "triage_table_hillslopes.csv")
    all_hillslopes = pd.read_csv(ARTIFACTS_DIR / "triage_table_hillslopes_all.csv")
    runs = pd.read_csv(ARTIFACTS_DIR / "triage_table_runs.csv")

    for df in (flagged, all_hillslopes):
        for col in ["outlier_is_outlet_ofe", "outlier_is_first_ofe", "outlier_is_interior_ofe"]:
            if col in df.columns:
                df[col] = df[col].map(normalize_bool)
        if "wepp_id" in df.columns:
            df["wepp_id"] = df["wepp_id"].astype(int)
        if "requires_scientific_review_days" in df.columns:
            df["requires_scientific_review_days"] = pd.to_numeric(
                df["requires_scientific_review_days"], errors="coerce"
            ).fillna(0).astype(int)
    for col in ["n_hillslopes_total", "n_hillslopes_flagged"]:
        if col in runs.columns:
            runs[col] = pd.to_numeric(runs[col], errors="coerce").fillna(0).astype(int)
    return flagged, all_hillslopes, runs


def assign_rule_families(flagged: pd.DataFrame) -> pd.DataFrame:
    records: list[dict[str, Any]] = []

    for row in flagged.to_dict(orient="records"):
        matches: list[str] = []
        late_max = float(row["late_max_abs_ofe_closure_residual_mm_max_abs"])
        ratio_max = row.get("late_max_qofe_to_q_ratio_max_abs")
        n_ofe_max = row.get("n_ofe_max")

        # D1
        ratio_sat = False
        if pd.notna(ratio_max) and pd.notna(n_ofe_max):
            ratio_sat = float(ratio_max) >= (float(n_ofe_max) - 0.01)
        if (
            bool(row["outlier_is_outlet_ofe"])
            and late_max > 1000.0
            and ratio_sat
        ):
            matches.append("D1")

        # D2
        d2_chain_triggers: list[str] = []
        if bool(row["outlier_is_interior_ofe"]):
            if pd.notna(row.get("chain_surface_transfer_residual_m3_p99")) and float(
                row["chain_surface_transfer_residual_m3_p99"]
            ) > 1e-3:
                d2_chain_triggers.append("chain_surface_transfer_residual_m3_p99>1e-3")
            if pd.notna(row.get("chain_subsurface_transfer_residual_m3_p99")) and float(
                row["chain_subsurface_transfer_residual_m3_p99"]
            ) > 1e-3:
                d2_chain_triggers.append("chain_subsurface_transfer_residual_m3_p99>1e-3")
            if pd.notna(row.get("runoff_pass_vs_outlet_qofe_residual_m3_max_abs")) and float(
                row["runoff_pass_vs_outlet_qofe_residual_m3_max_abs"]
            ) > 1.0:
                d2_chain_triggers.append("runoff_pass_vs_outlet_qofe_residual_m3_max_abs>1.0")
            if d2_chain_triggers:
                matches.append("D2")

        # D3
        sw_p99 = row.get("soilwater_to_porosity_fraction_p99")
        sw_days = row.get("soilwater_gt_porositycap_days")
        if (
            pd.notna(sw_p99)
            and pd.notna(sw_days)
            and float(sw_p99) >= 0.99
            and float(sw_days) >= 1.0
        ):
            matches.append("D3")

        # D4
        if int(row["requires_scientific_review_days"]) <= 3 and late_max >= 500.0:
            matches.append("D4")

        # D5
        if int(row["requires_scientific_review_days"]) >= 30 and 100.0 <= late_max <= 500.0:
            matches.append("D5")

        primary = matches[0] if matches else "D_UNCLASSIFIED"
        secondary = matches[1] if len(matches) > 1 else ""
        tertiary = matches[2] if len(matches) > 2 else ""

        if primary == "D1":
            rationale = (
                "D1 by outlier_is_outlet_ofe=True, "
                f"late_max_abs_ofe_closure_residual_mm_max_abs={late_max:.3f}>1000, "
                f"late_max_qofe_to_q_ratio_max_abs={float(ratio_max):.3f}>="
                f"(n_ofe_max-0.01)={float(n_ofe_max)-0.01:.3f}."
            )
        elif primary == "D2":
            rationale = (
                "D2 by outlier_is_interior_ofe=True and "
                + ", ".join(d2_chain_triggers)
                + "."
            )
        elif primary == "D3":
            rationale = (
                "D3 by soilwater_to_porosity_fraction_p99="
                f"{float(sw_p99):.3f}>=0.99 and soilwater_gt_porositycap_days={int(sw_days)}>=1."
            )
        elif primary == "D4":
            rationale = (
                "D4 by requires_scientific_review_days="
                f"{int(row['requires_scientific_review_days'])}<=3 and "
                f"late_max_abs_ofe_closure_residual_mm_max_abs={late_max:.3f}>=500."
            )
        elif primary == "D5":
            rationale = (
                "D5 by requires_scientific_review_days="
                f"{int(row['requires_scientific_review_days'])}>=30 and "
                f"late_max_abs_ofe_closure_residual_mm_max_abs={late_max:.3f} in [100,500]."
            )
        else:
            rationale = (
                "No D1-D5 rule matched from topology/chain/storage/persistence thresholds."
            )

        records.append(
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

    return pd.DataFrame.from_records(records)


def standardize(df: pd.DataFrame, columns: list[str]) -> pd.DataFrame:
    work = df[columns].copy()
    for col in columns:
        if work[col].dtype == bool:
            work[col] = work[col].astype(int)
        else:
            work[col] = pd.to_numeric(work[col], errors="coerce")
    means = work.mean(skipna=True)
    stds = work.std(skipna=True, ddof=0)
    stds = stds.replace(0, np.nan)
    z = (work - means) / stds
    z = z.replace([np.inf, -np.inf], np.nan).fillna(0.0)
    return z


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


def apply_d0_demotion(
    taxonomy: pd.DataFrame,
    flagged: pd.DataFrame,
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    merged = taxonomy.merge(flagged[HILLSLOPE_KEY + D0_FEATURES], on=HILLSLOPE_KEY, how="left")
    demotions: list[dict[str, Any]] = []
    tax = taxonomy.copy()

    for family in ["D1", "D2", "D3", "D4", "D5"]:
        family_rows = merged[merged["family_primary"] == family].copy()
        family_size = int(len(family_rows))
        if family_size < 5:
            continue

        counts = (
            family_rows.groupby(["runid", "config"], dropna=False)
            .size()
            .reset_index(name="count")
            .sort_values("count", ascending=False)
        )
        dominant = counts.iloc[0]
        dominant_key = (str(dominant["runid"]), str(dominant["config"]))
        concentration = float(dominant["count"] / family_size)
        if concentration < 0.95:
            continue

        run_rows = merged[
            (merged["runid"] == dominant_key[0]) & (merged["config"] == dominant_key[1])
        ].copy()
        for col in D0_FEATURES:
            run_rows[col] = pd.to_numeric(run_rows[col], errors="coerce").fillna(0.0)
            family_rows[col] = pd.to_numeric(family_rows[col], errors="coerce").fillna(0.0)

        run_mean = run_rows[D0_FEATURES].mean()
        run_std = run_rows[D0_FEATURES].std(ddof=0).replace(0.0, 1e-9)
        family_mean = family_rows[D0_FEATURES].mean()
        deltas = ((family_mean - run_mean).abs() / run_std).to_dict()
        deltas_values = list(deltas.values())
        count_small = sum(1 for d in deltas_values if d <= 0.35)
        max_delta = max(deltas_values) if deltas_values else 0.0
        should_demote = count_small >= 5 and max_delta <= 0.75
        if not should_demote:
            continue

        fam_mask = tax["family_primary"] == family
        for idx in tax[fam_mask].index:
            old_primary = tax.at[idx, "family_primary"]
            old_secondary = tax.at[idx, "family_secondary"]
            tax.at[idx, "family_primary"] = "D0"
            tax.at[idx, "family_secondary"] = old_primary
            tax.at[idx, "family_tertiary"] = old_secondary if old_secondary else tax.at[idx, "family_tertiary"]
            tax.at[idx, "family_rationale"] = (
                tax.at[idx, "family_rationale"]
                + " Demoted to D0: concentration="
                + f"{concentration:.3f} in {dominant_key[0]}/{dominant_key[1]}, "
                + f"feature_deltas={{{', '.join(f'{k}:{v:.3f}' for k, v in deltas.items())}}}."
            )

        demotions.append(
            {
                "from_family": family,
                "to_family": "D0",
                "family_size": family_size,
                "dominant_runid": dominant_key[0],
                "dominant_config": dominant_key[1],
                "concentration": concentration,
                "feature_deltas": {k: float(v) for k, v in deltas.items()},
                "small_delta_count": int(count_small),
                "max_delta": float(max_delta),
            }
        )

    return tax, demotions


def compute_rule_cluster_agreement(taxonomy: pd.DataFrame) -> pd.DataFrame:
    tax = taxonomy.copy()
    agreements: list[str] = []

    for row in tax.to_dict(orient="records"):
        cluster = int(row["cluster_label"])
        family = row["family_primary"]
        if cluster == -1:
            agreements.append("noise")
            continue
        in_cluster = tax[tax["cluster_label"] == cluster]
        in_family = tax[tax["family_primary"] == family]
        overlap = tax[(tax["cluster_label"] == cluster) & (tax["family_primary"] == family)]
        if len(in_cluster) == 0 or len(in_family) == 0:
            agreements.append("disagree")
            continue
        family_share_in_cluster = len(overlap) / len(in_cluster)
        cluster_share_of_family = len(overlap) / len(in_family)
        if family_share_in_cluster > 0.5 or cluster_share_of_family > 0.5:
            agreements.append("agree")
        else:
            agreements.append("disagree")

    tax["rule_cluster_agreement"] = agreements
    return tax


def build_disagreement_table(flagged: pd.DataFrame, taxonomy: pd.DataFrame) -> pd.DataFrame:
    joined = flagged.merge(
        taxonomy[
            HILLSLOPE_KEY + ["family_primary", "cluster_label", "rule_cluster_agreement"]
        ],
        on=HILLSLOPE_KEY,
        how="left",
    )
    return joined[joined["rule_cluster_agreement"] == "disagree"].copy()


def pick_representatives(
    flagged: pd.DataFrame,
    all_hillslopes: pd.DataFrame,
    runs: pd.DataFrame,
    taxonomy: pd.DataFrame,
) -> tuple[pd.DataFrame, list[dict[str, Any]]]:
    tagged_flagged = flagged.merge(taxonomy, on=HILLSLOPE_KEY, how="inner")
    tagged_all = all_hillslopes.merge(
        taxonomy[HILLSLOPE_KEY + ["family_primary"]],
        on=HILLSLOPE_KEY,
        how="left",
    )
    tagged_all["family_primary"] = tagged_all["family_primary"].fillna("")

    z_all = standardize(tagged_all, SEED_DISTANCE_FEATURES)
    z_all.columns = [f"z_{c}" for c in SEED_DISTANCE_FEATURES]
    tagged_all = pd.concat([tagged_all.reset_index(drop=True), z_all.reset_index(drop=True)], axis=1)

    run_context = runs.set_index(["runid", "config"])[["staged_runs_dir"]].to_dict()["staged_runs_dir"]
    rep_rows: list[dict[str, Any]] = []
    missing_context_alerts: list[dict[str, Any]] = []

    families = sorted(
        f for f in tagged_flagged["family_primary"].unique() if f and f != "D_UNCLASSIFIED"
    )
    z_cols = [f"z_{c}" for c in SEED_DISTANCE_FEATURES]

    for family in families:
        fam = tagged_flagged[tagged_flagged["family_primary"] == family].copy()
        if fam.empty:
            continue

        worst_idx = fam["late_max_abs_ofe_closure_residual_mm_max_abs"].idxmax()
        worst = fam.loc[worst_idx]

        median_target = fam["late_max_abs_ofe_closure_residual_mm_max_abs"].median()
        fam["median_dist"] = (
            fam["late_max_abs_ofe_closure_residual_mm_max_abs"] - median_target
        ).abs()
        fam_sorted = fam.sort_values(["median_dist", "requires_scientific_review_days"])
        median = fam_sorted.iloc[0]

        dominant = (
            fam.groupby(["runid", "config"]).size().reset_index(name="n").sort_values("n", ascending=False).iloc[0]
        )
        target_runid = str(dominant["runid"])
        target_config = str(dominant["config"])
        centroid = fam.merge(
            tagged_all[HILLSLOPE_KEY + z_cols], on=HILLSLOPE_KEY, how="left"
        )[z_cols].mean().to_numpy(dtype=float)

        candidates = tagged_all[
            (tagged_all["requires_scientific_review_days"] == 0)
            & (tagged_all["runid"] == target_runid)
            & (tagged_all["config"] == target_config)
        ].copy()
        if candidates.empty:
            candidates = tagged_all[
                (tagged_all["requires_scientific_review_days"] == 0)
                & (tagged_all["config"] == target_config)
            ].copy()
        if candidates.empty:
            raise RuntimeError(
                f"No unflagged contrast candidates found for family {family} in config {target_config}"
            )

        cand_vectors = candidates[z_cols].to_numpy(dtype=float)
        dists = np.linalg.norm(cand_vectors - centroid, axis=1)
        contrast = candidates.iloc[int(np.argmin(dists))]

        for role, row in [("worst", worst), ("median", median), ("contrast", contrast)]:
            key = (str(row["runid"]), str(row["config"]))
            staged_runs_dir = run_context.get(key)
            run_file = ""
            shared_paths: list[str] = []
            missing_context: list[str] = []
            if isinstance(staged_runs_dir, str) and staged_runs_dir:
                run_file = str(Path(staged_runs_dir) / f"p{int(row['wepp_id'])}.run")
                for fname in CONTEXT_FILES:
                    path = str(Path(staged_runs_dir) / fname)
                    shared_paths.append(path)
                    if not Path(path).exists():
                        missing_context.append(fname)

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
                "staged_runs_dir": staged_runs_dir if isinstance(staged_runs_dir, str) else "",
                "run_file": run_file,
                "shared_context_files": ";".join(shared_paths),
                "missing_shared_context": ";".join(missing_context),
                "top_days_csv_path": str(row["top_days_csv_path"]),
                "summary_json_path": str(row["summary_json_path"]),
            }
            rep_rows.append(rep_row)
            if role in {"worst", "median"} and missing_context:
                missing_context_alerts.append(rep_row)

    rep_df = pd.DataFrame(rep_rows)
    return rep_df, missing_context_alerts


def extract_incident_summary(md_text: str) -> tuple[str, str]:
    status_match = re.search(r"- `status`:\s*`([^`]+)`", md_text)
    status = status_match.group(1) if status_match else "unknown"

    summary_block = ""
    marker = "## 1) Summary"
    if marker in md_text:
        tail = md_text.split(marker, 1)[1]
        lines = [ln.strip() for ln in tail.strip().splitlines()]
        clean_lines: list[str] = []
        for ln in lines:
            if not ln:
                if clean_lines:
                    break
                continue
            if ln.startswith("## "):
                break
            normalized = ln[2:].strip() if ln.startswith("- ") else ln
            clean_lines.append(normalized)
            if len(clean_lines) >= 2:
                break
        summary_block = " ".join(clean_lines).strip()
    if not summary_block:
        summary_block = "Summary not parsed."
    return status, summary_block


def plausible_families_from_text(text: str) -> list[str]:
    t = text.lower()
    families: list[str] = []
    if "closure spike" in t or ("closure" in t and ("day-44" in t or "single-day" in t)):
        families.append("D4")
    if "outlet" in t and "ofe" in t:
        families.append("D1")
    if "chain" in t or "routing" in t:
        families.append("D2")
    if "porosity" in t or "soilwater" in t or "storage saturation" in t:
        families.append("D3")
    if "persistent" in t or "multi-day" in t or "chronic" in t:
        families.append("D5")
    return sorted(set(families))


def build_precedent_crosswalk(
    taxonomy: pd.DataFrame,
    coverage_families: list[str],
) -> tuple[str, dict[str, list[str]]]:
    incident_dirs = [
        p
        for p in sorted(ABLATION_DIR.iterdir())
        if p.is_dir() and re.match(r"^\d{8}_.+_(hillslope|mixed)_.+$", p.name)
    ]

    family_hits: dict[str, list[str]] = {fam: [] for fam in coverage_families}
    sections: list[str] = ["# Precedent Crosswalk", ""]
    flagged_keys = taxonomy[HILLSLOPE_KEY].to_dict(orient="records")

    for incident_dir in incident_dirs:
        incident_id = incident_dir.name
        incident_md = incident_dir / "incident.md"
        matrix_csv = incident_dir / "matrix.csv"
        md_text = incident_md.read_text(encoding="utf-8") if incident_md.exists() else ""
        matrix_text = matrix_csv.read_text(encoding="utf-8") if matrix_csv.exists() else ""
        combined_text = f"{md_text}\n{matrix_text}"
        combined_lower = combined_text.lower()

        status, summary = extract_incident_summary(md_text)
        overlaps: list[str] = []
        for key in flagged_keys:
            runid = str(key["runid"])
            wepp_id = int(key["wepp_id"])
            has_run = runid.lower() in combined_lower
            has_seed = (
                f"h{wepp_id}".lower() in combined_lower
                or f"p{wepp_id}.run".lower() in combined_lower
                or f"p{wepp_id},".lower() in combined_lower
            )
            if has_run and has_seed:
                overlaps.append(f"{runid}/H{wepp_id}")

        plausible = plausible_families_from_text(combined_text)
        for fam in plausible:
            if fam in family_hits:
                family_hits[fam].append(incident_id)

        if overlaps:
            recommendation = f"extend_{incident_id}"
        elif incident_id == "20260430_uncapped-spectacular_h2637_hillslope_closure-spike" and "D4" in coverage_families:
            recommendation = f"extend_{incident_id}"
        else:
            recommendation = "hold"

        sections.extend(
            [
                f"## {incident_id}",
                f"1. Status/signature: status=`{status}`; {summary}",
                (
                    "2. Overlap with current flagged set: "
                    + (", ".join(sorted(set(overlaps))) if overlaps else "none")
                ),
                (
                    "3. Plausible D-family signature match: "
                    + (", ".join(plausible) if plausible else "none")
                ),
                f"4. Recommendation: `{recommendation}`",
                "",
            ]
        )

    sections.append("## Family Coverage")
    for fam in coverage_families:
        hits = family_hits.get(fam, [])
        if hits:
            sections.append(f"- {fam}: precedent candidates -> {', '.join(sorted(set(hits)))}")
        else:
            sections.append(f"- {fam}: no precedent found.")
    sections.append("")
    return "\n".join(sections), family_hits


def build_campaign_matrix(
    taxonomy: pd.DataFrame,
    reps: pd.DataFrame,
    family_hits: dict[str, list[str]],
) -> pd.DataFrame:
    hypotheses = {
        "D0": "Config-correlated background dominates; anomaly shape resembles run baseline more than a distinct mechanism.",
        "D1": "Outlet-OFE saturation spike: outlet outlier + ratio saturation drives extreme late-window residual.",
        "D2": "Mid-OFE chain anomaly: interior outlier coincides with chain-transfer residual signatures.",
        "D3": "Storage-cap pressure: soilwater near/over porosity cap correlates with pulse-like late-window discharges.",
        "D4": "Single-day extreme: isolated closure spike with very few flagged days.",
        "D5": "Persistent moderate anomaly: chronic moderate residual over long flagged-day spans.",
        "D_UNCLASSIFIED": "No rule-conforming mechanism detected in current D1-D5 taxonomy.",
    }
    expected = {
        "D0": "Reduce run-level z-deltas for late_max_abs_ofe_closure_residual_mm_max_abs, late_max_surface_pulse_proxy_mm_max_abs, closure_residual_pct_of_rm_total, requires_scientific_review_days, chain_surface_transfer_residual_m3_p99, chain_subsurface_transfer_residual_m3_p99.",
        "D1": "Move late_outlier_ofe_id away from n_ofe_max and reduce late_max_qofe_to_q_ratio_max_abs below (n_ofe_max-0.01) with lower late_max_abs_ofe_closure_residual_mm_max_abs.",
        "D2": "Reduce chain_surface_transfer_residual_m3_p99<=1e-3, chain_subsurface_transfer_residual_m3_p99<=1e-3, and runoff_pass_vs_outlet_qofe_residual_m3_max_abs<=1.0.",
        "D3": "Reduce soilwater_to_porosity_fraction_p99 below 0.99 and soilwater_gt_porositycap_days to 0 while lowering late_max_surface_pulse_proxy_mm_max_abs.",
        "D4": "Reduce worst-day late_max_abs_ofe_closure_residual_mm_max_abs below 500 and collapse requires_scientific_review_days from <=3 to 0.",
        "D5": "Lower requires_scientific_review_days below 30 and shrink late_max_abs_ofe_closure_residual_mm_max_abs below 100.",
        "D_UNCLASSIFIED": "Define new observable separating condition before ablation.",
    }
    pass_fail = {
        "D0": "PASS if representative seeds converge toward run-background moments without creating new high-severity outliers.",
        "D1": "PASS if outlet saturation signature disappears and flagged-day criteria no longer trigger.",
        "D2": "PASS if chain residual thresholds clear and interior outlier classification resolves.",
        "D3": "PASS if porosity-cap pressure clears and late-window pulse threshold no longer exceeded.",
        "D4": "PASS if one-day spike is removed and no review days remain.",
        "D5": "PASS if persistent flagged-day burden is broken and severity drops below review thresholds.",
        "D_UNCLASSIFIED": "PASS criteria deferred pending new family definition.",
    }
    signature = {
        "D0": "config-correlated-background",
        "D1": "outlet-ofe-saturation-spike",
        "D2": "mid-ofe-chain-anomaly",
        "D3": "storage-cap-pressure",
        "D4": "single-day-closure-spike",
        "D5": "persistent-moderate-anomaly",
        "D_UNCLASSIFIED": "unclassified",
    }

    rows: list[dict[str, Any]] = []
    today = datetime.now(tz=timezone.utc).strftime("%Y%m%d")
    families = sorted(f for f in taxonomy["family_primary"].unique() if f)

    for family in families:
        fam_rows = taxonomy[taxonomy["family_primary"] == family]
        best_runid = (
            fam_rows["runid"].mode().iloc[0] if not fam_rows.empty else "unknown-runid"
        )
        reps_fam = reps[reps["family"] == family]
        rep_map = {
            role: reps_fam[reps_fam["role"] == role]
            for role in ["worst", "median", "contrast"]
        }

        def format_rep(role: str) -> str:
            role_df = rep_map[role]
            if role_df.empty:
                return ""
            r = role_df.iloc[0]
            return f"{r['runid']}/H{int(r['wepp_id'])}"

        precedent_hits = sorted(set(family_hits.get(family, [])))
        if family == "D0":
            recommendation = "hold"
        elif family == "D4" and "20260430_uncapped-spectacular_h2637_hillslope_closure-spike" in precedent_hits:
            recommendation = "extend_20260430_uncapped-spectacular_h2637_hillslope_closure-spike"
        elif precedent_hits:
            recommendation = f"extend_{precedent_hits[0]}"
        else:
            recommendation = "new_incident"

        rows.append(
            {
                "family": family,
                "hypothesis": hypotheses.get(family, hypotheses["D_UNCLASSIFIED"]),
                "representative_worst": format_rep("worst"),
                "representative_median": format_rep("median"),
                "representative_contrast": format_rep("contrast"),
                "expected_observable": expected.get(family, expected["D_UNCLASSIFIED"]),
                "pass_fail_criterion": pass_fail.get(family, pass_fail["D_UNCLASSIFIED"]),
                "suggested_lane_type": "G*",
                "candidate_incident_id": f"{today}_{best_runid}_hillslope_{signature.get(family, 'unclassified')}",
                "recommendation": recommendation,
            }
        )

    return pd.DataFrame(rows)


def build_defect_families_md(
    flagged: pd.DataFrame,
    taxonomy: pd.DataFrame,
    campaign_matrix: pd.DataFrame,
) -> str:
    merged = flagged.merge(taxonomy, on=HILLSLOPE_KEY, how="inner")
    total = len(merged)
    lines: list[str] = ["# Defect Families", ""]

    if total == 0:
        lines.extend(["No flagged hillslopes found.", ""])
        return "\n".join(lines)

    matrix_map = campaign_matrix.set_index("family")["recommendation"].to_dict()
    key_span_features = [
        "late_max_abs_ofe_closure_residual_mm_max_abs",
        "late_max_surface_pulse_proxy_mm_max_abs",
        "requires_scientific_review_days",
        "chain_surface_transfer_residual_m3_p99",
        "soilwater_to_porosity_fraction_p99",
    ]

    for family in sorted(merged["family_primary"].unique()):
        fam = merged[merged["family_primary"] == family].copy()
        n = len(fam)
        pct = 100.0 * n / total
        median_val = float(fam["late_max_abs_ofe_closure_residual_mm_max_abs"].median())
        max_val = float(fam["late_max_abs_ofe_closure_residual_mm_max_abs"].max())

        spans: list[str] = []
        for col in key_span_features:
            series = pd.to_numeric(fam[col], errors="coerce")
            if series.notna().any():
                spans.append(f"{col}=[{series.min():.3f}, {series.max():.3f}]")
            else:
                spans.append(f"{col}=[null, null]")

        recommendation = matrix_map.get(family, "hold")
        lines.extend(
            [
                f"## {family}",
                f"- prevalence: n={n} ({pct:.1f}% of flagged hillslopes)",
                f"- severity: median={median_val:.3f} mm, max={max_val:.3f} mm",
                f"- signature stability: {'; '.join(spans)}",
                f"- recommended next step: `{recommendation}`",
                "",
            ]
        )

    return "\n".join(lines)


def write_outputs(
    taxonomy: pd.DataFrame,
    disagreements: pd.DataFrame,
    reps: pd.DataFrame,
    crosswalk_md: str,
    campaign_matrix: pd.DataFrame,
    defect_families_md: str,
    metadata: dict[str, Any],
) -> None:
    taxonomy.to_csv(ARTIFACTS_DIR / "taxonomy_assignments.csv", index=False)
    disagreements.to_csv(ARTIFACTS_DIR / "taxonomy_disagreements.csv", index=False)
    reps.to_csv(ARTIFACTS_DIR / "representative_seeds.csv", index=False)
    (ARTIFACTS_DIR / "precedent_crosswalk.md").write_text(crosswalk_md, encoding="utf-8")
    campaign_matrix.to_csv(ARTIFACTS_DIR / "campaign_matrix.csv", index=False)
    (ARTIFACTS_DIR / "defect_families.md").write_text(defect_families_md, encoding="utf-8")
    (ARTIFACTS_DIR / "triage_pipeline_metadata.json").write_text(
        json.dumps(metadata, indent=2, sort_keys=True), encoding="utf-8"
    )


def main() -> int:
    flagged, all_hillslopes, runs = normalize_tables()
    taxonomy = assign_rule_families(flagged)

    features_z = standardize(flagged, CLUSTER_FEATURES)
    cluster_result = cluster_rows(features_z)
    taxonomy["cluster_label"] = cluster_result.labels

    taxonomy, demotions = apply_d0_demotion(taxonomy, flagged)
    taxonomy = compute_rule_cluster_agreement(taxonomy)
    disagreements = build_disagreement_table(flagged, taxonomy)

    reps, missing_context_alerts = pick_representatives(
        flagged=flagged,
        all_hillslopes=all_hillslopes,
        runs=runs,
        taxonomy=taxonomy,
    )

    populated_families = sorted(f for f in taxonomy["family_primary"].unique() if f)
    canonical_families = ["D0", "D1", "D2", "D3", "D4", "D5"]
    coverage_families = canonical_families + [
        fam for fam in populated_families if fam not in canonical_families
    ]
    crosswalk_md, family_hits = build_precedent_crosswalk(
        taxonomy=taxonomy, coverage_families=coverage_families
    )
    campaign_matrix = build_campaign_matrix(taxonomy=taxonomy, reps=reps, family_hits=family_hits)
    defect_families_md = build_defect_families_md(
        flagged=flagged, taxonomy=taxonomy, campaign_matrix=campaign_matrix
    )

    metadata = {
        "generated_utc": datetime.now(tz=timezone.utc).isoformat(),
        "cluster_algorithm": cluster_result.algorithm,
        "flagged_rows": int(len(flagged)),
        "taxonomy_counts": taxonomy["family_primary"].value_counts().to_dict(),
        "disagreement_rows": int(len(disagreements)),
        "demotions": demotions,
        "missing_context_alerts": [
            {
                "family": r["family"],
                "role": r["role"],
                "runid": r["runid"],
                "wepp_id": int(r["wepp_id"]),
                "missing_shared_context": r["missing_shared_context"],
            }
            for r in missing_context_alerts
        ],
        "populated_families": populated_families,
    }

    write_outputs(
        taxonomy=taxonomy,
        disagreements=disagreements,
        reps=reps,
        crosswalk_md=crosswalk_md,
        campaign_matrix=campaign_matrix,
        defect_families_md=defect_families_md,
        metadata=metadata,
    )

    print(
        "triage_pipeline complete: "
        f"{len(taxonomy)} taxonomy rows, {len(disagreements)} disagreements, "
        f"{len(reps)} representative seeds, families={','.join(populated_families)}"
    )
    print(f"cluster_algorithm: {cluster_result.algorithm}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
