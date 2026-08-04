#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
import re
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
    timeout_s: float = 120.0
    host_header: str | None = None
    verify_tls: bool = True

    def _url(self, path: str) -> str:
        return f"{self.base_url.rstrip('/')}/{path.lstrip('/')}"

    def query(self, run_slug: str, payload: dict[str, Any]) -> dict[str, Any]:
        url = self._url(f"runs/{run_slug}/query")
        headers = {"Content-Type": "application/json"}
        if self.host_header:
            headers["Host"] = self.host_header
        resp = requests.post(url, json=payload, headers=headers, timeout=self.timeout_s, verify=self.verify_tls)
        if resp.status_code >= 400:
            detail = resp.text[:2000]
            raise RuntimeError(f"Query failed ({resp.status_code}) for {url}: {detail}")
        return resp.json()


def _landuse_area_summary(
    client: QueryEngineClient,
    *,
    runid: str,
    scenario: str | None,
) -> pd.DataFrame:
    payload = {
        **({"scenario": scenario} if scenario else {}),
        "datasets": [{"path": "landuse/landuse.parquet", "alias": "l"}],
        "columns": ["l.desc AS landuse_desc", "l.disturbed_class AS disturbed_class"],
        "group_by": ["landuse_desc", "disturbed_class"],
        "aggregations": [{"sql": "COUNT(*)", "alias": "n"}, {"sql": "SUM(l.area)", "alias": "area_m2"}],
        "order_by": ["area_m2 DESC"],
        "limit": 1000,
    }
    result = client.query(runid, payload)
    df = pd.DataFrame(result.get("records", []))
    if df.empty:
        raise ValueError("No landuse records returned")
    return df


def _pass_peakro_by_day_and_class(
    client: QueryEngineClient,
    *,
    runid: str,
    scenario: str | None,
    disturbed_classes: list[str],
) -> pd.DataFrame:
    payload = {
        **({"scenario": scenario} if scenario else {}),
        "datasets": [
            {"path": "wepp/output/interchange/pass_pw0.events.parquet", "alias": "p"},
            {"path": "landuse/landuse.parquet", "alias": "l"},
        ],
        "joins": [{"left": "p", "right": "l", "on": "wepp_id", "type": "inner"}],
        "columns": [
            "p.sim_day_index AS sim_day_index",
            "p.year AS year",
            "p.month AS month",
            "p.day_of_month AS day_of_month",
            "p.julian AS julian",
            "l.disturbed_class AS disturbed_class",
        ],
        "filters": [
            {"column": "p.event", "operator": "=", "value": "EVENT"},
            {"column": "l.disturbed_class", "operator": "IN", "value": disturbed_classes},
        ],
        "group_by": ["sim_day_index", "year", "month", "day_of_month", "julian", "disturbed_class"],
        "aggregations": [
            {"sql": "SUM(l.area)", "alias": "area_m2"},
            {"sql": "SUM(p.peakro * l.area) / NULLIF(SUM(l.area), 0)", "alias": "peakro_area_weighted_mean"},
            {"sql": "MAX(p.peakro)", "alias": "peakro_max"},
            {"sql": "SUM(p.runvol)", "alias": "runvol_sum_m3"},
            {"sql": "SUM(p.runoff * l.area) / NULLIF(SUM(l.area), 0)", "alias": "runoff_area_weighted_mean"},
        ],
        "order_by": ["disturbed_class ASC", "sim_day_index ASC"],
        "limit": 250000,
    }
    result = client.query(runid, payload)
    df = pd.DataFrame(result.get("records", []))
    if df.empty:
        raise ValueError("No PASS rows returned for requested disturbed classes")
    df["date"] = pd.to_datetime(
        df[["year", "month", "day_of_month"]].rename(columns={"day_of_month": "day"}),
        errors="coerce",
    )
    return df


def _classify_landuse(disturbed_class: str) -> tuple[str, str] | None:
    """
    Returns (landuse_group, severity_group) where:
      landuse_group in {'shrub','forest'}
      severity_group in {'undisturbed','low','moderate','high'}
    """
    s = (disturbed_class or "").strip().lower()
    if not s:
        return None

    if s == "shrub":
        return ("shrub", "undisturbed")
    if s == "forest":
        return ("forest", "undisturbed")

    m = re.match(r"^(shrub|forest)\s+(low|moderate|high)\s+sev\s+fire$", s)
    if m:
        return (m.group(1), m.group(2))
    return None


