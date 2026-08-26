#!/usr/bin/env python3
"""Replay Hill 106 and screen kslast × anisotropy against 2020 runoff."""

from __future__ import annotations

import argparse
import csv
import hashlib
import re
import shutil
import subprocess
import tempfile
from pathlib import Path

import matplotlib.pyplot as plt
import numpy as np


KSLAST_VALUES = (0.00011, 0.001, 0.003, 0.01, 0.03, 0.1, 0.3, 0.6, 1.0, 3.0)
ANISOTROPY_VALUES = (0.1, 0.3, 1.0, 3.0, 10.0, 30.0)
TARGET_RUNOFF_MM = 6.2
EXPECTED_BINARY_SHA256 = (
    "365d44d643f70c5eee54e0ea81e74a125003799df8c912bab9ff267c476308a8"
)


def parse_args() -> argparse.Namespace:
    here = Path(__file__).resolve()
    investigation = here.parents[1]
    repo = here.parents[4]
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--binary",
        type=Path,
        default=repo / "wepp_runner/bin/wepp_dcc52a6_hill",
    )
    parser.add_argument(
        "--fixture",
        type=Path,
        default=investigation / "fixtures/hill-106/weppcloud-undisturbed/runs",
    )
    parser.add_argument(
        "--output",
        type=Path,
        default=here.with_name("kslast-anisotropy-2020-matrix.csv"),
    )
    return parser.parse_args()


def mutate_soil(source: str, kslast: float, anisotropy: float) -> str:
    lines = source.splitlines()
    data_rows = [i for i, line in enumerate(lines) if line.startswith("\t")]
    if len(data_rows) != 2:
        raise ValueError(f"expected two horizon rows, found {len(data_rows)}")

    for index in data_rows:
        fields = lines[index].split()
        fields[3] = format(anisotropy, "g")
        lines[index] = "\t" + "\t ".join(fields)

    restrictive = [i for i, line in enumerate(lines) if re.fullmatch(r"1\s+10000\.0\s+\S+", line)]
    if len(restrictive) != 1:
        raise ValueError(f"expected one restrictive-layer row, found {len(restrictive)}")
    lines[restrictive[0]] = f"1 10000.0 {kslast:g}"
    return "\n".join(lines) + "\n"


def summarize_2020(water_file: Path) -> dict[str, float]:
    totals = {key: 0.0 for key in ("p", "q", "ep", "es", "er", "dp", "lat")}
    end_soil_water = 0.0
    days = 0
    for line in water_file.read_text().splitlines():
        fields = line.split()
        if len(fields) != 20 or fields[2] != "2020":
            continue
        days += 1
        totals["p"] += float(fields[3])
        totals["q"] += float(fields[5])
        totals["ep"] += float(fields[6])
        totals["es"] += float(fields[7])
        totals["er"] += float(fields[8])
        totals["dp"] += float(fields[9])
        totals["lat"] += float(fields[12])
        end_soil_water = float(fields[13])
    if days != 366:
        raise ValueError(f"expected 366 records for 2020, found {days}")
    return totals | {"end_soil_water": end_soil_water}


def run_case(binary: Path, fixture: Path, root: Path, kslast: float, anisotropy: float) -> dict[str, float]:
    tag = f"k{kslast:g}_a{anisotropy:g}".replace(".", "p")
    run_dir = root / tag / "runs"
    output_dir = root / tag / "output"
    run_dir.mkdir(parents=True)
    output_dir.mkdir()
    for name in (
        "p106.run",
        "p106.man",
        "p106.slp",
        "p106.cli",
        "pmetpara.txt",
        "wepp_ui.txt",
        "gwcoeff.txt",
        "snow.txt",
    ):
        shutil.copy2(fixture / name, run_dir / name)
    (run_dir / "p106.sol").write_text(
        mutate_soil((fixture / "p106.sol").read_text(), kslast, anisotropy)
    )
    with (run_dir / "p106.run").open("rb") as run_input:
        completed = subprocess.run(
            [binary],
            cwd=run_dir,
            stdin=run_input,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            check=False,
        )
    if completed.returncode:
        raise RuntimeError(
            f"{tag} failed with exit {completed.returncode}: "
            f"{completed.stderr.decode(errors='replace')[-1000:]}"
        )
    return summarize_2020(output_dir / "H106.wat.dat")


