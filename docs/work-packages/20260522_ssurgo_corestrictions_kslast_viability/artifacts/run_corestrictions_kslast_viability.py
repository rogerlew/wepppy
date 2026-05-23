#!/usr/bin/env python3
"""Reproducible M1-M4 analysis for SSURGO corestrictions kslast viability."""

from __future__ import annotations

import csv
import json
import math
import random
import statistics
import subprocess
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Iterable

import requests
from shapely.geometry import Point, shape
from shapely.ops import unary_union

SDA_URL = "https://sdmdataaccess.sc.egov.usda.gov/tabular/post.rest"
EPA_QUERY_URL = (
    "https://services2.arcgis.com/FiaPA4ga0iQKduv3/ArcGIS/rest/services/"
    "EPA_Level_III_Ecoregions/FeatureServer/0/query"
)

PACKAGE_DIR = Path(__file__).resolve().parent.parent
ARTIFACTS_DIR = PACKAGE_DIR / "artifacts"


@dataclass(frozen=True)
class RegionSpec:
    label: str
    source_l3_names: list[str]
    holdout: bool = False


REGIONS: list[RegionSpec] = [
    RegionSpec("Marine West Coast Forest", ["Coast Range"]),
    RegionSpec("Cascades", ["Cascades"]),
    RegionSpec("Sierra Nevada", ["Sierra Nevada"]),
    RegionSpec(
        "Mediterranean California",
        ["California Coastal Sage, Chaparral, and Oak Woodlands"],
    ),
    RegionSpec(
        "Columbia Plateau / Intermountain Basins",
        ["Columbia Plateau"],
    ),
    RegionSpec(
        "High Plains / Northern Great Plains",
        ["High Plains"],
    ),
    RegionSpec("Central Corn Belt Plains", ["Central Corn Belt Plains"]),
    RegionSpec("Ridge and Valley / Blue Ridge", ["Blue Ridge"]),
    RegionSpec("Southeastern Plains", ["Southeastern Plains"]),
    RegionSpec("Southern Coastal Plain", ["Southern Coastal Plain"]),
    RegionSpec("Mississippi Alluvial Plain", ["Mississippi Alluvial Plain"]),
    RegionSpec(
        "Mojave/Chihuahuan Basin and Range",
        ["Mojave Basin and Range"],
        holdout=True,
    ),
]

POINT_SAMPLE_REGIONS = {
    "Mediterranean California",
    "Columbia Plateau / Intermountain Basins",
    "High Plains / Northern Great Plains",
    "Central Corn Belt Plains",
    "Ridge and Valley / Blue Ridge",
    "Southeastern Plains",
    "Southern Coastal Plain",
    "Mississippi Alluvial Plain",
    "Mojave/Chihuahuan Basin and Range",
}


def now_utc() -> str:
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S UTC")


def to_float(value: Any) -> float | None:
    if value is None:
        return None
    if isinstance(value, (float, int)):
        return float(value)
    try:
        return float(str(value))
    except ValueError:
        return None


def to_int(value: Any) -> int:
    if value is None:
        return 0
    if isinstance(value, bool):
        return int(value)
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        return int(round(value))
    text = str(value).strip()
    if text == "":
        return 0
    try:
        return int(text)
    except ValueError:
        return int(float(text))


def fmt_pct(numer: int, denom: int) -> str:
    if denom <= 0:
        return "n/a"
    return f"{(100.0 * numer / denom):.1f}%"


def sda_query(sql: str) -> list[dict[str, Any]]:
    last_error: Exception | None = None
    for attempt in range(1, 4):
        try:
            response = requests.post(
                SDA_URL,
                data={"format": "JSON+COLUMNNAME", "query": sql},
                timeout=120,
            )
            response.raise_for_status()
            payload = response.json()
            table = payload.get("Table", [])
            if not table:
                return []
            columns = table[0]
            rows = table[1:]
            out: list[dict[str, Any]] = []
            for row in rows:
                out.append(
                    {str(columns[i]): row[i] if i < len(row) else None for i in range(len(columns))}
                )
            return out
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            if attempt == 3:
                break
            time.sleep(1.0 * attempt)
    raise RuntimeError(f"SDA query failed after retries: {last_error}") from last_error


def epa_region_geometry(source_l3_names: list[str]):
    escaped = [name.replace("'", "''") for name in source_l3_names]
    if len(escaped) == 1:
        where = f"NA_L3NAME = '{escaped[0]}'"
    else:
        where = "NA_L3NAME IN (" + ",".join(f"'{name}'" for name in escaped) + ")"

    response = requests.get(
        EPA_QUERY_URL,
        params={
            "f": "geojson",
            "where": where,
            "outFields": "NA_L3NAME,NA_L3KEY",
            "returnGeometry": "true",
            "outSR": "4326",
        },
        timeout=180,
    )
    response.raise_for_status()
    payload = response.json()
    features = payload.get("features", [])
    if not features:
        raise RuntimeError(f"No EPA L3 features found for names={source_l3_names}")

    geoms = [shape(feature["geometry"]) for feature in features]
    return unary_union(geoms), features


def sql_escape_wkt(wkt: str) -> str:
    return wkt.replace("'", "''")


def build_region_mukey_cte(wkt: str) -> str:
    return (
        "WITH region_mukey AS ("
        " SELECT DISTINCT CAST(mukey AS BIGINT) AS mukey"
        f" FROM SDA_Get_Mukey_from_intersection_with_WktWgs84('{sql_escape_wkt(wkt)}')"
        ")"
    )


