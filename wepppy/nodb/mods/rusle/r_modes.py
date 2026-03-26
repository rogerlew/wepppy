"""RUSLE R-factor mode selectors for planning-climatology datasets."""

from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
import math
from pathlib import Path
from typing import Any

import pandas as pd
from shapely.geometry import Point

__all__ = [
    "RUSLE2_R_ENGLISH_TO_SI",
    "SUPPORTED_R_MODES",
    "RusleRModeSelection",
    "select_momm2025_county_region_r",
    "select_canonical_rusle2_r",
]

SUPPORTED_R_MODES: tuple[str, ...] = (
    "cligen_static",
    "momm2025_county_region",
    "canonical_rusle2",
)

RUSLE2_R_ENGLISH_TO_SI = 17.02

MONTH_COLUMNS: tuple[str, ...] = (
    "jan",
    "feb",
    "mar",
    "apr",
    "may",
    "jun",
    "jul",
    "aug",
    "sep",
    "oct",
    "nov",
    "dec",
)

R_SCALAR_UNITS_SI = "MJ*mm/(ha*h*yr)"
R_DATASET_UNITS_ENGLISH = "hundred_ft_tonf_in/(acre*hr*yr)"

MOMM_TABLE_RELPATH = "wepppy/nodb/mods/rusle/data/momm2025/momm2025_county_region_monthly_r.parquet"
MOMM_COUNTIES_RELPATH = "wepppy/nodb/mods/rusle/data/momm2025/momm2025_counties_conus_2010_500k.geoparquet"
RUSLE2_RECORDS_RELPATH = "wepppy/nodb/mods/rusle/data/rusle2/rusle2_official_climate_records.parquet"
RUSLE2_ZONES_RELPATH = "wepppy/nodb/mods/rusle/data/rusle2/rusle2_official_climate_zones.geoparquet"
RUSLE2_SOURCE_FILES_RELPATH = "wepppy/nodb/mods/rusle/data/rusle2/rusle2_official_source_files.parquet"


def _data_root() -> Path:
    return Path(__file__).resolve().parent / "data"


def _import_geopandas():
    try:
        import geopandas as gpd
    except ImportError as exc:
        raise ImportError(
            "RUSLE external r_mode selections require geopandas. Install geopandas "
            "or use r_mode='cligen_static'."
        ) from exc
    return gpd


def _optional_str(value: Any) -> str | None:
    if value is None:
        return None
    if isinstance(value, str):
        token = value.strip()
        return token if token else None
    if isinstance(value, (float, int)) and not math.isfinite(float(value)):
        return None
    token = str(value).strip()
    return token if token else None


def _coerce_centroid(centroid_lnglat: tuple[float, float]) -> tuple[float, float]:
    if not isinstance(centroid_lnglat, tuple) or len(centroid_lnglat) != 2:
        raise ValueError("Watershed centroid must be a (longitude, latitude) tuple.")
    lng = float(centroid_lnglat[0])
    lat = float(centroid_lnglat[1])
    if not math.isfinite(lng) or not math.isfinite(lat):
        raise ValueError("Watershed centroid coordinates must be finite numbers.")
    return lng, lat


def _coerce_finite_float(value: Any, *, field_name: str) -> float:
    try:
        parsed = float(value)
    except (TypeError, ValueError) as exc:
        raise ValueError(f"Expected numeric {field_name}, got {value!r}.") from exc
    if not math.isfinite(parsed):
        raise ValueError(f"Expected finite {field_name}, got {value!r}.")
    return parsed


def _point_in_crs(*, lng: float, lat: float, target_crs: Any):
    gpd = _import_geopandas()
    point_series = gpd.GeoSeries([Point(lng, lat)], crs="EPSG:4326")
    if target_crs is not None and str(point_series.crs) != str(target_crs):
        point_series = point_series.to_crs(target_crs)
    return point_series.iloc[0]


def _find_polygon_matches(frame, point):
    covered = frame.geometry.covers(point)
    matches = frame.loc[covered]
    if matches.empty:
        intersects = frame.geometry.intersects(point)
        matches = frame.loc[intersects]
    return matches


