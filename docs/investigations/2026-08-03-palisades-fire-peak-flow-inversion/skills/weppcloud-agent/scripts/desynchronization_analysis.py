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
    max_retries: int = 10

    def _url(self, path: str) -> str:
        return f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"

    def query(self, run_slug: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = self._url(f"runs/{run_slug}/query")
        last_error: str | None = None
        for attempt in range(int(self.max_retries)):
            try:
                resp = requests.post(url, json=payload, timeout=self.timeout_s, headers={"Connection": "close"})
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


def _parse_ids(raw: str) -> list[int]:
    s = raw.replace(",", " ").strip()
    toks = [t for t in s.split() if t]
    return [int(t) for t in toks]


def _topaz_to_wepp_channels(
    client: QueryEngineClient,
    *,
    run_slug: str,
    topaz_ids: list[int],
) -> pd.DataFrame:
    payload = {
        "datasets": [{"path": "watershed/channels.parquet", "alias": "c"}],
        "columns": ["c.topaz_id", "c.wepp_id", "c.order", "c.length", "c.slope_scalar", "c.elevation"],
        "filters": [{"column": "c.topaz_id", "operator": "IN", "value": [int(x) for x in topaz_ids]}],
        "order_by": ["c.topaz_id ASC"],
        "limit": 10000,
        "include_schema": False,
    }
    df = pd.DataFrame(client.query(run_slug, payload).get("records", []))
    if df.empty:
        raise ValueError("No channel mapping rows returned for requested TOPAZ IDs.")
    df["topaz_id"] = df["topaz_id"].astype(int)
    df["wepp_id"] = df["wepp_id"].astype(int)
    df["elevation"] = df["elevation"].astype(float)
    return df


def _ebe_top_n_outlet(
    client: QueryEngineClient,
    *,
    run_slug: str,
    scenario: str | None,
    outlet_wepp_id: int,
    top_n: int,
) -> pd.DataFrame:
    payload: dict[str, Any] = {
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
        "filters": [{"column": "e.element_id", "operator": "=", "value": int(outlet_wepp_id)}],
        "order_by": ["e.peak_runoff DESC", "e.sim_day_index ASC"],
        "limit": int(top_n),
        "include_schema": False,
    }
    df = pd.DataFrame(client.query(run_slug, payload).get("records", []))
    if df.empty:
        raise ValueError("No EBE rows returned for outlet.")
    df["date"] = pd.to_datetime(
        df[["year", "month", "day_of_month"]].rename(columns={"day_of_month": "day"}),
        errors="coerce",
    )
    return df


def _tc_out_day(
    client: QueryEngineClient,
    *,
    run_slug: str,
    year: int,
    julian: int,
) -> dict[str, float] | None:
    payload = {
        "datasets": [{"path": "wepp/output/interchange/tc_out.parquet", "alias": "t"}],
        "columns": [
            "t.year",
            "t.julian",
            't."Time of Conc (hr)" AS tc_hr',
            't."Storm Duration (hr)" AS storm_dur_hr',
            't."Storm Peak (hr)" AS storm_peak_hr',
        ],
        "filters": [
            {"column": "t.year", "operator": "=", "value": int(year)},
            {"column": "t.julian", "operator": "=", "value": int(julian)},
        ],
        "limit": 5,
        "include_schema": False,
    }
    df = pd.DataFrame(client.query(run_slug, payload).get("records", []))
    if df.empty:
        return None
    r = df.iloc[0]
    return {
        "tc_hr": float(r["tc_hr"]),
        "storm_dur_hr": float(r["storm_dur_hr"]),
        "storm_peak_hr": float(r["storm_peak_hr"]),
    }


def _soil_aw_day(
    client: QueryEngineClient,
    *,
    run_slug: str,
    scenario: str | None,
    year: int,
    julian: int,
) -> dict[str, float] | None:
    payload: dict[str, Any] = {
        **({"scenario": scenario} if scenario else {}),
        "datasets": [
            {"path": "wepp/output/interchange/soil_pw0.parquet", "alias": "s"},
            {"path": "wepp/output/interchange/pass_pw0.metadata.parquet", "alias": "m"},
        ],
        "joins": [{"left": "s", "right": "m", "on": "wepp_id", "type": "inner"}],
        "columns": ["s.year", "s.julian"],
        "filters": [
            {"column": "s.year", "operator": "=", "value": int(year)},
            {"column": "s.julian", "operator": "=", "value": int(julian)},
        ],
        "group_by": ["s.year", "s.julian"],
        "aggregations": [
            {"sql": "SUM(m.area)", "alias": "area_m2"},
            {"sql": "SUM(s.Saturation * m.area) / NULLIF(SUM(m.area),0)", "alias": "Saturation_aw"},
            {"sql": "SUM(s.TSW * m.area) / NULLIF(SUM(m.area),0)", "alias": "TSW_aw"},
            {"sql": "SUM(s.Suct * m.area) / NULLIF(SUM(m.area),0)", "alias": "Suct_aw"},
        ],
        "limit": 10,
        "include_schema": False,
    }
    df = pd.DataFrame(client.query(run_slug, payload).get("records", []))
    if df.empty:
        return None
    r = df.iloc[0]
    return {
        "Saturation_aw": float(r["Saturation_aw"]),
        "TSW_aw": float(r["TSW_aw"]),
        "Suct_aw": float(r["Suct_aw"]),
    }


def _chan_out_timeseries(
    client: QueryEngineClient,
    *,
    run_slug: str,
    scenario: str | None,
    year: int,
    julian: int,
    wepp_ids: list[int],
) -> pd.DataFrame:
    payload: dict[str, Any] = {
        **({"scenario": scenario} if scenario else {}),
        "datasets": [{"path": "wepp/output/interchange/chan.out.parquet", "alias": "c"}],
        "columns": [
            "c.year",
            "c.month",
            "c.day_of_month",
            "c.julian",
            "c.Elmt_ID AS wepp_id",
            'c."Time (s)" AS t_s',
            'c."Peak_Discharge (m^3/s)" AS q_m3s',
        ],
        "filters": [
            {"column": "c.year", "operator": "=", "value": int(year)},
            {"column": "c.julian", "operator": "=", "value": int(julian)},
            {"column": "c.Elmt_ID", "operator": "IN", "value": [int(x) for x in wepp_ids]},
        ],
        "order_by": ["wepp_id ASC", "t_s ASC"],
        "limit": 4000000,
        "include_schema": False,
    }
    df = pd.DataFrame(client.query(run_slug, payload).get("records", []))
    if df.empty:
        raise ValueError(
            "No chan.out rows returned for this day/ids. "
            "Confirm you reran with ichout=3 and dtchr=300 for the requested channels."
        )
    df["wepp_id"] = df["wepp_id"].astype(int)
    df["t_s"] = df["t_s"].astype(float)
    df["q_m3s"] = df["q_m3s"].astype(float)
    df["t_hr"] = df["t_s"] / 3600.0
    return df


def _hydro_metrics(ts: pd.DataFrame) -> dict[str, float]:
    t = ts["t_hr"].to_numpy(dtype=float)
    q = ts["q_m3s"].to_numpy(dtype=float)
    if len(t) < 2 or float(np.nanmax(q)) <= 0.0:
        return {"qpk": float(np.nanmax(q) if len(q) else 0.0), "tpk_hr": float(t[0] if len(t) else 0.0)}

    i_pk = int(np.nanargmax(q))
    qpk = float(q[i_pk])
    tpk = float(t[i_pk])

    half = 0.5 * qpk
    mask = q >= half
    width50 = float(t[mask][-1] - t[mask][0]) if mask.any() else float("nan")

    ten = 0.1 * qpk
    above10 = np.where(q >= ten)[0]
    t10 = float(t[int(above10[0])]) if len(above10) else float("nan")
    rise = float(tpk - t10) if np.isfinite(t10) else float("nan")

    # NumPy 2.x removed `np.trapz`; use `trapezoid`.
    v = float(np.trapezoid(q, t))
    centroid = float(np.trapezoid(q * t, t) / v) if v > 0 else float("nan")

    return {"qpk": qpk, "tpk_hr": tpk, "width50_hr": width50, "rise10_hr": rise, "centroid_hr": centroid}


def _value_at_time(ts: pd.DataFrame, t_hr: float) -> float:
    if ts.empty:
        return float("nan")
    idx = (ts["t_hr"].astype(float) - float(t_hr)).abs().idxmin()
    return float(ts.loc[idx, "q_m3s"])


def _plot_event_overlay(
    *,
    out_path: Path,
    date: str,
    mapping: pd.DataFrame,
    burned_ts: pd.DataFrame,
    undist_ts: pd.DataFrame,
    tc: dict[str, float] | None,
    soil_b: dict[str, float] | None,
    soil_u: dict[str, float] | None,
) -> None:
    m = mapping.sort_values("elevation", ascending=False).copy()
    ids = [int(x) for x in m["wepp_id"].tolist()]

    fig, axes = plt.subplots(len(ids), 1, figsize=(10.6, 7.8), sharex=True, constrained_layout=True)
    if len(ids) == 1:
        axes = [axes]

    for ax, wepp_id in zip(axes, ids, strict=False):
        b = burned_ts[burned_ts["wepp_id"] == wepp_id].copy()
        u = undist_ts[undist_ts["wepp_id"] == wepp_id].copy()

        ax.plot(b["t_hr"], b["q_m3s"], color="#ff3b30", linewidth=2, label="Burned")
        ax.plot(u["t_hr"], u["q_m3s"], color="#1e90ff", linewidth=2, label="Undisturbed")

        if not b.empty and float(b["q_m3s"].max()) > 0:
            i = int(b["q_m3s"].astype(float).idxmax())
            ax.scatter([float(b.loc[i, "t_hr"])], [float(b.loc[i, "q_m3s"])], color="#ff3b30", s=30, zorder=5)
        if not u.empty and float(u["q_m3s"].max()) > 0:
            i = int(u["q_m3s"].astype(float).idxmax())
            ax.scatter([float(u.loc[i, "t_hr"])], [float(u.loc[i, "q_m3s"])], color="#1e90ff", s=30, zorder=5)

        if tc is not None:
            ax.axvline(float(tc["storm_peak_hr"]), color="black", alpha=0.25, linewidth=1.5, linestyle="--")

        meta = m[m["wepp_id"] == wepp_id].iloc[0].to_dict()
        ax.set_title(f"TOPAZ {int(meta['topaz_id'])} (WEPP {wepp_id})  elev={float(meta['elevation']):0.1f} m")
        ax.set_ylabel("Q (m³/s)")
        ax.grid(True, alpha=0.25)

    axes[-1].set_xlabel("Time since day start (hr)")
    axes[0].legend(loc="upper right")

    lines: list[str] = [f"Date {date}"]
    if tc is not None:
        lines.append(
            f"tc_out: Tc={tc['tc_hr']:.2f} hr, dur={tc['storm_dur_hr']:.2f} hr, peak={tc['storm_peak_hr']:.2f} hr"
        )
    if soil_b is not None and soil_u is not None:
        lines.append(f"Soil aw Sat: burned={soil_b['Saturation_aw']:.3f}, undist={soil_u['Saturation_aw']:.3f}")
        lines.append(f"Soil aw TSW: burned={soil_b['TSW_aw']:.2f} mm, undist={soil_u['TSW_aw']:.2f} mm")
        lines.append(f"Soil aw Suct: burned={soil_b['Suct_aw']:.3g} mm, undist={soil_u['Suct_aw']:.3g} mm")

    fig.suptitle("\n".join(lines), fontsize=12)
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


def _to_latex_table(df: pd.DataFrame, caption: str, label: str) -> str:
    def tex_escape(s: str) -> str:
        return (
            str(s)
            .replace("\\", "\\textbackslash{}")
            .replace("&", "\\&")
            .replace("%", "\\%")
            .replace("_", "\\_")
        )

    cols = list(df.columns)
    out: list[str] = []
    out.append("\\begin{table}[H]")
    out.append("  \\centering")
    out.append(f"  \\caption{{{caption}}}")
    out.append(f"  \\label{{{label}}}")
    out.append("  \\resizebox{\\textwidth}{!}{%")
    out.append("  \\begin{tabular}{%s}" % (" ".join(["l"] * 2 + ["r"] * (len(cols) - 2))))
    out.append("    \\toprule")
    out.append("    " + " & ".join(tex_escape(c) for c in cols) + " \\\\")
    out.append("    \\midrule")
    for _, row in df.iterrows():
        parts: list[str] = []
        for c in cols:
            v = row[c]
            if isinstance(v, float) or isinstance(v, np.floating):
                parts.append(f"{float(v):0.5g}")
            else:
                parts.append(tex_escape(v))
        out.append("    " + " & ".join(parts) + " \\\\")
    out.append("    \\bottomrule")
    out.append("  \\end{tabular}}")
    out.append("\\end{table}")
    out.append("")
    return "\n".join(out)


def _fig_list_tex(df: pd.DataFrame, title: str) -> str:
    out: list[str] = []
    out.append(f"\\subsubsection{{{title}}}")
    for _, row in df.iterrows():
        path = str(row["plot"]).replace("_", "\\_")
        date = str(row["date"]).replace("_", "\\_")
        out.append("\\begin{figure}[H]")
        out.append("  \\centering")
        out.append(f"  \\includegraphics[width=0.98\\textwidth]{{{path}}}")
        out.append(f"  \\caption{{Channel hydrograph overlays (TOPAZ 604/324/24) for {date}.}}")
        out.append("\\end{figure}")
        out.append("")
    return "\n".join(out)


def _ebe_outlet_for_sim_days(
    client: QueryEngineClient,
    *,
    run_slug: str,
    scenario: str | None,
    outlet_wepp_id: int,
    sim_day_indexes: list[int],
) -> pd.DataFrame:
    if not sim_day_indexes:
        return pd.DataFrame()
    payload: dict[str, Any] = {
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
        "filters": [
            {"column": "e.element_id", "operator": "=", "value": int(outlet_wepp_id)},
            {"column": "e.sim_day_index", "operator": "IN", "value": [int(x) for x in sim_day_indexes]},
        ],
        "order_by": ["e.sim_day_index ASC"],
        "limit": 5000,
        "include_schema": False,
    }
    df = pd.DataFrame(client.query(run_slug, payload).get("records", []))
    if df.empty:
        return df
    df["date"] = pd.to_datetime(
        df[["year", "month", "day_of_month"]].rename(columns={"day_of_month": "day"}),
        errors="coerce",
    )
    return df


def main() -> int:
    ap = argparse.ArgumentParser(description="Spatial heterogeneity / desynchronization analysis using chan.out sub-daily hydrographs")
    ap.add_argument("--base-url", default="https://wc.bearhive.duckdns.org/query-engine")
    ap.add_argument("--runid", required=True)
    ap.add_argument("--undisturbed-scenario", default="undisturbed")
    ap.add_argument("--topaz-ids", default="604 324 24")
    ap.add_argument("--outlet-topaz-id", type=int, default=24)
    ap.add_argument("--top-n", type=int, default=30)
    ap.add_argument("--out-dir", type=Path, default=Path("tmp_upset_reckoning_desync"))
    args = ap.parse_args()

    run_slug = str(args.runid).strip("/")
    und_scn = str(args.undisturbed_scenario).strip("/") or None

    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    client = QueryEngineClient(base_url=str(args.base_url))
    topaz_ids = _parse_ids(str(args.topaz_ids))

    mapping = _topaz_to_wepp_channels(client, run_slug=run_slug, topaz_ids=topaz_ids)
    outlet_wepp_id = int(mapping[mapping["topaz_id"] == int(args.outlet_topaz_id)].iloc[0]["wepp_id"])
    wepp_ids = [int(x) for x in mapping["wepp_id"].tolist()]

    burned_top = _ebe_top_n_outlet(
        client, run_slug=run_slug, scenario=None, outlet_wepp_id=outlet_wepp_id, top_n=int(args.top_n)
    )
    und_top = _ebe_top_n_outlet(
        client, run_slug=run_slug, scenario=und_scn, outlet_wepp_id=outlet_wepp_id, top_n=int(args.top_n)
    )

    union_sim_days = sorted(
        set(burned_top["sim_day_index"].astype(int).tolist()) | set(und_top["sim_day_index"].astype(int).tolist())
    )

    burned_union = _ebe_outlet_for_sim_days(
        client,
        run_slug=run_slug,
        scenario=None,
        outlet_wepp_id=outlet_wepp_id,
        sim_day_indexes=union_sim_days,
    )
    und_union = _ebe_outlet_for_sim_days(
        client,
        run_slug=run_slug,
        scenario=und_scn,
        outlet_wepp_id=outlet_wepp_id,
        sim_day_indexes=union_sim_days,
    )

    b = burned_union.rename(
        columns={
            "precip": "burned_precip",
            "runoff_volume": "burned_runoff_volume",
            "peak_runoff": "burned_peak_runoff",
            "year": "burned_year",
            "month": "burned_month",
            "day_of_month": "burned_day_of_month",
            "julian": "burned_julian",
            "date": "burned_date",
        }
    )
    u = und_union.rename(
        columns={
            "precip": "undisturbed_precip",
            "runoff_volume": "undisturbed_runoff_volume",
            "peak_runoff": "undisturbed_peak_runoff",
            "year": "undisturbed_year",
            "month": "undisturbed_month",
            "day_of_month": "undisturbed_day_of_month",
            "julian": "undisturbed_julian",
            "date": "undisturbed_date",
        }
    )

    comp = b[
        [
            "sim_day_index",
            "burned_date",
            "burned_year",
            "burned_julian",
            "burned_precip",
            "burned_runoff_volume",
            "burned_peak_runoff",
        ]
    ].merge(
        u[
            [
                "sim_day_index",
                "undisturbed_date",
                "undisturbed_year",
                "undisturbed_julian",
                "undisturbed_precip",
                "undisturbed_runoff_volume",
                "undisturbed_peak_runoff",
            ]
        ],
        on="sim_day_index",
        how="outer",
    )
    comp["date"] = comp["burned_date"].combine_first(comp["undisturbed_date"])
    comp["year"] = comp["burned_year"].combine_first(comp["undisturbed_year"])
    comp["julian"] = comp["burned_julian"].combine_first(comp["undisturbed_julian"])
    comp["V_ratio"] = comp["undisturbed_runoff_volume"].astype(float) / comp["burned_runoff_volume"].astype(float)
    comp["Qp_ratio"] = comp["undisturbed_peak_runoff"].astype(float) / comp["burned_peak_runoff"].astype(float)
    comp["flag_peak_higher_volume_not_higher"] = (
        (comp["undisturbed_peak_runoff"].astype(float) > comp["burned_peak_runoff"].astype(float))
        & ((comp["V_ratio"].isna()) | (comp["V_ratio"].astype(float) <= 1.05))
    )
    comp = comp.dropna(subset=["date"]).sort_values("date").reset_index(drop=True)
    comp.to_csv(out_dir / "event_union_topN.csv", index=False)

    flagged = comp[(comp["flag_peak_higher_volume_not_higher"].fillna(False)) & comp["burned_peak_runoff"].notna() & comp["undisturbed_peak_runoff"].notna()].copy()
    nonflag = comp[(~comp["flag_peak_higher_volume_not_higher"].fillna(False)) & comp["burned_peak_runoff"].notna() & comp["undisturbed_peak_runoff"].notna()].copy()

    # Match one control per flagged by nearest burned_peak_runoff.
    controls: list[pd.Series] = []
    if not flagged.empty and not nonflag.empty:
        nonflag = nonflag.sort_values("burned_peak_runoff").copy()
        used: set[int] = set()
        for _, fr in flagged.iterrows():
            target = float(fr["burned_peak_runoff"])
            diffs = (nonflag["burned_peak_runoff"].astype(float) - target).abs()
            for idx in diffs.sort_values().index.tolist():
                if int(idx) in used:
                    continue
                used.add(int(idx))
                controls.append(nonflag.loc[idx])
                break
    controls_df = pd.DataFrame(controls)

    flagged.to_csv(out_dir / "flagged_events.csv", index=False)
    controls_df.to_csv(out_dir / "control_events_matched.csv", index=False)

    upstream_wepp_ids = mapping.sort_values("elevation", ascending=False)["wepp_id"].astype(int).tolist()[:2]
    outlet_wepp_id = int(mapping.sort_values("elevation", ascending=True)["wepp_id"].astype(int).tolist()[0])
    top_wepp_id = int(upstream_wepp_ids[0]) if len(upstream_wepp_ids) >= 1 else int(outlet_wepp_id)
    mid_wepp_id = int(upstream_wepp_ids[1]) if len(upstream_wepp_ids) >= 2 else int(outlet_wepp_id)

    rows: list[dict[str, Any]] = []

    def analyze_one(row: pd.Series, group: str) -> None:
        date = str(pd.to_datetime(row["date"]).date())
        year = int(float(row["year"]))
        julian = int(float(row["julian"]))

        try:
            burned_ts = _chan_out_timeseries(
                client, run_slug=run_slug, scenario=None, year=year, julian=julian, wepp_ids=wepp_ids
            )
            und_ts = _chan_out_timeseries(
                client, run_slug=run_slug, scenario=und_scn, year=year, julian=julian, wepp_ids=wepp_ids
            )
        except ValueError as exc:
            print(f"[warn] {date}: skipping (missing chan.out rows): {exc}")
            return

        tc = _tc_out_day(client, run_slug=run_slug, year=year, julian=julian)
        soil_b = _soil_aw_day(client, run_slug=run_slug, scenario=None, year=year, julian=julian)
        soil_u = _soil_aw_day(client, run_slug=run_slug, scenario=und_scn, year=year, julian=julian)

        metrics: dict[tuple[str, int], dict[str, float]] = {}
        for wepp_id in wepp_ids:
            metrics[("burned", wepp_id)] = _hydro_metrics(burned_ts[burned_ts["wepp_id"] == wepp_id])
            metrics[("undisturbed", wepp_id)] = _hydro_metrics(und_ts[und_ts["wepp_id"] == wepp_id])

        def sync_for(scn: str, ts: pd.DataFrame) -> dict[str, float]:
            t_top = float(metrics[(scn, int(top_wepp_id))].get("tpk_hr", float("nan")))
            t_mid = float(metrics[(scn, int(mid_wepp_id))].get("tpk_hr", float("nan")))
            t_out = float(metrics[(scn, int(outlet_wepp_id))].get("tpk_hr", float("nan")))

            spread_up = float(abs(t_top - t_mid)) if np.isfinite(t_top) and np.isfinite(t_mid) else float("nan")
            lag_top_out = float(t_out - t_top) if np.isfinite(t_out) and np.isfinite(t_top) else float("nan")
            lag_mid_out = float(t_out - t_mid) if np.isfinite(t_out) and np.isfinite(t_mid) else float("nan")

            fracs: list[float] = []
            for w in upstream_wepp_ids:
                ts_w = ts[ts["wepp_id"] == int(w)]
                q_at = _value_at_time(ts_w, t_out)
                q_pk = metrics[(scn, int(w))]["qpk"]
                fracs.append(float(q_at / q_pk) if q_pk > 0 else float("nan"))
            simult = float(np.nanmean(fracs)) if fracs else float("nan")
            width50_out = float(metrics[(scn, int(outlet_wepp_id))].get("width50_hr", float("nan")))
            rise10_out = float(metrics[(scn, int(outlet_wepp_id))].get("rise10_hr", float("nan")))
            return {
                "upstream_peak_spread_hr": spread_up,
                "lag_top_to_out_hr": lag_top_out,
                "lag_mid_to_out_hr": lag_mid_out,
                "upstream_simult_at_outlet_peak": simult,
                "outlet_width50_hr": width50_out,
                "outlet_rise10_hr": rise10_out,
                "tpk_top_hr": t_top,
                "tpk_mid_hr": t_mid,
                "tpk_out_hr": t_out,
                "qpk_top": float(metrics[(scn, int(top_wepp_id))].get("qpk", float("nan"))),
                "qpk_mid": float(metrics[(scn, int(mid_wepp_id))].get("qpk", float("nan"))),
                "qpk_out": float(metrics[(scn, int(outlet_wepp_id))].get("qpk", float("nan"))),
            }

        sync_b = sync_for("burned", burned_ts)
        sync_u = sync_for("undisturbed", und_ts)

        plot_path = out_dir / f"{group}_{date}_chan_wave_overlay.png"
        _plot_event_overlay(
            out_path=plot_path,
            date=date,
            mapping=mapping,
            burned_ts=burned_ts,
            undist_ts=und_ts,
            tc=tc,
            soil_b=soil_b,
            soil_u=soil_u,
        )

        out_qb = float(row.get("burned_peak_runoff"))
        out_qu = float(row.get("undisturbed_peak_runoff"))
        out_vb = float(row.get("burned_runoff_volume"))
        out_vu = float(row.get("undisturbed_runoff_volume"))

        rows.append(
            {
                "group": group,
                "date": date,
                "burned_Qp_out": out_qb,
                "undist_Qp_out": out_qu,
                "Qp_ratio": out_qu / out_qb if out_qb > 0 else float("nan"),
                "V_ratio": out_vu / out_vb if out_vb > 0 else float("nan"),
                "burned_upstream_peak_spread_hr": sync_b["upstream_peak_spread_hr"],
                "undist_upstream_peak_spread_hr": sync_u["upstream_peak_spread_hr"],
                "delta_upstream_peak_spread_hr": float(sync_u["upstream_peak_spread_hr"]) - float(
                    sync_b["upstream_peak_spread_hr"]
                ),
                "burned_upstream_simult_at_outlet_peak": sync_b["upstream_simult_at_outlet_peak"],
                "undist_upstream_simult_at_outlet_peak": sync_u["upstream_simult_at_outlet_peak"],
                "delta_upstream_simult_at_outlet_peak": float(sync_u["upstream_simult_at_outlet_peak"]) - float(
                    sync_b["upstream_simult_at_outlet_peak"]
                ),
                "burned_lag_top_to_out_hr": sync_b["lag_top_to_out_hr"],
                "undist_lag_top_to_out_hr": sync_u["lag_top_to_out_hr"],
                "burned_lag_mid_to_out_hr": sync_b["lag_mid_to_out_hr"],
                "undist_lag_mid_to_out_hr": sync_u["lag_mid_to_out_hr"],
                "burned_outlet_width50_hr": sync_b["outlet_width50_hr"],
                "undist_outlet_width50_hr": sync_u["outlet_width50_hr"],
                "delta_outlet_width50_hr": float(sync_u["outlet_width50_hr"]) - float(sync_b["outlet_width50_hr"]),
                "burned_outlet_rise10_hr": sync_b["outlet_rise10_hr"],
                "undist_outlet_rise10_hr": sync_u["outlet_rise10_hr"],
                "delta_outlet_rise10_hr": float(sync_u["outlet_rise10_hr"]) - float(sync_b["outlet_rise10_hr"]),
                "burned_tpk_top_hr": sync_b["tpk_top_hr"],
                "burned_tpk_mid_hr": sync_b["tpk_mid_hr"],
                "burned_tpk_out_hr": sync_b["tpk_out_hr"],
                "undist_tpk_top_hr": sync_u["tpk_top_hr"],
                "undist_tpk_mid_hr": sync_u["tpk_mid_hr"],
                "undist_tpk_out_hr": sync_u["tpk_out_hr"],
                "soilSat_b": soil_b["Saturation_aw"] if soil_b else float("nan"),
                "soilSat_u": soil_u["Saturation_aw"] if soil_u else float("nan"),
                "soilTSW_b": soil_b["TSW_aw"] if soil_b else float("nan"),
                "soilTSW_u": soil_u["TSW_aw"] if soil_u else float("nan"),
                "soilSuct_b": soil_b["Suct_aw"] if soil_b else float("nan"),
                "soilSuct_u": soil_u["Suct_aw"] if soil_u else float("nan"),
                "tc_hr": tc["tc_hr"] if tc else float("nan"),
                "storm_peak_hr": tc["storm_peak_hr"] if tc else float("nan"),
                "storm_dur_hr": tc["storm_dur_hr"] if tc else float("nan"),
                "plot": plot_path.as_posix(),
            }
        )

    for _, r in flagged.iterrows():
        analyze_one(r, "flagged")
    for _, r in controls_df.iterrows():
        analyze_one(r, "control")

    metrics_df = pd.DataFrame(rows)
    metrics_df.to_csv(out_dir / "desync_event_metrics.csv", index=False)

    # Summary scatter
    if not metrics_df.empty:
        def scatter(xcol: str, ycol: str, xlabel: str, ylabel: str, title: str, fname: str) -> None:
            fig, ax = plt.subplots(figsize=(8.6, 5.2), constrained_layout=True)
            for g, color in [("flagged", "#6a5acd"), ("control", "#2e8b57")]:
                sub = metrics_df[metrics_df["group"] == g]
                ax.scatter(
                    sub[xcol].astype(float),
                    sub[ycol].astype(float),
                    s=55,
                    alpha=0.82,
                    label=g,
                    color=color,
                    edgecolor="white",
                    linewidth=0.6,
                )
            ax.set_xlabel(xlabel)
            ax.set_ylabel(ylabel)
            ax.set_title(title)
            ax.grid(True, alpha=0.25)
            ax.legend()
            fig.savefig(out_dir / fname, dpi=200)
            plt.close(fig)

        scatter(
            "undist_upstream_peak_spread_hr",
            "Qp_ratio",
            "Upstream peak-time spread |tpk(top)-tpk(mid)| (hr) (undisturbed)",
            "Outlet peak ratio Qp(undist)/Qp(burned)",
            "Peak increase vs upstream timing spread (diagnostic)",
            "qp_ratio_vs_upstream_spread.png",
        )
        scatter(
            "delta_upstream_peak_spread_hr",
            "Qp_ratio",
            "Δ upstream spread (undisturbed − burned) (hr)",
            "Outlet peak ratio Qp(undist)/Qp(burned)",
            "Peak increase vs change in upstream timing spread",
            "qp_ratio_vs_delta_upstream_spread.png",
        )
        scatter(
            "delta_upstream_simult_at_outlet_peak",
            "Qp_ratio",
            "Δ upstream simultaneity at outlet peak (undisturbed − burned)",
            "Outlet peak ratio Qp(undist)/Qp(burned)",
            "Peak increase vs change in simultaneity at outlet peak",
            "qp_ratio_vs_delta_simult.png",
        )
        scatter(
            "delta_outlet_width50_hr",
            "Qp_ratio",
            "Δ outlet width50 (undisturbed − burned) (hr)",
            "Outlet peak ratio Qp(undist)/Qp(burned)",
            "Peak increase vs change in outlet hydrograph width",
            "qp_ratio_vs_delta_width50.png",
        )

        # 1:1 comparisons (burned vs undisturbed)
        def one_to_one(xcol: str, ycol: str, xlabel: str, ylabel: str, title: str, fname: str) -> None:
            fig, ax = plt.subplots(figsize=(7.2, 5.6), constrained_layout=True)
            mn = float(
                np.nanmin(
                    np.concatenate(
                        [
                            metrics_df[xcol].astype(float).to_numpy(),
                            metrics_df[ycol].astype(float).to_numpy(),
                        ]
                    )
                )
            )
            mx = float(
                np.nanmax(
                    np.concatenate(
                        [
                            metrics_df[xcol].astype(float).to_numpy(),
                            metrics_df[ycol].astype(float).to_numpy(),
                        ]
                    )
                )
            )
            for g, color in [("flagged", "#6a5acd"), ("control", "#2e8b57")]:
                sub = metrics_df[metrics_df["group"] == g]
                ax.scatter(
                    sub[xcol].astype(float),
                    sub[ycol].astype(float),
                    s=55,
                    alpha=0.82,
                    label=g,
                    color=color,
                    edgecolor="white",
                    linewidth=0.6,
                )
            if np.isfinite(mn) and np.isfinite(mx) and mx > mn:
                ax.plot([mn, mx], [mn, mx], color="black", linewidth=1.2, alpha=0.5)
            ax.set_xlabel(xlabel)
            ax.set_ylabel(ylabel)
            ax.set_title(title)
            ax.grid(True, alpha=0.25)
            ax.legend()
            fig.savefig(out_dir / fname, dpi=200)
            plt.close(fig)

        one_to_one(
            "burned_outlet_width50_hr",
            "undist_outlet_width50_hr",
            "Burned outlet width50 (hr)",
            "Undisturbed outlet width50 (hr)",
            "Outlet hydrograph width: undisturbed vs burned",
            "outlet_width50_undist_vs_burned.png",
        )
        one_to_one(
            "burned_lag_top_to_out_hr",
            "undist_lag_top_to_out_hr",
            "Burned lag top→out (hr)",
            "Undisturbed lag top→out (hr)",
            "Translation lag (top→out): undisturbed vs burned",
            "lag_top_to_out_undist_vs_burned.png",
        )

        # Group summary table (median/mean)
        group_cols = [
            "Qp_ratio",
            "V_ratio",
            "burned_outlet_width50_hr",
            "undist_outlet_width50_hr",
            "delta_outlet_width50_hr",
            "delta_upstream_peak_spread_hr",
            "delta_upstream_simult_at_outlet_peak",
            "soilSat_b",
            "soilSat_u",
            "soilTSW_b",
            "soilTSW_u",
            "soilSuct_b",
            "soilSuct_u",
            "tc_hr",
            "storm_peak_hr",
            "storm_dur_hr",
        ]
        gsum = (
            metrics_df.groupby("group")[group_cols]
            .agg(["median", "mean"])
            .reset_index()
        )
        # Flatten columns for readability.
        gsum.columns = ["group"] + [f"{c}_{stat}" for c, stat in gsum.columns.tolist()[1:]]
        gsum.to_csv(out_dir / "desync_group_summary.csv", index=False)

        (out_dir / "desync_group_summary_table.tex").write_text(
            _to_latex_table(
                gsum,
                caption="Group summary statistics for flagged vs matched-control events (median and mean).",
                label="tab:desync_group_summary",
            ),
            encoding="utf-8",
        )

        table_cols = [
            "group",
            "date",
            "Qp_ratio",
            "V_ratio",
            "burned_upstream_peak_spread_hr",
            "undist_upstream_peak_spread_hr",
            "delta_upstream_peak_spread_hr",
            "burned_upstream_simult_at_outlet_peak",
            "undist_upstream_simult_at_outlet_peak",
            "delta_upstream_simult_at_outlet_peak",
            "burned_outlet_width50_hr",
            "undist_outlet_width50_hr",
            "delta_outlet_width50_hr",
        ]
        tab = metrics_df[table_cols].copy()
        (out_dir / "desync_metrics_table.tex").write_text(
            _to_latex_table(
                tab,
                caption="Desynchronization metrics on flagged vs matched-control events (channel hydrographs at TOPAZ 604/324/24).",
                label="tab:desync_metrics",
            ),
            encoding="utf-8",
        )
        (out_dir / "flagged_event_figures.tex").write_text(
            _fig_list_tex(metrics_df[metrics_df["group"] == "flagged"], "Flagged events"), encoding="utf-8"
        )
        (out_dir / "control_event_figures.tex").write_text(
            _fig_list_tex(metrics_df[metrics_df["group"] == "control"], "Matched-control events"), encoding="utf-8"
        )

    meta = {
        "runid": run_slug,
        "undisturbed_scenario": und_scn or "<default>",
        "topaz_ids": topaz_ids,
        "wepp_ids": wepp_ids,
        "outlet_wepp_id": outlet_wepp_id,
        "top_n": int(args.top_n),
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
