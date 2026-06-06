"""Helper workflows and utilities for Climate NoDb build orchestration."""

from __future__ import annotations

import os
import random
import time
from concurrent.futures import FIRST_COMPLETED, ProcessPoolExecutor, ThreadPoolExecutor, wait
from dataclasses import dataclass
from datetime import date, datetime
from math import acos, cos, isfinite, pi, sin, tan
from os.path import exists as _exists
from os.path import join as _join
from pathlib import Path
from subprocess import PIPE, Popen
from typing import TYPE_CHECKING, Any, Optional, Tuple

import numpy as np
import pandas as pd
import pyproj
import rasterio
import requests
from pyproj import Proj

from wepppy.all_your_base import NCPU
from wepppy.all_your_base.geo import read_raster
from wepppy.all_your_base.geo.webclients import wmesque_retrieve
from wepppy.climates.cligen import ClimateFile, Cligen, CligenStationsManager, df_to_prn
from wepppy.climates.downscaled_nmme_client import retrieve_rcp85_timeseries
from wepppy.climates.gridmet import (
    retrieve_historical_precip as gridmet_retrieve_historical_precip,
)
from wepppy.climates.gridmet import (
    retrieve_historical_timeseries as gridmet_retrieve_historical_timeseries,
)
from wepppy.climates.gridmet import (
    retrieve_historical_wind as gridmet_retrieve_historical_wind,
)
from wepppy.climates.prism.daily_client import (
    retrieve_historical_timeseries as prism_retrieve_historical_timeseries,
)
from wepppy.query_engine.activate import update_catalog_entry
from wepppyo3.climate import calculate_p_annual_monthlies as pyo3_cli_calculate_annual_monthlies
from wepppyo3.climate import cli_revision as pyo3_cli_revision

if TYPE_CHECKING:
    from wepppy.nodb.core.climate import Climate


def _cap_ncpu(raw_ncpu: int) -> int:
    return min(raw_ncpu, 24)


NCPU = _cap_ncpu(NCPU)


CLIGEN_OBSERVED_QUALITY_GUARD_USER_MESSAGE = (
    "CLIGEN failed to converge, try selecting different station or setting Adjust MX .5 P Values"
)


_SUNMAP_SOLCON_LY_PER_MIN = 1.94
_SUNMAP_DOMAIN_EPS = 1.0e-12


@dataclass(frozen=True)
class DaymetRadiationNormalizationResult:
    normalized_values: pd.Series
    affected_count: int
    artifact_path: Optional[str]


def _is_cligen_observed_quality_guard_error(exc: RuntimeError) -> bool:
    return "cligen run_observed quality guard tripped" in str(exc).lower()


def _baseline_sunmap_horizontal_daily_potential_ly(julian_day: int, latitude_deg: float) -> float:
    """Return baseline ``sunmap.r3`` horizontal daily potential in Langleys/day."""
    if not 1 <= int(julian_day) <= 366:
        raise ValueError(f"julian_day must be in 1..366, got {julian_day!r}")
    if not isfinite(float(latitude_deg)):
        raise ValueError(f"latitude_deg must be finite, got {latitude_deg!r}")

    sdate = float(julian_day)
    radlat = float(latitude_deg) * pi / 180.0
    declination = 0.00698 - 0.4067 * cos((sdate + 10.0) * 0.0172)
    eccentricity = 1.0 - 0.0167 * cos((sdate - 3.0) * 0.0172)
    if abs(eccentricity) <= _SUNMAP_DOMAIN_EPS:
        raise ValueError(f"invalid sunmap eccentricity for julian_day={julian_day}")

    r1 = (60.0 * _SUNMAP_SOLCON_LY_PER_MIN) / (eccentricity * eccentricity)
    hour_angle_arg = -(tan(radlat) * tan(declination))
    hour_angle_arg = max(-1.0, min(1.0, hour_angle_arg))
    sunset_hour_angle = acos(hour_angle_arg)
    t1 = sunset_hour_angle
    t0 = -sunset_hour_angle

    r3 = r1 * (
        (sin(declination) * sin(radlat) * (t1 - t0) * 12.0 / pi)
        + (cos(declination) * cos(radlat) * (sin(t1) - sin(t0)) * 12.0 / pi)
    )
    if not isfinite(r3) or r3 <= _SUNMAP_DOMAIN_EPS:
        raise ValueError(
            "invalid baseline sunmap horizontal daily potential "
            f"for julian_day={julian_day} latitude_deg={latitude_deg}"
        )
    return r3


def _safe_daymet_radiation_artifact_label(label: str) -> str:
    safe = "".join(c if c.isalnum() or c in {"-", "_"} else "_" for c in str(label))
    return safe or "wepp"


def _normalize_daymet_radiation_to_toa_bound(
    df: pd.DataFrame,
    *,
    latitude_deg: float,
    cli_dir: Optional[str] = None,
    artifact_label: str = "wepp",
    logger: Optional[Any] = None,
) -> DaymetRadiationNormalizationResult:
    """Clamp Daymet over-TOA radiation to baseline daily horizontal potential.

    Daymet observed radiation remains the source value. This helper only
    normalizes rows that exceed the baseline ``sunmap.r3`` physical upper bound
    consumed by openWEPP, and records provenance columns/artifact for review.
    """
    if "srad(l/day)" not in df.columns:
        raise KeyError("expected Daymet dataframe column 'srad(l/day)'")

    source = pd.to_numeric(df["srad(l/day)"], errors="raise").astype(float)
    bounds = pd.Series(
        [
            _baseline_sunmap_horizontal_daily_potential_ly(
                pd.Timestamp(index_value).dayofyear,
                latitude_deg,
            )
            for index_value in df.index
        ],
        index=df.index,
        dtype=float,
        name="srad_toa_bound(l/day)",
    )
    over_toa = source > bounds
    normalized = source.mask(over_toa, bounds)

    affected_count = int(over_toa.sum())
    artifact_path = None
    if affected_count == 0:
        return DaymetRadiationNormalizationResult(normalized, affected_count, artifact_path)

    if "srad_source(l/day)" not in df.columns:
        df["srad_source(l/day)"] = source
    df["srad_toa_bound(l/day)"] = bounds
    df["srad_toa_normalized"] = over_toa
    df["srad_toa_normalization_reason"] = np.where(over_toa, "daymet_over_toa", "")
    df["srad_toa_bound_latitude(deg)"] = float(latitude_deg)
    df["srad(l/day)"] = normalized

    affected_dates = [pd.Timestamp(value) for value in df.index[over_toa]]
    provenance = pd.DataFrame(
        {
            "date": [value.date().isoformat() for value in affected_dates],
            "year": [int(value.year) for value in affected_dates],
            "julian": [int(value.dayofyear) for value in affected_dates],
            "latitude_deg": float(latitude_deg),
            "source_column": "srad(l/day)",
            "original_srad_l_day": source[over_toa].to_numpy(),
            "toa_bound_l_day": bounds[over_toa].to_numpy(),
            "normalized_srad_l_day": normalized[over_toa].to_numpy(),
            "excess_l_day": (source[over_toa] - bounds[over_toa]).to_numpy(),
            "normalization_reason": "daymet_over_toa",
        }
    )

    if cli_dir is not None:
        label = _safe_daymet_radiation_artifact_label(artifact_label)
        artifact = Path(cli_dir) / f"daymet_radiation_toa_normalization_{label}.csv"
        provenance.to_csv(artifact, index=False)
        artifact_path = str(artifact)

    if logger is not None:
        logger.warning(
            "  normalized %s Daymet radiation row(s) to baseline sunmap TOA bound"
            " using latitude %.5f",
            affected_count,
            latitude_deg,
        )

    return DaymetRadiationNormalizationResult(normalized, affected_count, artifact_path)