def _extract_monthly_values(row: Any, *, prefix: str = "") -> dict[str, float] | None:
    monthly: dict[str, float] = {}
    saw_value = False
    for month in MONTH_COLUMNS:
        key = f"{prefix}{month}"
        if key not in row:
            return None
        raw = row[key]
        if raw is None or (isinstance(raw, float) and math.isnan(raw)):
            if saw_value:
                raise ValueError(f"Partial monthly erosivity values found; missing {key}.")
            return None
        value = _coerce_finite_float(raw, field_name=key)
        monthly[month] = value
        saw_value = True
    return monthly if saw_value else None


def _parse_region_interval(value: Any) -> tuple[float, float] | None:
    token = _optional_str(value)
    if token is None:
        return None

    lower_token, separator, upper_token = token.partition("-")
    if separator != "-":
        return None

    lower = _coerce_finite_float(lower_token, field_name="region_lower")
    upper = _coerce_finite_float(upper_token, field_name="region_upper")
    if lower >= upper:
        raise ValueError(f"Expected region lower bound to be less than upper bound, got {token!r}.")
    return lower, upper


@lru_cache(maxsize=1)
def _load_momm_table():
    table = pd.read_parquet(_data_root() / "momm2025" / "momm2025_county_region_monthly_r.parquet").copy()
    table["fips"] = table["fips"].astype(str).str.zfill(5)
    return table


@lru_cache(maxsize=1)
def _load_momm_counties():
    gpd = _import_geopandas()
    counties = gpd.read_parquet(_data_root() / "momm2025" / "momm2025_counties_conus_2010_500k.geoparquet").copy()
    counties["fips"] = counties["fips"].astype(str).str.zfill(5)
    return counties


@lru_cache(maxsize=1)
def _load_rusle2_zones():
    gpd = _import_geopandas()
    return gpd.read_parquet(_data_root() / "rusle2" / "rusle2_official_climate_zones.geoparquet").copy()


@dataclass(frozen=True)
class RusleRModeSelection:
    r_mode: str
    r_source_label: str
    r_source_purpose: str
    r_selection_method: str
    r_scalar_value: float
    r_scalar_units: str
    annual_source_field: str
    annual_dataset_value: float
    annual_dataset_units: str
    centroid_lng: float
    centroid_lat: float
    selected_fips: str | None = None
    selected_county: str | None = None
    selected_region: str | None = None
    selected_rec_link: str | None = None
    selected_record_name: str | None = None
    selected_record_variant: str | None = None
    selected_source_zip: str | None = None
    monthly_dataset_values: dict[str, float] | None = None
    dataset_artifacts: dict[str, str] | None = None
    notes: list[str] | None = None

    def to_manifest_payload(self) -> dict[str, Any]:
        payload: dict[str, Any] = {
            "r_mode": self.r_mode,
            "r_source_label": self.r_source_label,
            "r_source_purpose": self.r_source_purpose,
            "r_selection_method": self.r_selection_method,
            "r_scalar": float(self.r_scalar_value),
            "r_scalar_units": self.r_scalar_units,
            "annual_source_field": self.annual_source_field,
            "annual_dataset_value": float(self.annual_dataset_value),
            "annual_dataset_units": self.annual_dataset_units,
            "watershed_centroid_lnglat": [float(self.centroid_lng), float(self.centroid_lat)],
            "selected_fips": self.selected_fips,
            "selected_county": self.selected_county,
            "selected_region": self.selected_region,
            "selected_rec_link": self.selected_rec_link,
            "selected_record_name": self.selected_record_name,
            "selected_record_variant": self.selected_record_variant,
            "selected_source_zip": self.selected_source_zip,
            "monthly_dataset_values": self.monthly_dataset_values,
            "dataset_artifacts": self.dataset_artifacts or {},
            "notes": list(self.notes or []),
        }
        return payload


