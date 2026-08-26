#!/usr/bin/env python3
"""Screen anisotropy × PMET Kcb at fixed Hill 106 Ksat and kslast."""

from __future__ import annotations

import argparse
import csv
import hashlib
import shutil
import subprocess
import tempfile
from datetime import date, timedelta
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np

from run_kslast_anisotropy_matrix import EXPECTED_BINARY_SHA256, TARGET_RUNOFF_MM


FIXED_KSLAST_MM_H = 0.6
FIXED_KSAT_MM_H = (35.0, 32.4)
ANISOTROPY_VALUES = (1.0, 2.0, 3.0, 5.0, 7.5, 10.0)
KCB_VALUES = (0.85, 0.90, 0.95, 1.00, 1.05, 1.10, 1.15, 1.20)
TARGET_CROP = "Tah_9591"


def parse_args() -> argparse.Namespace:
    here = Path(__file__).resolve()
    investigation = here.parents[1]
    repo = here.parents[4]
    parser = argparse.ArgumentParser()
    parser.add_argument("--binary", type=Path, default=repo / "wepp_runner/bin/wepp_dcc52a6_hill")
    parser.add_argument(
        "--fixture",
        type=Path,
        default=investigation / "fixtures/hill-106/weppcloud-undisturbed/runs",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=here.with_name("fixed-ksat-anisotropy-kcb-2020-matrix.csv"),
    )
    return parser.parse_args()


def mutate_soil(source: str, anisotropy: float) -> str:
    lines = source.splitlines()
    horizon_rows = [index for index, line in enumerate(lines) if line.startswith("\t")]
    if len(horizon_rows) != 2:
        raise ValueError(f"expected two horizon rows, found {len(horizon_rows)}")
    for row_number, index in enumerate(horizon_rows):
        fields = lines[index].split()
        if float(fields[2]) != FIXED_KSAT_MM_H[row_number]:
            raise ValueError(f"unexpected horizon Ksat: {fields[2]}")
        fields[3] = f"{anisotropy:g}"
        lines[index] = "\t" + "\t ".join(fields)
    restrictive_rows = [
        index for index, line in enumerate(lines) if line.split()[:2] == ["1", "10000.0"]
    ]
    if len(restrictive_rows) != 1:
        raise ValueError(f"expected one restrictive-layer row, found {len(restrictive_rows)}")
    lines[restrictive_rows[0]] = f"1 10000.0 {FIXED_KSLAST_MM_H:g}"
    return "\n".join(lines) + "\n"


def mutate_pmet(source: str, kcb: float) -> str:
    lines = source.splitlines()
    changed = 0
    for index, line in enumerate(lines[1:], start=1):
        fields = line.split(",")
        if fields[0] != TARGET_CROP:
            continue
        fields[1] = f"{kcb:g}"
        lines[index] = ",".join(fields)
        changed += 1
    if changed == 0:
        raise ValueError(f"no {TARGET_CROP} PMET records found")
    return "\n".join(lines) + "\n"


def summarize_2020(water_file: Path) -> tuple[dict[str, float], list[dict[str, float]]]:
    totals = {key: 0.0 for key in ("p", "q", "ep", "es", "er", "dp", "lat")}
    monthly = {
        month: {key: 0.0 for key in ("p", "q", "ep", "es", "er", "dp", "lat")}
        for month in range(1, 13)
    }
    days = 0
    end_soil_water = 0.0
    for line in water_file.read_text().splitlines():
        fields = line.split()
        if len(fields) != 20 or fields[2] != "2020":
            continue
        days += 1
        month = (date(2020, 1, 1) + timedelta(days=int(fields[1]) - 1)).month
        values = {
            "p": float(fields[3]), "q": float(fields[5]), "ep": float(fields[6]),
            "es": float(fields[7]), "er": float(fields[8]), "dp": float(fields[9]),
            "lat": float(fields[12]),
        }
        for key, value in values.items():
            totals[key] += value
            monthly[month][key] += value
        end_soil_water = float(fields[13])
    if days != 366:
        raise ValueError(f"expected 366 records for 2020, found {days}")
    return totals | {"end_soil_water": end_soil_water}, [monthly[month] for month in range(1, 13)]