def _run_observed_with_quality_guard_handling(
    cligen: "Cligen",
    prn_fn: str,
    cli_fn: str,
    *,
    adjust_mx_pt5: bool,
    silent_pass_observed_quality_guard: bool,
) -> bool:
    try:
        quality_guard_bypassed = bool(
            cligen.run_observed(
            prn_fn,
            cli_fn=cli_fn,
            adjust_mx_pt5=adjust_mx_pt5,
            silently_pass_quality_guard=silent_pass_observed_quality_guard,
            )
        )
        setattr(cligen, "_last_observed_quality_guard_bypassed", quality_guard_bypassed)
        return quality_guard_bypassed
    except RuntimeError as exc:
        setattr(cligen, "_last_observed_quality_guard_bypassed", False)
        if (
            not silent_pass_observed_quality_guard
            and _is_cligen_observed_quality_guard_error(exc)
        ):
            raise RuntimeError(CLIGEN_OBSERVED_QUALITY_GUARD_USER_MESSAGE) from exc
        raise


def lng_lat_to_pixel_center(
    lng: float,
    lat: float,
    proj4: str,
    transform: Tuple[float, float, float, float, float, float],
    width: int,
    height: int,
) -> Tuple[Optional[float], Optional[float]]:
    raster_proj = Proj(proj4)
    wgs84_proj = Proj(proj="latlong", datum="WGS84")

    x, y = pyproj.transform(wgs84_proj, raster_proj, lng, lat)

    a, b, c, d, e, f = transform
    col = (x - a) / b
    row = (y - d) / f

    col, row = round(col), round(row)

    if 0 <= col < width and 0 <= row < height:
        lng, lat = pyproj.transform(raster_proj, wgs84_proj, col * b + a, row * f + d)
        return lng, lat

    return None, None


def daymet_pixel_center(lng: float, lat: float) -> Tuple[Optional[float], Optional[float]]:
    width, height = (7814, 8075)
    proj4 = "+proj=lcc +lat_1=25 +lat_2=60 +lat_0=42.5 +lon_0=-100 +x_0=0 +y_0=0 +ellps=WGS84 +units=m +no_defs"
    transform = (-4560750.0, 1000.0, 0.0, 4984500.0, 0.0, -1000.0)
    return lng_lat_to_pixel_center(lng, lat, proj4, transform, width, height)


def gridmet_pixel_center(lng: float, lat: float) -> Tuple[Optional[float], Optional[float]]:
    width, height = (1386, 585)
    proj4 = "+proj=longlat +datum=WGS84 +no_defs"
    transform = (-124.79299639760372, 0.04166601298087771, 0.0, 49.41685580390774, 0.0, -0.041666014553749395)
    return lng_lat_to_pixel_center(lng, lat, proj4, transform, width, height)


def prism4k_pixel_center(lng: float, lat: float) -> Tuple[Optional[float], Optional[float]]:
    width, height = (1405, 621)
    proj4 = "+proj=longlat +datum=NAD83 +no_defs"
    transform = (-125.02083333333336, 0.0416666666667, 0.0, 49.93749999999975, 0.0, -0.0416666666667)
    return lng_lat_to_pixel_center(lng, lat, proj4, transform, width, height)


def nexrad_pixel_center(lng: float, lat: float) -> Tuple[float, float]:
    return round(lng * 4.0) / 4.0, round(lat * 4.0) / 4.0


def download_file(url: str, dst: str) -> None:
    response = requests.get(url)
    if response.status_code == 200:
        with open(dst, "wb") as file:
            file.write(response.content)
        return
    raise Exception(f"Error retrieving file from {url}")


def breakpoint_file_fix(fn: str) -> None:
    with open(fn) as fp:
        lines = fp.readlines()

    lines[13] = "da mo year nbrkpt tmax  tmin    rad   w-vel  w-dir   tdew\n"
    lines[14] = "                (mm)    (C)   (C) (l/day) (m/sec)(deg)    (C)\n"

    with open(fn, "w") as fp:
        fp.writelines(lines)


def get_prism_p_annual_monthlies(lng: float, lat: float, start_year: int, end_year: int) -> list[float]:
    df = prism_retrieve_historical_timeseries(lng, lat, start_year, end_year)
    months = df.index.month
    precip = df["ppt(mm)"].values
    return pyo3_cli_calculate_annual_monthlies(months=months, ppts=precip)


def build_observed_prism(
    cligen: "Cligen",
    lng: float,
    lat: float,
    start_year: int,
    end_year: int,
    cli_dir: str,
    prn_fn: str,
    cli_fn: str,
    gridmet_wind: bool = True,
    adjust_mx_pt5: bool = False,
    silent_pass_observed_quality_guard: bool = False,
) -> None:
    df = prism_retrieve_historical_timeseries(lng, lat, start_year, end_year, gridmet_wind=gridmet_wind)
    df_to_prn(df, _join(cli_dir, prn_fn), "ppt(mm)", "tmax(degc)", "tmin(degc)")

    max_retries = 3
    for retry in range(max_retries):
        try:
            _run_observed_with_quality_guard_handling(
                cligen,
                prn_fn,
                cli_fn,
                adjust_mx_pt5=adjust_mx_pt5,
                silent_pass_observed_quality_guard=silent_pass_observed_quality_guard,
            )
            break
        except AssertionError:
            if retry == max_retries - 1:
                raise
            time.sleep(0.5 * (retry + 1))

    dates = df.index
    cli_path = _join(cli_dir, cli_fn)
    climate = ClimateFile(cli_path)

    climate.replace_var("tdew", dates, df["tdmean(degc)"])

    if gridmet_wind:
        climate.replace_var("w-vl", dates, df["vs(m/s)"])
        climate.replace_var("w-dir", dates, df["th(DegreesClockwisefromnorth)"])

    df.to_parquet(_join(cli_dir, f"prism_{start_year}-{end_year}.parquet"))
    climate.write(cli_path)


