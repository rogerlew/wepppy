#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Iterable

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


def _parse_topaz_ids(raw: str) -> list[int]:
    s = raw.replace(",", " ").strip()
    toks = [t for t in s.split() if t]
    if not toks:
        return []
    ids = [int(t) for t in toks]
    return ids


def _topaz_to_wepp_ids(
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
    result = client.query(run_slug, payload)
    df = pd.DataFrame(result.get("records", []))
    if df.empty:
        raise ValueError("No matching channel rows found in watershed/channels.parquet for the requested TOPAZ IDs.")
    df["topaz_id"] = df["topaz_id"].astype(int)
    df["wepp_id"] = df["wepp_id"].astype(int)
    return df


def _sim_day_index_for_date(
    client: QueryEngineClient,
    *,
    run_slug: str,
    scenario: str | None,
    date: str,
    outlet_wepp_id: int,
) -> int:
    # Use EBE at the outlet element to find the unique sim_day_index for the date.
    # (sim_day_index is global across the run.)
    dt = pd.to_datetime(date).date()
    payload: dict[str, Any] = {
        **({"scenario": scenario} if scenario else {}),
        "datasets": [{"path": "wepp/output/interchange/ebe_pw0.parquet", "alias": "e"}],
        "columns": ["e.sim_day_index", "e.year", "e.month", "e.day_of_month"],
        "filters": [
            {"column": "e.year", "operator": "=", "value": int(dt.year)},
            {"column": "e.month", "operator": "=", "value": int(dt.month)},
            {"column": "e.day_of_month", "operator": "=", "value": int(dt.day)},
            {"column": "e.element_id", "operator": "=", "value": int(outlet_wepp_id)},
        ],
        "limit": 50,
        "include_schema": False,
    }
    result = client.query(run_slug, payload)
    df = pd.DataFrame(result.get("records", []))
    if df.empty:
        raise ValueError(f"No EBE row found for date={date} (scenario={scenario or '<default>'}).")
    sim_days = sorted(set(int(x) for x in df["sim_day_index"].dropna().tolist()))
    if len(sim_days) != 1:
        raise ValueError(f"Expected 1 sim_day_index for {date}, got {sim_days}")
    return int(sim_days[0])


def _chan_hydrograph(
    client: QueryEngineClient,
    *,
    run_slug: str,
    scenario: str | None,
    sim_day_index: int,
    wepp_ids: list[int],
) -> pd.DataFrame:
    payload: dict[str, Any] = {
        **({"scenario": scenario} if scenario else {}),
        "datasets": [{"path": "wepp/output/interchange/chan.out.parquet", "alias": "c"}],
        "columns": [
            "c.sim_day_index",
            "c.year",
            "c.month",
            "c.day_of_month",
            "c.julian",
            "c.Elmt_ID AS wepp_id",
            "c.Chan_ID AS chan_id",
            'c."Time (s)" AS t_s',
            'c."Peak_Discharge (m^3/s)" AS q_m3s',
        ],
        "filters": [
            {"column": "c.sim_day_index", "operator": "=", "value": int(sim_day_index)},
            {"column": "c.Elmt_ID", "operator": "IN", "value": [int(x) for x in wepp_ids]},
        ],
        "order_by": ["wepp_id ASC", "t_s ASC"],
        "limit": 2000000,
        "include_schema": False,
    }
    result = client.query(run_slug, payload)
    df = pd.DataFrame(result.get("records", []))
    if df.empty:
        raise ValueError(
            "No chan.out rows returned for this day/ids. "
            "If you want full hydrographs, you must rerun with ichout=3 and a small dtchr (e.g., 300s)."
        )
    df["wepp_id"] = df["wepp_id"].astype(int)
    df["t_s"] = df["t_s"].astype(float)
    df["q_m3s"] = df["q_m3s"].astype(float)
    df["t_hr"] = df["t_s"] / 3600.0
    return df


def _plot_wave(
    *,
    out_path: Path,
    df: pd.DataFrame,
    topaz_map: pd.DataFrame,
    title: str,
) -> None:
    # Order elements by elevation high->low as a proxy for top->bottom.
    m = topaz_map.copy()
    m["elevation"] = m["elevation"].astype(float)
    m = m.sort_values("elevation", ascending=False)
    order = [int(x) for x in m["wepp_id"].tolist()]

    fig, axes = plt.subplots(len(order), 1, figsize=(10.2, 7.2), sharex=True, constrained_layout=True)
    if len(order) == 1:
        axes = [axes]

    for ax, wepp_id in zip(axes, order, strict=False):
        sub = df[df["wepp_id"] == wepp_id].copy()
        if sub.empty:
            ax.set_title(f"wepp_id={wepp_id} (missing)")
            continue
        ax.plot(sub["t_hr"], sub["q_m3s"], color="#1f2937", linewidth=2)
        ax.grid(True, alpha=0.25)

        meta = m[m["wepp_id"] == wepp_id].iloc[0].to_dict()
        topaz_id = int(meta["topaz_id"])
        elev = float(meta.get("elevation", float("nan")))
        qpk = float(sub["q_m3s"].max())
        tpk = float(sub.loc[sub["q_m3s"].idxmax(), "t_hr"])
        ax.set_ylabel("Q (m³/s)")
        ax.set_title(f"TOPAZ {topaz_id} (WEPP {wepp_id})  elev={elev:0.1f} m  peak={qpk:0.2f} @ {tpk:0.2f} hr")

    axes[-1].set_xlabel("Time since day start (hr)")
    fig.suptitle(title, fontsize=14)
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser(
        description=(
            "Plot routed channel hydrographs at multiple TOPAZ channel IDs from chan.out.parquet. "
            "For a definitive kinematic-wave/routing visualization, rerun with ichout=3 and dtchr=300s."
        )
    )
    ap.add_argument("--base-url", default="https://wc.bearhive.duckdns.org/query-engine")
    ap.add_argument("--runid", required=True)
    ap.add_argument("--scenario", default="", help='Scenario name (e.g. "undisturbed"). Leave blank for default/base.')
    ap.add_argument("--topaz-ids", required=True, help="Comma/space separated TOPAZ channel IDs, e.g. '604 324 24'")
    ap.add_argument("--date", default="", help="Event date YYYY-MM-DD (preferred)")
    ap.add_argument("--sim-day-index", type=int, default=0, help="Override event day index directly")
    ap.add_argument("--out-dir", type=Path, default=Path("tmp_channel_wave"))
    args = ap.parse_args()

    run_slug = str(args.runid).strip("/")
    scenario = str(args.scenario).strip("/") or None
    topaz_ids = _parse_topaz_ids(str(args.topaz_ids))
    if not topaz_ids:
        raise SystemExit("No TOPAZ IDs provided")

    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    client = QueryEngineClient(base_url=str(args.base_url))

    topaz_map = _topaz_to_wepp_ids(client, run_slug=run_slug, topaz_ids=topaz_ids)
    wepp_ids = [int(x) for x in topaz_map["wepp_id"].tolist()]

    # For outlet lookup, use the minimum elevation entry as a default "bottom".
    outlet_wepp_id = int(topaz_map.sort_values("elevation", ascending=True).iloc[0]["wepp_id"])

    if int(args.sim_day_index) > 0:
        sim_day_index = int(args.sim_day_index)
    else:
        if not args.date:
            raise SystemExit("Provide --date YYYY-MM-DD or --sim-day-index")
        sim_day_index = _sim_day_index_for_date(
            client, run_slug=run_slug, scenario=scenario, date=str(args.date), outlet_wepp_id=outlet_wepp_id
        )

    df = _chan_hydrograph(
        client,
        run_slug=run_slug,
        scenario=scenario,
        sim_day_index=sim_day_index,
        wepp_ids=wepp_ids,
    )

    # Check if this looks like a full hydrograph (ichout=3): multiple time steps per element.
    steps_per_el = df.groupby("wepp_id")["t_s"].nunique().to_dict()
    if max(steps_per_el.values(), default=0) <= 2:
        (out_dir / "warning.txt").write_text(
            "chan.out contains only peak rows for this day/ids (likely ichout=1). "
            "Rerun with ichout=3 and dtchr=300s to get a full 5-min hydrograph.\n",
            encoding="utf-8",
        )

    title = f"Channel hydrograph wave (sim_day_index={sim_day_index})"
    if args.date:
        title += f" date={args.date}"
    if scenario:
        title += f" scenario={scenario}"
    out_path = out_dir / "channel_wave_hydrographs.png"
    _plot_wave(out_path=out_path, df=df, topaz_map=topaz_map, title=title)

    meta = {
        "runid": run_slug,
        "scenario": scenario or "<default>",
        "topaz_ids": topaz_ids,
        "wepp_ids": wepp_ids,
        "sim_day_index": sim_day_index,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
        "steps_per_element": steps_per_el,
    }
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")
    df.to_csv(out_dir / "chan_out_timeseries.csv", index=False)

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