def _rank_curve(df: pd.DataFrame, *, metric: str) -> pd.DataFrame:
    d = df.copy()
    d = d.dropna(subset=[metric])
    d = d.sort_values(metric, ascending=False).reset_index(drop=True)
    d["rank"] = d.index + 1
    return d


def _plot_rank_curves(
    *,
    out_path: Path,
    curves: dict[str, pd.DataFrame],
    metric: str,
    ylabel: str,
    title: str,
    log_y: bool,
) -> None:
    fig, ax = plt.subplots(figsize=(10.5, 6.0), constrained_layout=True)
    colors = {
        "undisturbed": "#1e90ff",
        "low": "#34c759",
        "moderate": "#ffcc00",
        "high": "#ff3b30",
    }

    for label, curve in curves.items():
        sev = label.split(":")[-1] if ":" in label else label
        color = colors.get(sev, None)
        y = curve[metric].astype(float)
        if log_y:
            y = y.clip(lower=1e-9)
        ax.plot(curve["rank"].astype(int), y, linewidth=2, label=label, color=color)

    ax.set_xlabel("Event rank (1 = largest within group)")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(True, alpha=0.25)
    ax.legend(fontsize=9)
    if log_y:
        ax.set_yscale("log")
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


def _expand_classification(df: pd.DataFrame) -> pd.DataFrame:
    if df.empty:
        df["landuse_group"] = pd.Series(dtype=str)
        df["severity_group"] = pd.Series(dtype=str)
        return df
    tuples = df["classification"].tolist()
    expanded = pd.DataFrame(tuples, columns=["landuse_group", "severity_group"], index=df.index)
    return df.join(expanded)