def get_daymet_p_annual_monthlies(lng: float, lat: float, start_year: int, end_year: int) -> list[float]:
    from wepppy.climates.daymet import retrieve_historical_timeseries as daymet_retrieve_historical_timeseries

    df = daymet_retrieve_historical_timeseries(lng, lat, start_year, end_year, gridmet_wind=False)
    months = df.index.month
    precip = df["prcp(mm/day)"].values
    return pyo3_cli_calculate_annual_monthlies(months=months, ppts=precip)


def build_observed_daymet(
    cligen: "Cligen",
    lng: float,
    lat: float,
    start_year: int,
    end_year: int,
    cli_dir: str,
    prn_fn: str,
    cli_fn: str,
    gridmet_wind: bool = True,
    adjust_mx_pt5: bool = False,
    silent_pass_observed_quality_guard: bool = False,
) -> None:
    from wepppy.climates.daymet import retrieve_historical_timeseries as daymet_retrieve_historical_timeseries

    df = daymet_retrieve_historical_timeseries(lng, lat, start_year, end_year, gridmet_wind=gridmet_wind)
    df.to_parquet(_join(cli_dir, f"daymet_{start_year}-{end_year}.parquet"))
    df_to_prn(df, _join(cli_dir, prn_fn), "prcp(mm/day)", "tmax(degc)", "tmin(degc)")

    max_retries = 3
    for retry in range(max_retries):
        try:
            _run_observed_with_quality_guard_handling(
                cligen,
                prn_fn,
                cli_fn,
                adjust_mx_pt5=adjust_mx_pt5,
                silent_pass_observed_quality_guard=silent_pass_observed_quality_guard,
            )
            break
        except AssertionError:
            if retry == max_retries - 1:
                raise
            time.sleep(0.5 * (retry + 1))

    dates = df.index
    cli_path = _join(cli_dir, cli_fn)
    climate = ClimateFile(cli_path)
    radiation = _normalize_daymet_radiation_to_toa_bound(
        df,
        latitude_deg=climate.lat,
        cli_dir=cli_dir,
        artifact_label=Path(cli_fn).stem,
    )

    climate.replace_var("rad", dates, radiation.normalized_values)
    climate.replace_var("tdew", dates, df["tdew(degc)"])

    if gridmet_wind:
        climate.replace_var("w-vl", dates, df["vs(m/s)"])
        climate.replace_var("w-dir", dates, df["th(DegreesClockwisefromnorth)"])

    df.to_parquet(_join(cli_dir, f"daymet_{start_year}-{end_year}.parquet"))
    climate.write(cli_path)


def build_observed_daymet_interpolated(
    cligen: "Cligen",
    topaz_id: str,
    lng: float,
    lat: float,
    start_year: int,
    end_year: int,
    cli_dir: str,
    cli_fn: str,
    prn_fn: str,
    wind_vs: Optional[Any] = None,
    wind_dir: Optional[Any] = None,
    adjust_mx_pt5: bool = False,
    silent_pass_observed_quality_guard: bool = False,
) -> tuple[str, bool]:
    _parquet_fn = f"daymet_observed_{topaz_id}_{start_year}-{end_year}.parquet"
    df = pd.read_parquet(_join(cli_dir, _parquet_fn))

    attempts = 3
    quality_guard_bypassed = False
    for attempt in range(attempts):
        try:
            quality_guard_bypassed = _run_observed_with_quality_guard_handling(
                cligen,
                prn_fn,
                cli_fn,
                adjust_mx_pt5=adjust_mx_pt5,
                silent_pass_observed_quality_guard=silent_pass_observed_quality_guard,
            )
            break
        except AssertionError:
            if attempt == attempts - 1:
                raise Exception("cligen.run_observed failed")

    dates = df.index
    cli_path = _join(cli_dir, cli_fn)
    climate = ClimateFile(cli_path)
    radiation = _normalize_daymet_radiation_to_toa_bound(
        df,
        latitude_deg=climate.lat,
        cli_dir=cli_dir,
        artifact_label=topaz_id,
    )

    climate.replace_var("rad", dates, radiation.normalized_values)
    climate.replace_var("tdew", dates, df["tdew(degc)"])

    if wind_vs is not None:
        climate.replace_var("w-vl", dates, wind_vs)

    if wind_dir is not None:
        climate.replace_var("w-dir", dates, wind_dir)

    df.to_parquet(_join(cli_dir, _parquet_fn))
    climate.write(cli_path)
    return topaz_id, bool(quality_guard_bypassed)


def build_observed_snotel(
    cligen: "Cligen",
    lng: float,
    lat: float,
    snotel_id: str,
    start_year: int,
    end_year: int,
    cli_dir: str,
    prn_fn: str,
    cli_fn: str,
    gridmet_supplement: bool = True,
    adjust_mx_pt5: bool = False,
    silent_pass_observed_quality_guard: bool = False,
) -> None:
    snotel_data_dir = "/workdir/wepppy/wepppy/climates/snotel/processed"
    df = pd.read_csv(_join(snotel_data_dir, f"{snotel_id}.csv"), parse_dates=[0], na_values=["", " "])

    df["Year"] = df["Date"].dt.year

    df = df[df["Year"] >= start_year]
    df = df[df["Year"] <= end_year]

    start_year = min(df["Year"])
    end_year = max(df["Year"])

    df["prcp(mm/day)"] = df["Precipitation Increment (in)"] * 25.4
    df["tmax(degc)"] = (df["Air Temperature Maximum (degF)"] - 32) * 5 / 9
    df["tmin(degc)"] = (df["Air Temperature Minimum (degF)"] - 32) * 5 / 9

    df.to_parquet(_join(cli_dir, f"snotel_{start_year}-{end_year}.parquet"))
    df_to_prn(df.set_index("Date"), _join(cli_dir, prn_fn), "prcp(mm/day)", "tmax(degc)", "tmin(degc)")
    _run_observed_with_quality_guard_handling(
        cligen,
        prn_fn,
        cli_fn,
        adjust_mx_pt5=adjust_mx_pt5,
        silent_pass_observed_quality_guard=silent_pass_observed_quality_guard,
    )

    cli_path = _join(cli_dir, cli_fn)
    climate = ClimateFile(cli_path)

    if gridmet_supplement:
        wind_df = gridmet_retrieve_historical_timeseries(lng, lat, start_year, end_year)
        dates = df.index
        climate.replace_var("rad", dates, wind_df["srad(l/day)"])
        climate.replace_var("tdew", dates, wind_df["tdew(degc)"])

        wind_dates = wind_df.index
        climate.replace_var("w-vl", wind_dates, wind_df["vs(m/s)"])
        climate.replace_var("w-dir", wind_dates, wind_df["th(DegreesClockwisefromnorth)"])

        df["vs(m/s)"] = wind_df["vs(m/s)"]
        df["vs(m/s)"] = wind_df["th(DegreesClockwisefromnorth)"]

        df.to_parquet(_join(cli_dir, f"snotel_gridmet_{start_year}-{end_year}.parquet"))
    else:
        df.to_parquet(_join(cli_dir, f"snotel_{start_year}-{end_year}.parquet"))

    climate.write(cli_path)


