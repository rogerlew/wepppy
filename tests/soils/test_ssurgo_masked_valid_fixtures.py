from __future__ import annotations

import json
from pathlib import Path

import pytest

from wepppyo3.raster_characteristics import local_mukey_candidates


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
