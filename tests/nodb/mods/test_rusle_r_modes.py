from __future__ import annotations

import pandas as pd
import pytest
from shapely.geometry import Polygon

from wepppy.nodb.mods.rusle.r_modes import (
    RUSLE2_R_ENGLISH_TO_SI,
    select_canonical_rusle2_r,
    select_momm2025_county_region_r,
)


gpd = pytest.importorskip("geopandas")

pytestmark = pytest.mark.unit


def _build_momm_row(*, fips: str, region: str | None, annual_r: float) -> dict[str, object]:
    monthly = {
        "jan": 1.0,
        "feb": 2.0,
        "mar": 3.0,
        "apr": 4.0,
        "may": 5.0,
        "jun": 6.0,
        "jul": 7.0,
        "aug": 8.0,
        "sep": 9.0,
        "oct": 10.0,
        "nov": 11.0,
        "dec": 12.0,
    }
    return {
        "fips": fips,
        "region": region,
        "county": "Example County",
        "state": "EX",
        "state_fips": 1,
        "county_fips": 1,
        **monthly,
        "annual_r": annual_r,
    }


def test_select_momm2025_county_region_r_returns_single_county_selection() -> None:
    counties = gpd.GeoDataFrame(
        {"fips": ["01001"]},
        geometry=[Polygon([(0, 0), (2, 0), (2, 2), (0, 2)])],
        crs="EPSG:4326",
    )
    table = pd.DataFrame([_build_momm_row(fips="01001", region=None, annual_r=78.0)])

    selection = select_momm2025_county_region_r((1.0, 1.0), table=table, counties=counties)

    assert selection.r_mode == "momm2025_county_region"
    assert selection.r_source_label == "Momm 2025 County Climatology"
    assert selection.selected_fips == "01001"
    assert selection.selected_region is None
    assert selection.r_scalar_value == pytest.approx(78.0)
    assert selection.monthly_dataset_values is not None
    assert selection.monthly_dataset_values["jul"] == pytest.approx(7.0)


def test_select_momm2025_county_region_r_requires_annual_precip_for_split_county() -> None:
    counties = gpd.GeoDataFrame(
        {"fips": ["53009"]},
        geometry=[Polygon([(0, 0), (2, 0), (2, 2), (0, 2)])],
        crs="EPSG:4326",
    )
    table = pd.DataFrame(
        [
            _build_momm_row(fips="53009", region="20-22", annual_r=70.0),
            _build_momm_row(fips="53009", region="22-25", annual_r=71.0),
        ]
    )

    with pytest.raises(ValueError, match="require localized annual precipitation"):
        select_momm2025_county_region_r((1.0, 1.0), table=table, counties=counties)


def test_select_momm2025_county_region_r_selects_split_county_by_annual_precip() -> None:
    counties = gpd.GeoDataFrame(
        {"fips": ["16015"]},
        geometry=[Polygon([(0, 0), (2, 0), (2, 2), (0, 2)])],
        crs="EPSG:4326",
    )
    table = pd.DataFrame(
        [
            _build_momm_row(fips="16015", region="20-22", annual_r=60.0),
            _build_momm_row(fips="16015", region="22-25", annual_r=61.0),
            _build_momm_row(fips="16015", region="25-28", annual_r=62.0),
        ]
    )

    selection = select_momm2025_county_region_r(
        (1.0, 1.0),
        annual_precip_in=22.4,
        table=table,
        counties=counties,
    )

    assert selection.selected_fips == "16015"
    assert selection.selected_region == "22-25"
    assert selection.r_selection_method == "watershed_centroid_county_annual_precip_bin"
    assert selection.r_scalar_value == pytest.approx(61.0)
    assert selection.notes == [
        "Split-county REGION row selected using localized annual precipitation 22.400 in."
    ]


def test_select_canonical_rusle2_r_converts_english_r_to_si() -> None:
    zones = gpd.GeoDataFrame(
        {
            "REC_LINK": ["10-11"],
            "has_climate_record": [True],
            "r_factor_english": [500.0],
            "selected_record_name_decoded": ["Example Record"],
            "selected_record_variant": ["plain"],
            "selected_source_zip_name": ["Example.zip"],
        },
        geometry=[Polygon([(0, 0), (2, 0), (2, 2), (0, 2)])],
        crs="EPSG:4326",
    )

    selection = select_canonical_rusle2_r((1.0, 1.0), zones=zones)

    assert selection.r_mode == "canonical_rusle2"
    assert selection.selected_rec_link == "10-11"
    assert selection.selected_record_name == "Example Record"
    assert selection.r_scalar_value == pytest.approx(500.0 * RUSLE2_R_ENGLISH_TO_SI)
    assert selection.annual_source_field == "r_factor_english"


def test_select_canonical_rusle2_r_rejects_polygon_without_record() -> None:
    zones = gpd.GeoDataFrame(
        {
            "REC_LINK": ["10-11"],
            "has_climate_record": [False],
            "r_factor_english": [500.0],
        },
        geometry=[Polygon([(0, 0), (2, 0), (2, 2), (0, 2)])],
        crs="EPSG:4326",
    )

    with pytest.raises(ValueError, match="no polygon-backed climate record"):
        select_canonical_rusle2_r((1.0, 1.0), zones=zones)


def test_select_canonical_rusle2_r_rejects_ambiguous_rec_links() -> None:
    zones = gpd.GeoDataFrame(
        {
            "REC_LINK": ["10-11", "12-13"],
            "has_climate_record": [True, True],
            "r_factor_english": [500.0, 600.0],
        },
        geometry=[
            Polygon([(0, 0), (2, 0), (2, 2), (0, 2)]),
            Polygon([(0, 0), (2, 0), (2, 2), (0, 2)]),
        ],
        crs="EPSG:4326",
    )

    with pytest.raises(ValueError, match="multiple official RUSLE2 REC_LINK polygons"):
        select_canonical_rusle2_r((1.0, 1.0), zones=zones)