def get_gridmet_p_annual_monthlies(lng: float, lat: float, start_year: int, end_year: int) -> list[float]:
    df = gridmet_retrieve_historical_precip(lng, lat, start_year, end_year)
    months = df.index.month
    precip = df["pr(mm/day)"].values
    return pyo3_cli_calculate_annual_monthlies(months=months, ppts=precip)


def build_observed_gridmet(
    cligen: "Cligen",
    lng: float,
    lat: float,
    start_year: int,
    end_year: int,
    cli_dir: str,
    prn_fn: str,
    cli_fn: str,
    adjust_mx_pt5: bool = False,
    silent_pass_observed_quality_guard: bool = False,
) -> None:
    df = gridmet_retrieve_historical_timeseries(lng, lat, start_year, end_year)
    df.to_parquet(_join(cli_dir, f"gridmet_{start_year}-{end_year}.parquet"))
    df_to_prn(df, _join(cli_dir, prn_fn), "pr(mm/day)", "tmmx(degc)", "tmmn(degc)")

    max_retries = 3
    for retry in range(max_retries):
        try:
            _run_observed_with_quality_guard_handling(
                cligen,
                prn_fn,
                cli_fn,
                adjust_mx_pt5=adjust_mx_pt5,
                silent_pass_observed_quality_guard=silent_pass_observed_quality_guard,
            )
            break
        except AssertionError:
            if retry == max_retries - 1:
                raise
            time.sleep(0.5 * (retry + 1))

    dates = df.index
    cli_path = _join(cli_dir, cli_fn)
    climate = ClimateFile(cli_path)

    climate.replace_var("rad", dates, df["srad(l/day)"])
    climate.replace_var("tdew", dates, df["tdew(degc)"])
    climate.replace_var("w-vl", dates, df["vs(m/s)"])
    climate.replace_var("w-dir", dates, df["th(DegreesClockwisefromnorth)"])

    climate.write(cli_path)


def build_observed_gridmet_interpolated(
    cligen: "Cligen",
    topaz_id: str,
    lng: float,
    lat: float,
    start_year: int,
    end_year: int,
    cli_dir: str,
    cli_fn: str,
    prn_fn: str,
    adjust_mx_pt5: bool = False,
    silent_pass_observed_quality_guard: bool = False,
) -> tuple[str, bool]:
    _parquet_fn = f"gridmet_observed_{topaz_id}_{start_year}-{end_year}.parquet"
    df = pd.read_parquet(_join(cli_dir, _parquet_fn))

    max_retries = 3
    quality_guard_bypassed = False
    for retry in range(max_retries):
        try:
            quality_guard_bypassed = _run_observed_with_quality_guard_handling(
                cligen,
                prn_fn,
                cli_fn,
                adjust_mx_pt5=adjust_mx_pt5,
                silent_pass_observed_quality_guard=silent_pass_observed_quality_guard,
            )
            break
        except AssertionError:
            if retry == max_retries - 1:
                raise
            time.sleep(0.5 * (retry + 1))

    dates = df.index
    cli_path = _join(cli_dir, cli_fn)
    climate = ClimateFile(cli_path)

    climate.replace_var("rad", dates, df["srad(l/day)"])
    climate.replace_var("tdew", dates, df["tdew(degc)"])
    climate.replace_var("w-vl", dates, df["vs(m/s)"])
    climate.replace_var("w-dir", dates, df["th(DegreesClockwisefromnorth)"])

    climate.write(cli_path)
    return topaz_id, bool(quality_guard_bypassed)


def build_future(
    cligen: "Cligen",
    lng: float,
    lat: float,
    start_year: int,
    end_year: int,
    cli_dir: str,
    prn_fn: str,
    cli_fn: str,
    adjust_mx_pt5: bool = False,
) -> None:
    df = retrieve_rcp85_timeseries(lng, lat, datetime(start_year, 1, 1), datetime(end_year, 12, 31))
    df_to_prn(df, _join(cli_dir, prn_fn), "pr(mm)", "tasmax(degc)", "tasmin(degc)")
    _run_observed_with_quality_guard_handling(
        cligen,
        prn_fn,
        cli_fn,
        adjust_mx_pt5=adjust_mx_pt5,
        silent_pass_observed_quality_guard=False,
    )

    cli_path = _join(cli_dir, cli_fn)
    climate = ClimateFile(cli_path)
    climate.write(cli_path)


def get_monthlies(fn: str, lng: float, lat: float) -> list[float]:
    cmd = ["gdallocationinfo", "-wgs84", "-valonly", fn, str(lng), str(lat)]
    p = Popen(cmd, stdout=PIPE)
    p.wait()
    out = p.stdout.read()

    try:
        return [float(v) for v in out.decode("utf-8").strip().split("\n")]
    except ValueError:
        pass

    with rasterio.open(fn) as src:
        x, y = src.index(lng, lat)
        x = max(0, min(x, src.width - 1))
        y = max(0, min(y, src.height - 1))

    cmd = ["gdallocationinfo", "-valonly", fn, str(x), str(y)]
    p = Popen(cmd, stdout=PIPE, stderr=PIPE)
    p.wait()
    out = p.stdout.read()
    return [float(v) for v in out.decode("utf-8").strip().split("\n")]


