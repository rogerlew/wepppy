#!/usr/bin/env python3
from __future__ import annotations
import argparse
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Any

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
    return str(s).replace("\\", "\\textbackslash{}").replace("&", "\\&").replace("%", "\\%").replace("_", "\\_")


def _outlet_wepp_id(client: QueryEngineClient, *, run_slug: str, outlet_topaz_id: int) -> int:
    payload = {
        "datasets": [{"path": "watershed/channels.parquet", "alias": "c"}],
        "columns": ["c.topaz_id", "c.wepp_id"],
        "filters": [{"column": "c.topaz_id", "operator": "=", "value": int(outlet_topaz_id)}],
        "limit": 5,
        "include_schema": False,
    }
    df = pd.DataFrame(client.query(run_slug, payload).get("records", []))
    if df.empty:
        raise ValueError("Failed to resolve outlet wepp_id from watershed/channels.parquet")
    return int(df.iloc[0]["wepp_id"])


def _chan_daily_qp(
    client: QueryEngineClient,
    *,
    run_slug: str,
    scenario: str | None,
    outlet_wepp_id: int,
) -> pd.DataFrame:
    payload: dict[str, Any] = {
        **({"scenario": scenario} if scenario else {}),
        "datasets": [{"path": "wepp/output/interchange/chan.out.parquet", "alias": "c"}],
        "columns": ["c.year", "c.month", "c.day_of_month", "c.julian"],
        "filters": [{"column": "c.Elmt_ID", "operator": "=", "value": int(outlet_wepp_id)}],
        "group_by": ["c.year", "c.month", "c.day_of_month", "c.julian"],
        "aggregations": [{'sql': 'MAX(c."Peak_Discharge (m^3/s)")', "alias": "qp_m3s"}],
        "order_by": ["c.year ASC", "c.julian ASC"],
        "limit": 25000,
        "include_schema": False,
    }
    df = pd.DataFrame(client.query(run_slug, payload).get("records", []))
    if df.empty:
        raise ValueError(f"No chan.out daily maxima returned (scenario={scenario or '<base>'}).")
    df["date"] = pd.to_datetime(
        df[["year", "month", "day_of_month"]].rename(columns={"day_of_month": "day"}), errors="coerce"
    )
    df["qp_m3s"] = df["qp_m3s"].astype(float)
    df["year"] = df["year"].astype(int)
    df["julian"] = df["julian"].astype(int)
    return df


def _ebe_daily_vp(
    client: QueryEngineClient,
    *,
    run_slug: str,
    scenario: str | None,
    outlet_wepp_id: int,
) -> pd.DataFrame:
    payload: dict[str, Any] = {
        **({"scenario": scenario} if scenario else {}),
        "datasets": [{"path": "wepp/output/interchange/ebe_pw0.parquet", "alias": "e"}],
        "columns": ["e.year", "e.month", "e.day_of_month", "e.julian", "e.precip", "e.runoff_volume"],
        "filters": [{"column": "e.element_id", "operator": "=", "value": int(outlet_wepp_id)}],
        "order_by": ["e.sim_day_index ASC"],
        "limit": 25000,
        "include_schema": False,
    }
    df = pd.DataFrame(client.query(run_slug, payload).get("records", []))
    if df.empty:
        raise ValueError(f"No ebe_pw0 outlet rows returned (scenario={scenario or '<base>'}).")
    df["date"] = pd.to_datetime(
        df[["year", "month", "day_of_month"]].rename(columns={"day_of_month": "day"}), errors="coerce"
    )
    df["precip"] = df["precip"].astype(float)
    df["runoff_volume"] = df["runoff_volume"].astype(float)
    df["year"] = df["year"].astype(int)
    df["julian"] = df["julian"].astype(int)
    return df


def _cta_pick_table(daily_qp: pd.DataFrame, recurrence_years: list[int]) -> pd.DataFrame:
    d = daily_qp.dropna(subset=["date", "qp_m3s"]).copy()
    d = d.sort_values(["qp_m3s", "year", "julian"], ascending=[False, True, True]).reset_index(drop=True)
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
                "return_period_yr": int(target),
                "date": str(pd.to_datetime(r["date"]).date()),
                "qp_m3s": float(r["qp_m3s"]),
            }
        )
    return pd.DataFrame(rows).sort_values("return_period_yr")


def _write_cta_rp_table(
    out_path: Path,
    *,
    burned_picks: pd.DataFrame,
    und_picks: pd.DataFrame,
) -> None:
    # Merge on return period.
    merged = burned_picks.merge(und_picks, on="return_period_yr", how="outer", suffixes=("_b", "_u")).sort_values(
        "return_period_yr"
    )
    lines: list[str] = []
    lines.append("\\begin{table}[H]")
    lines.append("  \\centering")
    lines.append("  \\caption{CTA peak-discharge return-period events for burned vs.\\ undisturbed.}")
    lines.append("  \\label{tab:cta_rp}")
    lines.append("  \\begin{tabular}{r l r l r}")
    lines.append("    \\toprule")
    lines.append(
        "    Return period (yr) & Burned date & $Q_{p,B}$ (m\\textsuperscript{3}/s) & Undisturbed date & $Q_{p,U}$ (m\\textsuperscript{3}/s) \\\\"
    )
    lines.append("    \\midrule")
    for _, row in merged.iterrows():
        rp = int(row["return_period_yr"])
        bd = _tex_escape(row.get("date_b", ""))
        ud = _tex_escape(row.get("date_u", ""))
        qb = float(row["qp_m3s_b"]) if pd.notna(row.get("qp_m3s_b")) else float("nan")
        qu = float(row["qp_m3s_u"]) if pd.notna(row.get("qp_m3s_u")) else float("nan")
        lines.append(f"    {rp} & {bd} & {qb:0.2f} & {ud} & {qu:0.2f} \\\\")
    lines.append("    \\bottomrule")
    lines.append("  \\end{tabular}")
    lines.append("\\end{table}")
    lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")


