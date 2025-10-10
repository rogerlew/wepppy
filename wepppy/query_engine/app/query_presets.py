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
                "limit": 25
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
                "limit": 25
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
                    "pass.day AS day",
                ],
                "group_by": ["year", "month", "day"],
                "order_by": ["year", "month", "day"],
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