def cli_revision(
    cli_fn: str,
    is_breakpoint: bool,
    ws_ppts: np.ndarray,
    ws_tmaxs: np.ndarray,
    ws_tmins: np.ndarray,
    ppt_fn: str,
    tmin_fn: str,
    tmax_fn: str,
    hill_lng: float,
    hill_lat: float,
    new_cli_path: str,
) -> str:
    hill_ppts = get_monthlies(ppt_fn, hill_lng, hill_lat)
    hill_tmins = get_monthlies(tmin_fn, hill_lng, hill_lat)
    hill_tmaxs = get_monthlies(tmax_fn, hill_lng, hill_lat)

    if not is_breakpoint:
        pyo3_cli_revision(
            cli_fn,
            new_cli_path,
            ws_ppts,
            ws_tmaxs,
            ws_tmins,
            hill_ppts,
            hill_tmaxs,
            hill_tmins,
        )
        assert _exists(new_cli_path), "wepppyo3.climate.cli_revision failed"
        return new_cli_path

    cli2 = ClimateFile(cli_fn)

    df = cli2.as_dataframe()
    rev_ppt = np.zeros(df.prcp.shape)
    rev_tmax = np.zeros(df.prcp.shape)
    rev_tmin = np.zeros(df.prcp.shape)
    dates = []

    for index, row in df.iterrows():
        mo = int(row.mo) - 1
        rev_ppt[index] = row.prcp * hill_ppts[mo] / ws_ppts[mo]
        rev_tmax[index] = row.tmax - ws_tmaxs[mo] + hill_tmaxs[mo]
        rev_tmin[index] = row.tmin - ws_tmins[mo] + hill_tmins[mo]
        dates.append((int(row.year), int(row.mo), int(row.da)))

    cli2.replace_var("prcp", dates, rev_ppt)
    cli2.replace_var("tmax", dates, rev_tmax)
    cli2.replace_var("tmin", dates, rev_tmin)
    cli2.write(new_cli_path)
    del cli2

    assert _exists(new_cli_path), "ClimateFile.revision failed"
    return new_cli_path


def _clip_cli_to_observed_years(cli_dir: str, cli_fn: str, start_year: int, end_year: int) -> ClimateFile:
    cli = ClimateFile(_join(cli_dir, cli_fn))
    cli.clip(date(start_year, 1, 1), date(end_year, 12, 31))
    cli.write(_join(cli_dir, cli_fn))
    return ClimateFile(_join(cli_dir, cli_fn))


def _apply_depnexrad_daily_temp_overrides(
    climate: "Climate",
    cli: ClimateFile,
    cli_dir: str,
    cli_fn: str,
    lng: float,
    lat: float,
    start_year: int,
    end_year: int,
) -> tuple[ClimateFile, str]:
    if climate.climate_daily_temp_ds == "prism":
        from wepppy.climates.prism.daily_client import retrieve_historical_timeseries

        df = retrieve_historical_timeseries(lng=lng, lat=lat, start_year=start_year, end_year=end_year)
        dates = df.index
        cli.replace_var("tmax", dates, df["tmax(degc)"])
        cli.replace_var("tmin", dates, df["tmin(degc)"])
        cli.replace_var("tdew", dates, df["tdmean(degc)"])
        cli_fn = cli_fn[:-4] + ".prism.cli"
        climate.cli_fn = cli_fn
        cli.write(_join(cli_dir, cli_fn))
        return ClimateFile(_join(cli_dir, cli_fn)), cli_fn

    if climate.climate_daily_temp_ds == "gridmet":
        df = gridmet_retrieve_historical_timeseries(lng, lat, start_year, end_year)
        dates = df.index
        cli.replace_var("tmax", dates, df["tmmx(degc)"])
        cli.replace_var("tmin", dates, df["tmmn(degc)"])
        cli.replace_var("rad", dates, df["srad(l/day)"])
        cli.replace_var("tdew", dates, df["tdew(degc)"])
        cli.replace_var("w-vl", dates, df["vs(m/s)"])
        cli.replace_var("w-dir", dates, df["th(DegreesClockwisefromnorth)"])
        cli_fn = cli_fn[:-4] + ".gridmet.cli"
        climate.cli_fn = cli_fn
        cli.write(_join(cli_dir, cli_fn))
        return ClimateFile(_join(cli_dir, cli_fn)), cli_fn

    if climate.climate_daily_temp_ds == "daymet":
        from wepppy.climates.daymet import retrieve_historical_timeseries as daymet_retrieve_historical_timeseries

        df = daymet_retrieve_historical_timeseries(lng, lat, start_year, end_year)
        dates = df.index
        cli.replace_var("tmax", dates, df["tmax(degc)"])
        cli.replace_var("tmin", dates, df["tmin(degc)"])
        cli.replace_var("rad", dates, df["srad(l/day)"])
        cli.replace_var("tdew", dates, df["tdew(degc)"])
        cli_fn = cli_fn[:-4] + ".daymet.cli"
        climate.cli_fn = cli_fn
        cli.write(_join(cli_dir, cli_fn))
        return ClimateFile(_join(cli_dir, cli_fn)), cli_fn

    return cli, cli_fn


def _build_depnexrad_hillslope_files(
    climate: "Climate",
    watershed: Any,
    cli_dir: str,
    start_year: int,
    end_year: int,
) -> tuple[dict[str, str], dict[str, str]]:
    sub_par_fns: dict[str, str] = {}
    sub_cli_fns: dict[str, str] = {}

    for topaz_id, (lng, lat) in watershed.centroid_hillslope_iter():
        climate.logger.info("submitting climate build for {}... ".format(topaz_id))

        lng, lat = watershed.hillslope_centroid_lnglat(topaz_id)
        hill_cli_fn = f"{lng:.02f}x{lat:.02f}.cli"
        url = f"https://mesonet-dep.agron.iastate.edu/dl/climatefile.py?lon={lng:.02f}&lat={lat:.02f}"

        if not _exists(_join(cli_dir, hill_cli_fn)):
            download_file(url, _join(cli_dir, hill_cli_fn))
            _clip_cli_to_observed_years(cli_dir, hill_cli_fn, start_year, end_year)

        sub_par_fns[topaz_id] = ".par"
        sub_cli_fns[topaz_id] = hill_cli_fn

    return sub_par_fns, sub_cli_fns


