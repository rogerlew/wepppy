"""Prepare a conservative LOTE daily series for WEPPcloud Observed; no gap filling."""

import argparse
import hashlib
import json
from pathlib import Path
from zipfile import ZipFile

import numpy as np
import pandas as pd


SOURCES = {
    "daily": {
        "doi": "10.2737/RDS-2017-0030",
        "sha256": "61bc75572523ec5786f161918cc9ac1882c976bf5ee17c994f593d29b05279a0",
        "member": "Data/Tenderfoot_avg_daily_streamflow.csv",
    },
    "quarter_hour": {
        "doi": "10.2737/RDS-2010-0003.2",
        "sha256": "cc4e579cc92762488ebd27b10dabf03f4f1717f5b70f7bd8c9b4639e0780006a",
        "member": "Data/Tenderfoot_15min_streamflow_data.csv",
    },
}
OUTPUT = "lote_observed_daily_1992-2015.csv"


def read_source(path, source, columns):
    digest = hashlib.sha256(path.read_bytes()).hexdigest()
    if digest != source["sha256"]:
        raise ValueError(f"Archive checksum mismatch: {path}")
    with ZipFile(path) as archive:
        frame = pd.read_csv(archive.open(source["member"]), usecols=columns)
    frame["Date"] = pd.to_datetime(frame.pop("DATE"), format="%m/%d/%Y")
    return frame


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--daily-archive", type=Path, required=True)
    parser.add_argument("--quarter-hour-archive", type=Path, required=True)
    parser.add_argument("--area-km2", type=float, required=True)
    args = parser.parse_args()
    if not np.isfinite(args.area_km2) or args.area_km2 <= 0:
        raise ValueError("Drainage area must be finite and positive")
    outdir = Path(__file__).resolve().parent
    columns = ["DATE", "LOTE_cfs", "LOTE_flag"]
    daily = read_source(args.daily_archive, SOURCES["daily"], columns)
    quarter = read_source(args.quarter_hour_archive, SOURCES["quarter_hour"], columns + ["TIME"])
    if daily.Date.duplicated().any():
        raise ValueError("Duplicate dates in daily archive")

    # Preserve source date labels (metadata specifies MST); do not shift to UTC.
    quarter["timestamp"] = pd.to_datetime(
        quarter.Date.dt.strftime("%Y-%m-%d") + " " + quarter.TIME,
        format="%Y-%m-%d %H:%M",
    )
    if (quarter.timestamp.dt.minute % 15 != 0).any():
        raise ValueError("Unexpected sampling interval")
    for frame in (daily, quarter):
        frame["flagged"] = frame.LOTE_flag.notna()
        frame["invalid"] = ~np.isfinite(frame.LOTE_cfs) | (frame.LOTE_cfs < 0)
        frame["good"] = ~frame.flagged & ~frame.invalid
    quarter["duplicate"] = quarter.timestamp.duplicated(keep=False)
    qdays = quarter.groupby("Date").agg(
        source_samples=("timestamp", "size"),
        unique_samples=("timestamp", "nunique"),
        flagged_samples=("flagged", "sum"),
        invalid_samples=("invalid", "sum"),
        good_samples=("good", "sum"),
        duplicate_samples=("duplicate", "sum"),
        mean_cfs=("LOTE_cfs", "mean"),
    )
    qdays["accepted"] = (
        (qdays.source_samples == 96)
        & (qdays.unique_samples == 96)
        & (qdays.good_samples == 96)
    )
    qdays["source"] = SOURCES["quarter_hour"]["doi"]
    ddays = daily.set_index("Date")
    daudit = pd.DataFrame(index=ddays.index)
    daudit["source_samples"] = 1
    daudit["unique_samples"] = 1
    daudit["flagged_samples"] = ddays.flagged.astype(int)
    daudit["invalid_samples"] = ddays.invalid.astype(int)
    daudit["good_samples"] = ddays.good.astype(int)
    daudit["duplicate_samples"] = 0
    daudit["mean_cfs"] = ddays.LOTE_cfs
    daudit["accepted"] = ddays.good
    daudit["source"] = SOURCES["daily"]["doi"]

    # First complete usable LOTE logger day; prefer logger data thereafter,
    # including the overlap with the strip-chart archive. No fallback to estimates.
    switch = qdays.index[qdays.accepted].min()
    audit = pd.concat([daudit.loc[daudit.index < switch], qdays.loc[switch:]])
    audit = audit.reindex(pd.date_range(daily.Date.min(), quarter.Date.max(), name="Date"))
    audit["accepted"] = audit.accepted.eq(True)
    audit["source"] = audit.source.fillna(SOURCES["quarter_hour"]["doi"])
    audit.to_csv(outdir / "daily_quality.csv", date_format="%Y-%m-%d", float_format="%.9f")

    conversion = 0.3048 ** 3 * 86400 * 1000 / (args.area_km2 * 1e6)
    accepted = audit.loc[audit.accepted]
    result = pd.DataFrame({"Streamflow (mm)": accepted.mean_cfs * conversion})
    assert result.index.is_unique and result.index.is_monotonic_increasing
    assert np.isfinite(result["Streamflow (mm)"]).all()
    assert (result["Streamflow (mm)"] >= 0).all()
    result.to_csv(outdir / OUTPUT, date_format="%m/%d/%Y", float_format="%.6f")

    coverage = audit.groupby(audit.index.year).agg(
        archive_days=("accepted", "size"), accepted_days=("accepted", "sum")
    )
    coverage.index.name = "Year"
    coverage["excluded_days"] = coverage.archive_days - coverage.accepted_days
    coverage["accepted_fraction_of_archive_days"] = coverage.accepted_days / coverage.archive_days
    coverage.to_csv(outdir / "annual_coverage.csv", float_format="%.4f")

    overlap = daudit[["mean_cfs", "accepted"]].join(
        qdays[["mean_cfs", "accepted"]], how="inner", lsuffix="_daily", rsuffix="_logger"
    )
    paired = overlap.loc[overlap.accepted_daily & overlap.accepted_logger]
    provenance = {
        "station": "Lower Tenderfoot Creek (LOTE)",
        "source_retrieved": "2026-10-08",
        "sources": SOURCES,
        "gauge_location": {"latitude_wgs84": 46.926932, "longitude_wgs84": -110.902815,
                           "source_nad27_utm12n_easting_m": 507463,
                           "source_nad27_utm12n_northing_m": 5196842},
        "normalization_area_km2": args.area_km2,
        "area_reference": "https://doi.org/10.1002/2015WR017972",
        "area_reference_detail": "Bergstrom et al. (2016), section 2.1 and Figure 1: 22.8 km2 gauged Tenderfoot catchment; adopted literature area, not a new delineation.",
        "conversion": "mm/day = mean_cfs * 0.3048^3 * 86400 * 1000 / area_m2",
        "mm_per_day_per_cfs": conversion,
        "time_basis": "Source calendar dates; metadata specifies Mountain Standard Time; no UTC/DST conversion.",
        "date_format_correction": "CSV dates are month/day/year despite metadata saying dd/mm/yyyy.",
        "quality_policy": "Exclude any nonblank LOTE flag, nonfinite or negative flow. Logger days require exactly 96 distinct quarter-hour timestamps and 96 valid unflagged values. No gap filling or outlier clipping.",
        "source_priority": f"Daily strip-chart archive before {switch.date()}; logger daily means from that date onward, without fallback.",
        "flag_meanings": {"daily_1": "Estimated missing data from nearby-stream regression",
                          "daily_2": "Estimated winter flow during frozen-well conditions",
                          "quarter_hour_1": "Sensor anomalies",
                          "quarter_hour_2": "Frozen-well winter readings"},
        "archive_caveat": "Unflagged does not certify accuracy. The logger archive includes some short gaps estimated by its authors without separate flags.",
        "overlap_unflagged_paired_days": len(paired),
        "overlap_mean_absolute_difference_cfs": float((paired.mean_cfs_daily - paired.mean_cfs_logger).abs().mean()) if len(paired) else None,
        "quarter_hour_duplicate_timestamp_rows": int(quarter.duplicate.sum()),
        "first_accepted_date": str(result.index.min().date()),
        "last_accepted_date": str(result.index.max().date()),
        "accepted_days": len(result),
        "excluded_days": int((~audit.accepted).sum()),
        "accepted_days_by_source": accepted.source.value_counts().to_dict(),
        "output": OUTPUT,
        "output_sha256": hashlib.sha256((outdir / OUTPUT).read_bytes()).hexdigest(),
    }
    (outdir / "provenance.json").write_text(json.dumps(provenance, indent=2) + "\n")
    print(json.dumps({key: provenance[key] for key in (
        "first_accepted_date", "last_accepted_date", "accepted_days", "excluded_days",
        "accepted_days_by_source", "overlap_unflagged_paired_days",
    )}, indent=2))


if __name__ == "__main__":
    main()