def run_case(
    binary: Path, fixture: Path, root: Path, anisotropy: float, kcb: float
) -> tuple[dict[str, float], list[dict[str, float]]]:
    tag = f"a{anisotropy:g}_kcb{kcb:g}".replace(".", "p")
    run_dir = root / tag / "runs"
    output_dir = root / tag / "output"
    run_dir.mkdir(parents=True)
    output_dir.mkdir()
    for name in (
        "p106.run", "p106.man", "p106.slp", "p106.cli", "wepp_ui.txt",
        "gwcoeff.txt", "snow.txt",
    ):
        shutil.copy2(fixture / name, run_dir / name)
    (run_dir / "p106.sol").write_text(mutate_soil((fixture / "p106.sol").read_text(), anisotropy))
    (run_dir / "pmetpara.txt").write_text(mutate_pmet((fixture / "pmetpara.txt").read_text(), kcb))
    with (run_dir / "p106.run").open("rb") as run_input:
        completed = subprocess.run(
            [binary], cwd=run_dir, stdin=run_input,
            stdout=subprocess.PIPE, stderr=subprocess.PIPE, check=False,
        )
    if completed.returncode:
        raise RuntimeError(
            f"{tag} failed with exit {completed.returncode}: "
            f"{completed.stderr.decode(errors='replace')[-1000:]}"
        )
    return summarize_2020(output_dir / "H106.wat.dat")


def plot_results(
    rows: list[dict[str, float]], monthly_rows: list[dict[str, float]], output_dir: Path
) -> None:
    lookup = {(row["anisotropy"], row["kcb"]): row for row in rows}
    runoff = np.array([
        [lookup[(anisotropy, kcb)]["total_runoff_mm"] for kcb in KCB_VALUES]
        for anisotropy in ANISOTROPY_VALUES
    ])
    fig, (heat_ax, line_ax) = plt.subplots(1, 2, figsize=(13, 5.3), constrained_layout=True)
    image = heat_ax.imshow(runoff, aspect="auto", cmap="viridis_r")
    for row_index in range(runoff.shape[0]):
        for column_index in range(runoff.shape[1]):
            heat_ax.text(column_index, row_index, f"{runoff[row_index, column_index]:.1f}",
                         ha="center", va="center", fontsize=8)
    best = np.unravel_index(np.argmin(abs(runoff - TARGET_RUNOFF_MM)), runoff.shape)
    heat_ax.scatter(best[1], best[0], marker="s", s=340, facecolors="none",
                    edgecolors="#e31a1c", linewidths=2)
    heat_ax.set_xticks(range(len(KCB_VALUES)), [f"{value:g}" for value in KCB_VALUES])
    heat_ax.set_yticks(range(len(ANISOTROPY_VALUES)), [f"{value:g}" for value in ANISOTROPY_VALUES])
    heat_ax.set_xlabel("PMET Kcb")
    heat_ax.set_ylabel("Anisotropy")
    heat_ax.set_title("2020 total runoff (surface + lateral), mm")
    fig.colorbar(image, ax=heat_ax, label="Runoff (mm)")
    for row_index, anisotropy in enumerate(ANISOTROPY_VALUES):
        line_ax.plot(KCB_VALUES, runoff[row_index], marker="o", label=f"{anisotropy:g}")
    line_ax.axhline(TARGET_RUNOFF_MM, color="#e31a1c", linestyle="--", label="6.2 mm target")
    line_ax.set_xlabel("PMET Kcb")
    line_ax.set_ylabel("2020 total runoff (mm)")
    line_ax.set_title("Response curves at fixed Ksat and kslast")
    line_ax.grid(alpha=0.25)
    line_ax.legend(title="Anisotropy", fontsize=8, ncol=2)
    for suffix in ("png", "svg"):
        fig.savefig(output_dir / f"fixed-ksat-anisotropy-kcb-total-runoff.{suffix}", dpi=180)
    plt.close(fig)

    best_row = min(rows, key=lambda row: abs(row["target_error_mm"]))
    reference = next(row for row in rows if row["anisotropy"] == 10.0 and row["kcb"] == 0.95)
    selected = {
        "Kcb 0.95, anisotropy 10": (reference["anisotropy"], reference["kcb"]),
        f"Kcb {best_row['kcb']:g}, anisotropy {best_row['anisotropy']:g}":
            (best_row["anisotropy"], best_row["kcb"]),
    }
    fig, (runoff_ax, et_ax) = plt.subplots(2, 1, figsize=(10, 7), sharex=True, constrained_layout=True)
    months = np.arange(1, 13)
    for label, key in selected.items():
        case = sorted(
            (row for row in monthly_rows if (row["anisotropy"], row["kcb"]) == key),
            key=lambda row: row["month"],
        )
        runoff_ax.plot(months, [row["total_runoff_mm"] for row in case], marker="o", label=label)
        et_ax.plot(months, [row["total_et_mm"] for row in case], marker="o", label=label)
    runoff_ax.set_ylabel("Runoff (mm/month)")
    runoff_ax.set_title("2020 monthly response")
    runoff_ax.grid(alpha=0.25)
    runoff_ax.legend(fontsize=8)
    et_ax.set_ylabel("ET (mm/month)")
    et_ax.set_xlabel("Month")
    et_ax.set_xticks(months)
    et_ax.grid(alpha=0.25)
    for suffix in ("png", "svg"):
        fig.savefig(output_dir / f"fixed-ksat-anisotropy-kcb-monthly.{suffix}", dpi=180)
    plt.close(fig)


