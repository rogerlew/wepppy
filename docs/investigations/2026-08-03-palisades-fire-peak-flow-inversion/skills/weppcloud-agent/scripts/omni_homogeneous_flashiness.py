#!/usr/bin/env python3
from __future__ import annotations
import argparse
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


def _tex_escape(s: str) -> str:
    return (
        str(s)
        .replace("\\", "\\textbackslash{}")
        .replace("&", "\\&")
        .replace("%", "\\%")
        .replace("_", "\\_")
    )


def _to_latex_table(df: pd.DataFrame, caption: str, label: str) -> str:
    cols = list(df.columns)
    out: list[str] = []
    out.append("\\begin{table}[H]")
    out.append("  \\centering")
    out.append(f"  \\caption{{{caption}}}")
    out.append(f"  \\label{{{label}}}")
    out.append("  \\resizebox{\\textwidth}{!}{%")
    out.append("  \\begin{tabular}{%s}" % (" ".join(["l"] * 2 + ["r"] * (len(cols) - 2))))
    out.append("    \\toprule")
    out.append("    " + " & ".join(_tex_escape(c) for c in cols) + " \\\\")
    out.append("    \\midrule")
    for _, row in df.iterrows():
        parts: list[str] = []
        for c in cols:
            v = row[c]
            if isinstance(v, float) or isinstance(v, np.floating):
                parts.append(f"{float(v):0.6g}")
            else:
                parts.append(_tex_escape(v))
        out.append("    " + " & ".join(parts) + " \\\\")
    out.append("    \\bottomrule")
    out.append("  \\end{tabular}}")
    out.append("\\end{table}")
    out.append("")
    return "\n".join(out)


def _outlet_wepp_id_from_topaz(
    client: QueryEngineClient,
    *,
    run_slug: str,
    scenario: str | None,
    outlet_topaz_id: int,
) -> int:
    payload: dict[str, Any] = {
        **({"scenario": scenario} if scenario else {}),
        "datasets": [{"path": "watershed/channels.parquet", "alias": "c"}],
        "columns": ["c.topaz_id", "c.wepp_id"],
        "filters": [{"column": "c.topaz_id", "operator": "=", "value": int(outlet_topaz_id)}],
        "limit": 5,
        "include_schema": False,
    }
    df = pd.DataFrame(client.query(run_slug, payload).get("records", []))
    if df.empty:
        raise ValueError("No outlet row found in watershed/channels.parquet for given topaz id.")
    return int(df.iloc[0]["wepp_id"])


def _ebe_outlet(
    client: QueryEngineClient,
    *,
    run_slug: str,
    scenario: str,
    outlet_wepp_id: int,
) -> pd.DataFrame:
    payload: dict[str, Any] = {
        "scenario": scenario,
        "datasets": [{"path": "wepp/output/interchange/ebe_pw0.parquet", "alias": "e"}],
        "columns": [
            "e.sim_day_index",
            "e.year",
            "e.month",
            "e.day_of_month",
            "e.julian",
            "e.precip",
            "e.runoff_volume",
            "e.element_id",
        ],
        "filters": [{"column": "e.element_id", "operator": "=", "value": int(outlet_wepp_id)}],
        "order_by": ["e.sim_day_index ASC"],
        "limit": 25000,
        "include_schema": False,
    }
    df = pd.DataFrame(client.query(run_slug, payload).get("records", []))
    if df.empty:
        raise ValueError(f"No EBE outlet rows for scenario={scenario}")
    df["date"] = pd.to_datetime(
        df[["year", "month", "day_of_month"]].rename(columns={"day_of_month": "day"}),
        errors="coerce",
    )
    df["runoff_volume"] = df["runoff_volume"].astype(float)
    df["precip"] = df["precip"].astype(float)
    df["julian"] = df["julian"].astype(int)
    df["year"] = df["year"].astype(int)
    return df