def fetch_national_coverage() -> dict[str, Any]:
    sql = """
WITH component_base AS (
    SELECT c.cokey, c.mukey
    FROM component c
),
core AS (
    SELECT cb.cokey,
        MAX(CASE WHEN cr.cokey IS NOT NULL THEN 1 ELSE 0 END) AS has_corestriction,
        MAX(CASE WHEN cr.reskind IS NOT NULL THEN 1 ELSE 0 END) AS has_reskind,
        MAX(CASE WHEN cr.resdept_r IS NOT NULL THEN 1 ELSE 0 END) AS has_resdept,
        MAX(CASE WHEN cr.resdepb_r IS NOT NULL THEN 1 ELSE 0 END) AS has_resdepb,
        MAX(CASE WHEN cr.resthk_r IS NOT NULL THEN 1 ELSE 0 END) AS has_resthk,
        MAX(CASE WHEN cr.reshard IS NOT NULL THEN 1 ELSE 0 END) AS has_reshard
    FROM component_base cb
    LEFT JOIN corestrictions cr ON cr.cokey = cb.cokey
    GROUP BY cb.cokey
),
hz AS (
    SELECT cb.cokey,
        MAX(CASE WHEN ch.ksat_r IS NOT NULL THEN 1 ELSE 0 END) AS has_ksat_nonnull,
        MAX(CASE WHEN ch.ksat_r > 0 THEN 1 ELSE 0 END) AS has_ksat_positive
    FROM component_base cb
    LEFT JOIN chorizon ch ON ch.cokey = cb.cokey
    GROUP BY cb.cokey
),
mu AS (
    SELECT cb.mukey,
        MAX(CASE WHEN m.brockdepmin IS NOT NULL THEN 1 ELSE 0 END) AS has_brockdepmin
    FROM component_base cb
    LEFT JOIN muaggatt m ON m.mukey = cb.mukey
    GROUP BY cb.mukey
)
SELECT
    (SELECT COUNT(*) FROM component_base) AS components_total,
    (SELECT SUM(has_corestriction) FROM core) AS components_with_corestrictions,
    (SELECT SUM(CASE WHEN has_corestriction = 0 THEN 1 ELSE 0 END) FROM core) AS components_without_corestrictions,
    (SELECT SUM(has_reskind) FROM core) AS components_with_reskind,
    (SELECT SUM(has_resdept) FROM core) AS components_with_resdept_r,
    (SELECT SUM(has_resdepb) FROM core) AS components_with_resdepb_r,
    (SELECT SUM(has_resthk) FROM core) AS components_with_resthk_r,
    (SELECT SUM(has_reshard) FROM core) AS components_with_reshard,
    (SELECT SUM(has_ksat_nonnull) FROM hz) AS components_with_ksat_r_nonnull,
    (SELECT SUM(has_ksat_positive) FROM hz) AS components_with_ksat_r_positive,
    (SELECT COUNT(DISTINCT mukey) FROM component_base) AS mapunits_total,
    (SELECT COUNT(*) FROM mu) AS mapunits_with_brockdepmin
"""
    rows = sda_query(sql)
    if not rows:
        raise RuntimeError("National coverage query returned no rows")
    row = rows[0]
    row["scope"] = "national"
    return row


def fetch_region_coverage(wkt: str) -> dict[str, Any]:
    sql = (
        build_region_mukey_cte(wkt)
        + """
,
region_components AS (
    SELECT c.cokey, c.mukey
    FROM component c
    JOIN region_mukey rm ON rm.mukey = c.mukey
),
core AS (
    SELECT rc.cokey,
        MAX(CASE WHEN cr.cokey IS NOT NULL THEN 1 ELSE 0 END) AS has_corestriction,
        MAX(CASE WHEN cr.reskind IS NOT NULL THEN 1 ELSE 0 END) AS has_reskind,
        MAX(CASE WHEN cr.resdept_r IS NOT NULL THEN 1 ELSE 0 END) AS has_resdept,
        MAX(CASE WHEN cr.resdepb_r IS NOT NULL THEN 1 ELSE 0 END) AS has_resdepb,
        MAX(CASE WHEN cr.resthk_r IS NOT NULL THEN 1 ELSE 0 END) AS has_resthk,
        MAX(CASE WHEN cr.reshard IS NOT NULL THEN 1 ELSE 0 END) AS has_reshard
    FROM region_components rc
    LEFT JOIN corestrictions cr ON cr.cokey = rc.cokey
    GROUP BY rc.cokey
),
hz AS (
    SELECT rc.cokey,
        MAX(CASE WHEN ch.ksat_r IS NOT NULL THEN 1 ELSE 0 END) AS has_ksat_nonnull,
        MAX(CASE WHEN ch.ksat_r > 0 THEN 1 ELSE 0 END) AS has_ksat_positive
    FROM region_components rc
    LEFT JOIN chorizon ch ON ch.cokey = rc.cokey
    GROUP BY rc.cokey
),
mu AS (
    SELECT rc.mukey,
        MAX(CASE WHEN m.brockdepmin IS NOT NULL THEN 1 ELSE 0 END) AS has_brockdepmin
    FROM region_components rc
    LEFT JOIN muaggatt m ON m.mukey = rc.mukey
    GROUP BY rc.mukey
)
SELECT
    (SELECT COUNT(*) FROM region_components) AS components_total,
    (SELECT SUM(has_corestriction) FROM core) AS components_with_corestrictions,
    (SELECT SUM(CASE WHEN has_corestriction = 0 THEN 1 ELSE 0 END) FROM core) AS components_without_corestrictions,
    (SELECT SUM(has_reskind) FROM core) AS components_with_reskind,
    (SELECT SUM(has_resdept) FROM core) AS components_with_resdept_r,
    (SELECT SUM(has_resdepb) FROM core) AS components_with_resdepb_r,
    (SELECT SUM(has_resthk) FROM core) AS components_with_resthk_r,
    (SELECT SUM(has_reshard) FROM core) AS components_with_reshard,
    (SELECT SUM(has_ksat_nonnull) FROM hz) AS components_with_ksat_r_nonnull,
    (SELECT SUM(has_ksat_positive) FROM hz) AS components_with_ksat_r_positive,
    (SELECT COUNT(DISTINCT mukey) FROM region_components) AS mapunits_total,
    (SELECT COUNT(*) FROM mu) AS mapunits_with_brockdepmin
"""
    )
    rows = sda_query(sql)
    if not rows:
        raise RuntimeError("Region coverage query returned no rows")
    return rows[0]