def run_depnexrad_build(climate: "Climate", verbose: bool = False, attrs: Optional[dict[str, Any]] = None) -> None:
    climate.logger.info("  running _build_climate_depnexrad... ")

    with climate.locked():
        climate.set_attrs(attrs)

        cli_dir = os.path.abspath(climate.cli_dir)
        watershed = climate.watershed_instance
        start_year, end_year = climate._require_observed_year_bounds_for_build()

        lng, lat = watershed.centroid
        climate.par_fn = ".par"
        climate.cli_fn = cli_fn = f"{lng:.02f}x{lat:.02f}.cli"
        url = f"https://mesonet-dep.agron.iastate.edu/dl/climatefile.py?lon={lng:.02f}&lat={lat:.02f}"
        download_file(url, _join(cli_dir, cli_fn))

        cli = _clip_cli_to_observed_years(cli_dir, cli_fn, start_year, end_year)
        climate.logger.info("Calculating monthlies...")
        cli, cli_fn = _apply_depnexrad_daily_temp_overrides(
            climate,
            cli,
            cli_dir,
            cli_fn,
            lng,
            lat,
            start_year,
            end_year,
        )

        climate._input_years = cli.input_years
        climate.monthlies = cli.calc_monthlies()

        from wepppy.nodb.core.climate import ClimateSpatialMode

        if climate.climate_spatialmode == ClimateSpatialMode.Multiple:
            climate.logger.info("  building climates for hillslopes... ")
            sub_par_fns, sub_cli_fns = _build_depnexrad_hillslope_files(
                climate,
                watershed,
                cli_dir,
                start_year,
                end_year,
            )
            climate.sub_par_fns = sub_par_fns
            climate.sub_cli_fns = sub_cli_fns


def _retrieve_prism_revision_tiles(climate: "Climate", map_obj: Any, ppt_fn: str, tmin_fn: str, tmax_fn: str) -> None:
    wmesque_retrieve(
        "prism/ppt",
        map_obj.extent,
        ppt_fn,
        map_obj.cellsize,
        resample="cubic",
        v=climate.wmesque_version,
        wmesque_endpoint=climate.wmesque_endpoint,
    )
    ppt_data, _transform, _proj = read_raster(ppt_fn)

    if np.any(ppt_data < 0):
        climate.logger.info("    prism/ppt contains <0 values (cubic); reacquiring with bilinear...")
        wmesque_retrieve(
            "prism/ppt",
            map_obj.extent,
            ppt_fn,
            map_obj.cellsize,
            resample="bilinear",
            v=climate.wmesque_version,
            wmesque_endpoint=climate.wmesque_endpoint,
        )

    wmesque_retrieve(
        "prism/ppt",
        map_obj.extent,
        ppt_fn,
        map_obj.cellsize,
        resample="bilinear",
        v=climate.wmesque_version,
        wmesque_endpoint=climate.wmesque_endpoint,
    )
    wmesque_retrieve(
        "prism/tmin",
        map_obj.extent,
        tmin_fn,
        map_obj.cellsize,
        resample="cubic",
        v=climate.wmesque_version,
        wmesque_endpoint=climate.wmesque_endpoint,
    )
    wmesque_retrieve(
        "prism/tmax",
        map_obj.extent,
        tmax_fn,
        map_obj.cellsize,
        resample="cubic",
        v=climate.wmesque_version,
        wmesque_endpoint=climate.wmesque_endpoint,
    )


def _collect_prism_revision_monthlies(watershed: Any, ppt_fn: str, tmin_fn: str, tmax_fn: str) -> tuple[list[float], list[float], list[float]]:
    ws_lng, ws_lat = watershed.centroid
    ws_ppts = get_monthlies(ppt_fn, ws_lng, ws_lat)
    ws_tmins = get_monthlies(tmin_fn, ws_lng, ws_lat)
    ws_tmaxs = get_monthlies(tmax_fn, ws_lng, ws_lat)
    return ws_ppts, ws_tmins, ws_tmaxs


def _submit_prism_revision_futures(
    climate: "Climate",
    executor: ThreadPoolExecutor,
    watershed: Any,
    cli: ClimateFile,
    cli_dir: str,
    ws_ppts: list[float],
    ws_tmaxs: list[float],
    ws_tmins: list[float],
    ppt_fn: str,
    tmin_fn: str,
    tmax_fn: str,
) -> tuple[dict[Any, str], dict[str, str], dict[str, str]]:
    future_map: dict[Any, str] = {}
    sub_par_fns: dict[str, str] = {}
    sub_cli_fns: dict[str, str] = {}

    for topaz_id, (hill_lng, hill_lat) in watershed.centroid_hillslope_iter():
        climate.logger.info(f"submitting climate build for {topaz_id} to thread pool... ")
        hill_lng, hill_lat = watershed.hillslope_centroid_lnglat(topaz_id)

        suffix = f"_{topaz_id}"
        new_cli_fn = f"{suffix}.cli"
        new_cli_path = _join(cli_dir, new_cli_fn)

        args = (
            cli.cli_fn,
            cli.breakpoint,
            ws_ppts,
            ws_tmaxs,
            ws_tmins,
            ppt_fn,
            tmin_fn,
            tmax_fn,
            hill_lng,
            hill_lat,
            new_cli_path,
        )

        future = executor.submit(cli_revision, *args)
        future_map[future] = topaz_id
        sub_par_fns[topaz_id] = ".par"
        sub_cli_fns[topaz_id] = new_cli_fn

    return future_map, sub_par_fns, sub_cli_fns


def _wait_for_prism_revision_futures(climate: "Climate", future_map: dict[Any, str]) -> None:
    futures_n = len(future_map)
    count = 0
    pending = set(future_map.keys())

    while pending:
        done, pending = wait(pending, timeout=30, return_when=FIRST_COMPLETED)

        if not done:
            climate.logger.warning("  Climate build tasks still running after 30 seconds; continuing to wait.")
            continue

        for future in done:
            try:
                result = future.result()
                count += 1
                climate.logger.info(f" ({count}/{futures_n}) _prism_revision() -> {result}")
            except Exception as exc:
                # Deliberate concurrency boundary: workers can raise arbitrary task exceptions.
                climate.logger.info(f"_prism_revision() -> {exc}")
                for pending_future in future_map:
                    pending_future.cancel()
                raise


def run_prism_revision(climate: "Climate", verbose: bool = False) -> None:
    wd = climate.wd
    cli_dir = climate.cli_dir

    with climate.locked():
        climate.logger.info("  running _prism_revision... ")

        cli_path = climate.cli_path
        map_obj = climate.ron_instance.map

        ppt_fn = _join(cli_dir, "ppt.tif")
        tmin_fn = _join(cli_dir, "tmin.tif")
        tmax_fn = _join(cli_dir, "tmax.tif")
        _retrieve_prism_revision_tiles(climate, map_obj, ppt_fn, tmin_fn, tmax_fn)

        watershed = climate.watershed_instance
        ws_ppts, ws_tmins, ws_tmaxs = _collect_prism_revision_monthlies(watershed, ppt_fn, tmin_fn, tmax_fn)
        climate.logger.info("  building climates for hillslopes... ")

        cli = ClimateFile(cli_path)
        with ThreadPoolExecutor(max_workers=NCPU) as executor:
            future_map, sub_par_fns, sub_cli_fns = _submit_prism_revision_futures(
                climate,
                executor,
                watershed,
                cli,
                cli_dir,
                ws_ppts,
                ws_tmaxs,
                ws_tmins,
                ppt_fn,
                tmin_fn,
                tmax_fn,
            )
            _wait_for_prism_revision_futures(climate, future_map)

        climate.sub_par_fns = sub_par_fns
        climate.sub_cli_fns = sub_cli_fns
        update_catalog_entry(wd, "climate")