def _chan_daily_peak_outlet(
    client: QueryEngineClient,
    *,
    run_slug: str,
    scenario: str,
    outlet_wepp_id: int,
) -> pd.DataFrame:
    payload: dict[str, Any] = {
        "scenario": scenario,
        "datasets": [{"path": "wepp/output/interchange/chan.out.parquet", "alias": "c"}],
        "columns": [
            "c.year",
            "c.month",
            "c.day_of_month",
            "c.julian",
        ],
        "filters": [{"column": "c.Elmt_ID", "operator": "=", "value": int(outlet_wepp_id)}],
        "group_by": ["c.year", "c.month", "c.day_of_month", "c.julian"],
        "aggregations": [{'sql': 'MAX(c."Peak_Discharge (m^3/s)")', "alias": "peak_discharge_m3s"}],
        "order_by": ["c.year ASC", "c.julian ASC"],
        "limit": 25000,
        "include_schema": False,
    }
    df = pd.DataFrame(client.query(run_slug, payload).get("records", []))
    if df.empty:
        raise ValueError(f"No chan.out daily peaks for scenario={scenario}.")
    df["date"] = pd.to_datetime(
        df[["year", "month", "day_of_month"]].rename(columns={"day_of_month": "day"}),
        errors="coerce",
    )
    df["peak_discharge_m3s"] = df["peak_discharge_m3s"].astype(float)
    df["julian"] = df["julian"].astype(int)
    df["year"] = df["year"].astype(int)
    return df


def _cta_picks(daily: pd.DataFrame, recurrence_years: list[int]) -> pd.DataFrame:
    d = daily.copy()
    d = d.dropna(subset=["peak_discharge_m3s", "date"]).copy()
    d = d.sort_values(["peak_discharge_m3s", "year", "julian"], ascending=[False, True, True]).reset_index(drop=True)
    n = len(d)
    d["rank"] = np.arange(1, n + 1, dtype=int)
    d["T_years"] = ((n + 1) / d["rank"].astype(float)) / 365.25

    rows: list[dict[str, Any]] = []
    for target in sorted(set(int(x) for x in recurrence_years)):
        sub = d[d["T_years"].astype(float) >= float(target)]
        if sub.empty:
            continue
        r = sub.iloc[-1]
        rows.append(
            {
                "Return period (yr)": int(target),
                "Date": str(pd.to_datetime(r["date"]).date()),
                "Qp (m3/s)": float(r["peak_discharge_m3s"]),
                "Weibull rank": int(r["rank"]),
                "Weibull T (yr)": float(r["T_years"]),
            }
        )
    return pd.DataFrame(rows).sort_values("Return period (yr)")


def _flashiness_rank_series(daily: pd.DataFrame, *, top_n: int) -> pd.DataFrame:
    d = daily.copy()
    d = d.dropna(subset=["peak_discharge_m3s", "runoff_volume"]).copy()
    d = d.sort_values(["peak_discharge_m3s", "year", "julian"], ascending=[False, True, True]).reset_index(drop=True)
    d["rank"] = np.arange(1, len(d) + 1, dtype=int)
    d["teff_hr"] = (d["runoff_volume"].astype(float) / d["peak_discharge_m3s"].astype(float)) / 3600.0
    d["qp_over_v_1_per_s"] = d["peak_discharge_m3s"].astype(float) / d["runoff_volume"].astype(float)
    return d.head(int(top_n)).copy()


def _rank_plot(
    *,
    df_by_scn: dict[str, pd.DataFrame],
    ycol: str,
    ylabel: str,
    title: str,
    out_path: Path,
) -> None:
    colors = {
        "undisturbed": "#1e90ff",
        "uniform_moderate": "#ffcc00",
        "uniform_high": "#ff3b30",
    }
    labels = {
        "undisturbed": "Undisturbed",
        "uniform_moderate": "Uniform moderate severity fire",
        "uniform_high": "Uniform high severity fire",
    }

    fig, ax = plt.subplots(figsize=(9.2, 5.4), constrained_layout=True)
    for scn, df in df_by_scn.items():
        if df.empty:
            continue
        ax.plot(
            df["rank"].astype(int),
            df[ycol].astype(float),
            linewidth=2.2,
            color=colors.get(scn, "black"),
            label=labels.get(scn, scn),
        )
    ax.set_xlabel("Event rank by outlet daily peak discharge (1 = largest)")
    ax.set_ylabel(ylabel)
    ax.set_title(title)
    ax.grid(True, alpha=0.25)
    ax.legend()
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