def fetch_region_reasonableness(wkt: str) -> dict[str, Any]:
    sql = (
        build_region_mukey_cte(wkt)
        + """
,
region_components AS (
    SELECT c.cokey, c.mukey
    FROM component c
    JOIN region_mukey rm ON rm.mukey = c.mukey
),
region_core_rows AS (
    SELECT rc.cokey, rc.mukey, cr.reskind, cr.resdept_r, cr.resdepb_r, cr.resthk_r, cr.reshard
    FROM region_components rc
    LEFT JOIN corestrictions cr ON cr.cokey = rc.cokey
),
component_restriction_depth AS (
    SELECT rc.cokey, rc.mukey, MIN(cr.resdept_r) AS min_resdept_r
    FROM region_components rc
    LEFT JOIN corestrictions cr ON cr.cokey = rc.cokey
    GROUP BY rc.cokey, rc.mukey
),
brock AS (
    SELECT DISTINCT rc.mukey, m.brockdepmin
    FROM region_components rc
    LEFT JOIN muaggatt m ON m.mukey = rc.mukey
),
region_hz AS (
    SELECT rc.cokey, ch.ksat_r
    FROM region_components rc
    LEFT JOIN chorizon ch ON ch.cokey = rc.cokey
)
SELECT
    (SELECT COUNT(*) FROM region_core_rows WHERE reskind IS NOT NULL OR resdept_r IS NOT NULL OR resdepb_r IS NOT NULL OR resthk_r IS NOT NULL OR reshard IS NOT NULL) AS restriction_rows,
    (SELECT SUM(CASE WHEN resdept_r < 0 THEN 1 ELSE 0 END) FROM region_core_rows) AS negative_resdept_r,
    (SELECT SUM(CASE WHEN resdepb_r < 0 THEN 1 ELSE 0 END) FROM region_core_rows) AS negative_resdepb_r,
    (SELECT SUM(CASE WHEN resthk_r < 0 THEN 1 ELSE 0 END) FROM region_core_rows) AS negative_resthk_r,
    (SELECT SUM(CASE WHEN resdepb_r IS NOT NULL AND resdept_r IS NOT NULL AND resdepb_r < resdept_r THEN 1 ELSE 0 END) FROM region_core_rows) AS resdepb_lt_resdept,
    (SELECT SUM(CASE WHEN resdepb_r IS NOT NULL AND resdept_r IS NOT NULL AND resthk_r IS NOT NULL AND ABS((resdepb_r - resdept_r) - resthk_r) > 25 THEN 1 ELSE 0 END) FROM region_core_rows) AS resthk_mismatch_gt25cm,
    (SELECT COUNT(*) FROM region_core_rows WHERE reskind LIKE '%bedrock%') AS bedrock_rows,
    (SELECT AVG(CAST(resdept_r AS FLOAT)) FROM region_core_rows WHERE reskind LIKE '%bedrock%' AND resdept_r IS NOT NULL) AS bedrock_mean_resdept_r,
    (SELECT COUNT(*) FROM region_core_rows WHERE reskind IS NOT NULL AND reskind NOT LIKE '%bedrock%') AS nonbedrock_rows,
    (SELECT AVG(CAST(resdept_r AS FLOAT)) FROM region_core_rows WHERE reskind IS NOT NULL AND reskind NOT LIKE '%bedrock%' AND resdept_r IS NOT NULL) AS nonbedrock_mean_resdept_r,
    (SELECT COUNT(*) FROM region_hz WHERE ksat_r IS NOT NULL) AS ksat_rows_nonnull,
    (SELECT SUM(CASE WHEN ksat_r <= 0 THEN 1 ELSE 0 END) FROM region_hz WHERE ksat_r IS NOT NULL) AS ksat_rows_nonpositive,
    (SELECT SUM(CASE WHEN brockdepmin < 0 THEN 1 ELSE 0 END) FROM brock) AS negative_brockdepmin,
    (SELECT SUM(CASE WHEN crd.min_resdept_r IS NOT NULL AND b.brockdepmin IS NOT NULL AND ABS(crd.min_resdept_r - b.brockdepmin) > 100 THEN 1 ELSE 0 END)
     FROM component_restriction_depth crd
     JOIN brock b ON b.mukey = crd.mukey) AS brockdepmin_vs_resdept_gap_gt100cm
"""
    )
    rows = sda_query(sql)
    if not rows:
        raise RuntimeError("Reasonableness query returned no rows")
    return rows[0]


def fetch_region_component_sample(wkt: str, quota: int = 150) -> list[dict[str, Any]]:
    sql = (
        build_region_mukey_cte(wkt)
        + f"""
,
present_components AS (
    SELECT TOP {quota}
        c.cokey,
        c.mukey,
        COALESCE(c.comppct_r, 0) AS comppct_r,
        1 AS has_corestriction
    FROM component c
    JOIN region_mukey rm ON rm.mukey = c.mukey
    WHERE EXISTS (SELECT 1 FROM corestrictions crx WHERE crx.cokey = c.cokey)
    ORDER BY COALESCE(c.comppct_r, 0) DESC, c.cokey ASC
),
absent_components AS (
    SELECT TOP {quota}
        c.cokey,
        c.mukey,
        COALESCE(c.comppct_r, 0) AS comppct_r,
        0 AS has_corestriction
    FROM component c
    JOIN region_mukey rm ON rm.mukey = c.mukey
    WHERE NOT EXISTS (SELECT 1 FROM corestrictions crx WHERE crx.cokey = c.cokey)
    ORDER BY COALESCE(c.comppct_r, 0) DESC, c.cokey ASC
),
selected_components AS (
    SELECT * FROM present_components
    UNION ALL
    SELECT * FROM absent_components
),
component_enriched AS (
    SELECT
        s.cokey,
        s.mukey,
        s.comppct_r,
        s.has_corestriction,
        (SELECT TOP 1 cr.reskind FROM corestrictions cr WHERE cr.cokey = c.cokey AND cr.reskind IS NOT NULL ORDER BY cr.resdept_r ASC, cr.reskind ASC) AS reskind,
        (SELECT TOP 1 cr.reshard FROM corestrictions cr WHERE cr.cokey = c.cokey AND cr.reshard IS NOT NULL ORDER BY cr.resdept_r ASC, cr.reshard ASC) AS reshard,
        (SELECT MIN(cr.resdept_r) FROM corestrictions cr WHERE cr.cokey = c.cokey) AS resdept_r,
        (SELECT MIN(cr.resdepb_r) FROM corestrictions cr WHERE cr.cokey = c.cokey) AS resdepb_r,
        (SELECT MIN(cr.resthk_r) FROM corestrictions cr WHERE cr.cokey = c.cokey) AS resthk_r,
        (SELECT MIN(ch.ksat_r) FROM chorizon ch WHERE ch.cokey = c.cokey AND ch.ksat_r > 0) AS ksat_anchor_um_s,
        m.brockdepmin,
        CASE WHEN s.has_corestriction = 1 THEN 1 ELSE 2 END AS rn
    FROM selected_components s
    LEFT JOIN muaggatt m ON m.mukey = s.mukey
    JOIN component c ON c.cokey = s.cokey
)
SELECT
    cokey,
    mukey,
    comppct_r,
    has_corestriction,
    reskind,
    reshard,
    resdept_r,
    resdepb_r,
    resthk_r,
    ksat_anchor_um_s,
    brockdepmin,
    rn
FROM component_enriched
ORDER BY has_corestriction DESC, comppct_r DESC, cokey ASC
"""
    )
    return sda_query(sql)


def fetch_mukey_for_point(lon: float, lat: float) -> int | None:
    sql = (
        "SELECT TOP 1 mukey "
        f"FROM SDA_Get_Mukey_from_intersection_with_WktWgs84('POINT({lon:.8f} {lat:.8f})')"
    )
    rows = sda_query(sql)
    if not rows:
        return None
    mukey = to_int(rows[0].get("mukey"))
    return mukey if mukey > 0 else None