def _ensure_cligen_seed(climate: "Climate") -> None:
    if climate._cligen_seed is None:
        climate._cligen_seed = random.randint(0, 99999)
        climate.dump()


def _run_mod_single_climate(
    climate: "Climate",
    mod_function: Any,
    cli_dir: str,
    watershed: Any,
) -> tuple[str, int]:
    climatestation = climate.climatestation
    years = climate._input_years
    lng, lat = watershed.centroid

    climate.par_fn = f"{climatestation}.par"
    climate.cli_fn = f"{climatestation}.cli"
    climate.monthlies = mod_function(
        par=climatestation,
        years=years,
        lng=lng,
        lat=lat,
        wd=cli_dir,
        logger=climate.logger,
        nwds_method="",
    )
    return climatestation, years


def _submit_mod_build_futures(
    climate: "Climate",
    executor: ProcessPoolExecutor,
    mod_function: Any,
    watershed: Any,
    climatestation: str,
    years: int,
    cli_dir: str,
) -> tuple[dict[Any, str], dict[str, str], dict[str, str]]:
    futures: dict[Any, str] = {}
    sub_par_fns: dict[str, str] = {}
    sub_cli_fns: dict[str, str] = {}

    for topaz_id, (hill_lng, hill_lat) in watershed.centroid_hillslope_iter():
        climate.logger.info("submitting climate build for {} to worker pool... ".format(topaz_id))

        hill_lng, hill_lat = watershed.hillslope_centroid_lnglat(topaz_id)
        suffix = f"_{topaz_id}"
        kwargs = dict(
            par=climatestation,
            years=years,
            lng=hill_lng,
            lat=hill_lat,
            wd=cli_dir,
            suffix=suffix,
            logger=None,
            nwds_method="",
        )

        sub_par_fns[topaz_id] = f"{climatestation}{suffix}.par"
        sub_cli_fns[topaz_id] = f"{climatestation}{suffix}.cli"
        futures[executor.submit(mod_function, **kwargs)] = topaz_id

    return futures, sub_par_fns, sub_cli_fns


def _wait_for_mod_build_futures(climate: "Climate", futures: dict[Any, str]) -> None:
    futures_n = len(futures)
    count = 0
    pending = set(futures.keys())

    while pending:
        done, pending = wait(pending, timeout=60, return_when=FIRST_COMPLETED)

        if not done:
            climate.logger.warning("  Climate build worker pool still running after 60 seconds; continuing to wait.")
            continue

        for future in done:
            topaz_id = futures[future]
            try:
                result = future.result()
                ppts = ["%.2f" % value for value in result["ppts"]]
                count += 1
                climate.logger.info(f"  ({count}/{futures_n})ppts: {ppts} ")
            except Exception as exc:
                # Deliberate concurrency boundary: worker tasks may raise arbitrary exceptions.
                for pending_future in pending:
                    pending_future.cancel()
                climate.logger.error(f"  Climate build for topaz {topaz_id} failed with an error: {exc}")
                raise


def _build_mod_multiple_climates(
    climate: "Climate",
    mod_function: Any,
    watershed: Any,
    climatestation: str,
    years: int,
    cli_dir: str,
) -> tuple[dict[str, str], dict[str, str]]:
    with climate.timed("  building climates for hillslopes"):
        with ProcessPoolExecutor(max_workers=NCPU) as executor:
            futures, sub_par_fns, sub_cli_fns = _submit_mod_build_futures(
                climate,
                executor,
                mod_function,
                watershed,
                climatestation,
                years,
                cli_dir,
            )
            _wait_for_mod_build_futures(climate, futures)

    return sub_par_fns, sub_cli_fns


def run_mod_build(
    climate: "Climate",
    mod_function: Any,
    verbose: bool = False,
    attrs: Optional[dict[str, Any]] = None,
) -> None:
    climate.logger.info("  running _build_climate_mod{}... \n".format(mod_function.__name__))

    with climate.locked():
        climate.set_attrs(attrs)
        _ensure_cligen_seed(climate)

        cli_dir = os.path.abspath(climate.cli_dir)
        watershed = climate.watershed_instance
        climatestation, years = _run_mod_single_climate(climate, mod_function, cli_dir, watershed)

        from wepppy.nodb.core.climate import ClimateSpatialMode

        if climate.climate_spatialmode == ClimateSpatialMode.Multiple:
            sub_par_fns, sub_cli_fns = _build_mod_multiple_climates(
                climate,
                mod_function,
                watershed,
                climatestation,
                years,
                cli_dir,
            )
            climate.sub_par_fns = sub_par_fns
            climate.sub_cli_fns = sub_cli_fns


def _prepare_daymet_multiple_context(climate: "Climate") -> tuple[Any, float, float, str, int, int, str, Cligen]:
    watershed = climate.watershed_instance
    ws_lng, ws_lat = watershed.centroid
    cli_dir = climate.cli_dir
    start_year, end_year = climate._require_observed_year_bounds_for_build()
    assert end_year <= climate.daymet_last_available_year, end_year
    climate._input_years = end_year - start_year + 1

    station_manager = CligenStationsManager(version=climate.cligen_db)
    climatestation = climate.climatestation
    station_meta = station_manager.get_station_fromid(climatestation)
    par_fn = station_meta.par
    cligen = Cligen(station_meta, wd=cli_dir)

    return watershed, ws_lng, ws_lat, cli_dir, start_year, end_year, par_fn, cligen


def _build_daymet_hillslope_locations(watershed: Any, ws_lng: float, ws_lat: float) -> dict[str, dict[str, float]]:
    hillslope_locations: dict[str, dict[str, float]] = {"ws": {"longitude": ws_lng, "latitude": ws_lat}}
    for topaz_id, (_lng, _lat) in watershed.centroid_hillslope_iter():
        hillslope_locations[topaz_id] = {"longitude": _lng, "latitude": _lat}
    return hillslope_locations