def main() -> None:
    args = parse_args()
    digest = hashlib.sha256(args.binary.read_bytes()).hexdigest()
    if digest != EXPECTED_BINARY_SHA256:
        raise ValueError(f"unexpected binary SHA-256: {digest}")
    rows: list[dict[str, float]] = []
    monthly_rows: list[dict[str, float]] = []
    with tempfile.TemporaryDirectory(prefix="topanga-anisotropy-kcb-") as tmp:
        root = Path(tmp)
        for anisotropy in ANISOTROPY_VALUES:
            for kcb in KCB_VALUES:
                values, months = run_case(args.binary, args.fixture, root, anisotropy, kcb)
                total_runoff = values["q"] + values["lat"]
                rows.append({
                    "kslast_mm_h": FIXED_KSLAST_MM_H,
                    "upper_ksat_mm_h": FIXED_KSAT_MM_H[0],
                    "minimum_ksat_mm_h": FIXED_KSAT_MM_H[1],
                    "anisotropy": anisotropy, "kcb": kcb, "precip_mm": values["p"],
                    "surface_runoff_mm": values["q"], "lateral_flow_mm": values["lat"],
                    "total_runoff_mm": total_runoff,
                    "target_error_mm": total_runoff - TARGET_RUNOFF_MM,
                    "transpiration_mm": values["ep"], "soil_evaporation_mm": values["es"],
                    "total_et_mm": values["ep"] + values["es"] + values["er"],
                    "deep_percolation_printed_mm": values["dp"],
                    "end_soil_water_mm": values["end_soil_water"],
                })
                for month, monthly in enumerate(months, start=1):
                    monthly_rows.append({
                        "anisotropy": anisotropy, "kcb": kcb, "month": month,
                        "precip_mm": monthly["p"], "surface_runoff_mm": monthly["q"],
                        "lateral_flow_mm": monthly["lat"],
                        "total_runoff_mm": monthly["q"] + monthly["lat"],
                        "total_et_mm": monthly["ep"] + monthly["es"] + monthly["er"],
                        "deep_percolation_printed_mm": monthly["dp"],
                    })
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0])
        writer.writeheader()
        for row in rows:
            writer.writerow({
                "kslast_mm_h": f"{row['kslast_mm_h']:g}",
                "upper_ksat_mm_h": f"{row['upper_ksat_mm_h']:.2f}",
                "minimum_ksat_mm_h": f"{row['minimum_ksat_mm_h']:.2f}",
                "anisotropy": f"{row['anisotropy']:g}", "kcb": f"{row['kcb']:g}",
                "precip_mm": f"{row['precip_mm']:.2f}",
                "surface_runoff_mm": f"{row['surface_runoff_mm']:.5f}",
                "lateral_flow_mm": f"{row['lateral_flow_mm']:.2f}",
                "total_runoff_mm": f"{row['total_runoff_mm']:.5f}",
                "target_error_mm": f"{row['target_error_mm']:.5f}",
                "transpiration_mm": f"{row['transpiration_mm']:.2f}",
                "soil_evaporation_mm": f"{row['soil_evaporation_mm']:.2f}",
                "total_et_mm": f"{row['total_et_mm']:.2f}",
                "deep_percolation_printed_mm": f"{row['deep_percolation_printed_mm']:.2f}",
                "end_soil_water_mm": f"{row['end_soil_water_mm']:.2f}",
            })
    monthly_output = args.output.with_name(args.output.stem + "-monthly.csv")
    with monthly_output.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=monthly_rows[0])
        writer.writeheader()
        for row in monthly_rows:
            writer.writerow({
                "anisotropy": f"{row['anisotropy']:g}", "kcb": f"{row['kcb']:g}",
                "month": int(row["month"]), "precip_mm": f"{row['precip_mm']:.2f}",
                "surface_runoff_mm": f"{row['surface_runoff_mm']:.5f}",
                "lateral_flow_mm": f"{row['lateral_flow_mm']:.2f}",
                "total_runoff_mm": f"{row['total_runoff_mm']:.5f}",
                "total_et_mm": f"{row['total_et_mm']:.2f}",
                "deep_percolation_printed_mm": f"{row['deep_percolation_printed_mm']:.2f}",
            })
    plot_results(rows, monthly_rows, args.output.parent)


if __name__ == "__main__":
    main()