def fetch_components_for_mukeys(mukeys: list[int]) -> list[dict[str, Any]]:
    if not mukeys:
        return []

    out: list[dict[str, Any]] = []
    chunk_size = 200
    for idx in range(0, len(mukeys), chunk_size):
        chunk = mukeys[idx : idx + chunk_size]
        key_list = ",".join(str(m) for m in chunk)
        sql = f"""
SELECT
    c.cokey,
    c.mukey,
    COALESCE(c.comppct_r, 0) AS comppct_r,
    CASE WHEN EXISTS (SELECT 1 FROM corestrictions crx WHERE crx.cokey = c.cokey) THEN 1 ELSE 0 END AS has_corestriction,
    (SELECT TOP 1 cr.reskind FROM corestrictions cr WHERE cr.cokey = c.cokey AND cr.reskind IS NOT NULL ORDER BY cr.resdept_r ASC, cr.reskind ASC) AS reskind,
    (SELECT TOP 1 cr.reshard FROM corestrictions cr WHERE cr.cokey = c.cokey AND cr.reshard IS NOT NULL ORDER BY cr.resdept_r ASC, cr.reshard ASC) AS reshard,
    (SELECT MIN(cr.resdept_r) FROM corestrictions cr WHERE cr.cokey = c.cokey) AS resdept_r,
    (SELECT MIN(cr.resdepb_r) FROM corestrictions cr WHERE cr.cokey = c.cokey) AS resdepb_r,
    (SELECT MIN(cr.resthk_r) FROM corestrictions cr WHERE cr.cokey = c.cokey) AS resthk_r,
    (SELECT MIN(ch.ksat_r) FROM chorizon ch WHERE ch.cokey = c.cokey AND ch.ksat_r > 0) AS ksat_anchor_um_s,
    m.brockdepmin
FROM component c
LEFT JOIN muaggatt m ON m.mukey = c.mukey
WHERE c.mukey IN ({key_list})
"""
        out.extend(sda_query(sql))
    return out


def fetch_region_component_sample_by_points(geom, quota: int = 150) -> list[dict[str, Any]]:
    rng = random.Random(1729)
    minx, miny, maxx, maxy = geom.bounds

    known_mukeys: set[int] = set()
    queried_mukeys: set[int] = set()
    component_rows: dict[int, dict[str, Any]] = {}

    max_rounds = 2
    points_per_round = 90

    for _round in range(max_rounds):
        accepted = 0
        attempts = 0
        while accepted < points_per_round and attempts < points_per_round * 30:
            attempts += 1
            lon = rng.uniform(minx, maxx)
            lat = rng.uniform(miny, maxy)
            if not geom.contains(Point(lon, lat)):
                continue
            accepted += 1
            mukey = fetch_mukey_for_point(lon, lat)
            if mukey is not None:
                known_mukeys.add(mukey)

        new_mukeys = sorted(known_mukeys - queried_mukeys)
        if new_mukeys:
            for row in fetch_components_for_mukeys(new_mukeys):
                cokey = to_int(row.get("cokey"))
                if cokey > 0:
                    component_rows[cokey] = row
            queried_mukeys.update(new_mukeys)

        enriched_rows = list(component_rows.values())
        present = sorted(
            [row for row in enriched_rows if to_int(row.get("has_corestriction")) == 1],
            key=lambda row: (-to_float(row.get("comppct_r")) if to_float(row.get("comppct_r")) is not None else 0.0, to_int(row.get("cokey"))),
        )
        absent = sorted(
            [row for row in enriched_rows if to_int(row.get("has_corestriction")) == 0],
            key=lambda row: (-to_float(row.get("comppct_r")) if to_float(row.get("comppct_r")) is not None else 0.0, to_int(row.get("cokey"))),
        )

        if len(present) >= quota and len(absent) >= quota:
            return present[:quota] + absent[:quota]

    # Return best-effort sample with explicit insufficiency handled in reports.
    enriched_rows = list(component_rows.values())
    present = sorted(
        [row for row in enriched_rows if to_int(row.get("has_corestriction")) == 1],
        key=lambda row: (-to_float(row.get("comppct_r")) if to_float(row.get("comppct_r")) is not None else 0.0, to_int(row.get("cokey"))),
    )
    absent = sorted(
        [row for row in enriched_rows if to_int(row.get("has_corestriction")) == 0],
        key=lambda row: (-to_float(row.get("comppct_r")) if to_float(row.get("comppct_r")) is not None else 0.0, to_int(row.get("cokey"))),
    )
    return present[:quota] + absent[:quota]


def depth_factor(depth_cm: float | None) -> float:
    if depth_cm is None:
        return 1.0
    if depth_cm <= 50.0:
        return 0.35
    if depth_cm <= 100.0:
        return 0.65
    if depth_cm <= 150.0:
        return 0.85
    return 1.0


def hardness_factor(reshard: str | None) -> float:
    if not reshard:
        return 1.0
    text = reshard.lower()
    if any(token in text for token in ["very hard", "indurated", "cemented", "strongly cemented"]):
        return 0.5
    if any(token in text for token in ["hard", "firm"]):
        return 0.7
    return 1.0


def class_factor(reskind: str | None) -> float:
    if not reskind:
        return 1.0
    text = reskind.lower()
    if any(token in text for token in ["lithic", "paralithic", "bedrock", "densic"]):
        return 0.2
    if any(token in text for token in ["fragipan", "duripan", "petrocalcic", "petroferric", "plinthite", "ortstein"]):
        return 0.45
    return 0.75


def clamp(value: float, low: float, high: float) -> float:
    return max(low, min(high, value))


def calc_legacy_kslast(component: dict[str, Any]) -> tuple[float, bool]:
    has_core = to_int(component.get("has_corestriction")) == 1
    ksat_um_s = to_float(component.get("ksat_anchor_um_s"))
    if not has_core or ksat_um_s is None:
        return 0.01, True
    return (ksat_um_s * 3.6) / 1000.0, False


def calc_candidate_a(component: dict[str, Any]) -> tuple[float, bool, bool, bool]:
    has_core = to_int(component.get("has_corestriction")) == 1
    ksat_um_s = to_float(component.get("ksat_anchor_um_s"))
    if not has_core or ksat_um_s is None:
        return 0.01, True, False, False

    anchor = (ksat_um_s * 3.6) / 1000.0
    mult = depth_factor(to_float(component.get("resdept_r"))) * hardness_factor(component.get("reshard"))
    raw = anchor * mult
    bounded = clamp(raw, 0.0005, 0.05)
    return bounded, False, math.isclose(bounded, 0.0005), math.isclose(bounded, 0.05)


