#!/usr/bin/env python3
"""Run a Hill 106 initial canopy-cover by ground-cover peak-flow matrix."""

from __future__ import annotations

import argparse
from concurrent.futures import ThreadPoolExecutor, as_completed
import shutil
import subprocess
import tempfile
from pathlib import Path

import pandas as pd

from analyze_hill106_ksat_mutation import read_element, read_water
from wepppy.wepp.management.managements import Management


COVER_LEVELS = (0.30, 0.55, 0.70, 0.80, 0.90, 0.95)
EXTRA_DATES = ("1980-02-14", "1986-02-15")


def case_name(canopy_cover: float, ground_cover: float) -> str:
    return f"c{round(canopy_cover * 100):02d}_g{round(ground_cover * 100):02d}"


def prepare_case(template: Path, root: Path, canopy_cover: float, ground_cover: float) -> Path:
    case = root / case_name(canopy_cover, ground_cover)
    runs = case / "runs"
    output = case / "output"
    shutil.copytree(template, runs)
    output.mkdir()

    management = Management.load(None, "p106.man", str(runs), None)
    initial = management.inis[0].data
    initial.cancov = canopy_cover
    initial.inrcov = ground_cover
    initial.rilcov = ground_cover
    (runs / "p106.man").write_text(str(management))
    return case


def run_case(binary: Path, case: Path) -> tuple[str, str]:
    with (case / "runs" / "p106.run").open("rb") as run_input:
        completed = subprocess.run(
            [binary],
            cwd=case / "runs",
            stdin=run_input,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    if completed.returncode != 0 or b"SUCCESSFULLY" not in completed.stdout:
        raise RuntimeError(
            f"{case.name} failed with {completed.returncode}: "
            f"{completed.stderr.decode(errors='replace')[-2000:]}"
        )
    return case.name, completed.stdout.decode(errors="replace")


def extract_case(case: Path, selected_dates: pd.DatetimeIndex) -> tuple[list[dict], dict]:
    canopy_cover = int(case.name[1:3]) / 100.0
    ground_cover = int(case.name[5:7]) / 100.0
    water = read_water(case / "output" / "H106.wat.dat")
    element = read_element(case / "output" / "H106.element.dat", int(water.year.min()))
    prior_water = water.soil_water.shift(1)

    rows: list[dict] = []
    for event_date in selected_dates:
        event = element.loc[event_date] if event_date in element.index else None
        rows.append(
            {
                "case": case.name,
                "initial_canopy_cover": canopy_cover,
                "initial_ground_cover": ground_cover,
                "event_date": event_date.date().isoformat(),
                "runoff_mm": 0.0 if event is None else event.runoff,
                "peak_ro_mm_h": 0.0 if event is None else event.peak_ro,
                "eff_int_mm_h": 0.0 if event is None else event.eff_int,
                "eff_dur_h": 0.0 if event is None else event.eff_dur,
                "keff_mm_h": 0.0 if event is None else event.keff,
                "event_soil_water_mm": pd.NA if event is None else event.sm,
                "event_lai": pd.NA if event is None else event.leaf_area,
                "event_canopy_height_m": pd.NA if event is None else event.can_hgt,
                "event_canopy_cover_pct": pd.NA if event is None else event.can_cov,
                "event_interrill_cover_pct": pd.NA if event is None else event.int_cov,
                "event_rill_cover_pct": pd.NA if event is None else event.ril_cov,
                "live_biomass_kg_m2": pd.NA if event is None else event.live_bio,
                "dead_biomass_kg_m2": pd.NA if event is None else event.dead_bio,
                "rill_width_m": pd.NA if event is None else event.ril_width,
                "pre_event_soil_water_mm": prior_water.get(event_date, pd.NA),
            }
        )

    year_2020 = water.loc[water.year == 2020]
    summary = {
        "case": case.name,
        "initial_canopy_cover": canopy_cover,
        "initial_ground_cover": ground_cover,
        "runoff_2020_mm": year_2020.runoff.sum(),
        "lateral_2020_mm": year_2020.lateral.sum(),
        "total_et_2020_mm": year_2020[["ep", "es", "er"]].sum().sum(),
        "mean_soil_water_2020_mm": year_2020.soil_water.mean(),
        "maximum_peak_ro_mm_h": element.peak_ro.max(),
        "median_positive_peak_ro_mm_h": element.loc[element.peak_ro > 0, "peak_ro"].median(),
    }
    return rows, summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--template", type=Path, required=True)
    parser.add_argument("--binary", type=Path, required=True)
    parser.add_argument("--selected-dates", type=Path, required=True)
    parser.add_argument("--events-output", type=Path, required=True)
    parser.add_argument("--summary-output", type=Path, required=True)
    parser.add_argument("--workers", type=int, default=8)
    args = parser.parse_args()

    selected = pd.read_csv(args.selected_dates, usecols=["event_date"])
    dates = list(pd.to_datetime(selected.event_date.unique()))
    dates.extend(pd.to_datetime(EXTRA_DATES))
    selected_dates = pd.DatetimeIndex(sorted(set(dates)))

    event_rows: list[dict] = []
    summary_rows: list[dict] = []
    with tempfile.TemporaryDirectory(prefix="topanga-h106-cover-matrix-") as temporary:
        root = Path(temporary)
        cases = [
            prepare_case(args.template, root, canopy, ground)
            for canopy in COVER_LEVELS
            for ground in COVER_LEVELS
        ]
        with ThreadPoolExecutor(max_workers=args.workers) as executor:
            futures = {executor.submit(run_case, args.binary, case): case for case in cases}
            for completed_count, future in enumerate(as_completed(futures), start=1):
                case = futures[future]
                future.result()
                rows, summary = extract_case(case, selected_dates)
                event_rows.extend(rows)
                summary_rows.append(summary)
                if completed_count % 10 == 0 or completed_count == len(cases):
                    print(f"completed {completed_count}/{len(cases)}")

    events = pd.DataFrame(event_rows).sort_values(
        ["event_date", "initial_canopy_cover", "initial_ground_cover"]
    )
    summary = pd.DataFrame(summary_rows).sort_values(
        ["initial_canopy_cover", "initial_ground_cover"]
    )
    events.to_csv(args.events_output, index=False, float_format="%.6f")
    summary.to_csv(args.summary_output, index=False, float_format="%.6f")


if __name__ == "__main__":
    main()