def _interpolate_daymet_hillslope_series(climate: "Climate", cli_dir: str, hillslope_locations: dict[str, dict[str, float]]) -> None:
    from wepppy.climates.daymet.daymet_singlelocation_client import interpolate_daily_timeseries

    with climate.timed("  interpolating daymet grids"):
        interpolate_daily_timeseries(
            hillslope_locations,
            climate.observed_start_year,
            climate.observed_end_year,
            output_dir=cli_dir,
            output_type="prn parquet",
            logger=climate.logger,
        )


def _resolve_daymet_wind(
    climate: "Climate",
    ws_lng: float,
    ws_lat: float,
    start_year: int,
    end_year: int,
) -> tuple[Optional[Any], Optional[Any]]:
    if not climate.use_gridmet_wind_when_applicable:
        return None, None

    with climate.timed("  retrieving gridmet wind"):
        wind_df = gridmet_retrieve_historical_wind(ws_lng, ws_lat, start_year, end_year)
        return wind_df["vs(m/s)"], wind_df["th(DegreesClockwisefromnorth)"]


def _resolve_daymet_worker_count() -> int:
    workers = 40
    if os.getenv("WEPPPY_NCPU"):
        workers = min(workers, NCPU)
    return workers


def _submit_daymet_futures(
    climate: "Climate",
    executor: ProcessPoolExecutor,
    watershed: Any,
    cligen: Cligen,
    ws_lng: float,
    ws_lat: float,
    start_year: int,
    end_year: int,
    cli_dir: str,
    wind_vs: Optional[Any],
    wind_dir: Optional[Any],
) -> tuple[list[Any], dict[str, str], dict[str, str], str]:
    futures: list[Any] = []
    sub_par_fns: dict[str, str] = {}
    sub_cli_fns: dict[str, str] = {}

    for topaz_id, (_lng, _lat) in watershed.centroid_hillslope_iter():
        prn_fn = f"daymet_observed_{topaz_id}_{start_year}-{end_year}.prn"
        hill_cli_fn = f"daymet_observed_{topaz_id}_{start_year}-{end_year}.cli"
        climate.logger.info(f"submitting climate build for {topaz_id} ...")

        futures.append(
            executor.submit(
                build_observed_daymet_interpolated,
                cligen,
                topaz_id,
                _lng,
                _lat,
                start_year,
                end_year,
                cli_dir,
                hill_cli_fn,
                prn_fn,
                wind_vs=wind_vs,
                wind_dir=wind_dir,
                adjust_mx_pt5=climate.adjust_mx_pt5,
                silent_pass_observed_quality_guard=climate.silent_pass_observed_quality_guard,
            )
        )
        sub_par_fns[topaz_id] = prn_fn
        sub_cli_fns[topaz_id] = hill_cli_fn

    ws_topaz_id = "ws"
    ws_prn_fn = f"daymet_observed_{ws_topaz_id}_{start_year}-{end_year}.prn"
    ws_cli_fn = "wepp.cli"
    futures.append(
        executor.submit(
            build_observed_daymet_interpolated,
            cligen,
            ws_topaz_id,
            ws_lng,
            ws_lat,
            start_year,
            end_year,
            cli_dir,
            ws_cli_fn,
            ws_prn_fn,
            wind_vs=wind_vs,
            wind_dir=wind_dir,
            adjust_mx_pt5=climate.adjust_mx_pt5,
            silent_pass_observed_quality_guard=climate.silent_pass_observed_quality_guard,
        )
    )

    return futures, sub_par_fns, sub_cli_fns, ws_cli_fn


def _wait_for_daymet_futures(climate: "Climate", futures: list[Any], executor: ProcessPoolExecutor) -> bool:
    any_quality_guard_bypassed = False

    def _normalize_result(result: Any) -> tuple[Any, bool]:
        if isinstance(result, tuple) and len(result) == 2:
            topaz_id, bypassed = result
            return topaz_id, bool(bypassed)
        return result, False

    pending = set(futures)
    try:
        while pending:
            done, pending = wait(pending, timeout=60, return_when=FIRST_COMPLETED)

            if not done:
                climate.logger.warning("  Daymet climate build still running after 60 seconds; continuing to wait.")
                continue

            for future in done:
                completed_topaz, bypassed = _normalize_result(future.result())
                if bypassed:
                    any_quality_guard_bypassed = True
                climate.logger.info(f"  climate for {completed_topaz} done.")
        return any_quality_guard_bypassed
    except Exception:
        # Deliberate concurrency boundary: cancel remaining worker tasks before surfacing failure.
        for pending_future in futures:
            if not pending_future.done():
                pending_future.cancel()
        executor.shutdown(wait=False, cancel_futures=True)
        raise


def _finalize_daymet_multiple_build(
    climate: "Climate",
    cli_dir: str,
    cli_fn: str,
    par_fn: str,
    sub_par_fns: dict[str, str],
    sub_cli_fns: dict[str, str],
) -> None:
    climate_file = ClimateFile(_join(cli_dir, cli_fn))
    climate.monthlies = climate_file.calc_monthlies()
    climate.cli_fn = cli_fn
    climate.par_fn = par_fn
    climate.sub_par_fns = sub_par_fns
    climate.sub_cli_fns = sub_cli_fns


def run_observed_daymet_multiple_build(
    climate: "Climate",
    verbose: bool = False,
    attrs: Optional[dict[str, Any]] = None,
) -> bool:
    with climate.locked():
        climate.set_attrs(attrs)
        climate.logger.info("  running _build_climate_observed_daymet_multiple")

        (
            watershed,
            ws_lng,
            ws_lat,
            cli_dir,
            start_year,
            end_year,
            par_fn,
            cligen,
        ) = _prepare_daymet_multiple_context(climate)
        hillslope_locations = _build_daymet_hillslope_locations(watershed, ws_lng, ws_lat)
        _interpolate_daymet_hillslope_series(climate, cli_dir, hillslope_locations)
        wind_vs, wind_dir = _resolve_daymet_wind(climate, ws_lng, ws_lat, start_year, end_year)

        with ProcessPoolExecutor(max_workers=_resolve_daymet_worker_count()) as executor:
            futures, sub_par_fns, sub_cli_fns, cli_fn = _submit_daymet_futures(
                climate,
                executor,
                watershed,
                cligen,
                ws_lng,
                ws_lat,
                start_year,
                end_year,
                cli_dir,
                wind_vs,
                wind_dir,
            )
            any_quality_guard_bypassed = _wait_for_daymet_futures(climate, futures, executor)

        _finalize_daymet_multiple_build(
            climate,
            cli_dir,
            cli_fn,
            par_fn,
            sub_par_fns,
            sub_cli_fns,
        )
        climate._publish_quality_guard_bypass_warning_if_needed(
            quality_guard_bypassed=any_quality_guard_bypassed
        )
        return any_quality_guard_bypassed