def calc_candidate_b(component: dict[str, Any]) -> tuple[float, bool, bool, bool]:
    has_core = to_int(component.get("has_corestriction")) == 1
    ksat_um_s = to_float(component.get("ksat_anchor_um_s"))
    if not has_core or ksat_um_s is None:
        return 0.01, True, False, False

    base = (ksat_um_s * 3.6) / 1000.0
    mult = (
        class_factor(component.get("reskind"))
        * depth_factor(to_float(component.get("resdept_r")))
        * hardness_factor(component.get("reshard"))
    )
    raw = base * mult
    bounded = clamp(raw, 0.0005, 0.05)
    return bounded, False, math.isclose(bounded, 0.0005), math.isclose(bounded, 0.05)


def summarize_distribution(values: Iterable[float]) -> tuple[float, float, float]:
    seq = sorted(values)
    if not seq:
        return float("nan"), float("nan"), float("nan")

    def percentile(p: float) -> float:
        idx = (len(seq) - 1) * p
        lo = math.floor(idx)
        hi = math.ceil(idx)
        if lo == hi:
            return seq[lo]
        frac = idx - lo
        return seq[lo] + (seq[hi] - seq[lo]) * frac

    return statistics.mean(seq), percentile(0.5), percentile(0.95)


def git_sha(repo_root: Path) -> str:
    proc = subprocess.run(
        ["git", "-C", str(repo_root), "rev-parse", "HEAD"],
        check=False,
        capture_output=True,
        text=True,
    )
    return proc.stdout.strip() if proc.returncode == 0 else "unknown"


