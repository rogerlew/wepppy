"""Build the Tenerife CLIGEN station catalog from Tenerife metadata and `.par` files."""

from __future__ import annotations

import argparse
import csv
import shutil
import sqlite3
from pathlib import Path

import numpy as np


DEFAULT_OUTPUT_DIR = Path(__file__).resolve().parents[1]
DEFAULT_SOURCE_CLIMATE_DIR = DEFAULT_OUTPUT_DIR
TARGET_DB_NAME = "tenerife_stations.db"
TARGET_PAR_DIR_NAME = "tenerife_par_files"
SOURCE_CSV_NAME = "tenerife_stations.csv"
SOURCE_PAR_DIR_NAME = "tenerife_par_files"
STATE_CODE = "TF"
STATE_NAME = "Tenerife"


def _parse_station_header(par_path: Path) -> tuple[float, int, float, float, float]:
    with par_path.open(encoding="utf-8", errors="replace") as handle:
        handle.readline()
        line1 = handle.readline().replace("LATT=", "").replace("LONG=", "").replace("YEARS=", "").replace("TYPE=", "")
        lat_str, lon_str, years_str, station_type_str = line1.split()

        line2 = handle.readline().replace("ELEVATION", "").replace("=", "").replace("TP5", "").replace("TP6", "")
        elevation_str, tp5_str, tp6_str = line2.split()

    return (
        float(years_str),
        int(station_type_str),
        float(elevation_str),
        float(tp5_str),
        float(tp6_str),
    )


def _annual_ppt(par_path: Path) -> float:
    lines = par_path.read_text(encoding="utf-8", errors="replace").splitlines()
    ppts = np.array([float(value) for value in lines[3].split()[-12:]], dtype=float)
    pwws = np.array([float(value) for value in lines[6].split()[-12:]], dtype=float)
    pwds = np.array([float(value) for value in lines[7].split()[-12:]], dtype=float)
    den = np.maximum(0.01, 1.0 - pwws + pwds)
    mdays = np.array([31, 28.25, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31], dtype=float)
    nwds = np.minimum(mdays, mdays * (pwds / den))
    return float(sum(ppt * nwd for ppt, nwd in zip(ppts, nwds)))


def _load_station_rows(csv_path: Path) -> list[dict[str, str]]:
    with csv_path.open(newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        return list(reader)


def _copy_station_par_files(source_dir: Path, target_dir: Path, rows: list[dict[str, str]]) -> list[Path]:
    target_dir.mkdir(parents=True, exist_ok=True)
    copied_paths: list[Path] = []

    for row in rows:
        par_name = f"Estacion_{row['id_weatherstation']}_{row['name']}.par"
        src = source_dir / par_name
        if not src.exists():
            raise FileNotFoundError(src)
        dst = target_dir / par_name
        shutil.copyfile(src, dst)
        copied_paths.append(dst)

    return copied_paths


def _station_description(row: dict[str, str]) -> str:
    parts = [row["name"]]
    place = row.get("place") or ""
    municipality = row.get("municipality_name") or ""
    if place:
        parts.append(place)
    if municipality:
        parts.append(municipality)
    return " - ".join(parts)


def build_tenerife_catalog(source_climate_dir: Path, output_dir: Path) -> tuple[Path, Path]:
    stations_csv = source_climate_dir / SOURCE_CSV_NAME
    if not stations_csv.exists():
        stations_csv = source_climate_dir / "stations.csv"

    source_par_dir = source_climate_dir / SOURCE_PAR_DIR_NAME
    if not source_par_dir.exists():
        source_par_dir = source_climate_dir / "station_par_files"

    target_par_dir = output_dir / TARGET_PAR_DIR_NAME
    target_db = output_dir / TARGET_DB_NAME
    target_csv = output_dir / SOURCE_CSV_NAME

    rows = _load_station_rows(stations_csv)

    if stations_csv.resolve() != target_csv.resolve():
        shutil.copyfile(stations_csv, target_csv)

    if source_par_dir.resolve() == target_par_dir.resolve():
        if not target_par_dir.exists():
            raise FileNotFoundError(target_par_dir)
        by_name = {path.name: path for path in target_par_dir.glob("*.par")}
    else:
        if target_par_dir.exists():
            shutil.rmtree(target_par_dir)
        target_par_dir.mkdir(parents=True, exist_ok=True)
        copied_paths = _copy_station_par_files(source_par_dir, target_par_dir, rows)
        by_name = {path.name: path for path in copied_paths}

    if target_db.exists():
        target_db.unlink()

    conn = sqlite3.connect(target_db)
    cursor = conn.cursor()
    cursor.execute(
        """
        CREATE TABLE stations
            (state text, desc text, par text, latitude real, longitude real, years real,
             type integer, elevation real, tp5 real, tp6 real, annual_ppt real)
        """
    )
    cursor.execute(
        """
        CREATE TABLE states
            (state_code text, state_name text)
        """
    )

    station_records = []
    for row in rows:
        par_name = f"Estacion_{row['id_weatherstation']}_{row['name']}.par"
        par_path = by_name[par_name]
        years, station_type, elevation, tp5, tp6 = _parse_station_header(par_path)
        annual_ppt = _annual_ppt(par_path)
        station_records.append(
            (
                STATE_CODE,
                _station_description(row),
                par_name,
                float(row["latitude"]),
                float(row["longitude"]),
                years,
                station_type,
                elevation,
                tp5,
                tp6,
                annual_ppt,
            )
        )

    cursor.executemany("INSERT INTO stations VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)", station_records)
    cursor.execute("INSERT INTO states VALUES (?, ?)", (STATE_CODE, STATE_NAME))
    conn.commit()
    conn.close()
    target_db.chmod(0o755)

    return target_db, target_par_dir


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--source-climate-dir",
        default=str(DEFAULT_SOURCE_CLIMATE_DIR),
        help=(
            "Directory containing Tenerife climate source files. Supported layouts are "
            "tenerife_stations.csv + tenerife_par_files/ or stations.csv + station_par_files/."
        ),
    )
    parser.add_argument(
        "--output-dir",
        default=str(DEFAULT_OUTPUT_DIR),
        help="Target directory for tenerife_stations.db and tenerife_par_files/.",
    )
    args = parser.parse_args()

    db_path, par_dir = build_tenerife_catalog(
        source_climate_dir=Path(args.source_climate_dir),
        output_dir=Path(args.output_dir),
    )
    print(f"Built {db_path}")
    print(f"Copied Tenerife station files into {par_dir}")


if __name__ == "__main__":
    main()
