#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd
import requests


@dataclass(frozen=True)
class QueryEngineClient:
    base_url: str
    timeout_s: float = 60.0

    def _url(self, path: str) -> str:
        return f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"

    def schema(self, run_slug: str) -> dict[str, Any]:
        url = self._url(f"runs/{run_slug}/schema")
        resp = requests.get(url, timeout=self.timeout_s)
        resp.raise_for_status()
        return resp.json()

    def query(self, run_slug: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = self._url(f"runs/{run_slug}/query")
        resp = requests.post(url, json=payload, timeout=self.timeout_s)
        resp.raise_for_status()
        return resp.json()

def _ebe_top_events(
    client: QueryEngineClient,
    *,
    run_slug: str,
    scenario: str | None,
    top_n: int,
    order_by_col: str = "peak_runoff",
) -> pd.DataFrame:
    order_by_col = str(order_by_col)
    if order_by_col not in {"peak_runoff", "runoff_volume"}:
        raise ValueError('order_by_col must be "peak_runoff" or "runoff_volume"')

    payload = {
        **({"scenario": scenario} if scenario else {}),
        "datasets": [{"path": "wepp/output/interchange/ebe_pw0.parquet", "alias": "e"}],
        "columns": [
            "e.sim_day_index",
            "e.year",
            "e.month",
            "e.day_of_month",
            "e.julian",
            "e.precip",
            "e.runoff_volume",
            "e.peak_runoff",
            "e.element_id",
        ],
        "order_by": [f"e.{order_by_col} DESC", "e.sim_day_index ASC"],
        "limit": int(top_n),
        "include_schema": False,
    }
    result = client.query(run_slug, payload)
    df = pd.DataFrame(result.get("records", []))
    if df.empty:
        raise ValueError(f"No EBE records returned for {run_slug}")

    df["date"] = pd.to_datetime(
        df[["year", "month", "day_of_month"]].rename(columns={"day_of_month": "day"}),
        errors="coerce",
    )
    df["effective_duration_hr"] = (df["runoff_volume"].astype(float) / df["peak_runoff"].astype(float)) / 3600.0
    return df


def _chan_peaks_for_days(
    client: QueryEngineClient,
    *,
    run_slug: str,
    scenario: str | None,
) -> pd.DataFrame:
    payload = {
        **({"scenario": scenario} if scenario else {}),
        "datasets": [{"path": "wepp/output/interchange/chan.out.parquet", "alias": "c"}],
        "columns": [
            "c.year AS year",
            "c.month AS month",
            "c.day_of_month AS day_of_month",
            "c.julian AS julian",
            "c.Elmt_ID AS element_id",
            'c."Time (s)" AS time_to_peak_s',
            'c."Peak_Discharge (m^3/s)" AS peak_discharge_m3s',
        ],
        "order_by": ["year ASC", "julian ASC", "element_id ASC"],
        "limit": 25000,
    }
    result = client.query(run_slug, payload)
    df = pd.DataFrame(result.get("records", []))
    if df.empty:
        raise ValueError(f"No chan.out records returned for {run_slug}")
    df["date"] = pd.to_datetime(
        df[["year", "month", "day_of_month"]].rename(columns={"day_of_month": "day"}),
        errors="coerce",
    )
    return df


def _pass_event_diagnostics_for_days(
    client: QueryEngineClient,
    *,
    run_slug: str,
    scenario: str | None,
    sim_day_indexes: list[int],
) -> pd.DataFrame:
    payload = {
        **({"scenario": scenario} if scenario else {}),
        "datasets": [
            {"path": "wepp/output/interchange/pass_pw0.events.parquet", "alias": "p"},
            {"path": "wepp/output/interchange/pass_pw0.metadata.parquet", "alias": "m"},
        ],
        "joins": [{"left": "p", "right": "m", "on": "wepp_id", "type": "inner"}],
        "columns": [
            "p.sim_day_index",
            "p.year",
            "p.month",
            "p.day_of_month",
            "p.julian",
        ],
        "filters": [
            {"column": "p.event", "operator": "=", "value": "EVENT"},
            {"column": "p.sim_day_index", "operator": "IN", "value": [int(x) for x in sim_day_indexes]},
        ],
        "group_by": [
            "p.sim_day_index",
            "p.year",
            "p.month",
            "p.day_of_month",
            "p.julian",
        ],
        "aggregations": [
            {"sql": "SUM(m.area)", "alias": "total_area_m2"},
            {"sql": "SUM(CASE WHEN p.runvol > 0 THEN m.area ELSE 0 END)", "alias": "contrib_area_m2"},
            {"sql": "SUM(p.runvol)", "alias": "sum_hillslope_runvol_m3"},
            {"sql": "SUM(p.sbrunv)", "alias": "sum_sbrunv_m3"},
            {"sql": "SUM(p.drrunv)", "alias": "sum_drrunv_m3"},
            {"sql": "SUM(p.gwbfv)", "alias": "sum_gwbfv_m3"},
            {"sql": "SUM(p.gwdsv)", "alias": "sum_gwdsv_m3"},
            {"sql": "SUM(p.dur * m.area) / NULLIF(SUM(m.area), 0)", "alias": "dur_area_weighted"},
            {"sql": "SUM(p.peakro * m.area) / NULLIF(SUM(m.area), 0)", "alias": "peakro_area_weighted"},
            {"sql": "AVG(p.dur)", "alias": "dur_mean"},
            {"sql": "AVG(p.peakro)", "alias": "peakro_mean"},
            {"sql": "COUNT(*)", "alias": "hillslope_rows"},
        ],
        "order_by": ["p.sim_day_index ASC"],
        "limit": 100000,
    }
    result = client.query(run_slug, payload)
    df = pd.DataFrame(result.get("records", []))
    if df.empty:
        raise ValueError(f"No PASS diagnostic rows returned for {run_slug}")
    df["date"] = pd.to_datetime(
        df[["year", "month", "day_of_month"]].rename(columns={"day_of_month": "day"}),
        errors="coerce",
    )
    df["contrib_area_fraction"] = df["contrib_area_m2"].astype(float) / df["total_area_m2"].astype(float)
    denom = df["sum_hillslope_runvol_m3"].astype(float).where(lambda s: s != 0.0)
    df["subsurface_fraction_of_runvol"] = df["sum_sbrunv_m3"].astype(float) / denom
    df["drain_fraction_of_runvol"] = df["sum_drrunv_m3"].astype(float) / denom
    return df


def _triangle_hydrograph_points(*, duration_s: float, t_peak_s: float, q_peak: float) -> tuple[list[float], list[float]]:
    duration_s = max(float(duration_s), 0.0)
    t_peak_s = max(float(t_peak_s), 0.0)
    if duration_s <= 0.0 or not (q_peak > 0.0):
        return [0.0, 1.0], [0.0, 0.0]
    t_peak_s = min(t_peak_s, duration_s)
    return [0.0, t_peak_s, duration_s], [0.0, float(q_peak), 0.0]


def _plot_proxy_hydrographs(
    *,
    out_path: Path,
    comparison: pd.DataFrame,
    title: str,
    max_plots: int = 8,
) -> None:
    df = comparison.copy()
    df = df.sort_values("undisturbed_peak_runoff", ascending=False)
    df = df.head(int(max_plots))

    n = len(df)
    if n == 0:
        return

    cols = 2
    rows = (n + cols - 1) // cols
    fig, axes = plt.subplots(rows, cols, figsize=(12, 3.2 * rows), constrained_layout=True)
    if hasattr(axes, "ravel"):
        axes_list = list(axes.ravel())
    else:
        axes_list = [axes]

    for ax, (_, row) in zip(axes_list, df.iterrows(), strict=False):
        date = str(row["date"])

        def series(prefix: str, label: str, color: str) -> None:
            runoff_vol = float(row.get(f"{prefix}_runoff_volume") or 0.0)
            peak = float(row.get(f"{prefix}_peak_runoff") or 0.0)
            t_peak_raw = row.get(f"{prefix}_time_to_peak_s")
            t_peak = float(t_peak_raw) if t_peak_raw is not None and pd.notna(t_peak_raw) else 0.0
            duration = (2.0 * runoff_vol / peak) if peak > 0 else 0.0
            xs, ys = _triangle_hydrograph_points(duration_s=duration, t_peak_s=t_peak, q_peak=peak)
            ax.plot(xs, ys, label=label, color=color, linewidth=2)

        series("burned", "Burned (proxy)", "#ff3b30")
        series("undisturbed", "Undisturbed (proxy)", "#1e90ff")

        ax.set_title(date)
        ax.set_xlabel("Time (s)")
        ax.set_ylabel("Discharge (m³/s)")
        ax.grid(True, alpha=0.25)
        ax.legend(fontsize=9)

    for ax in axes_list[n:]:
        ax.axis("off")

    fig.suptitle(title, fontsize=14)
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


def _plot_peak_vs_volume(
    *,
    out_path: Path,
    burned: pd.DataFrame,
    undisturbed: pd.DataFrame,
    title: str,
) -> None:
    fig, ax = plt.subplots(figsize=(9.5, 6.0), constrained_layout=True)
    ax.scatter(
        burned["runoff_volume"].astype(float),
        burned["peak_runoff"].astype(float),
        s=38,
        alpha=0.75,
        color="#ff3b30",
        label="Burned (top N)",
        edgecolor="white",
        linewidth=0.6,
    )
    ax.scatter(
        undisturbed["runoff_volume"].astype(float),
        undisturbed["peak_runoff"].astype(float),
        s=38,
        alpha=0.75,
        color="#1e90ff",
        label="Undisturbed (top N)",
        edgecolor="white",
        linewidth=0.6,
    )
    ax.set_xlabel("Runoff volume (m³)")
    ax.set_ylabel("Peak discharge (m³/s)")
    ax.set_title(title)
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


def _plot_metric_vs_rank(
    *,
    out_path: Path,
    burned: pd.DataFrame,
    undisturbed: pd.DataFrame,
    metric_col: str,
    rank_by_col: str,
    xlabel: str,
    ylabel: str,
    title: str,
) -> None:
    b = burned.sort_values(rank_by_col, ascending=False).reset_index(drop=True).copy()
    u = undisturbed.sort_values(rank_by_col, ascending=False).reset_index(drop=True).copy()
    b["rank"] = b.index + 1
    u["rank"] = u.index + 1

    fig, ax = plt.subplots(figsize=(9.5, 5.8), constrained_layout=True)
    ax.plot(
        b["rank"].astype(int),
        b[metric_col].astype(float),
        color="#ff3b30",
        linewidth=2,
        label="Burned",
    )
    ax.plot(
        u["rank"].astype(int),
        u[metric_col].astype(float),
        color="#1e90ff",
        linewidth=2,
        label="Undisturbed",
    )
    ax.set_xlabel(xlabel)
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description=(
            "Compare burned vs undisturbed peakflow 'hydrograph shape' proxies by date using WEPPcloud Query Engine datasets "
            "(EBE peak+volume, chan.out time-to-peak, PASS hillslope duration/components)."
        )
    )
    parser.add_argument("--base-url", default="https://wc.bearhive.duckdns.org/query-engine", help="Query Engine base URL")
    parser.add_argument("--runid", required=True, help="WEPPcloud run id (e.g., upset-reckoning)")
    parser.add_argument("--scenario", default="undisturbed", help="Scenario name under _pups/omni/scenarios/<scenario>")
    parser.add_argument("--top-n", type=int, default=30, help="Top N peakflow days to analyze (default: 30)")
    parser.add_argument("--out-dir", default="hydrograph_shape_compare_out", help="Output directory")
    args = parser.parse_args(argv)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    client = QueryEngineClient(base_url=str(args.base_url))

    run_slug = str(args.runid).strip("/")
    scenario = str(args.scenario).strip("/")

    burned_ebe_peak = _ebe_top_events(
        client, run_slug=run_slug, scenario=None, top_n=int(args.top_n), order_by_col="peak_runoff"
    )
    undisturbed_ebe_peak = _ebe_top_events(
        client, run_slug=run_slug, scenario=scenario, top_n=int(args.top_n), order_by_col="peak_runoff"
    )

    burned_ebe_vol = _ebe_top_events(
        client, run_slug=run_slug, scenario=None, top_n=int(args.top_n), order_by_col="runoff_volume"
    )
    undisturbed_ebe_vol = _ebe_top_events(
        client, run_slug=run_slug, scenario=scenario, top_n=int(args.top_n), order_by_col="runoff_volume"
    )

    burned_days = sorted(set(int(x) for x in burned_ebe_peak["sim_day_index"].dropna().tolist()))
    undisturbed_days = sorted(set(int(x) for x in undisturbed_ebe_peak["sim_day_index"].dropna().tolist()))
    all_days = sorted(set(burned_days + undisturbed_days))

    burned_chan = _chan_peaks_for_days(client, run_slug=run_slug, scenario=None)
    undisturbed_chan = _chan_peaks_for_days(client, run_slug=run_slug, scenario=scenario)

    burned_pass = _pass_event_diagnostics_for_days(client, run_slug=run_slug, scenario=None, sim_day_indexes=all_days)
    undisturbed_pass = _pass_event_diagnostics_for_days(
        client, run_slug=run_slug, scenario=scenario, sim_day_indexes=all_days
    )

    def merge_all(ebe: pd.DataFrame, chan: pd.DataFrame, passed: pd.DataFrame) -> pd.DataFrame:
        df = ebe.merge(
            chan[["year", "julian", "element_id", "time_to_peak_s", "peak_discharge_m3s"]],
            on=["year", "julian", "element_id"],
            how="left",
        )
        df = df.merge(
            passed[
                [
                    "sim_day_index",
                    "total_area_m2",
                    "contrib_area_m2",
                    "contrib_area_fraction",
                    "sum_hillslope_runvol_m3",
                    "sum_sbrunv_m3",
                    "sum_drrunv_m3",
                    "sum_gwbfv_m3",
                    "sum_gwdsv_m3",
                    "dur_area_weighted",
                    "peakro_area_weighted",
                    "dur_mean",
                    "peakro_mean",
                    "hillslope_rows",
                    "subsurface_fraction_of_runvol",
                    "drain_fraction_of_runvol",
                ]
            ],
            on=["sim_day_index"],
            how="left",
        )

        # Derived “shape/intensity” proxies.
        df["peak_to_volume_1_per_s"] = df["peak_runoff"].astype(float) / df["runoff_volume"].astype(float).where(lambda s: s != 0.0)
        dur_hours = df["dur_area_weighted"].astype(float) / 3600.0
        df["approx_intensity_mm_per_hr"] = df["precip"].astype(float) / dur_hours.where(lambda s: s > 0.0)

        return df

    burned = merge_all(burned_ebe_peak, burned_chan, burned_pass).copy()
    undisturbed = merge_all(undisturbed_ebe_peak, undisturbed_chan, undisturbed_pass).copy()

    burned.to_csv(out_dir / "burned_top_events_with_diagnostics.csv", index=False)
    undisturbed.to_csv(out_dir / "undisturbed_top_events_with_diagnostics.csv", index=False)

    b = burned.rename(
        columns={
            "precip": "burned_precip",
            "runoff_volume": "burned_runoff_volume",
            "peak_runoff": "burned_peak_runoff",
            "effective_duration_hr": "burned_effective_duration_hr",
            "time_to_peak_s": "burned_time_to_peak_s",
            "dur_area_weighted": "burned_dur_area_weighted",
            "peakro_area_weighted": "burned_peakro_area_weighted",
            "contrib_area_fraction": "burned_contrib_area_fraction",
            "subsurface_fraction_of_runvol": "burned_subsurface_fraction_of_runvol",
            "drain_fraction_of_runvol": "burned_drain_fraction_of_runvol",
            "approx_intensity_mm_per_hr": "burned_approx_intensity_mm_per_hr",
            "peak_to_volume_1_per_s": "burned_peak_to_volume_1_per_s",
        }
    )
    u = undisturbed.rename(
        columns={
            "precip": "undisturbed_precip",
            "runoff_volume": "undisturbed_runoff_volume",
            "peak_runoff": "undisturbed_peak_runoff",
            "effective_duration_hr": "undisturbed_effective_duration_hr",
            "time_to_peak_s": "undisturbed_time_to_peak_s",
            "dur_area_weighted": "undisturbed_dur_area_weighted",
            "peakro_area_weighted": "undisturbed_peakro_area_weighted",
            "contrib_area_fraction": "undisturbed_contrib_area_fraction",
            "subsurface_fraction_of_runvol": "undisturbed_subsurface_fraction_of_runvol",
            "drain_fraction_of_runvol": "undisturbed_drain_fraction_of_runvol",
            "approx_intensity_mm_per_hr": "undisturbed_approx_intensity_mm_per_hr",
            "peak_to_volume_1_per_s": "undisturbed_peak_to_volume_1_per_s",
        }
    )

    comparison = pd.merge(
        u[
            [
                "sim_day_index",
                "date",
                "undisturbed_precip",
                "undisturbed_runoff_volume",
                "undisturbed_peak_runoff",
                "undisturbed_effective_duration_hr",
                "undisturbed_time_to_peak_s",
                "undisturbed_dur_area_weighted",
                "undisturbed_peakro_area_weighted",
                "undisturbed_contrib_area_fraction",
                "undisturbed_subsurface_fraction_of_runvol",
                "undisturbed_drain_fraction_of_runvol",
                "undisturbed_approx_intensity_mm_per_hr",
                "undisturbed_peak_to_volume_1_per_s",
            ]
        ],
        b[
            [
                "sim_day_index",
                "burned_precip",
                "burned_runoff_volume",
                "burned_peak_runoff",
                "burned_effective_duration_hr",
                "burned_time_to_peak_s",
                "burned_dur_area_weighted",
                "burned_peakro_area_weighted",
                "burned_contrib_area_fraction",
                "burned_subsurface_fraction_of_runvol",
                "burned_drain_fraction_of_runvol",
                "burned_approx_intensity_mm_per_hr",
                "burned_peak_to_volume_1_per_s",
            ]
        ],
        on="sim_day_index",
        how="outer",
    ).sort_values("date")

    comparison["peak_diff_undist_minus_burned"] = (
        comparison["undisturbed_peak_runoff"].astype(float) - comparison["burned_peak_runoff"].astype(float)
    )
    comparison["runoff_vol_diff_undist_minus_burned"] = (
        comparison["undisturbed_runoff_volume"].astype(float) - comparison["burned_runoff_volume"].astype(float)
    )
    comparison["effective_duration_hr_diff_undist_minus_burned"] = (
        comparison["undisturbed_effective_duration_hr"].astype(float)
        - comparison["burned_effective_duration_hr"].astype(float)
    )

    # “Undisturbed higher peak with similar/lower volume” flag (<= 5% higher volume).
    denom = comparison["burned_runoff_volume"].astype(float).where(lambda s: s != 0, other=pd.NA)
    comparison["undisturbed_volume_ratio_to_burned"] = comparison["undisturbed_runoff_volume"].astype(float) / denom
    comparison["flag_peak_higher_volume_not_higher"] = (
        (comparison["peak_diff_undist_minus_burned"] > 0)
        & ((comparison["undisturbed_volume_ratio_to_burned"].isna()) | (comparison["undisturbed_volume_ratio_to_burned"] <= 1.05))
    )

    comparison.to_csv(out_dir / "top_events_hydroshape_comparison.csv", index=False)

    _plot_peak_vs_volume(
        out_path=out_dir / "peak_vs_volume_scatter_topN.png",
        burned=burned,
        undisturbed=undisturbed,
        title="Top-N events: peak discharge vs runoff volume",
    )

    _plot_metric_vs_rank(
        out_path=out_dir / "runoff_volume_vs_rank_topN.png",
        burned=burned_ebe_vol,
        undisturbed=undisturbed_ebe_vol,
        metric_col="runoff_volume",
        rank_by_col="runoff_volume",
        xlabel="Event rank (1 = largest runoff volume)",
        ylabel="Runoff volume (m³)",
        title="Runoff volume vs event rank (top N by runoff volume)",
    )
    _plot_metric_vs_rank(
        out_path=out_dir / "peak_discharge_vs_rank_topN.png",
        burned=burned,
        undisturbed=undisturbed,
        metric_col="peak_runoff",
        rank_by_col="peak_runoff",
        xlabel="Event rank (1 = largest peak discharge)",
        ylabel="Peak discharge (m³/s)",
        title="Peak discharge vs event rank (top N by peak discharge)",
    )

    _plot_proxy_hydrographs(
        out_path=out_dir / "proxy_hydrographs_top.png",
        comparison=comparison[comparison["flag_peak_higher_volume_not_higher"].fillna(False)],
        title="Proxy hydrographs (triangle from runoff volume + peak, with chan.out time-to-peak)",
        max_plots=8,
    )

    meta = {
        "runid": str(args.runid),
        "scenario": str(args.scenario),
        "top_n": int(args.top_n),
        "note": (
            "These are proxy hydrographs (triangle assumption) using only event runoff volume, peak discharge, "
            "and time-to-peak from chan.out. They are meant for quick interpretation when full intra-storm "
            "hydrographs are not available."
        ),
    }
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