def select_momm2025_county_region_r(
    centroid_lnglat: tuple[float, float],
    *,
    annual_precip_in: float | None = None,
    table: pd.DataFrame | None = None,
    counties=None,
) -> RusleRModeSelection:
    """Select Momm 2025 annual R by watershed centroid county."""
    lng, lat = _coerce_centroid(centroid_lnglat)
    county_table = table.copy() if table is not None else _load_momm_table().copy()
    county_polygons = counties.copy() if counties is not None else _load_momm_counties().copy()

    point = _point_in_crs(lng=lng, lat=lat, target_crs=county_polygons.crs)
    county_matches = _find_polygon_matches(county_polygons, point)
    if county_matches.empty:
        raise ValueError(
            "Watershed centroid does not intersect a supported Momm 2025 county polygon; "
            "momm2025_county_region supports CONUS+DC county coverage only."
        )

    matched_fips = sorted(
        {
            str(value).zfill(5)
            for value in county_matches["fips"].tolist()
            if _optional_str(value) is not None
        }
    )
    if len(matched_fips) != 1:
        raise ValueError(
            "Watershed centroid intersects multiple county polygons in the Momm 2025 "
            f"county layer ({matched_fips}); cannot determine one county deterministically."
        )

    selected_fips = matched_fips[0]
    matched_rows = county_table.loc[county_table["fips"] == selected_fips].copy()
    if matched_rows.empty:
        raise ValueError(f"Momm 2025 table did not contain FIPS {selected_fips}.")

    selection_method = "watershed_centroid_county"
    notes: list[str] | None = None
    if len(matched_rows) > 1:
        region_labels = sorted(
            {
                label
                for label in (_optional_str(value) for value in matched_rows["region"].tolist())
                if label is not None
            }
        )
        if annual_precip_in is None:
            raise ValueError(
                "Momm 2025 split-county REGION rows require localized annual precipitation for "
                f"runtime selection (selected county FIPS {selected_fips}, regions={region_labels})."
            )

        precip_in = _coerce_finite_float(annual_precip_in, field_name="annual_precip_in")
        parsed_rows: list[tuple[float, float, int]] = []
        for row_index, region_value in matched_rows["region"].items():
            bounds = _parse_region_interval(region_value)
            if bounds is None:
                raise ValueError(
                    "Momm 2025 split-county REGION rows must use numeric interval labels for "
                    f"runtime selection (selected county FIPS {selected_fips}, regions={region_labels})."
                )
            parsed_rows.append((bounds[0], bounds[1], row_index))

        parsed_rows.sort(key=lambda item: (item[0], item[1], item[2]))
        max_upper = max(upper for _, upper, _ in parsed_rows)
        matching_indexes = [
            row_index
            for lower, upper, row_index in parsed_rows
            if (lower <= precip_in < upper)
            or (math.isclose(precip_in, max_upper) and math.isclose(upper, max_upper))
        ]
        if len(matching_indexes) != 1:
            raise ValueError(
                "Momm 2025 split-county REGION rows did not contain a unique annual precipitation "
                f"match for county FIPS {selected_fips} (annual_precip_in={precip_in}, regions={region_labels})."
            )

        matched_rows = matched_rows.loc[matching_indexes].copy()
        selection_method = "watershed_centroid_county_annual_precip_bin"
        notes = [f"Split-county REGION row selected using localized annual precipitation {precip_in:.3f} in."]

    row = matched_rows.iloc[0]
    monthly_values = _extract_monthly_values(row)
    if monthly_values is None:
        raise ValueError(
            f"Momm 2025 row for FIPS {selected_fips} is missing monthly erosivity values."
        )

    annual_r = _coerce_finite_float(row.get("annual_r"), field_name="annual_r")
    return RusleRModeSelection(
        r_mode="momm2025_county_region",
        r_source_label="Momm 2025 County Climatology",
        r_source_purpose=(
            "Uses the published Momm et al. (2025) RUSLE2 monthly erosivity "
            "climatology for the watershed centroid county."
        ),
        r_selection_method=selection_method,
        r_scalar_value=annual_r,
        r_scalar_units=R_SCALAR_UNITS_SI,
        annual_source_field="annual_r",
        annual_dataset_value=annual_r,
        annual_dataset_units=R_SCALAR_UNITS_SI,
        centroid_lng=lng,
        centroid_lat=lat,
        selected_fips=selected_fips,
        selected_county=_optional_str(row.get("county")),
        selected_region=_optional_str(row.get("region")),
        monthly_dataset_values=monthly_values,
        dataset_artifacts={
            "momm_table": MOMM_TABLE_RELPATH,
            "momm_counties": MOMM_COUNTIES_RELPATH,
        },
        notes=notes,
    )