def plot_results(rows: list[dict[str, float]], output_dir: Path) -> None:
    def matrix(metric: str) -> np.ndarray:
        lookup = {(row["kslast_mm_h"], row["anisotropy"]): row[metric] for row in rows}
        return np.array(
            [[lookup[(kslast, anisotropy)] for kslast in KSLAST_VALUES] for anisotropy in ANISOTROPY_VALUES]
        )

    runoff = matrix("total_runoff_mm")
    surface = matrix("surface_runoff_mm")
    lateral = matrix("lateral_flow_mm")
    xlabels = [f"{value:g}" for value in KSLAST_VALUES]
    ylabels = [f"{value:g}" for value in ANISOTROPY_VALUES]

    fig, (heat_ax, line_ax) = plt.subplots(1, 2, figsize=(13, 5.4), constrained_layout=True)
    image = heat_ax.imshow(runoff, aspect="auto", cmap="viridis_r")
    for row_index in range(runoff.shape[0]):
        for column_index in range(runoff.shape[1]):
            heat_ax.text(column_index, row_index, f"{runoff[row_index, column_index]:.1f}",
                         ha="center", va="center", fontsize=7,
                         color="white" if runoff[row_index, column_index] > 70 else "black")
    best_index = np.unravel_index(np.argmin(abs(runoff - TARGET_RUNOFF_MM)), runoff.shape)
    heat_ax.scatter(best_index[1], best_index[0], marker="s", s=340, facecolors="none",
                    edgecolors="#e31a1c", linewidths=2)
    heat_ax.set_xticks(range(len(xlabels)), xlabels, rotation=45, ha="right")
    heat_ax.set_yticks(range(len(ylabels)), ylabels)
    heat_ax.set_xlabel("Restrictive-layer conductivity, kslast (mm/h)")
    heat_ax.set_ylabel("Anisotropy")
    heat_ax.set_title("2020 total runoff (surface + lateral), mm")
    fig.colorbar(image, ax=heat_ax, label="Runoff (mm)")

    for row_index, anisotropy in enumerate(ANISOTROPY_VALUES):
        line_ax.plot(KSLAST_VALUES, runoff[row_index], marker="o", label=f"{anisotropy:g}")
    line_ax.axhline(TARGET_RUNOFF_MM, color="#e31a1c", linestyle="--", label="6.2 mm target")
    line_ax.set_xscale("log")
    line_ax.set_xlabel("Restrictive-layer conductivity, kslast (mm/h)")
    line_ax.set_ylabel("2020 total runoff (mm)")
    line_ax.set_title("Response curves by anisotropy")
    line_ax.grid(alpha=0.25)
    line_ax.legend(title="Anisotropy", fontsize=8, ncol=2)
    for suffix in ("png", "svg"):
        fig.savefig(output_dir / f"kslast-anisotropy-total-runoff.{suffix}", dpi=180)
    plt.close(fig)

    fig, axes = plt.subplots(1, 2, figsize=(12, 4.8), constrained_layout=True)
    for ax, values, title in zip(
        axes,
        (surface, lateral),
        ("Surface runoff", "Lateral subsurface flow"),
        strict=True,
    ):
        image = ax.imshow(values, aspect="auto", cmap="magma_r")
        ax.set_xticks(range(len(xlabels)), xlabels, rotation=45, ha="right")
        ax.set_yticks(range(len(ylabels)), ylabels)
        ax.set_xlabel("kslast (mm/h)")
        ax.set_ylabel("Anisotropy")
        ax.set_title(f"2020 {title} (mm)")
        fig.colorbar(image, ax=ax, label="mm")
    for suffix in ("png", "svg"):
        fig.savefig(output_dir / f"kslast-anisotropy-runoff-components.{suffix}", dpi=180)
    plt.close(fig)


def main() -> None:
    args = parse_args()
    digest = hashlib.sha256(args.binary.read_bytes()).hexdigest()
    if digest != EXPECTED_BINARY_SHA256:
        raise ValueError(f"unexpected binary SHA-256: {digest}")

    rows = []
    with tempfile.TemporaryDirectory(prefix="topanga-kslast-anisotropy-") as tmp:
        root = Path(tmp)
        for kslast in KSLAST_VALUES:
            for anisotropy in ANISOTROPY_VALUES:
                values = run_case(args.binary, args.fixture, root, kslast, anisotropy)
                total_runoff = values["q"] + values["lat"]
                rows.append(
                    {
                        "kslast_mm_h": kslast,
                        "anisotropy": anisotropy,
                        "precip_mm": values["p"],
                        "surface_runoff_mm": values["q"],
                        "lateral_flow_mm": values["lat"],
                        "total_runoff_mm": total_runoff,
                        "target_error_mm": total_runoff - TARGET_RUNOFF_MM,
                        "transpiration_mm": values["ep"],
                        "soil_evaporation_mm": values["es"],
                        "residue_evaporation_mm": values["er"],
                        "total_et_mm": values["ep"] + values["es"] + values["er"],
                        "deep_percolation_printed_mm": values["dp"],
                        "end_soil_water_mm": values["end_soil_water"],
                    }
                )

    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("w", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=rows[0])
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "kslast_mm_h": f"{row['kslast_mm_h']:g}",
                    "anisotropy": f"{row['anisotropy']:g}",
                    "precip_mm": f"{row['precip_mm']:.2f}",
                    "surface_runoff_mm": f"{row['surface_runoff_mm']:.5f}",
                    "lateral_flow_mm": f"{row['lateral_flow_mm']:.2f}",
                    "total_runoff_mm": f"{row['total_runoff_mm']:.5f}",
                    "target_error_mm": f"{row['target_error_mm']:.5f}",
                    "transpiration_mm": f"{row['transpiration_mm']:.2f}",
                    "soil_evaporation_mm": f"{row['soil_evaporation_mm']:.2f}",
                    "residue_evaporation_mm": f"{row['residue_evaporation_mm']:.2f}",
                    "total_et_mm": f"{row['total_et_mm']:.2f}",
                    "deep_percolation_printed_mm": f"{row['deep_percolation_printed_mm']:.2f}",
                    "end_soil_water_mm": f"{row['end_soil_water_mm']:.2f}",
                }
            )
    plot_results(rows, args.output.parent)


if __name__ == "__main__":
    main()
