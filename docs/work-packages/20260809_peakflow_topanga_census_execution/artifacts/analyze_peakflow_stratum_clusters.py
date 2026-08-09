#!/usr/bin/env python3
"""Reproduce the Topanga burned/unburned peak-response cluster analysis."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import numpy as np
import pandas as pd


PLAN_ID = "b575fde4a28cf85f1d28e0dfff305472b5419fd9b3639d39dc437600617080de"
EVIDENCE = (
    Path("/home/workdir/peakflow-topanga-census-evidence")
    / PLAN_ID
    / "ledgers"
    / "event-pairs.parquet"
)
OUTPUT_DIR = Path(__file__).parent
BIN_OUTPUT = OUTPUT_DIR / "topanga-peakflow-stratum-cluster-bins.csv"
CLUSTER_OUTPUT = OUTPUT_DIR / "topanga-peakflow-stratum-cluster-summary.csv"
MATCHED_OUTPUT = OUTPUT_DIR / "topanga-peakflow-stratum-matched-clusters.csv"
MANIFEST_OUTPUT = OUTPUT_DIR / "topanga-peakflow-stratum-cluster-manifest.json"
PEAK_FLOOR_M_S = 1e-7
M_S_TO_MM_H = 3.6e6
BIN_EDGES_MM_H = [0.3, 1, 3, 10, 30, 100, 300, 800]
BIN_LABELS = ["0.3-1", "1-3", "3-10", "10-30", "30-100", "100-300", "300-800"]
MATCH_KEYS = ["hillslope_id", "family", "direction", "year", "day", "ofe", "ordinal"]


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def load_population() -> pd.DataFrame:
    frame = pd.read_parquet(
        EVIDENCE,
        columns=[
            "scenario", "hillslope_id", "family", "direction", "year", "day",
            "ofe", "ordinal", "baseline_event_present", "mutant_event_present",
            "peak_m_s_baseline", "peak_m_s_mutant",
        ],
    )
    frame = frame.loc[
        frame.baseline_event_present
        & frame.mutant_event_present
        & frame.peak_m_s_baseline.ge(PEAK_FLOOR_M_S)
        & frame.peak_m_s_mutant.gt(0)
    ].copy()
    frame["baseline_peak_mm_h"] = frame.peak_m_s_baseline * M_S_TO_MM_H
    frame["peak_ratio"] = frame.peak_m_s_mutant / frame.peak_m_s_baseline
    increased = frame.peak_m_s_mutant.gt(frame.peak_m_s_baseline)
    decreased = frame.peak_m_s_mutant.lt(frame.peak_m_s_baseline)
    frame["congruent"] = (
        frame.direction.eq("plus") & decreased
    ) | (
        frame.direction.eq("minus") & increased
    )
    frame["incongruent"] = ~frame.congruent
    frame["central_band"] = frame.peak_ratio.between(0.5, 2.0, inclusive="both")
    frame["peak_change_gt25pct"] = (
        (frame.peak_m_s_mutant - frame.peak_m_s_baseline).abs()
        / frame.peak_m_s_baseline.abs().clip(lower=PEAK_FLOOR_M_S)
    ).gt(0.25)
    frame["baseline_peak_bin_mm_h"] = pd.cut(
        frame.baseline_peak_mm_h,
        BIN_EDGES_MM_H,
        labels=BIN_LABELS,
        right=False,
    )
    return frame


def bin_summary(frame: pd.DataFrame) -> pd.DataFrame:
    pieces = []
    for family in ("all", "ksat", "cover"):
        family_frame = frame if family == "all" else frame.loc[frame.family.eq(family)]
        central = family_frame.loc[family_frame.central_band]
        grouped = central.groupby(
            ["scenario", "baseline_peak_bin_mm_h"], observed=True, sort=False
        )
        summary = grouped.agg(
            event_rows=("peak_ratio", "size"),
            incongruent_rows=("incongruent", "sum"),
            peak_change_gt25pct_rows=("peak_change_gt25pct", "sum"),
        ).reset_index()
        summary.insert(1, "family", family)
        summary["incongruent_share"] = summary.incongruent_rows / summary.event_rows
        summary["peak_change_gt25pct_share"] = (
            summary.peak_change_gt25pct_rows / summary.event_rows
        )
        pieces.append(summary)
    return pd.concat(pieces, ignore_index=True)


def distribution_row(scenario: str, definition: str, subset: pd.DataFrame) -> dict[str, object]:
    peaks = subset.baseline_peak_mm_h
    return {
        "scenario": scenario,
        "definition": definition,
        "event_rows": len(subset),
        "baseline_peak_q25_mm_h": peaks.quantile(0.25),
        "baseline_peak_median_mm_h": peaks.median(),
        "baseline_peak_q75_mm_h": peaks.quantile(0.75),
        "baseline_peak_geometric_mean_mm_h": np.exp(np.log(peaks).mean()),
    }


def cluster_summary(frame: pd.DataFrame) -> pd.DataFrame:
    rows = []
    definitions = {
        "ksat_incongruent_central_band": (
            frame.family.eq("ksat") & frame.incongruent & frame.central_band
        ),
        "absolute_fractional_peak_change_gt25pct": frame.peak_change_gt25pct,
    }
    for definition, mask in definitions.items():
        for scenario in ("undisturbed", "burned"):
            rows.append(distribution_row(
                scenario,
                definition,
                frame.loc[mask & frame.scenario.eq(scenario)],
            ))
    return pd.DataFrame(rows)


def matched_summary(frame: pd.DataFrame) -> pd.DataFrame:
    ksat = frame.loc[frame.family.eq("ksat")]
    columns = MATCH_KEYS + ["baseline_peak_mm_h", "peak_ratio", "incongruent", "central_band"]
    unburned = ksat.loc[ksat.scenario.eq("undisturbed"), columns].rename(columns={
        "baseline_peak_mm_h": "unburned_baseline_peak_mm_h",
        "peak_ratio": "unburned_peak_ratio",
        "incongruent": "unburned_incongruent",
        "central_band": "unburned_central_band",
    })
    burned = ksat.loc[ksat.scenario.eq("burned"), columns].rename(columns={
        "baseline_peak_mm_h": "burned_baseline_peak_mm_h",
        "peak_ratio": "burned_peak_ratio",
        "incongruent": "burned_incongruent",
        "central_band": "burned_central_band",
    })
    matched = unburned.merge(burned, on=MATCH_KEYS, how="inner")
    matched = matched.loc[matched.unburned_central_band & matched.burned_central_band].copy()
    matched["classification"] = np.select(
        [
            matched.unburned_incongruent & matched.burned_incongruent,
            matched.unburned_incongruent & ~matched.burned_incongruent,
            ~matched.unburned_incongruent & matched.burned_incongruent,
        ],
        ["both_incongruent", "unburned_only_incongruent", "burned_only_incongruent"],
        default="neither_incongruent",
    )
    return matched.groupby("classification", sort=False).agg(
        matched_event_rows=("classification", "size"),
        unburned_baseline_peak_q25_mm_h=("unburned_baseline_peak_mm_h", lambda x: x.quantile(0.25)),
        unburned_baseline_peak_median_mm_h=("unburned_baseline_peak_mm_h", "median"),
        unburned_baseline_peak_q75_mm_h=("unburned_baseline_peak_mm_h", lambda x: x.quantile(0.75)),
        burned_baseline_peak_q25_mm_h=("burned_baseline_peak_mm_h", lambda x: x.quantile(0.25)),
        burned_baseline_peak_median_mm_h=("burned_baseline_peak_mm_h", "median"),
        burned_baseline_peak_q75_mm_h=("burned_baseline_peak_mm_h", lambda x: x.quantile(0.75)),
        median_burned_to_unburned_baseline_peak_ratio=(
            "burned_baseline_peak_mm_h",
            lambda values: np.nan,
        ),
    ).reset_index()


def main() -> None:
    frame = load_population()
    bins = bin_summary(frame)
    clusters = cluster_summary(frame)
    matched = matched_summary(frame)

    # Calculate this paired ratio after aggregation to preserve rowwise pairing.
    ksat = frame.loc[frame.family.eq("ksat")]
    columns = MATCH_KEYS + ["baseline_peak_mm_h", "incongruent", "central_band"]
    unburned = ksat.loc[ksat.scenario.eq("undisturbed"), columns].rename(columns={
        "baseline_peak_mm_h": "u_peak", "incongruent": "u_inc", "central_band": "u_central"
    })
    burned = ksat.loc[ksat.scenario.eq("burned"), columns].rename(columns={
        "baseline_peak_mm_h": "b_peak", "incongruent": "b_inc", "central_band": "b_central"
    })
    pairs = unburned.merge(burned, on=MATCH_KEYS).loc[lambda x: x.u_central & x.b_central].copy()
    pairs["classification"] = np.select(
        [pairs.u_inc & pairs.b_inc, pairs.u_inc & ~pairs.b_inc, ~pairs.u_inc & pairs.b_inc],
        ["both_incongruent", "unburned_only_incongruent", "burned_only_incongruent"],
        default="neither_incongruent",
    )
    ratios = pairs.assign(ratio=pairs.b_peak / pairs.u_peak).groupby("classification").ratio.median()
    matched["median_burned_to_unburned_baseline_peak_ratio"] = matched.classification.map(ratios)

    bins.to_csv(BIN_OUTPUT, index=False, float_format="%.9g")
    clusters.to_csv(CLUSTER_OUTPUT, index=False, float_format="%.9g")
    matched.to_csv(MATCHED_OUTPUT, index=False, float_format="%.9g")
    manifest = {
        "schema_version": "1.0.0",
        "plan_id": PLAN_ID,
        "source": str(EVIDENCE),
        "source_sha256": sha256_file(EVIDENCE),
        "population": {
            "baseline_event_present": True,
            "mutant_event_present": True,
            "baseline_peak_floor_m_s": PEAK_FLOOR_M_S,
            "mutant_peak_positive": True,
        },
        "central_band_inclusive": [0.5, 2.0],
        "baseline_peak_bins_mm_h_left_closed_right_open": BIN_EDGES_MM_H,
        "matched_keys": MATCH_KEYS,
        "directional_rule": "plus/lower or minus/higher is congruent; all other responses are incongruent",
        "peak_change_gt25pct_rule": "abs(mutant-baseline)/max(abs(baseline), 1e-7 m/s) > 0.25",
        "outputs": [BIN_OUTPUT.name, CLUSTER_OUTPUT.name, MATCHED_OUTPUT.name],
    }
    MANIFEST_OUTPUT.write_text(json.dumps(manifest, indent=2, sort_keys=True) + "\n")
    print(clusters.to_string(index=False))
    print(matched.to_string(index=False))


if __name__ == "__main__":
    main()