def select_canonical_rusle2_r(
    centroid_lnglat: tuple[float, float],
    *,
    zones=None,
) -> RusleRModeSelection:
    """Select canonical official RUSLE2 annual R by centroid polygon lookup."""
    lng, lat = _coerce_centroid(centroid_lnglat)
    zone_polygons = zones.copy() if zones is not None else _load_rusle2_zones().copy()

    point = _point_in_crs(lng=lng, lat=lat, target_crs=zone_polygons.crs)
    zone_matches = _find_polygon_matches(zone_polygons, point)
    if zone_matches.empty:
        raise ValueError(
            "Watershed centroid does not intersect a polygon-backed official RUSLE2 climate zone. "
            "canonical_rusle2 currently supports polygon-backed official links only."
        )

    matched_rec_links = sorted(
        {
            str(value).strip()
            for value in zone_matches["REC_LINK"].tolist()
            if _optional_str(value) is not None
        }
    )
    if not matched_rec_links:
        raise ValueError("Matched official climate zone rows are missing REC_LINK values.")

    if len(matched_rec_links) > 1:
        raise ValueError(
            "Watershed centroid intersects multiple official RUSLE2 REC_LINK polygons "
            f"({matched_rec_links}); cannot select one climate zone deterministically."
        )

    selected_rec_link = matched_rec_links[0]
    link_matches = zone_matches.loc[zone_matches["REC_LINK"].astype(str).str.strip() == selected_rec_link].copy()
    if link_matches.empty:
        raise ValueError(f"Official RUSLE2 REC_LINK {selected_rec_link} could not be resolved.")

    sort_columns = [column for column in ("OBJECTID", "Shape_Area") if column in link_matches.columns]
    if sort_columns:
        link_matches = link_matches.sort_values(by=sort_columns, kind="mergesort")
    selected_row = link_matches.iloc[0]

    has_record = bool(selected_row.get("has_climate_record", False))
    if not has_record:
        raise ValueError(
            "Official RUSLE2 centroid polygon was found but has no polygon-backed climate record "
            f"(REC_LINK={selected_rec_link})."
        )

    r_factor_english = _coerce_finite_float(
        selected_row.get("r_factor_english"),
        field_name="r_factor_english",
    )
    r_scalar_si = r_factor_english * RUSLE2_R_ENGLISH_TO_SI

    monthly_values = _extract_monthly_values(selected_row, prefix="r_monthly_")
    notes = [f"Converted official RUSLE2 English R to SI using factor {RUSLE2_R_ENGLISH_TO_SI}."]
    return RusleRModeSelection(
        r_mode="canonical_rusle2",
        r_source_label="Canonical RUSLE2",
        r_source_purpose=(
            "Uses the vendored official RUSLE2 climate database and climate-zone "
            "polygons at the watershed centroid."
        ),
        r_selection_method="watershed_centroid_official_polygon",
        r_scalar_value=r_scalar_si,
        r_scalar_units=R_SCALAR_UNITS_SI,
        annual_source_field="r_factor_english",
        annual_dataset_value=r_factor_english,
        annual_dataset_units=R_DATASET_UNITS_ENGLISH,
        centroid_lng=lng,
        centroid_lat=lat,
        selected_rec_link=selected_rec_link,
        selected_record_name=_optional_str(
            selected_row.get("selected_record_name_decoded") or selected_row.get("selected_record_name")
        ),
        selected_record_variant=_optional_str(selected_row.get("selected_record_variant")),
        selected_source_zip=_optional_str(selected_row.get("selected_source_zip_name")),
        monthly_dataset_values=monthly_values,
        dataset_artifacts={
            "official_records": RUSLE2_RECORDS_RELPATH,
            "official_zones": RUSLE2_ZONES_RELPATH,
            "official_source_inventory": RUSLE2_SOURCE_FILES_RELPATH,
        },
        notes=notes,
    )