def _add_derived_metrics(df: pd.DataFrame) -> pd.DataFrame:
    """
    Adds derived metrics used as flashiness proxies:
      - flash_index = peakro_area_weighted_mean / runoff_area_weighted_mean
      - teff_proxy = runoff_area_weighted_mean / peakro_area_weighted_mean
    These are unit-consistent ratios if peakro and runoff are in compatible units.
    """
    d = df.copy()
    d["peakro_area_weighted_mean"] = pd.to_numeric(d.get("peakro_area_weighted_mean"), errors="coerce")
    d["runoff_area_weighted_mean"] = pd.to_numeric(d.get("runoff_area_weighted_mean"), errors="coerce")
    peak = d["peakro_area_weighted_mean"]
    runoff = d["runoff_area_weighted_mean"]

    valid = (peak.notna()) & (runoff.notna()) & (peak > 0) & (runoff > 0)
    d["flash_index"] = pd.NA
    d.loc[valid, "flash_index"] = (peak[valid] / runoff[valid]).astype(float)
    d["teff_proxy"] = pd.NA
    d.loc[valid, "teff_proxy"] = (runoff[valid] / peak[valid]).astype(float)
    return d


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Partition hillslope peak runoff proxies (PASS peakro) by landuse and burn severity, comparing burned vs undisturbed scenarios."
    )
    parser.add_argument("--runid", required=True, help="WEPPcloud run id (e.g., upset-reckoning)")
    parser.add_argument("--scenario", default="undisturbed", help="Undisturbed scenario name (default: undisturbed)")
    parser.add_argument("--base-url", default="https://wc.bearhive.duckdns.org/query-engine", help="Query Engine base URL")
    parser.add_argument(
        "--host-ip",
        default=None,
        help="Optional: connect via https://<ip>/... with Host header set (helps when DNS is flaky).",
    )
    parser.add_argument("--out-dir", default="landuse_peakflow_partition_out", help="Output directory")
    parser.add_argument("--metric", default="peakro_area_weighted_mean", help="Metric column to rank/plot")
    parser.add_argument("--max-rank", type=int, default=300, help="Max rank to show on plots (default: 300)")
    parser.add_argument("--log-y", action="store_true", help="Use log-scale y-axis on plots (recommended for peakro).")
    args = parser.parse_args(argv)

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    base_url = str(args.base_url)
    host_header = None
    verify_tls = True
    if args.host_ip:
        host_header = "wc.bearhive.duckdns.org"
        base_url = f"https://{args.host_ip}/query-engine"
        verify_tls = False

    client = QueryEngineClient(base_url=base_url, host_header=host_header, verify_tls=verify_tls)

    runid = str(args.runid).strip("/")
    scenario = str(args.scenario).strip("/")

    # Discover disturbed classes by scenario.
    burned_landuse = _landuse_area_summary(client, runid=runid, scenario=None)
    undist_landuse = _landuse_area_summary(client, runid=runid, scenario=scenario)

    burned_landuse["classification"] = burned_landuse["disturbed_class"].map(_classify_landuse)
    undist_landuse["classification"] = undist_landuse["disturbed_class"].map(_classify_landuse)

    burned_landuse = burned_landuse.dropna(subset=["classification"])
    undist_landuse = undist_landuse.dropna(subset=["classification"])

    burned_landuse = _expand_classification(burned_landuse)
    undist_landuse = _expand_classification(undist_landuse)

    burned_landuse.to_csv(out_dir / "burned_landuse_area_summary.csv", index=False)
    undist_landuse.to_csv(out_dir / "undisturbed_landuse_area_summary.csv", index=False)

    burned_classes = sorted(set(burned_landuse["disturbed_class"].astype(str)))
    undist_classes = sorted(set(undist_landuse["disturbed_class"].astype(str)))

    burned_pass = _pass_peakro_by_day_and_class(client, runid=runid, scenario=None, disturbed_classes=burned_classes)
    undist_pass = _pass_peakro_by_day_and_class(client, runid=runid, scenario=scenario, disturbed_classes=undist_classes)

    burned_pass["classification"] = burned_pass["disturbed_class"].map(_classify_landuse)
    undist_pass["classification"] = undist_pass["disturbed_class"].map(_classify_landuse)
    burned_pass = burned_pass.dropna(subset=["classification"])
    undist_pass = undist_pass.dropna(subset=["classification"])
    burned_pass = _expand_classification(burned_pass)
    undist_pass = _expand_classification(undist_pass)

    burned_pass = _add_derived_metrics(burned_pass)
    undist_pass = _add_derived_metrics(undist_pass)

    burned_pass.to_csv(out_dir / "burned_pass_peakro_by_day_and_class.csv", index=False)
    undist_pass.to_csv(out_dir / "undisturbed_pass_peakro_by_day_and_class.csv", index=False)

    metric = str(args.metric)
    max_rank = int(args.max_rank)
    log_y = bool(args.log_y)

    ylabel_by_metric = {
        "peakro_area_weighted_mean": "Area-weighted mean peakro (PASS peak-runoff proxy)",
        "flash_index": "Flashiness proxy: peakro/runoff (1/time proxy)",
        "teff_proxy": "Effective-duration proxy: runoff/peakro (time proxy)",
    }

    # Build and plot rank curves by landuse group.
    for landuse_group in ("shrub", "forest"):
        curves: dict[str, pd.DataFrame] = {}

        u = undist_pass[undist_pass["landuse_group"] == landuse_group].copy()
        u_curve = _rank_curve(u, metric=metric).head(max_rank)
        curves[f"undisturbed:{landuse_group}:undisturbed"] = u_curve

        b = burned_pass[burned_pass["landuse_group"] == landuse_group].copy()
        for severity in ("low", "moderate", "high"):
            sub = b[b["severity_group"] == severity].copy()
            if sub.empty:
                continue
            curves[f"burned:{landuse_group}:{severity}"] = _rank_curve(sub, metric=metric).head(max_rank)

        _plot_rank_curves(
            out_path=out_dir / f"{landuse_group}_{metric}_vs_rank_by_severity.png",
            curves=curves,
            metric=metric,
            ylabel=ylabel_by_metric.get(metric, metric),
            title=f"{landuse_group.title()}: {metric} vs rank (undisturbed vs burned severities)",
            log_y=log_y,
        )

        # Summary ratios at selected ranks.
        rows = []
        for label, curve in curves.items():
            for rnk in (1, 2, 5, 10, 25, 50, 100):
                if rnk <= len(curve):
                    rows.append({"landuse_group": landuse_group, "series": label, "rank": rnk, metric: float(curve.iloc[rnk - 1][metric])})
        pd.DataFrame(rows).to_csv(out_dir / f"{landuse_group}_{metric}_rank_summary.csv", index=False)

    meta = {
        "runid": runid,
        "undisturbed_scenario": scenario,
        "metric": metric,
        "note": (
            "Peakflow partition is based on PASS hillslope event variable 'peakro' aggregated by day and disturbed_class "
            "using landuse/landuse.parquet. Interpret as a peak-runoff proxy at hillslope scale."
        ),
    }
    (out_dir / "meta.json").write_text(json.dumps(meta, indent=2) + "\n", encoding="utf-8")

    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