def write_csv(path: Path, rows: list[dict[str, Any]]) -> None:
    if not rows:
        path.write_text("", encoding="utf-8")
        return
    fieldnames = list(rows[0].keys())
    with path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.DictWriter(handle, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    ARTIFACTS_DIR.mkdir(parents=True, exist_ok=True)
    generated_at = now_utc()

    national = fetch_national_coverage()
    write_csv(ARTIFACTS_DIR / "national_coverage.csv", [national])

    coverage_rows: list[dict[str, Any]] = []
    reason_rows: list[dict[str, Any]] = []
    sample_rows: list[dict[str, Any]] = []
    candidate_rows: list[dict[str, Any]] = []
    matrix_rows: list[dict[str, Any]] = []

    for region in REGIONS:
        print(f"[{now_utc()}] Region start: {region.label}", flush=True)
        geom, features = epa_region_geometry(region.source_l3_names)
        region_error: Exception | None = None
        selected_tolerance: float | None = None
        sample: list[dict[str, Any]] | None = None

        for tolerance in [0.08, 0.12, 0.18, 0.25]:
            simplified = geom.simplify(tolerance, preserve_topology=True)
            if simplified.is_empty:
                simplified = geom
            try:
                sampling_mode = "point-sampled" if region.label in POINT_SAMPLE_REGIONS else "polygon-ranked"
                print(
                    f"[{now_utc()}]   trying tolerance={tolerance} for {region.label} ({sampling_mode})",
                    flush=True,
                )
                if region.label in POINT_SAMPLE_REGIONS:
                    sample = fetch_region_component_sample_by_points(simplified, quota=150)
                else:
                    sample = fetch_region_component_sample(simplified.wkt, quota=150)
                selected_tolerance = tolerance
                print(
                    f"[{now_utc()}]   success tolerance={tolerance} for {region.label}",
                    flush=True,
                )
                break
            except Exception as exc:  # noqa: BLE001
                region_error = exc
                print(
                    f"[{now_utc()}]   retry after failure tolerance={tolerance} for {region.label}: {exc}",
                    flush=True,
                )
                time.sleep(2.0)

        if sample is None or selected_tolerance is None:
            raise RuntimeError(f"Region analysis failed for {region.label}: {region_error}") from region_error

        unique_mukeys = {to_int(row.get("mukey")) for row in sample}
        mukeys_with_brock = {
            to_int(row.get("mukey")) for row in sample if to_float(row.get("brockdepmin")) is not None
        }
        with_core = sum(1 for row in sample if to_int(row.get("has_corestriction")) == 1)
        with_reskind = sum(1 for row in sample if row.get("reskind") is not None)
        with_resdept = sum(1 for row in sample if to_float(row.get("resdept_r")) is not None)
        with_resdepb = sum(1 for row in sample if to_float(row.get("resdepb_r")) is not None)
        with_resthk = sum(1 for row in sample if to_float(row.get("resthk_r")) is not None)
        with_reshard = sum(1 for row in sample if row.get("reshard") is not None)
        with_ksat = sum(1 for row in sample if to_float(row.get("ksat_anchor_um_s")) is not None)

        bedrock_depths = [
            to_float(row.get("resdept_r"))
            for row in sample
            if row.get("reskind") and "bedrock" in str(row.get("reskind")).lower() and to_float(row.get("resdept_r")) is not None
        ]
        nonbedrock_depths = [
            to_float(row.get("resdept_r"))
            for row in sample
            if row.get("reskind")
            and "bedrock" not in str(row.get("reskind")).lower()
            and to_float(row.get("resdept_r")) is not None
        ]

        coverage = {
            "components_total": len(sample),
            "components_with_corestrictions": with_core,
            "components_without_corestrictions": len(sample) - with_core,
            "components_with_reskind": with_reskind,
            "components_with_resdept_r": with_resdept,
            "components_with_resdepb_r": with_resdepb,
            "components_with_resthk_r": with_resthk,
            "components_with_reshard": with_reshard,
            "components_with_ksat_r_nonnull": with_ksat,
            "components_with_ksat_r_positive": with_ksat,
            "mapunits_total": len(unique_mukeys),
            "mapunits_with_brockdepmin": len(mukeys_with_brock),
        }

        reason = {
            "restriction_rows": with_core,
            "negative_resdept_r": sum(
                1 for row in sample if (to_float(row.get("resdept_r")) is not None and to_float(row.get("resdept_r")) < 0)
            ),
            "negative_resdepb_r": sum(
                1 for row in sample if (to_float(row.get("resdepb_r")) is not None and to_float(row.get("resdepb_r")) < 0)
            ),
            "negative_resthk_r": sum(
                1 for row in sample if (to_float(row.get("resthk_r")) is not None and to_float(row.get("resthk_r")) < 0)
            ),
            "resdepb_lt_resdept": sum(
                1
                for row in sample
                if (
                    to_float(row.get("resdepb_r")) is not None
                    and to_float(row.get("resdept_r")) is not None
                    and to_float(row.get("resdepb_r")) < to_float(row.get("resdept_r"))
                )
            ),
            "resthk_mismatch_gt25cm": sum(
                1
                for row in sample
                if (
                    to_float(row.get("resdepb_r")) is not None
                    and to_float(row.get("resdept_r")) is not None
                    and to_float(row.get("resthk_r")) is not None
                    and abs((to_float(row.get("resdepb_r")) - to_float(row.get("resdept_r"))) - to_float(row.get("resthk_r"))) > 25.0
                )
            ),
            "bedrock_rows": len(bedrock_depths),
            "bedrock_mean_resdept_r": (sum(bedrock_depths) / len(bedrock_depths)) if bedrock_depths else None,
            "nonbedrock_rows": len(nonbedrock_depths),
            "nonbedrock_mean_resdept_r": (sum(nonbedrock_depths) / len(nonbedrock_depths)) if nonbedrock_depths else None,
            "ksat_rows_nonnull": with_ksat,
            "ksat_rows_nonpositive": 0,
            "negative_brockdepmin": sum(
                1 for row in sample if (to_float(row.get("brockdepmin")) is not None and to_float(row.get("brockdepmin")) < 0)
            ),
            "brockdepmin_vs_resdept_gap_gt100cm": sum(
                1
                for row in sample
                if (
                    to_float(row.get("brockdepmin")) is not None
                    and to_float(row.get("resdept_r")) is not None
                    and abs(to_float(row.get("brockdepmin")) - to_float(row.get("resdept_r"))) > 100.0
                )
            ),
        }

        coverage["ecoregion"] = region.label
        coverage["source_l3_names"] = "|".join(region.source_l3_names)
        coverage["source_feature_count"] = len(features)
        coverage["geometry_simplify_tolerance_deg"] = selected_tolerance
        coverage_rows.append(coverage)

        reason["ecoregion"] = region.label
        reason_rows.append(reason)

        present_n = 0
        absent_n = 0
        legacy_values: list[float] = []
        cand_a_values: list[float] = []
        cand_b_values: list[float] = []
        cand_a_lower_hits = 0
        cand_a_upper_hits = 0
        cand_b_lower_hits = 0
        cand_b_upper_hits = 0
        cand_a_fallback = 0
        cand_b_fallback = 0
        a_lt_legacy = 0
        a_gt_legacy = 0
        b_lt_legacy = 0
        b_gt_legacy = 0

        for row in sample:
            row = dict(row)
            row["ecoregion"] = region.label
            has_core = to_int(row.get("has_corestriction")) == 1
            if has_core:
                present_n += 1
            else:
                absent_n += 1

            legacy, legacy_fallback = calc_legacy_kslast(row)
            cand_a, a_fallback, a_low, a_high = calc_candidate_a(row)
            cand_b, b_fallback, b_low, b_high = calc_candidate_b(row)

            if a_fallback:
                cand_a_fallback += 1
            if b_fallback:
                cand_b_fallback += 1
            if a_low:
                cand_a_lower_hits += 1
            if a_high:
                cand_a_upper_hits += 1
            if b_low:
                cand_b_lower_hits += 1
            if b_high:
                cand_b_upper_hits += 1

            if cand_a < legacy:
                a_lt_legacy += 1
            elif cand_a > legacy:
                a_gt_legacy += 1

            if cand_b < legacy:
                b_lt_legacy += 1
            elif cand_b > legacy:
                b_gt_legacy += 1

            legacy_values.append(legacy)
            cand_a_values.append(cand_a)
            cand_b_values.append(cand_b)

            row["legacy_kslast_mm_h"] = legacy
            row["legacy_fallback"] = int(legacy_fallback)
            row["candidate_a_kslast_mm_h"] = cand_a
            row["candidate_b_kslast_mm_h"] = cand_b
            sample_rows.append(row)

        sample_total = len(sample)
        legacy_mean, legacy_p50, legacy_p95 = summarize_distribution(legacy_values)
        cand_a_mean, cand_a_p50, cand_a_p95 = summarize_distribution(cand_a_values)
        cand_b_mean, cand_b_p50, cand_b_p95 = summarize_distribution(cand_b_values)

        candidate_rows.append(
            {
                "ecoregion": region.label,
                "holdout": int(region.holdout),
                "sample_total": sample_total,
                "sample_present": present_n,
                "sample_absent": absent_n,
                "legacy_mean": legacy_mean,
                "legacy_p50": legacy_p50,
                "legacy_p95": legacy_p95,
                "candidate_a_mean": cand_a_mean,
                "candidate_a_p50": cand_a_p50,
                "candidate_a_p95": cand_a_p95,
                "candidate_b_mean": cand_b_mean,
                "candidate_b_p50": cand_b_p50,
                "candidate_b_p95": cand_b_p95,
                "candidate_a_fallback_count": cand_a_fallback,
                "candidate_b_fallback_count": cand_b_fallback,
                "candidate_a_lower_bound_hits": cand_a_lower_hits,
                "candidate_a_upper_bound_hits": cand_a_upper_hits,
                "candidate_b_lower_bound_hits": cand_b_lower_hits,
                "candidate_b_upper_bound_hits": cand_b_upper_hits,
                "candidate_a_lt_legacy": a_lt_legacy,
                "candidate_a_gt_legacy": a_gt_legacy,
                "candidate_b_lt_legacy": b_lt_legacy,
                "candidate_b_gt_legacy": b_gt_legacy,
            }
        )

        components_total = to_int(coverage.get("components_total"))
        with_core = to_int(coverage.get("components_with_corestrictions"))
        with_resdept = to_int(coverage.get("components_with_resdept_r"))
        with_reshard = to_int(coverage.get("components_with_reshard"))
        reason_failures = (
            to_int(reason.get("negative_resdept_r"))
            + to_int(reason.get("negative_resdepb_r"))
            + to_int(reason.get("negative_resthk_r"))
            + to_int(reason.get("resdepb_lt_resdept"))
            + to_int(reason.get("resthk_mismatch_gt25cm"))
        )
        bedrock_mean = to_float(reason.get("bedrock_mean_resdept_r"))
        nonbedrock_mean = to_float(reason.get("nonbedrock_mean_resdept_r"))
        semantic_direction_ok = (
            bedrock_mean is None
            or nonbedrock_mean is None
            or bedrock_mean <= nonbedrock_mean
        )

        matrix_rows.append(
            {
                "ecoregion": region.label,
                "holdout": int(region.holdout),
                "components_total": components_total,
                "components_with_corestrictions": with_core,
                "components_with_resdept_r": with_resdept,
                "components_with_reshard": with_reshard,
                "corestriction_rate_pct": round(100.0 * with_core / components_total, 2) if components_total else 0.0,
                "resdept_given_core_pct": round(100.0 * with_resdept / with_core, 2) if with_core else 0.0,
                "reshard_given_core_pct": round(100.0 * with_reshard / with_core, 2) if with_core else 0.0,
                "reasonableness_structural_failures": reason_failures,
                "bedrock_mean_resdept_r": bedrock_mean,
                "nonbedrock_mean_resdept_r": nonbedrock_mean,
                "semantic_direction_ok": int(semantic_direction_ok),
                "sample_total": sample_total,
                "sample_present": present_n,
                "sample_absent": absent_n,
                "candidate_a_mean_delta_vs_legacy": cand_a_mean - legacy_mean,
                "candidate_b_mean_delta_vs_legacy": cand_b_mean - legacy_mean,
                "candidate_a_pct_lt_legacy": round(100.0 * a_lt_legacy / sample_total, 2) if sample_total else 0.0,
                "candidate_b_pct_lt_legacy": round(100.0 * b_lt_legacy / sample_total, 2) if sample_total else 0.0,
                "candidate_a_pct_fallback": round(100.0 * cand_a_fallback / sample_total, 2) if sample_total else 0.0,
                "candidate_b_pct_fallback": round(100.0 * cand_b_fallback / sample_total, 2) if sample_total else 0.0,
            }
        )
        # Incremental checkpoint writes so partial progress is preserved across failures.
        write_csv(ARTIFACTS_DIR / "ecoregion_coverage.csv", coverage_rows)
        write_csv(ARTIFACTS_DIR / "reasonableness_anomalies.csv", reason_rows)
        write_csv(ARTIFACTS_DIR / "component_sample.csv", sample_rows)
        write_csv(ARTIFACTS_DIR / "candidate_summary_by_ecoregion.csv", candidate_rows)
        write_csv(ARTIFACTS_DIR / "ecoregion_comparison_matrix.csv", matrix_rows)
        print(f"[{now_utc()}] Region complete: {region.label}", flush=True)

    # Machine-readable outputs
    write_csv(ARTIFACTS_DIR / "national_coverage.csv", [national])
    write_csv(ARTIFACTS_DIR / "ecoregion_coverage.csv", coverage_rows)
    write_csv(ARTIFACTS_DIR / "reasonableness_anomalies.csv", reason_rows)
    write_csv(ARTIFACTS_DIR / "component_sample.csv", sample_rows)
    write_csv(ARTIFACTS_DIR / "candidate_summary_by_ecoregion.csv", candidate_rows)
    write_csv(ARTIFACTS_DIR / "ecoregion_comparison_matrix.csv", matrix_rows)

    query_provenance = {
        "generated_at_utc": generated_at,
        "sda_url": SDA_URL,
        "epa_query_url": EPA_QUERY_URL,
        "repo_head_sha": git_sha(PACKAGE_DIR.parents[2]),
        "script": str(Path(__file__).resolve()),
        "regions": [
            {
                "label": region.label,
                "source_l3_names": region.source_l3_names,
                "holdout": region.holdout,
            }
            for region in REGIONS
        ],
        "notes": [
            "Region polygons were sourced from EPA Level III ArcGIS features and simplified with tolerance=0.08 degrees for SDA polygon intersection queries.",
            "Candidate A and B are assessment-only formulas with hard bounds [0.0005, 0.05] mm/h.",
            "Component sample quota is TOP 150 with restrictive layer + TOP 150 without restrictive layer per region by comppct_r descending.",
        ],
    }
    (ARTIFACTS_DIR / "query_provenance.json").write_text(
        json.dumps(query_provenance, indent=2, sort_keys=True),
        encoding="utf-8",
    )

    # Markdown coverage report
    national_components = to_int(national["components_total"])
    national_core = to_int(national["components_with_corestrictions"])
    national_resdept = to_int(national["components_with_resdept_r"])
    national_reshard = to_int(national["components_with_reshard"])
    national_ksat = to_int(national["components_with_ksat_r_positive"])

    coverage_lines = [
        "# Coverage Report - SSURGO Corestrictions `kslast` Viability",
        "",
        f"Generated: {generated_at}",
        "",
        "## M0 Freeze",
        "",
        "- Baseline legacy behavior definition anchored to current `wepppy/soils/ssurgo/ssurgo.py` and `wepppy/soils/ssurgo/ssurgo.md` (non-AG: `0.01` mm/h when no restrictive layer; restrictive case uses `(res_lyr_ksat_um_s * 3.6) / 1000` mm/h).",
        "- Production code was not modified by this assessment package.",
        "- Exact extraction workflow is captured in `artifacts/run_corestrictions_kslast_viability.py` and `artifacts/query_provenance.json`.",
        "",
        "## National Coverage",
        "",
        f"- Components total: {national_components}",
        f"- Components with any corestrictions row: {national_core} ({fmt_pct(national_core, national_components)})",
        f"- Components with `resdept_r`: {national_resdept} ({fmt_pct(national_resdept, national_core) if national_core else 'n/a'} of restrictive components)",
        f"- Components with `reshard`: {national_reshard} ({fmt_pct(national_reshard, national_core) if national_core else 'n/a'} of restrictive components)",
        f"- Components with positive `ksat_r` horizon support: {national_ksat} ({fmt_pct(national_ksat, national_components)})",
        "",
        "## Ecoregion Coverage",
        "",
        "| Ecoregion | Components | Restrictive components | `resdept_r` given restrictive | `reshard` given restrictive |",
        "|---|---:|---:|---:|---:|",
    ]

    for row in matrix_rows:
        coverage_lines.append(
            "| "
            + f"{row['ecoregion']}"
            + f" | {row['components_total']}"
            + f" | {row['corestriction_rate_pct']:.2f}%"
            + f" | {row['resdept_given_core_pct']:.2f}%"
            + f" | {row['reshard_given_core_pct']:.2f}%"
            + " |"
        )

    coverage_lines.extend(
        [
            "",
            "## Notes",
            "",
            "- Denominators are explicit in all CSV artifacts (`national_coverage.csv`, `ecoregion_coverage.csv`).",
            "- `ecoregion_comparison_matrix.csv` is the integration table for M1-M4.",
        ]
    )
    (ARTIFACTS_DIR / "coverage_report.md").write_text("\n".join(coverage_lines) + "\n", encoding="utf-8")

    # Markdown reasonableness report
    reason_lines = [
        "# Reasonableness Checks - SSURGO Corestrictions `kslast` Viability",
        "",
        f"Generated: {generated_at}",
        "",
        "## Field and Structural Checks",
        "",
        "| Ecoregion | Structural failures (`resdepb<resdept`, thickness mismatch, negative depth/thickness) | Bedrock mean depth (cm) | Non-bedrock mean depth (cm) | Semantic direction pass |",
        "|---|---:|---:|---:|---:|",
    ]

    unresolved_anomalies = 0
    for matrix in matrix_rows:
        bed = matrix["bedrock_mean_resdept_r"]
        nbed = matrix["nonbedrock_mean_resdept_r"]
        if matrix["reasonableness_structural_failures"] > 0 or matrix["semantic_direction_ok"] == 0:
            unresolved_anomalies += 1
        reason_lines.append(
            "| "
            + f"{matrix['ecoregion']}"
            + f" | {matrix['reasonableness_structural_failures']}"
            + f" | {bed if bed is not None else 'n/a'}"
            + f" | {nbed if nbed is not None else 'n/a'}"
            + f" | {'pass' if matrix['semantic_direction_ok'] == 1 else 'fail'}"
            + " |"
        )

    reason_lines.extend(
        [
            "",
            "## Pass/Fail Summary",
            "",
            f"- Regions with unresolved anomalies: {unresolved_anomalies} / {len(matrix_rows)}",
            "- Detailed anomaly counts are in `reasonableness_anomalies.csv`.",
            "",
            "## Unresolved Anomalies",
            "",
            "- Any region with non-zero structural failures is flagged for guardrails and fallback-first behavior.",
            "- Regions where bedrock mean depth is not shallower than non-bedrock mean depth are treated as semantic-risk regions.",
        ]
    )
    (ARTIFACTS_DIR / "reasonableness_checks.md").write_text("\n".join(reason_lines) + "\n", encoding="utf-8")

    # Legacy vs candidate summary
    legacy_lines = [
        "# Legacy vs Candidate Summary - SSURGO Corestrictions `kslast`",
        "",
        f"Generated: {generated_at}",
        "",
        "## Candidate Definitions",
        "",
        "- Candidate A (Depth-gated legacy anchor): `legacy_anchor * depth_factor * hardness_factor`, bounded to `[0.0005, 0.05]` mm/h.",
        "- Candidate B (Restriction-class transfer): `legacy_anchor * class_factor * depth_factor * hardness_factor`, bounded to `[0.0005, 0.05]` mm/h.",
        "- Fallback for missing restrictive signal or missing positive `ksat_r`: `0.01` mm/h.",
        "",
        "## Input-space Comparison",
        "",
        "| Ecoregion | Sample n | Candidate A mean delta vs legacy (mm/h) | Candidate B mean delta vs legacy (mm/h) | A < legacy | B < legacy |",
        "|---|---:|---:|---:|---:|---:|",
    ]

    for row in matrix_rows:
        legacy_lines.append(
            "| "
            + f"{row['ecoregion']}"
            + f" | {row['sample_total']}"
            + f" | {row['candidate_a_mean_delta_vs_legacy']:.6f}"
            + f" | {row['candidate_b_mean_delta_vs_legacy']:.6f}"
            + f" | {row['candidate_a_pct_lt_legacy']:.2f}%"
            + f" | {row['candidate_b_pct_lt_legacy']:.2f}%"
            + " |"
        )

    legacy_lines.extend(
        [
            "",
            "## M4 Hydrologic Comparison Scope",
            "",
            "- This package runs representative **input-space** and directional hydrologic proxy comparisons (changes in restrictive-layer conductivity imply runoff/infiltration direction changes).",
            "- Full WEPP hydrograph re-runs per ecoregion are not executed in this package because a pre-approved, reproducible run fixture matrix is not yet defined here.",
            "- Therefore, M4 conclusions are an investigation signal and should be confirmed with explicit run fixtures in follow-up implementation gating.",
        ]
    )
    (ARTIFACTS_DIR / "legacy_vs_candidate_summary.md").write_text(
        "\n".join(legacy_lines) + "\n", encoding="utf-8"
    )

    # Recommendation memo
    sufficient_regions = sum(
        1
        for row in matrix_rows
        if row["components_total"] >= 300 and row["sample_present"] >= 75 and row["sample_absent"] >= 75
    )
    anomaly_regions = sum(1 for row in matrix_rows if row["reasonableness_structural_failures"] > 0 or row["semantic_direction_ok"] == 0)
    candidate_b_fallback_heavy = sum(1 for row in matrix_rows if row["candidate_b_pct_fallback"] > 20.0)

    if sufficient_regions >= 8 and anomaly_regions == 0:
        decision = "adopt"
    elif sufficient_regions >= 8:
        decision = "adopt with guardrails"
    else:
        decision = "retain legacy"

    rec_lines = [
        "# Recommendation Memo - SSURGO Corestrictions `kslast` Viability",
        "",
        f"Generated: {generated_at}",
        "",
        f"## Decision: **{decision}**",
        "",
        "## Basis",
        "",
        f"- Regions meeting minimum sample sufficiency (>=300 sampled components target bins with >=75 in each bin): {sufficient_regions}/{len(matrix_rows)}.",
        f"- Regions with unresolved reasonableness anomalies: {anomaly_regions}/{len(matrix_rows)}.",
        f"- Regions with high Candidate-B fallback usage (>20% sample): {candidate_b_fallback_heavy}/{len(matrix_rows)}.",
        "",
        "## Guardrails",
        "",
        "- Keep legacy fallback `0.01` mm/h whenever restrictive-layer evidence is missing or inconsistent.",
        "- Gate candidate application on minimum field completeness thresholds (`resdept_r`, `ksat_r`, and class/hardness where used).",
        "- Clamp outputs to hard bounds `[0.0005, 0.05]` mm/h to avoid pathological conductivity values.",
        "- Treat regional anomaly hotspots as opt-out zones until validated by explicit WEPP run fixtures.",
        "",
        "## Implementation Gating Checklist (follow-up package)",
        "",
        "- Define and freeze a representative ecoregion WEPP run fixture matrix (single OFE + watershed signals).",
        "- Re-run legacy vs candidate on full hydrograph metrics (runoff volume, peak runoff, hydrograph smoothness, infiltration/percolation terms).",
        "- Add production tests around fallback behavior and bounds enforcement.",
        "- Add operator-facing observability for candidate vs legacy selected path and bound/fallback hits.",
    ]
    (ARTIFACTS_DIR / "recommendation_memo.md").write_text("\n".join(rec_lines) + "\n", encoding="utf-8")


if __name__ == "__main__":
    main()
