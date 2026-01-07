#!/usr/bin/env python3
"""
Generate a DSS vs parquet comparison plot for peak channel flows.

Example:
    python wepppy/nodb/scripts/dss_export/plot_peak_chan_compare.py \\
        --run-dir /wc1/runs/in/increasing-sheepskin \\
        --channel-id 24
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path

import matplotlib
import pandas as pd
from pydsstools.heclib.dss import HecDss

matplotlib.use("Agg")
import matplotlib.pyplot as plt

TOPAZ_KEYS = ("TopazID", "topaz_id", "topazId", "topaz", "id", "ID")
WEPP_KEYS = ("WeppID", "wepp_id", "weppId", "wepp", "WEPPID", "WeppId")


def _safe_int(value: object) -> int | None:
    try:
        return int(value)
    except (TypeError, ValueError):
        return None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--run-dir",
        type=Path,
        help="Path to the run directory (overrides --run-id).",
    )
    parser.add_argument(
        "--run-id",
        help="Run id used to resolve the path under --run-root.",
    )
    parser.add_argument(
        "--run-root",
        type=Path,
        default=Path("/wc1/runs"),
        help="Run root used with --run-id (default: %(default)s).",
    )
    parser.add_argument(
        "--channel-id",
        type=int,
        required=True,
        help="Topaz channel id (matches peak_chan_<id>.dss).",
    )
    parser.add_argument(
        "--wepp-id",
        type=int,
        help="Override WEPP Elmt_ID for the parquet filter.",
    )
    parser.add_argument(
        "--parquet",
        type=Path,
        help="Override chan.out.parquet path.",
    )
    parser.add_argument(
        "--dss",
        type=Path,
        help="Override peak_chan_<id>.dss path.",
    )
    parser.add_argument(
        "--geojson",
        type=Path,
        help="Override dss_channels.geojson path.",
    )
    parser.add_argument(
        "--output",
        type=Path,
        help="Output plot path (default: export/dss/peak_chan_<id>_dss_vs_parquet.png).",
    )
    parser.add_argument(
        "--dpi",
        type=int,
        default=150,
        help="PNG output DPI (default: %(default)s).",
    )
    return parser.parse_args()


def resolve_run_dir(args: argparse.Namespace) -> Path:
    if args.run_dir is not None:
        return args.run_dir
    if not args.run_id:
        raise ValueError("Provide --run-dir or --run-id.")
    if len(args.run_id) < 2:
        raise ValueError("run id must be at least two characters.")
    return args.run_root / args.run_id[:2] / args.run_id


def resolve_wepp_id(geojson_path: Path, channel_id: int) -> int:
    if not geojson_path.exists():
        raise FileNotFoundError(f"Missing geojson: {geojson_path}")
    data = json.loads(geojson_path.read_text(encoding="utf-8"))
    for feature in data.get("features", []):
        props = feature.get("properties")
        if not isinstance(props, dict):
            continue
        topaz_id = None
        for key in TOPAZ_KEYS:
            topaz_id = _safe_int(props.get(key))
            if topaz_id is not None:
                break
        if topaz_id != channel_id:
            continue
        for key in WEPP_KEYS:
            wepp_id = _safe_int(props.get(key))
            if wepp_id is not None:
                return wepp_id
    raise ValueError(
        f"Unable to resolve WEPP id for channel {channel_id} in {geojson_path}. "
        "Pass --wepp-id to override."
    )


def load_dss_series(dss_path: Path) -> pd.DataFrame:
    if not dss_path.exists():
        raise FileNotFoundError(f"Missing DSS file: {dss_path}")
    with HecDss.Open(str(dss_path), mode="r") as fid:
        pathnames = fid.getPathnameList("/*/*/*/*/*/*/")
        if not pathnames:
            raise ValueError(f"No DSS records found in {dss_path}")
        ts = fid.read_ts(pathnames[0])
    return pd.DataFrame({"datetime": ts.pytimes, "dss_peak": ts.values})


def load_parquet_series(parquet_path: Path, wepp_id: int) -> pd.DataFrame:
    if not parquet_path.exists():
        raise FileNotFoundError(f"Missing parquet file: {parquet_path}")
    columns = ["year", "julian", "Elmt_ID", "Time (s)", "Peak_Discharge (m^3/s)"]
    df = pd.read_parquet(parquet_path, columns=columns)
    df = df[df["Elmt_ID"] == wepp_id].copy()
    if df.empty:
        raise ValueError(f"No rows found for Elmt_ID={wepp_id} in {parquet_path}")
    base = pd.to_datetime(
        df["year"].astype(int).astype(str) + df["julian"].astype(int).astype(str).str.zfill(3),
        format="%Y%j",
    )
    df["datetime"] = base + pd.to_timedelta(df["Time (s)"].fillna(0.0), unit="s")
    df = df.sort_values("datetime").reset_index(drop=True)
    return df[["datetime", "Peak_Discharge (m^3/s)"]].rename(
        columns={"Peak_Discharge (m^3/s)": "parquet_peak"}
    )


def main() -> None:
    args = parse_args()
    run_dir = resolve_run_dir(args)
    if not run_dir.exists():
        raise FileNotFoundError(f"Run directory not found: {run_dir}")

    export_dir = run_dir / "export" / "dss"
    dss_path = args.dss or export_dir / f"peak_chan_{args.channel_id}.dss"
    geojson_path = args.geojson or export_dir / "dss_channels.geojson"
    parquet_path = args.parquet or run_dir / "wepp" / "output" / "interchange" / "chan.out.parquet"
    output_path = args.output or export_dir / f"peak_chan_{args.channel_id}_dss_vs_parquet.png"

    wepp_id = args.wepp_id if args.wepp_id is not None else resolve_wepp_id(
        geojson_path, args.channel_id
    )

    dss_df = load_dss_series(dss_path)
    parquet_df = load_parquet_series(parquet_path, wepp_id)

    start = dss_df["datetime"].min()
    end = dss_df["datetime"].max()
    parquet_window = parquet_df[
        (parquet_df["datetime"] >= start) & (parquet_df["datetime"] <= end)
    ].copy()

    merged = pd.merge(dss_df, parquet_window, on="datetime", how="outer").sort_values("datetime")
    overlap = merged.dropna(subset=["dss_peak", "parquet_peak"]).copy()

    print(f"Channel {args.channel_id} (WEPP Elmt_ID {wepp_id})")
    print(f"DSS window: {start} to {end} ({len(dss_df)} records)")
    print(f"Parquet window rows: {len(parquet_window)}")
    print(f"Overlap rows: {len(overlap)}")
    print(f"Missing DSS rows: {merged['dss_peak'].isna().sum()}")
    print(f"Missing parquet rows: {merged['parquet_peak'].isna().sum()}")
    if not overlap.empty:
        diff = (overlap["dss_peak"] - overlap["parquet_peak"]).abs()
        print(f"Max abs diff: {diff.max():.9f}")
        print(f"Mean abs diff: {diff.mean():.9f}")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    plt.figure(figsize=(12, 5))
    plt.plot(
        merged["datetime"],
        merged["parquet_peak"],
        label="chan.out.parquet",
        color="#1f77b4",
        linewidth=1,
    )
    plt.plot(
        merged["datetime"],
        merged["dss_peak"],
        label="peak_chan_{}.dss".format(args.channel_id),
        color="#ff7f0e",
        linewidth=1,
        alpha=0.7,
    )
    plt.title(f"Peak flow channel {args.channel_id} (WEPP Elmt_ID {wepp_id})")
    plt.xlabel("Datetime")
    plt.ylabel("Peak discharge (m^3/s)")
    plt.legend(loc="upper right")
    plt.tight_layout()
    plt.savefig(output_path, dpi=args.dpi)
    print(f"Saved plot: {output_path}")


if __name__ == "__main__":
    main()
