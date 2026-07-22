from __future__ import annotations

import json
from pathlib import Path

import pytest

from wepppyo3.raster_characteristics import local_mukey_candidates, local_mukey_geometry


pytestmark = pytest.mark.unit

FIXTURE_DIRECTORY = Path(__file__).parents[1] / "data" / "ssurgo_masked_valid"


def _local_majority(support: list[tuple[int, int]]) -> int | None:
    if not support:
        return None
    return sorted(support, key=lambda item: (-item[1], item[0]))[0][0]


def test_masked_valid_raster_fixture_corpus() -> None:
    scenarios = json.loads((FIXTURE_DIRECTORY / "scenarios.json").read_text(encoding="utf-8"))

    for scenario in scenarios:
        clusters = [
            (cluster["id"], cluster["source_mukeys"], tuple(cluster["bounds"]))
            for cluster in scenario["clusters"]
        ]
        results = local_mukey_candidates(
            raster_path=str(FIXTURE_DIRECTORY / scenario["raster"]),
            clusters=clusters,
            valid_mukeys=set(scenario["valid_mukeys"]),
            initial_radius_m=scenario["initial_radius_m"],
            max_radius_m=scenario["max_radius_m"],
            workers=2,
        )

        assert set(results) == {cluster["id"] for cluster in scenario["clusters"]}
        for cluster in scenario["clusters"]:
            _, radius_m, support, exhausted, _ = results[cluster["id"]]
            assert radius_m == cluster["expected_radius_m"]
            assert _local_majority(support) == cluster["expected_mukey"]
            assert exhausted is (cluster["expected_mukey"] is None)


def test_masked_valid_geometry_separates_shared_edges_from_support() -> None:
    result = local_mukey_geometry(
        raster_path=str(FIXTURE_DIRECTORY / "direct_local.tif"),
        sources=[("source", 10, (0, 0, 90, 90))],
        valid_mukeys={20, 30},
        initial_radius_m=1,
        max_radius_m=1,
        workers=1,
    )
    source_mukey, radius_m, candidates, exhausted, _ = result["source"]
    assert source_mukey == 10
    assert radius_m == 1
    assert candidates == [(20, 3, 2), (30, 2, 0)]
    assert exhausted is False


def test_masked_valid_geometry_keeps_sources_distinct_in_one_call() -> None:
    results = local_mukey_geometry(
        raster_path=str(FIXTURE_DIRECTORY / "separated_clusters.tif"),
        sources=[
            ("left", 10, (0, 0, 90, 90)),
            ("right", 11, (90, 0, 180, 90)),
        ],
        valid_mukeys={20, 30},
        initial_radius_m=1,
        max_radius_m=1,
        workers=2,
    )
    # Support is calculated from each source's own bounded search window;
    # a candidate can therefore have regional support but no shared edge.
    assert results["left"][2] == [(20, 4, 2), (30, 1, 0)]
    assert results["right"][2] == [(20, 1, 1), (30, 4, 2)]
