#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import requests


@dataclass(frozen=True)
class QueryEngineClient:
    base_url: str
    timeout_s: float = 180.0
    max_retries: int = 8

    def _url(self, path: str) -> str:
        return f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"

    def query(self, run_slug: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = self._url(f"runs/{run_slug}/query")
        last_error: str | None = None
        for attempt in range(int(self.max_retries)):
            try:
                resp = requests.post(
                    url,
                    json=payload,
                    timeout=self.timeout_s,
                    headers={"Connection": "close"},
                )
                # Some backends intermittently respond with 404 "Run not found" behind a LB.
                if resp.status_code in (404, 502, 503, 504):
                    last_error = f"{resp.status_code}: {resp.text[:200]}"
                    time.sleep(0.5 * (2**attempt))
                    continue
                resp.raise_for_status()
                return resp.json()
            except requests.RequestException as exc:
                last_error = repr(exc)
                time.sleep(0.5 * (2**attempt))
        raise RuntimeError(f"QueryEngine request failed after retries: {last_error}")


def _add_rank(df: pd.DataFrame) -> pd.DataFrame:
    out = df.copy()
    out = out.sort_values(["peak_runoff", "sim_day_index"], ascending=[False, True]).reset_index(drop=True)
    out["rank"] = np.arange(1, len(out) + 1, dtype=int)
    return out


def _soil_state_for_days(
    client: QueryEngineClient,
    *,
    run_slug: str,
    scenario: str | None,
    days: pd.DataFrame,
) -> pd.DataFrame:
    years = sorted(int(x) for x in days["year"].astype(int).unique())
    julians = sorted(int(x) for x in days["julian"].astype(int).unique())
    keep = set(zip(days["year"].astype(int).tolist(), days["julian"].astype(int).tolist(), strict=True))

    payload: dict[str, Any] = {
        "datasets": [
            {"path": "wepp/output/interchange/soil_pw0.parquet", "alias": "s"},
            {"path": "wepp/output/interchange/pass_pw0.metadata.parquet", "alias": "m"},
        ],
        "joins": [{"left": "s", "right": "m", "on": "wepp_id", "type": "inner"}],
        "columns": ["s.year AS year", "s.julian AS julian"],
        "filters": [
            {"column": "s.year", "operator": "IN", "value": years},
            {"column": "s.julian", "operator": "IN", "value": julians},
        ],
        "group_by": ["year", "julian"],
        "aggregations": [
            {"sql": "SUM(m.area)", "alias": "area_m2"},
            {"sql": "SUM(s.Saturation * m.area) / NULLIF(SUM(m.area),0)", "alias": "Saturation_aw"},
            {"sql": "SUM(s.TSW * m.area) / NULLIF(SUM(m.area),0)", "alias": "TSW_aw"},
            {"sql": "SUM(s.Suct * m.area) / NULLIF(SUM(m.area),0)", "alias": "Suct_aw"},
            {"sql": "SUM(s.Keff * m.area) / NULLIF(SUM(m.area),0)", "alias": "Keff_aw"},
            {"sql": "SUM(s.Rough * m.area) / NULLIF(SUM(m.area),0)", "alias": "Rough_aw"},
        ],
        "order_by": ["year ASC", "julian ASC"],
        "limit": 200000,
        "include_schema": False,
    }
    if scenario:
        payload["scenario"] = scenario
    result = client.query(run_slug, payload)
    df = pd.DataFrame(result.get("records", []))
    if df.empty:
        raise ValueError(f"No soil_pw0 records returned for {run_slug} scenario={scenario}")

    df["year"] = df["year"].astype(int)
    df["julian"] = df["julian"].astype(int)
    df = df[df.apply(lambda r: (int(r["year"]), int(r["julian"])) in keep, axis=1)].copy()
    return df


def _summarize_iqr(series: pd.Series) -> tuple[float, float, float]:
    s = series.astype(float).dropna()
    return float(s.median()), float(s.quantile(0.25)), float(s.quantile(0.75))


def _build_rank_summary(
    *,
    undisturbed: pd.DataFrame,
    burned: pd.DataFrame,
    rank_min: int,
    rank_max: int,
) -> pd.DataFrame:
    u = undisturbed[(undisturbed["rank"] >= rank_min) & (undisturbed["rank"] <= rank_max)].copy()
    b = burned[(burned["rank"] >= rank_min) & (burned["rank"] <= rank_max)].copy()

    metrics: list[tuple[str, str]] = [
        ("peak_runoff", "Outlet peak discharge $Q_p$ (m$^3$/s)"),
        ("runoff_volume", "Outlet runoff volume $V$ (m$^3$)"),
        ("effective_duration_hr", "Outlet effective duration $T_{eff}=V/Q_p$ (hr)"),
        ("peak_to_volume_1_per_s", "Peak-to-volume ratio $Q_p/V$ (1/s)"),
        ("time_to_peak_s", "Outlet time-to-peak (s)"),
        ("approx_intensity_mm_per_hr", "Intensity proxy $P/\\mathrm{dur}$ (mm/hr)"),
        ("contrib_area_fraction", "Contributing-area fraction (PASS)"),
        ("subsurface_fraction_of_runvol", "Subsurface fraction of runoff volume (PASS)"),
        ("Saturation_aw", "Area-weighted soil saturation (soil\\_pw0)"),
        ("TSW_aw", "Area-weighted total soil water TSW (soil\\_pw0)"),
        ("Suct_aw", "Area-weighted suction (mm) (soil\\_pw0)"),
        ("Keff_aw", "Area-weighted $K_{eff}$ (soil\\_pw0)"),
        ("Rough_aw", "Area-weighted roughness (soil\\_pw0)"),
    ]

    rows: list[dict[str, Any]] = []
    for col, label in metrics:
        if col not in u.columns or col not in b.columns:
            continue
        u_med, u_q25, u_q75 = _summarize_iqr(u[col])
        b_med, b_q25, b_q75 = _summarize_iqr(b[col])
        rows.append(
            {
                "metric": col,
                "label": label,
                "U_median": u_med,
                "U_q25": u_q25,
                "U_q75": u_q75,
                "B_median": b_med,
                "B_q25": b_q25,
                "B_q75": b_q75,
                "U_minus_B_median": u_med - b_med,
                "n_U": int(len(u)),
                "n_B": int(len(b)),
            }
        )
    return pd.DataFrame(rows)


def _plot_metric_vs_rank(
    *,
    out_path: Path,
    undisturbed: pd.DataFrame,
    burned: pd.DataFrame,
    metric: str,
    ylabel: str,
    title: str,
    rank_min: int,
    rank_max: int,
    log_y: bool = False,
) -> None:
    u = undisturbed[(undisturbed["rank"] >= rank_min) & (undisturbed["rank"] <= rank_max)].copy()
    b = burned[(burned["rank"] >= rank_min) & (burned["rank"] <= rank_max)].copy()

    fig, ax = plt.subplots(figsize=(9.4, 4.8), constrained_layout=True)
    ax.plot(u["rank"], u[metric], "-o", color="#1e90ff", label="Undisturbed", linewidth=2, markersize=4.5)
    ax.plot(b["rank"], b[metric], "-o", color="#ff3b30", label="Burned", linewidth=2, markersize=4.5)
    ax.set_xlabel("Outlet event rank by $Q_p$ (1 = largest)")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    if log_y:
        ax.set_yscale("log")
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


def _same_date_union_correlations(comp: pd.DataFrame) -> pd.DataFrame:
    df = comp.dropna(
        subset=[
            "undisturbed_peak_runoff",
            "burned_peak_runoff",
            "undisturbed_runoff_volume",
            "burned_runoff_volume",
            "undisturbed_effective_duration_hr",
            "burned_effective_duration_hr",
        ]
    ).copy()
    if df.empty:
        return pd.DataFrame()

    for c in [
        "undisturbed_peak_runoff",
        "burned_peak_runoff",
        "undisturbed_runoff_volume",
        "burned_runoff_volume",
        "undisturbed_effective_duration_hr",
        "burned_effective_duration_hr",
    ]:
        df[c] = df[c].astype(float)

    df["dlogQ"] = np.log(df["undisturbed_peak_runoff"]) - np.log(df["burned_peak_runoff"])
    df["dlogV"] = np.log(df["undisturbed_runoff_volume"]) - np.log(df["burned_runoff_volume"])
    df["dTeff"] = df["undisturbed_effective_duration_hr"] - df["burned_effective_duration_hr"]

    if "undisturbed_subsurface_fraction_of_runvol" in df.columns and "burned_subsurface_fraction_of_runvol" in df.columns:
        df["dsubfrac"] = df["undisturbed_subsurface_fraction_of_runvol"].astype(float) - df[
            "burned_subsurface_fraction_of_runvol"
        ].astype(float)
    if "undisturbed_time_to_peak_s" in df.columns and "burned_time_to_peak_s" in df.columns:
        df["dttp"] = df["undisturbed_time_to_peak_s"].astype(float) - df["burned_time_to_peak_s"].astype(float)

    cols = [c for c in ["dlogV", "dTeff", "dsubfrac", "dttp"] if c in df.columns]
    rows: list[dict[str, Any]] = []
    for c in cols:
        corr = float(df[["dlogQ", c]].corr().iloc[0, 1])
        rows.append({"driver": c, "pearson_r_with_dlogQ": corr, "n": int(len(df))})
    return pd.DataFrame(rows)

def _tc_out_for_sim_days(
    client: QueryEngineClient,
    *,
    run_slug: str,
    sim_day_indexes: list[int],
) -> pd.DataFrame:
    payload: dict[str, Any] = {
        "datasets": [{"path": "wepp/output/interchange/tc_out.parquet", "alias": "t"}],
        "columns": [
            "t.sim_day_index",
            "t.year",
            "t.julian",
            't."Time of Conc (hr)" AS tc_hr',
            't."Storm Duration (hr)" AS storm_dur_hr',
            't."Storm Peak (hr)" AS storm_peak_hr',
        ],
        "filters": [{"column": "t.sim_day_index", "operator": "IN", "value": [int(x) for x in sim_day_indexes]}],
        "order_by": ["t.sim_day_index ASC"],
        "limit": 200000,
        "include_schema": False,
    }
    result = client.query(run_slug, payload)
    df = pd.DataFrame(result.get("records", []))
    if df.empty:
        raise ValueError("No tc_out records returned for requested sim_day_indexes")
    for c in ["tc_hr", "storm_dur_hr", "storm_peak_hr"]:
        df[c] = df[c].astype(float)
    df["storm_peak_minus_tc_hr"] = df["storm_peak_hr"] - df["tc_hr"]
    df["storm_peak_minus_tc_abs_hr"] = (df["storm_peak_hr"] - df["tc_hr"]).abs()
    df["tc_over_dur"] = df["tc_hr"] / df["storm_dur_hr"].where(lambda s: s != 0)
    df["peak_over_dur"] = df["storm_peak_hr"] / df["storm_dur_hr"].where(lambda s: s != 0)
    df["peak_over_tc"] = df["storm_peak_hr"] / df["tc_hr"].where(lambda s: s != 0)
    return df


def _tc_alignment_correlations(comp_with_tc: pd.DataFrame) -> pd.DataFrame:
    df = comp_with_tc.dropna(
        subset=[
            "undisturbed_peak_runoff",
            "burned_peak_runoff",
            "tc_hr",
            "storm_dur_hr",
            "storm_peak_hr",
        ]
    ).copy()
    if df.empty:
        return pd.DataFrame()

    df["undisturbed_peak_runoff"] = df["undisturbed_peak_runoff"].astype(float)
    df["burned_peak_runoff"] = df["burned_peak_runoff"].astype(float)
    df["dlogQ"] = np.log(df["undisturbed_peak_runoff"]) - np.log(df["burned_peak_runoff"])
    df["abs_dlogQ"] = df["dlogQ"].abs()

    drivers = [
        ("tc_hr", "$T_c$ (hr)"),
        ("storm_dur_hr", "Storm duration (hr)"),
        ("storm_peak_hr", "Storm peak time (hr)"),
        ("storm_peak_minus_tc_hr", "$t_{peak}-T_c$ (hr)"),
        ("storm_peak_minus_tc_abs_hr", "$|t_{peak}-T_c|$ (hr)"),
        ("tc_over_dur", "$T_c/\\mathrm{dur}$"),
        ("peak_over_dur", "$t_{peak}/\\mathrm{dur}$"),
        ("peak_over_tc", "$t_{peak}/T_c$"),
    ]

    rows: list[dict[str, Any]] = []
    for col, label in drivers:
        if col not in df.columns:
            continue
        r = float(df[["abs_dlogQ", col]].corr().iloc[0, 1])
        rows.append({"driver": col, "label": label, "pearson_r_with_abs_dlogQ": r, "n": int(len(df))})
    return pd.DataFrame(rows)


def _plot_abs_dlogq_vs_peak_minus_tc(
    *,
    out_path: Path,
    comp_with_tc: pd.DataFrame,
    title: str,
) -> None:
    df = comp_with_tc.dropna(
        subset=["undisturbed_peak_runoff", "burned_peak_runoff", "storm_peak_minus_tc_hr"]
    ).copy()
    if df.empty:
        return
    df["undisturbed_peak_runoff"] = df["undisturbed_peak_runoff"].astype(float)
    df["burned_peak_runoff"] = df["burned_peak_runoff"].astype(float)
    df["abs_dlogQ"] = (np.log(df["undisturbed_peak_runoff"]) - np.log(df["burned_peak_runoff"])).abs()
    x = df["storm_peak_minus_tc_hr"].astype(float)
    y = df["abs_dlogQ"].astype(float)

    fig, ax = plt.subplots(figsize=(8.8, 4.8), constrained_layout=True)
    ax.scatter(x, y, s=36, alpha=0.75, edgecolor="white", linewidth=0.6, color="#6a5acd")
    ax.axvline(0.0, color="black", linewidth=1.2, alpha=0.35)
    ax.set_xlabel("$t_{peak} - T_c$ (hr) (from tc_out)")
    ax.set_ylabel("$|\\Delta \\log(Q_p)|$ (undisturbed minus burned)")
    ax.set_title(title)
    ax.grid(True, alpha=0.25)
    fig.savefig(out_path, dpi=200)
    plt.close(fig)

def _to_latex_table(
    *,
    df: pd.DataFrame,
    caption: str,
    label: str,
    columns: list[tuple[str, str]],
    float_fmt: dict[str, str] | None = None,
) -> str:
    float_fmt = float_fmt or {}
    out: list[str] = []
    out.append("\\begin{table}[H]")
    out.append("  \\centering")
    out.append(f"  \\caption{{{caption}}}")
    out.append(f"  \\label{{{label}}}")
    out.append("  \\resizebox{\\textwidth}{!}{%")
    out.append("  \\begin{tabular}{%s}" % (" ".join(["l"] + ["r"] * (len(columns) - 1))))
    out.append("    \\toprule")
    out.append("    " + " & ".join(h for _, h in columns) + " \\\\")
    out.append("    \\midrule")

    for _, row in df.iterrows():
        cells: list[str] = []
        for key, _hdr in columns:
            val = row.get(key)
            if isinstance(val, float) or isinstance(val, np.floating):
                fmt = float_fmt.get(key)
                if fmt:
                    cells.append(fmt.format(float(val)))
                else:
                    cells.append(f"{float(val):0.5g}")
            else:
                # Treat values as LaTeX-ready strings (many labels include math/escapes).
                cells.append(str(val))
        out.append("    " + " & ".join(cells) + " \\\\")

    out.append("    \\bottomrule")
    out.append("  \\end{tabular}}")
    out.append("\\end{table}")
    out.append("")
    return "\n".join(out)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--runid", required=True)
    ap.add_argument("--base-url", required=True)
    ap.add_argument("--out-dir", type=Path, required=True)
    ap.add_argument("--rank-min", type=int, default=4)
    ap.add_argument("--rank-max", type=int, default=30)
    ap.add_argument(
        "--refresh",
        action="store_true",
        help="Re-query Query Engine for soil-state joins even if cached CSVs exist in out-dir.",
    )
    ap.add_argument(
        "--undisturbed-csv",
        type=Path,
        default=Path("tmp_upset_reckoning_hydroshape/undisturbed_top_events_with_diagnostics.csv"),
    )
    ap.add_argument(
        "--burned-csv",
        type=Path,
        default=Path("tmp_upset_reckoning_hydroshape/burned_top_events_with_diagnostics.csv"),
    )
    ap.add_argument(
        "--comparison-csv",
        type=Path,
        default=Path("tmp_upset_reckoning_hydroshape/top_events_hydroshape_comparison.csv"),
    )
    args = ap.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)

    cached_u_path = args.out_dir / "undisturbed_rank_metrics_with_soil.csv"
    cached_b_path = args.out_dir / "burned_rank_metrics_with_soil.csv"
    cached_comp_tc_path = args.out_dir / "same_date_union_with_tc_out.csv"

    def has_soil_cols(df: pd.DataFrame) -> bool:
        return all(c in df.columns for c in ["Saturation_aw", "TSW_aw", "Suct_aw", "Keff_aw", "Rough_aw"])

    if cached_u_path.exists() and not args.refresh:
        u = pd.read_csv(cached_u_path)
    else:
        u = _add_rank(pd.read_csv(args.undisturbed_csv))

    if cached_b_path.exists() and not args.refresh:
        b = pd.read_csv(cached_b_path)
    else:
        b = _add_rank(pd.read_csv(args.burned_csv))

    client = QueryEngineClient(base_url=args.base_url)

    if not has_soil_cols(u) or not has_soil_cols(b) or args.refresh:
        u_days = u[(u["rank"] >= args.rank_min) & (u["rank"] <= args.rank_max)][["year", "julian"]].copy()
        b_days = b[(b["rank"] >= args.rank_min) & (b["rank"] <= args.rank_max)][["year", "julian"]].copy()

        # Note: the earlier hydroshape workflow treats "burned" as the default/base scenario
        # and queries it with scenario omitted. We mirror that convention here.
        u_soil = _soil_state_for_days(client, run_slug=args.runid, scenario="undisturbed", days=u_days)
        b_soil = _soil_state_for_days(client, run_slug=args.runid, scenario=None, days=b_days)

        u = u.merge(u_soil, on=["year", "julian"], how="left")
        b = b.merge(b_soil, on=["year", "julian"], how="left")

        cached_u_path.write_text(u.to_csv(index=False))
        cached_b_path.write_text(b.to_csv(index=False))

    summary = _build_rank_summary(undisturbed=u, burned=b, rank_min=args.rank_min, rank_max=args.rank_max)
    summary.to_csv(args.out_dir / "rank_summary_ranks_4_30.csv", index=False)

    comp = pd.read_csv(args.comparison_csv)
    corr = _same_date_union_correlations(comp)
    corr.to_csv(args.out_dir / "same_date_union_driver_correlations.csv", index=False)

    # tc_out synchronization proxies: join to the same-date union table (tc_out is outlet storm timing).
    if cached_comp_tc_path.exists() and not args.refresh:
        comp_tc = pd.read_csv(cached_comp_tc_path)
    else:
        sim_days = sorted(int(x) for x in comp["sim_day_index"].dropna().unique().tolist())
        tc = _tc_out_for_sim_days(client, run_slug=args.runid, sim_day_indexes=sim_days)
        comp_tc = comp.merge(tc, on=["sim_day_index"], how="left")
        cached_comp_tc_path.write_text(comp_tc.to_csv(index=False))

    tc_corr = _tc_alignment_correlations(comp_tc)
    tc_corr.to_csv(args.out_dir / "tc_out_alignment_correlations.csv", index=False)

    # Write LaTeX tables for report inclusion.
    summary_tex = _to_latex_table(
        df=summary,
        caption=f"Rank-based summary (ranks {args.rank_min}--{args.rank_max}): median and IQR for key flashiness proxies and soil-state variables.",
        label="tab:root_cause_rank_summary",
        columns=[
            ("label", "Metric"),
            ("U_median", "U median"),
            ("U_q25", "U q25"),
            ("U_q75", "U q75"),
            ("B_median", "B median"),
            ("B_q25", "B q25"),
            ("B_q75", "B q75"),
            ("U_minus_B_median", "U--B (median)"),
        ],
        float_fmt={
            "U_median": "{:0.6g}",
            "U_q25": "{:0.6g}",
            "U_q75": "{:0.6g}",
            "B_median": "{:0.6g}",
            "B_q25": "{:0.6g}",
            "B_q75": "{:0.6g}",
            "U_minus_B_median": "{:0.6g}",
        },
    )
    (args.out_dir / "rank_summary_table.tex").write_text(summary_tex)

    if not corr.empty:
        corr_tex = _to_latex_table(
            df=corr,
            caption="Same-date union: Pearson correlation of $\\Delta\\log(Q_p)$ with candidate driver deltas (undisturbed minus burned).",
            label="tab:root_cause_same_date_corr",
            columns=[
                ("driver", "Driver delta"),
                ("pearson_r_with_dlogQ", "$r$ with $\\Delta\\log(Q_p)$"),
                ("n", "$n$ dates"),
            ],
            float_fmt={"pearson_r_with_dlogQ": "{:0.3f}"},
        )
        (args.out_dir / "same_date_union_driver_correlations_table.tex").write_text(corr_tex)

    if not tc_corr.empty:
        tc_corr_tex = _to_latex_table(
            df=tc_corr,
            caption="Same-date union: Pearson correlation of $|\\Delta\\log(Q_p)|$ with storm timing/synchronization proxies from \\texttt{tc\\_out}.",
            label="tab:root_cause_tc_out_corr",
            columns=[
                ("label", "Proxy"),
                ("pearson_r_with_abs_dlogQ", "$r$ with $|\\Delta\\log(Q_p)|$"),
                ("n", "$n$ dates"),
            ],
            float_fmt={"pearson_r_with_abs_dlogQ": "{:0.3f}"},
        )
        (args.out_dir / "tc_out_alignment_correlations_table.tex").write_text(tc_corr_tex)

    _plot_abs_dlogq_vs_peak_minus_tc(
        out_path=args.out_dir / "abs_dlogq_vs_peak_minus_tc.png",
        comp_with_tc=comp_tc,
        title="Peak-difference magnitude vs storm-peak alignment ($t_{peak}-T_c$) from tc_out",
    )

    meta = {
        "runid": args.runid,
        "rank_min": args.rank_min,
        "rank_max": args.rank_max,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    (args.out_dir / "meta.json").write_text(json.dumps(meta, indent=2))

    # Plots used in the report.
    _plot_metric_vs_rank(
        out_path=args.out_dir / "teff_outlet_hr_vs_rank.png",
        undisturbed=u,
        burned=b,
        metric="effective_duration_hr",
        ylabel="$T_{eff}=V/Q_p$ (hr)",
        title=f"Effective-duration proxy vs. rank (ranks {args.rank_min}–{args.rank_max})",
        rank_min=args.rank_min,
        rank_max=args.rank_max,
    )
    _plot_metric_vs_rank(
        out_path=args.out_dir / "qp_over_v_vs_rank.png",
        undisturbed=u,
        burned=b,
        metric="peak_to_volume_1_per_s",
        ylabel="$Q_p/V$ (1/s)",
        title=f"Peak-to-volume ratio vs. rank (ranks {args.rank_min}–{args.rank_max})",
        rank_min=args.rank_min,
        rank_max=args.rank_max,
    )
    _plot_metric_vs_rank(
        out_path=args.out_dir / "subsurface_fraction_vs_rank.png",
        undisturbed=u,
        burned=b,
        metric="subsurface_fraction_of_runvol",
        ylabel="Subsurface fraction of runoff volume (PASS)",
        title=f"Runoff-partition proxy vs. rank (ranks {args.rank_min}–{args.rank_max})",
        rank_min=args.rank_min,
        rank_max=args.rank_max,
    )
    _plot_metric_vs_rank(
        out_path=args.out_dir / "soil_saturation_vs_rank.png",
        undisturbed=u,
        burned=b,
        metric="Saturation_aw",
        ylabel="Area-weighted saturation (soil_pw0)",
        title=f"Antecedent soil wetness proxy vs. rank (ranks {args.rank_min}–{args.rank_max})",
        rank_min=args.rank_min,
        rank_max=args.rank_max,
    )
    _plot_metric_vs_rank(
        out_path=args.out_dir / "soil_suction_vs_rank.png",
        undisturbed=u,
        burned=b,
        metric="Suct_aw",
        ylabel="Area-weighted suction (mm) (soil_pw0)",
        title=f"Soil suction proxy vs. rank (ranks {args.rank_min}–{args.rank_max})",
        rank_min=args.rank_min,
        rank_max=args.rank_max,
        log_y=True,
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
