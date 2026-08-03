#!/usr/bin/env python3
"""Add a canonical forest-high-severity scenario to the hillslope fixture."""

from __future__ import annotations

import argparse
import csv
import hashlib
import shutil
from pathlib import Path

from wepppy.wepp.management import get_management
from wepppy.wepp.soils.utils.wepp_soil_util import WeppSoilUtil


DEFAULT_FIXTURE = Path("/wc1/ablation/stevens-canyon-peak-flow-20260803-hillslopes")
LOOKUP = Path(
    "wepppy/nodb/mods/disturbed/data/disturbed_land_soil_lookup.csv"
)
ALL_HILLSLOPES = tuple(range(49, 62))
HIGH_SEVERITY_FOREST = (50, 51, 52, 53, 54, 55, 56, 58, 59, 60, 61)
UNCHANGED_CONTROLS = (49, 57)
SIDECARS = (
    "gwcoeff.txt",
    "snow.txt",
    "pmetpara.txt",
    "wepp_ui.txt",
    "chntyp.txt",
    "tc.txt",
    "chan.inp",
)


def file_hash(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def lookup_rows() -> dict[tuple[str, str], dict[str, str]]:
    with LOOKUP.open(newline="", encoding="utf-8") as stream:
        rows = list(csv.DictReader(stream))
    return {(row["stext"], row["luse"]): row for row in rows}


def build_management(row: dict[str, str]) -> str:
    management = get_management(105, _map="ca-disturbed").build_multiple_year_man(100)
    for key, value in row.items():
        if value.strip() and (key.startswith("plant.data.") or key.startswith("ini.data.")):
            management[key] = value
    return str(management)


def add_pmet_entry(path: Path) -> None:
    lines = path.read_text(encoding="utf-8").splitlines()
    count = int(lines[0])
    if any(line.startswith("Tah_6892,") for line in lines[1:]):
        return
    lines[0] = str(count + 1)
    lines.append(
        f"Tah_6892,0.95,0.8,{count + 1},forest_high_sev_fire_fixture"
    )
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def stage(fixture_root: Path) -> None:
    source = fixture_root / "undisturbed" / "wepp" / "runs"
    scenario_root = fixture_root / "high_severity" / "wepp"
    destination = scenario_root / "runs"
    output = scenario_root / "output"

    if not source.is_dir():
        raise FileNotFoundError(f"missing undisturbed fixture: {source}")
    if destination.exists():
        shutil.rmtree(destination)
    if output.exists():
        shutil.rmtree(output)
    destination.mkdir(parents=True)
    output.mkdir(parents=True)

    for hillslope_id in ALL_HILLSLOPES:
        for extension in ("run", "man", "slp", "cli", "sol"):
            shutil.copy2(
                source / f"p{hillslope_id}.{extension}",
                destination / f"p{hillslope_id}.{extension}",
            )
    for sidecar in SIDECARS:
        shutil.copy2(source / sidecar, destination / sidecar)

    rows = lookup_rows()
    manifest_lines = [
        "hillslope_id,role,texture,management_class,soil_class",
    ]
    for hillslope_id in HIGH_SEVERITY_FOREST:
        source_soil = source / f"p{hillslope_id}.sol"
        soil = WeppSoilUtil(str(source_soil))
        texture = soil.simple_texture
        row = dict(rows[(texture, "forest high sev fire")])

        (destination / f"p{hillslope_id}.man").write_text(
            build_management(row), encoding="utf-8"
        )
        disturbed_soil = soil.to_over9000(
            row,
            h0_max_om=None,
            version=9002,
            recompute_wp_fc_using_rosetta_on_bd_override=False,
        )
        disturbed_soil.write(str(destination / f"p{hillslope_id}.sol"))
        manifest_lines.append(
            f"{hillslope_id},high_severity_forest,{texture},"
            "forest high sev fire,forest high sev fire"
        )

    for hillslope_id in UNCHANGED_CONTROLS:
        texture = WeppSoilUtil(str(source / f"p{hillslope_id}.sol")).simple_texture
        manifest_lines.append(
            f"{hillslope_id},unchanged_control,{texture},undisturbed,undisturbed"
        )

    add_pmet_entry(destination / "pmetpara.txt")
    (scenario_root / "fixture_manifest.csv").write_text(
        "\n".join(manifest_lines) + "\n", encoding="utf-8"
    )

    for sidecar in SIDECARS:
        if not (destination / sidecar).exists():
            raise RuntimeError(f"missing required sidecar: {sidecar}")
    if (destination / "wepp_ui.txt").stat().st_size != 0:
        raise RuntimeError("wepp_ui.txt must be the zero-byte hourly-water-balance flag")
    for hillslope_id in UNCHANGED_CONTROLS:
        for extension in ("man", "sol"):
            name = f"p{hillslope_id}.{extension}"
            if file_hash(source / name) != file_hash(destination / name):
                raise RuntimeError(f"control changed unexpectedly: {name}")

    print(f"Staged high-severity fixture at {scenario_root}")
    print(f"High-severity forest hillslopes: {HIGH_SEVERITY_FOREST}")
    print(f"Unchanged controls: {UNCHANGED_CONTROLS}")


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("fixture_root", nargs="?", type=Path, default=DEFAULT_FIXTURE)
    args = parser.parse_args()
    stage(args.fixture_root)


if __name__ == "__main__":
    main()
