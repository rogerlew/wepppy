#!/usr/bin/env python3
from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable

import matplotlib
import numpy as np
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt


EBE_COLUMNS = [
    "day_of_month",
    "month",
    "simulation_year",
    "calendar_year",
    "precip_mm",
    "runoff_volume_m3",
    "peak_discharge_m3s",
    "sediment_yield_kg",
    "soluble_reactive_p_kg",
    "particulate_p_kg",
    "total_p_kg",
    "element_id",
]


def _parse_ebe_pw0_txt(path: Path, *, start_year: int | None) -> pd.DataFrame:
    rows: list[list[float | int | None]] = []
    with path.open("r", encoding="utf-8", errors="replace") as handle:
        for raw in handle:
            line = raw.strip()
            if (
                not line
                or line.startswith("WATERSHED")
                or line.startswith("(")
                or line.startswith("Day")
                or line.startswith("-")
                or line.startswith("Month")
                or line.startswith("Year")
            ):
                continue

            tokens = line.split()
            if len(tokens) not in (10, 11):
                continue

            day_of_month = int(tokens[0])
            month = int(tokens[1])
            sim_year = int(tokens[2])

            if start_year is not None and sim_year < 1000:
                calendar_year = start_year + sim_year - 1
            else:
                calendar_year = sim_year

            values = [
                day_of_month,
                month,
                sim_year,
                calendar_year,
                float(tokens[3]),
                float(tokens[4]),
                float(tokens[5]),
                float(tokens[6]),
                float(tokens[7]),
                float(tokens[8]),
                float(tokens[9]),
                int(tokens[10]) if len(tokens) == 11 else None,
            ]
            rows.append(values)

    df = pd.DataFrame(rows, columns=EBE_COLUMNS)
    if df.empty:
        raise ValueError(f"No EBE rows found in {path}")

    df["date_key"] = (
        df["calendar_year"].astype(int).astype(str).str.zfill(4)
        + "-"
        + df["month"].astype(int).astype(str).str.zfill(2)
        + "-"
        + df["day_of_month"].astype(int).astype(str).str.zfill(2)
    )
    df["event_id"] = np.arange(len(df), dtype=int)
    return df


def _weibull_series(
    recurrence: Iterable[float],
    years: float,
    *,
    method: str,
    gringorten_correction: bool,
) -> dict[float, int]:
    if years <= 0:
        raise ValueError("years must be > 0")

    method = method.lower()
    if method == "cta":
        count = int(round(years * 365.25))
    elif method == "am":
        count = int(round(years))
    else:
        raise ValueError('method must be either "cta" or "am"')

    ranks = np.arange(1, count + 1, dtype=float)
    if gringorten_correction:
        periods = (count + 1.0) / (ranks - 0.44)
    else:
        periods = (count + 1.0) / ranks

    if method == "cta":
        periods /= 365.25

    result: dict[float, int] = {}
    for target in sorted(float(x) for x in recurrence):
        for rank, period in zip(ranks[::-1], periods[::-1], strict=False):
            index = int(rank - 1)
            if period >= target and index not in result.values():
                result[target] = index
                break
    return result


@dataclass(frozen=True)
class ReturnPeriodRow:
    recurrence_years: int
    weibull_rank: int
    weibull_t_years: float
    date_key: str
    peak_discharge_m3s: float


