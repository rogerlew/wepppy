from __future__ import annotations

import os
from typing import Iterable, Sequence

import pytest

from wepppy.soils.ssurgo import (
    StatsgoSpatial,
    SurgoSoilCollection,
    query_mukeys_in_extent,
)

pytestmark = [pytest.mark.integration, pytest.mark.slow]

_ENV_FLAG = "SSURGO_INTEGRATION"
_TRUE_VALUES = {"1", "true", "yes", "on"}

_CDA_EXTENT = (-116.05, 47.0, -116.0, 47.05)
_CDA_EXPECTED_MUKEYS = {
    2396743,
    2396746,
    2396747,
    2396748,
    2396765,
    2396774,
    2396775,
    2396776,
    2396777,
    2396851,
    2396852,
    2396853,
    2396855,
    2396856,
    2396857,
    2396858,
    2396860,
    2396861,
    2396863,
    2396866,
    2396867,
    2397009,
    2397043,
    2397044,
    2397046,
    2397047,
    2397467,
    2397468,
    2397480,
    2397482,
}

_MEADOW_EXTENT = (-115.201226, 45.372097, -115.20, 45.373)
_MEADOW_EXPECTED = {2518587, 3332297}
_MIN_DEPTH_MUKEY = 1652031


def _require_ssurgo_env() -> None:
    if os.getenv(_ENV_FLAG, "").strip().lower() not in _TRUE_VALUES:
        pytest.skip(f"Set {_ENV_FLAG}=1 to run SSURGO integration tests.")


def _assert_expected_subset(actual: Iterable[int], expected_subset: Sequence[int]) -> None:
    missing = [value for value in expected_subset if value not in actual]
    assert not missing, f"Missing expected mukeys: {missing}"


@pytest.mark.requires_network
def test_query_mukeys_in_extent_returns_expected_sample() -> None:
    _require_ssurgo_env()
    mukeys = query_mukeys_in_extent(_CDA_EXTENT)
    assert mukeys, "Query returned no mukeys for CDA extent"
    _assert_expected_subset(mukeys, sorted(_CDA_EXPECTED_MUKEYS))


@pytest.mark.requires_network
def test_query_mukeys_in_extent_handles_small_bbox() -> None:
    _require_ssurgo_env()
    mukeys = query_mukeys_in_extent(_MEADOW_EXTENT)
    assert mukeys, "Query returned no mukeys for Meadow extent"
    assert _MEADOW_EXPECTED & mukeys, f"Expected one of {_MEADOW_EXPECTED}, got {sorted(mukeys)}"


@pytest.mark.requires_network
def test_surgo_collection_builds_valid_wepp_soils(tmp_path) -> None:
    _require_ssurgo_env()
    mukeys = query_mukeys_in_extent(_CDA_EXTENT)
    assert mukeys

    collection = SurgoSoilCollection(mukeys)
    collection.makeWeppSoils()

    valid = set(collection.getValidWeppSoils())
    assert valid, "No valid WEPP soils were built"
    _assert_expected_subset(valid, sorted(_CDA_EXPECTED_MUKEYS))

    outputs = collection.writeWeppSoils(str(tmp_path))
    assert outputs, "writeWeppSoils did not persist any soil files"
    assert list(tmp_path.glob("*.sol")), "WEPP .sol files were not written"


@pytest.mark.requires_network
def test_surgo_collection_handles_sparse_extent() -> None:
    _require_ssurgo_env()
    mukeys = query_mukeys_in_extent(_MEADOW_EXTENT)
    assert mukeys

    collection = SurgoSoilCollection(mukeys)
    collection.makeWeppSoils()
    valid = collection.getValidWeppSoils()

    assert valid in ([], [3332297]), f"Unexpected valid soils list: {valid}"


@pytest.mark.requires_network
def test_surgo_collection_writes_min_depth_soil(tmp_path) -> None:
    _require_ssurgo_env()
    collection = SurgoSoilCollection([_MIN_DEPTH_MUKEY])
    collection.makeWeppSoils()

    outputs = collection.writeWeppSoils(str(tmp_path))
    assert _MIN_DEPTH_MUKEY in outputs
    assert list(tmp_path.glob("*.sol")), "Expected WEPP soil file in tmp directory"


@pytest.fixture(scope="module")
def statsgo_spatial() -> StatsgoSpatial:
    return StatsgoSpatial()


def test_statsgo_identify_mukey_point(statsgo_spatial: StatsgoSpatial) -> None:
    mukey = statsgo_spatial.identify_mukey_point(-115.201226, 45.372097)
    assert mukey == 661951


def test_statsgo_identify_mukeys_extent(statsgo_spatial: StatsgoSpatial) -> None:
    mukeys = statsgo_spatial.identify_mukeys_extent(_MEADOW_EXTENT)
    assert mukeys == [661787, 661951, 661956]


def test_statsgo_mukey_catalog_size(statsgo_spatial: StatsgoSpatial) -> None:
    mukeys = statsgo_spatial.mukeys
    assert mukeys is not None
    assert len(mukeys) == 84000