def main() -> int:
    ap = argparse.ArgumentParser(description="Compare flashiness of omni homogeneous-severity scenarios to undisturbed")
    ap.add_argument("--base-url", default="https://wc.bearhive.duckdns.org/query-engine")
    ap.add_argument("--runid", required=True)
    ap.add_argument("--out-dir", type=Path, default=Path("tmp_upset_reckoning_omni_homog"))
    ap.add_argument("--outlet-topaz-id", type=int, default=24)
    ap.add_argument("--top-n", type=int, default=100)
    ap.add_argument("--recurrence", default="2,5,10")
    ap.add_argument("--scenarios", default="undisturbed,uniform_moderate,uniform_high")
    args = ap.parse_args()

    run_slug = str(args.runid).strip("/")
    scenarios = [s.strip() for s in str(args.scenarios).split(",") if s.strip()]
    recurrence = [int(x.strip()) for x in str(args.recurrence).replace(" ", "").split(",") if x.strip()]

    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    client = QueryEngineClient(base_url=str(args.base_url))

    # Use undisturbed to resolve the outlet wepp_id (same channel network across omni scenarios).
    outlet_wepp_id = _outlet_wepp_id_from_topaz(
        client, run_slug=run_slug, scenario="undisturbed", outlet_topaz_id=int(args.outlet_topaz_id)
    )

    daily_by_scn: dict[str, pd.DataFrame] = {}
    cta_rows: list[pd.DataFrame] = []
    rank_series: dict[str, pd.DataFrame] = {}

    for scn in scenarios:
        ebe = _ebe_outlet(client, run_slug=run_slug, scenario=scn, outlet_wepp_id=outlet_wepp_id)
        qp = _chan_daily_peak_outlet(client, run_slug=run_slug, scenario=scn, outlet_wepp_id=outlet_wepp_id)
        daily = ebe.merge(qp[["year", "julian", "peak_discharge_m3s"]], on=["year", "julian"], how="inner")
        daily_by_scn[scn] = daily

        picks = _cta_picks(daily, recurrence)
        picks.insert(0, "Scenario", scn)
        cta_rows.append(picks)

        rank_series[scn] = _flashiness_rank_series(daily, top_n=int(args.top_n))

    cta_df = pd.concat(cta_rows, ignore_index=True) if cta_rows else pd.DataFrame()
    (out_dir / "cta_return_periods.csv").write_text(cta_df.to_csv(index=False), encoding="utf-8")
    (out_dir / "cta_return_periods_table.tex").write_text(
        _to_latex_table(
            cta_df,
            caption="CTA return-period picks (2/5/10 years) using daily outlet peak discharge from 5-minute channel hydrographs (chan.out grouped to daily maxima).",
            label="tab:cta_rp_omni_homog",
        ),
        encoding="utf-8",
    )

    # Rank plots
    _rank_plot(
        df_by_scn=rank_series,
        ycol="teff_hr",
        ylabel="Teff = V/Qp (hr)",
        title=f"Flashiness proxy vs rank (top-{int(args.top_n)} peakflow days)",
        out_path=out_dir / "teff_hr_vs_rank_topN_omni.png",
    )
    _rank_plot(
        df_by_scn=rank_series,
        ycol="qp_over_v_1_per_s",
        ylabel="Qp/V (1/s)",
        title=f"Peak-to-volume ratio vs rank (top-{int(args.top_n)} peakflow days)",
        out_path=out_dir / "qp_over_v_vs_rank_topN_omni.png",
    )

    # Summary table on ranks 4-30 (as used elsewhere in the report)
    summary_rows: list[dict[str, Any]] = []
    for scn, rs in rank_series.items():
        sub = rs[(rs["rank"] >= 4) & (rs["rank"] <= 30)].copy()
        if sub.empty:
            continue
        teff = sub["teff_hr"].astype(float)
        qpov = sub["qp_over_v_1_per_s"].astype(float)
        summary_rows.append(
            {
                "Scenario": scn,
                "n (ranks 4-30)": int(len(sub)),
                "Median Teff (hr)": float(teff.median()),
                "IQR Teff (hr)": f"{float(teff.quantile(0.25)):.4g}--{float(teff.quantile(0.75)):.4g}",
                "Median Qp/V (1/s)": float(qpov.median()),
                "IQR Qp/V (1/s)": f"{float(qpov.quantile(0.25)):.4g}--{float(qpov.quantile(0.75)):.4g}",
            }
        )
    summary_df = pd.DataFrame(summary_rows)
    (out_dir / "flashiness_rank_4_30_summary.csv").write_text(summary_df.to_csv(index=False), encoding="utf-8")
    (out_dir / "flashiness_rank_4_30_summary_table.tex").write_text(
        _to_latex_table(
            summary_df,
            caption="Flashiness summaries for ranks 4--30 (daily outlet peaks), comparing undisturbed to homogeneous-severity fire scenarios.",
            label="tab:flashiness_omni_homog_summary",
        ),
        encoding="utf-8",
    )

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