def _return_period_rows_for_peak_discharge(
    events: pd.DataFrame,
    *,
    recurrence: tuple[int, ...],
    method: str,
    gringorten_correction: bool,
) -> tuple[list[ReturnPeriodRow], pd.DataFrame]:
    method = method.lower()
    if method not in {"cta", "am"}:
        raise ValueError("method must be cta or am")

    df = events.copy()
    df = df.dropna(subset=["peak_discharge_m3s"])

    years = sorted(int(y) for y in df["calendar_year"].dropna().unique())
    if not years:
        raise ValueError("No year values present in events")
    years_count = len(set(years))

    total_events = len(df)
    days_in_year = total_events / max(years_count, 1)

    ranked = df.sort_values(["peak_discharge_m3s", "event_id"], ascending=[False, True]).reset_index(drop=True)

    if method == "am":
        ranked = (
            ranked.sort_values(["calendar_year", "peak_discharge_m3s"], ascending=[True, False])
            .groupby("calendar_year", as_index=False, sort=False)
            .head(1)
            .sort_values(["peak_discharge_m3s", "event_id"], ascending=[False, True])
            .reset_index(drop=True)
        )

    ranked["weibull_rank"] = ranked.index + 1
    if days_in_year > 0:
        ranked["weibull_T_years"] = ((total_events + 1) / ranked["weibull_rank"]) / days_in_year
    else:
        ranked["weibull_T_years"] = np.nan

    rec_map = _weibull_series(
        recurrence,
        years_count,
        method=method,
        gringorten_correction=gringorten_correction,
    )

    rows: list[ReturnPeriodRow] = []
    for ret in sorted(recurrence, reverse=True):
        idx = rec_map.get(float(ret))
        if idx is None or idx >= len(ranked):
            continue
        r = ranked.iloc[int(idx)]
        rows.append(
            ReturnPeriodRow(
                recurrence_years=int(ret),
                weibull_rank=int(r["weibull_rank"]),
                weibull_t_years=float(r["weibull_T_years"]),
                date_key=str(r["date_key"]),
                peak_discharge_m3s=float(r["peak_discharge_m3s"]),
            )
        )

    return rows, ranked[["date_key", "calendar_year", "peak_discharge_m3s", "weibull_rank", "weibull_T_years"]].copy()


def _overlay_histogram(
    *,
    burned: pd.Series,
    unburned: pd.Series,
    out_path: Path,
    title: str,
) -> None:
    burned = burned.dropna()
    unburned = unburned.dropna()

    fig, ax = plt.subplots(figsize=(9, 5.2), constrained_layout=True)
    bins = 40
    ax.hist(burned.values, bins=bins, alpha=0.55, label="Burned", color="#ff3b30", edgecolor="white")
    ax.hist(unburned.values, bins=bins, alpha=0.55, label="Undisturbed", color="#1e90ff", edgecolor="white")
    ax.set_xlabel("Peak discharge (m³/s)")
    ax.set_ylabel("Event count")
    ax.set_title(title)
    ax.legend()
    ax.grid(True, axis="y", alpha=0.25)
    fig.savefig(out_path, dpi=200)
    plt.close(fig)


def _join_by_date(burned: pd.DataFrame, unburned: pd.DataFrame) -> pd.DataFrame:
    b = burned.rename(
        columns={
            "peak_discharge_m3s": "burned_peak_discharge_m3s",
            "weibull_rank": "burned_rank",
            "weibull_T_years": "burned_weibull_T_years",
        }
    )
    u = unburned.rename(
        columns={
            "peak_discharge_m3s": "undisturbed_peak_discharge_m3s",
            "weibull_rank": "undisturbed_rank",
            "weibull_T_years": "undisturbed_weibull_T_years",
        }
    )
    merged = pd.merge(u, b, on="date_key", how="outer").sort_values("date_key")
    return merged


def _fmt_rows(rows: list[ReturnPeriodRow]) -> pd.DataFrame:
    return pd.DataFrame(
        [
            {
                "Recurrence Interval (years)": r.recurrence_years,
                "Weibull Rank": r.weibull_rank,
                "Weibull T (years)": r.weibull_t_years,
                "Date": r.date_key,
                "Peak Discharge (m3/s)": r.peak_discharge_m3s,
            }
            for r in rows
        ]
    ).sort_values("Recurrence Interval (years)", ascending=False)