def _write_union_date_compare_table(
    out_path: Path,
    *,
    dates: list[str],
    burned_daily: pd.DataFrame,
    und_daily: pd.DataFrame,
) -> None:
    b = burned_daily.set_index("date").copy()
    u = und_daily.set_index("date").copy()

    lines: list[str] = []
    lines.append("\\begin{table}[H]")
    lines.append("  \\centering")
    lines.append("  \\caption{Same-date comparison of burned vs.\\ undisturbed for the union of CTA-picked dates.}")
    lines.append("  \\label{tab:date_compare}")
    lines.append("  \\resizebox{\\textwidth}{!}{%")
    lines.append("  \\begin{tabular}{l r r r r r r}")
    lines.append("    \\toprule")
    lines.append(
        "    Date & $P_B$ (mm) & $V_B$ (m\\textsuperscript{3}) & $Q_{p,B}$ (m\\textsuperscript{3}/s) & $P_U$ (mm) & $V_U$ (m\\textsuperscript{3}) & $Q_{p,U}$ (m\\textsuperscript{3}/s) \\\\"
    )
    lines.append("    \\midrule")
    for d in dates:
        dt = pd.Timestamp(d)
        rb = b.loc[dt] if dt in b.index else None
        ru = u.loc[dt] if dt in u.index else None
        pb = float(rb["precip"]) if rb is not None else float("nan")
        vb = float(rb["runoff_volume"]) if rb is not None else float("nan")
        qb = float(rb["qp_m3s"]) if rb is not None else float("nan")
        pu = float(ru["precip"]) if ru is not None else float("nan")
        vu = float(ru["runoff_volume"]) if ru is not None else float("nan")
        qu = float(ru["qp_m3s"]) if ru is not None else float("nan")
        lines.append(f"    {d} & {pb:0.1f} & {vb:0.0f} & {qb:0.2f} & {pu:0.1f} & {vu:0.0f} & {qu:0.2f} \\\\")
    lines.append("    \\bottomrule")
    lines.append("  \\end{tabular}}")
    lines.append("\\end{table}")
    lines.append("")
    out_path.write_text("\n".join(lines), encoding="utf-8")


def main() -> int:
    ap = argparse.ArgumentParser(description="Generate Scope CTA tables for burned vs undisturbed (chan.out daily maxima)")
    ap.add_argument("--base-url", default="https://wc.bearhive.duckdns.org/query-engine")
    ap.add_argument("--runid", required=True)
    ap.add_argument("--undisturbed-scenario", default="undisturbed")
    ap.add_argument("--outlet-topaz-id", type=int, default=24)
    ap.add_argument("--recurrence", default="2,5,10")
    ap.add_argument("--out-dir", type=Path, default=Path("tmp_upset_reckoning_scope"))
    args = ap.parse_args()

    run_slug = str(args.runid).strip("/")
    und = str(args.undisturbed_scenario).strip() or "undisturbed"
    recurrence = [int(x) for x in str(args.recurrence).replace(" ", "").split(",") if x]

    out_dir: Path = args.out_dir
    out_dir.mkdir(parents=True, exist_ok=True)

    client = QueryEngineClient(base_url=str(args.base_url))
    outlet_wepp_id = _outlet_wepp_id(client, run_slug=run_slug, outlet_topaz_id=int(args.outlet_topaz_id))

    burned_qp = _chan_daily_qp(client, run_slug=run_slug, scenario=None, outlet_wepp_id=outlet_wepp_id)
    und_qp = _chan_daily_qp(client, run_slug=run_slug, scenario=und, outlet_wepp_id=outlet_wepp_id)

    burned_ebe = _ebe_daily_vp(client, run_slug=run_slug, scenario=None, outlet_wepp_id=outlet_wepp_id)
    und_ebe = _ebe_daily_vp(client, run_slug=run_slug, scenario=und, outlet_wepp_id=outlet_wepp_id)

    burned_daily = burned_ebe.merge(burned_qp[["year", "julian", "qp_m3s"]], on=["year", "julian"], how="inner")
    und_daily = und_ebe.merge(und_qp[["year", "julian", "qp_m3s"]], on=["year", "julian"], how="inner")

    burned_picks = _cta_pick_table(burned_qp, recurrence)
    und_picks = _cta_pick_table(und_qp, recurrence)

    (out_dir / "cta_rp_burned_vs_undisturbed.csv").write_text(
        burned_picks.merge(und_picks, on="return_period_yr", how="outer", suffixes=("_burned", "_undist")).to_csv(
            index=False
        ),
        encoding="utf-8",
    )

    _write_cta_rp_table(out_dir / "cta_rp_table.tex", burned_picks=burned_picks, und_picks=und_picks)

    union_dates = sorted(set(burned_picks["date"].tolist()) | set(und_picks["date"].tolist()))
    _write_union_date_compare_table(
        out_dir / "date_compare_table.tex",
        dates=union_dates,
        burned_daily=burned_daily,
        und_daily=und_daily,
    )

    meta = {
        "runid": run_slug,
        "undisturbed_scenario": und,
        "outlet_topaz_id": int(args.outlet_topaz_id),
        "outlet_wepp_id": int(outlet_wepp_id),
        "recurrence": recurrence,
        "generated": time.strftime("%Y-%m-%dT%H:%M:%S%z"),
    }
    (out_dir / "meta.json").write_text(pd.Series(meta).to_json(indent=2) + "\n", encoding="utf-8")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
