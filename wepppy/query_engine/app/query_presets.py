"""Example query payloads surfaced in the query console UI.

The presets are intentionally lightweight and fall into broad categories so they can
be re-used in documentation, smoke tests, and the Starlette console without creating
hard dependencies on specific run inventories. Payloads rely on canonical dataset
paths that commonly exist after activation.
"""

from __future__ import annotations

from collections import OrderedDict
from typing import Dict, List, TypedDict


class QueryPreset(TypedDict):
    id: str
    name: str
    description: str
    payload: Dict[str, object]


QUERY_PRESETS: Dict[str, List[QueryPreset]] = OrderedDict({
    "Quick Look": [
        {
            "id": "landuse-head",
            "name": "Landuse preview (first 25)",
            "description": "Fetch the first 25 rows from landuse/landuse.parquet including schema metadata.",
            "payload": {
                "datasets": [
                    {
                        "path": "landuse/landuse.parquet",
                        "alias": "landuse",
                    }
                ],
                "columns": [
                    "landuse.TopazID",
                    "landuse.key",
                ],
                "limit": 25,
                "include_schema": True,
            },
        },
        {
            "id": "soils-head",
            "name": "Soils preview (first 25)",
            "description": "Inspect dominant soil properties with schema output for quick metadata discovery.",
            "payload": {
                "datasets": [
                    {
                        "path": "soils/soils.parquet",
                        "alias": "soils",
                    }
                ],
                "columns": [
                    "soils.TopazID",
                    "soils.mukey",
                    "soils.simple_texture",
                    "soils.soil_depth",
                ],
                "limit": 25,
                "include_schema": True,
            },
        },
        {
            "id": "landuse-filter",
            "name": "Landuse key 43, canopy < 0.6",
            "description": "Filter landuse to key 43 and canopy coverage under 0.6, returning the first 50 sorted entries.",
            "payload": {
                "datasets": [
                    {
                        "path": "landuse/landuse.parquet",
                        "alias": "landuse",
                    }
                ],
                "columns": [
                    "landuse.TopazID AS topaz_id",
                    "landuse.key AS landuse_key",
                    "landuse.cancov AS canopy_cover",
                ],
                "filters": [
                    {"column": "landuse.key", "operator": "=", "value": 43},
                    {"column": "landuse.cancov", "operator": "<", "value": 0.6},
                ],
                "order_by": ["landuse.TopazID"],
                "limit": 50,
                "include_schema": True,
                "include_sql": True,
            },
        },
        {
            "id": "landuse-filter-in",
            "name": "Landuse keys in [105, 118]",
            "description": "Demonstrate IN filter support by returning landuse rows with key 43 or 45.",
            "payload": {
                "datasets": [
                    {"path": "landuse/landuse.parquet", "alias": "landuse"},
                ],
                "filters": [
                    {"column": "landuse.key", "operator": "IN", "value": [105, 118]},
                ],
                "order_by": ["landuse.TopazID"],
                "limit": 100,
                "include_schema": True,
                "include_sql": True,
            },
        },
    ],
    "Joins": [
        {
            "id": "landuse-soils-topaz",
            "name": "Landuse ↔ Soils by TopazID",
            "description": "Inner join landuse and soils datasets on TopazID to align management and soil texture.",
            "payload": {
                "datasets": [
                    {"path": "landuse/landuse.parquet", "alias": "landuse"},
                    {"path": "soils/soils.parquet", "alias": "soils"},
                ],
                "joins": [
                    {"left": "landuse", "right": "soils", "on": ["TopazID"]},
                ],
                "columns": [
                    "landuse.TopazID AS topaz_id",
                    "landuse.desc AS landuse_desc",
                    "soils.simple_texture AS soil_texture",
                ],
                "limit": 50,
                "include_schema": True,
            },
        },
    ],
    "Aggregations": [
        {
            "id": "pass-daily-runoff",
            "name": "Daily runoff + sediment totals",
            "description": "Aggregate WEPP interchange runoff and sediment to daily watershed totals.",
            "payload": {
                "datasets": [
                    {"path": "wepp/output/interchange/H.pass.parquet", "alias": "pass"},
                ],
                "columns": [
                    "pass.year AS year",
                    "pass.month AS month",
                    "pass.sim_day_index AS sim_day_index",
                ],
                "group_by": ["year", "month", "sim_day_index"],
                "order_by": ["year", "month", "sim_day_index"],
                "aggregations": [
                    {
                    "alias": "detachment",
                    "column": "pass.tdet",
                    "fn": "sum"
                    },
                    {
                    "alias": "runoff_volume",
                    "column": "pass.runvol",
                    "fn": "sum"
                    }
                ],
                "include_schema": True,
                "include_sql": True,
            },
        },
    ],
})