def main(argv: list[str]) -> int:
    parser = argparse.ArgumentParser(
        description="Compare peak-discharge return periods between two WEPPcloud scenarios using ebe_pw0.txt exports.",
    )
    parser.add_argument("--burned-ebe", required=True, help="Path to burned scenario ebe_pw0.txt")
    parser.add_argument("--undisturbed-ebe", required=True, help="Path to undisturbed scenario ebe_pw0.txt")
    parser.add_argument("--start-year", type=int, default=None, help="Calendar start year (only needed if ebe uses simulation years 1..N)")
    parser.add_argument("--out-dir", default="return_period_compare_out", help="Output directory")
    parser.add_argument("--recurrence", default="2,5,10", help="Comma-separated recurrence years (default: 2,5,10)")
    parser.add_argument("--gringorten", action="store_true", help="Use Gringorten correction (matches many WEPPcloud defaults)")
    args = parser.parse_args(argv)

    recurrence = tuple(int(x.strip()) for x in str(args.recurrence).split(",") if x.strip())
    if not recurrence:
        raise ValueError("No recurrence intervals provided")

    out_dir = Path(args.out_dir)
    out_dir.mkdir(parents=True, exist_ok=True)

    burned_events = _parse_ebe_pw0_txt(Path(args.burned_ebe), start_year=args.start_year)
    undisturbed_events = _parse_ebe_pw0_txt(Path(args.undisturbed_ebe), start_year=args.start_year)

    burned_cta_rows, burned_cta_ranked = _return_period_rows_for_peak_discharge(
        burned_events,
        recurrence=recurrence,
        method="cta",
        gringorten_correction=bool(args.gringorten),
    )
    undisturbed_cta_rows, undisturbed_cta_ranked = _return_period_rows_for_peak_discharge(
        undisturbed_events,
        recurrence=recurrence,
        method="cta",
        gringorten_correction=bool(args.gringorten),
    )

    burned_am_rows, burned_am_ranked = _return_period_rows_for_peak_discharge(
        burned_events,
        recurrence=recurrence,
        method="am",
        gringorten_correction=bool(args.gringorten),
    )
    undisturbed_am_rows, undisturbed_am_ranked = _return_period_rows_for_peak_discharge(
        undisturbed_events,
        recurrence=recurrence,
        method="am",
        gringorten_correction=bool(args.gringorten),
    )

    burned_cta_df = _fmt_rows(burned_cta_rows)
    undisturbed_cta_df = _fmt_rows(undisturbed_cta_rows)
    burned_am_df = _fmt_rows(burned_am_rows)
    undisturbed_am_df = _fmt_rows(undisturbed_am_rows)

    burned_cta_df.to_csv(out_dir / "burned_cta_return_periods_peak_discharge.csv", index=False)
    undisturbed_cta_df.to_csv(out_dir / "undisturbed_cta_return_periods_peak_discharge.csv", index=False)
    burned_am_df.to_csv(out_dir / "burned_am_return_periods_peak_discharge.csv", index=False)
    undisturbed_am_df.to_csv(out_dir / "undisturbed_am_return_periods_peak_discharge.csv", index=False)

    # Rank tables for side-by-side date comparisons.
    burned_cta_ranked.to_csv(out_dir / "burned_cta_rank_table_peak_discharge.csv", index=False)
    undisturbed_cta_ranked.to_csv(out_dir / "undisturbed_cta_rank_table_peak_discharge.csv", index=False)
    _join_by_date(burned_cta_ranked, undisturbed_cta_ranked).to_csv(
        out_dir / "cta_event_date_comparison_peak_discharge.csv",
        index=False,
    )

    burned_am_ranked.to_csv(out_dir / "burned_am_rank_table_peak_discharge.csv", index=False)
    undisturbed_am_ranked.to_csv(out_dir / "undisturbed_am_rank_table_peak_discharge.csv", index=False)
    _join_by_date(burned_am_ranked, undisturbed_am_ranked).to_csv(
        out_dir / "am_event_date_comparison_peak_discharge.csv",
        index=False,
    )

    _overlay_histogram(
        burned=burned_events["peak_discharge_m3s"],
        unburned=undisturbed_events["peak_discharge_m3s"],
        out_path=out_dir / "peak_discharge_hist_overlay.png",
        title="Peak discharge event distribution (ebe_pw0.txt)",
    )

    summary = {
        "burned": {
            "events": int(len(burned_events)),
            "years": int(burned_events["calendar_year"].nunique()),
            "events_per_year": float(len(burned_events) / max(1, burned_events["calendar_year"].nunique())),
        },
        "undisturbed": {
            "events": int(len(undisturbed_events)),
            "years": int(undisturbed_events["calendar_year"].nunique()),
            "events_per_year": float(len(undisturbed_events) / max(1, undisturbed_events["calendar_year"].nunique())),
        },
        "note": (
            "For return periods <= 10 years, CTA/PDS-style methods are typically preferred when there are "
            "multiple runoff events per year (events_per_year > 1). Use the generated CTA vs AM tables to "
            "see whether the short-return-period peaks are sensitive to method for this climate/run."
        ),
    }
    (out_dir / "summary.json").write_text(json.dumps(summary, indent=2) + "\n", encoding="utf-8")

    return 0


if __name__ == "__main__":
    import sys

    raise SystemExit(main(sys.argv[1:]))
