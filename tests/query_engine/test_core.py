from __future__ import annotations

import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from wepppy.query_engine.catalog import DatasetCatalog
from wepppy.query_engine.context import RunContext
from wepppy.query_engine.core import run_query, build_query_plan
from wepppy.query_engine.payload import QueryRequest


def _write_parquet(path: Path, table: pa.Table | None = None) -> None:
    if table is None:
        table = pa.table({"id": [1, 2, 3], "value": ["a", "b", "c"]})
    path.parent.mkdir(parents=True, exist_ok=True)
    pq.write_table(table, path)


def _write_catalog(root: Path, rel_path: str) -> None:
    _write_catalog_entries(root, [rel_path])


def _write_catalog_entries(root: Path, rel_paths: list[str]) -> None:
    files = []
    for rel_path in rel_paths:
        full_path = root / rel_path
        parquet_schema = None
        if full_path.exists() and full_path.suffix == ".parquet":
            parquet_schema = pq.read_table(full_path).schema

        catalog_entry = {
            "path": rel_path,
            "extension": full_path.suffix or ".parquet",
            "size_bytes": full_path.stat().st_size,
            "modified": "2024-01-01T00:00:00Z",
        }
        if parquet_schema is not None:
            catalog_entry["schema"] = {
                "fields": [
                    {"name": field.name, "type": str(field.type)}
                    for field in parquet_schema
                ]
            }
        files.append(catalog_entry)

    catalog = {
        "version": 1,
        "generated_at": "2024-01-01T00:00:00Z",
        "root": str(root),
        "files": files,
    }
    out_dir = root / "_query_engine"
    out_dir.mkdir(parents=True, exist_ok=True)
    (out_dir / "catalog.json").write_text(json.dumps(catalog), encoding="utf-8")


def test_run_query_basic(tmp_path: Path) -> None:
    rel = "data/sample.parquet"
    parquet_path = tmp_path / rel
    _write_parquet(parquet_path)
    _write_catalog(tmp_path, rel)

    catalog = DatasetCatalog.load(tmp_path / "_query_engine" / "catalog.json")
    run_context = RunContext(runid=str(tmp_path), base_dir=tmp_path, scenario=None, catalog=catalog)

    payload = QueryRequest(datasets=[rel], columns=["id", "value"], limit=2)
    result = run_query(run_context, payload)

    assert result.row_count == 2
    assert result.records == [{"id": 1, "value": "a"}, {"id": 2, "value": "b"}]
    assert result.schema is None


def test_run_query_include_schema(tmp_path: Path) -> None:
    rel = "data/sample.parquet"
    parquet_path = tmp_path / rel
    _write_parquet(parquet_path)
    _write_catalog(tmp_path, rel)

    catalog = DatasetCatalog.load(tmp_path / "_query_engine" / "catalog.json")
    run_context = RunContext(runid=str(tmp_path), base_dir=tmp_path, scenario=None, catalog=catalog)

    payload = QueryRequest(datasets=[rel], include_schema=True)
    result = run_query(run_context, payload)

    assert result.row_count == 3
    assert len(result.records) == 3
    assert result.schema is not None
    assert any(field["name"] == "id" for field in result.schema)


def test_run_query_join(tmp_path: Path) -> None:
    landuse_rel = "landuse/landuse.parquet"
    soils_rel = "soils/soils.parquet"

    landuse_table = pa.table(
        {
            "TopazID": [1, 2, 3],
            "landuse": ["Forest", "Pasture", "Urban"],
        }
    )
    soils_table = pa.table(
        {
            "TopazID": [1, 2, 4],
            "soil_texture": ["Loam", "Sandy", "Clay"],
        }
    )

    _write_parquet(tmp_path / landuse_rel, landuse_table)
    _write_parquet(tmp_path / soils_rel, soils_table)
    _write_catalog_entries(tmp_path, [landuse_rel, soils_rel])

    catalog = DatasetCatalog.load(tmp_path / "_query_engine" / "catalog.json")
    run_context = RunContext(runid=str(tmp_path), base_dir=tmp_path, scenario=None, catalog=catalog)

    payload = QueryRequest(
        datasets=[
            {"path": landuse_rel, "alias": "landuse"},
            {"path": soils_rel, "alias": "soils"},
        ],
        joins=[
            {"left": "landuse", "right": "soils", "on": ["TopazID"]},
        ],
        columns=[
            "landuse.TopazID AS topaz_id",
            "landuse.landuse AS landuse",
            "soils.soil_texture AS soil_texture",
        ],
    )
    result = run_query(run_context, payload)

    assert result.row_count == 2  # TopazID 1 and 2 join successfully
    assert result.records == [
        {"topaz_id": 1, "landuse": "Forest", "soil_texture": "Loam"},
        {"topaz_id": 2, "landuse": "Pasture", "soil_texture": "Sandy"},
    ]


def test_run_query_aggregation(tmp_path: Path) -> None:
    rel = "wepp/output/interchange/pass_daily.parquet"
    table = pa.table(
        {
            "wepp_id": [10, 11, 10, 11],
            "year": [2020, 2020, 2020, 2020],
            "month": [6, 6, 7, 7],
            "day": [1, 1, 1, 1],
            "runoff": [1.0, 2.0, 3.0, 4.0],
            "sediment": [0.5, 0.1, 0.3, 0.2],
        }
    )
    _write_parquet(tmp_path / rel, table)
    _write_catalog_entries(tmp_path, [rel])

    catalog = DatasetCatalog.load(tmp_path / "_query_engine" / "catalog.json")
    run_context = RunContext(runid=str(tmp_path), base_dir=tmp_path, scenario=None, catalog=catalog)

    payload = QueryRequest(
        datasets=[{"path": rel, "alias": "pass"}],
        columns=[
            "pass.year AS year",
            "pass.month AS month",
            "pass.day AS day",
        ],
        group_by=["year", "month", "day"],
        aggregations=[
            {"fn": "sum", "column": "pass.runoff", "alias": "runoff_sum"},
            {"fn": "sum", "column": "pass.sediment", "alias": "sediment_sum"},
        ],
        order_by=["year", "month", "day"],
        include_sql=True,
    )
    result = run_query(run_context, payload)

    assert result.row_count == 2
    assert result.sql is not None
    assert "ORDER BY year, month, day" in result.sql
    expected = {
        (2020, 6, 1): {"runoff_sum": 3.0, "sediment_sum": 0.6},
        (2020, 7, 1): {"runoff_sum": 7.0, "sediment_sum": 0.5},
    }
    ordered_keys = []
    for row in result.records:
        key = (row.get("year"), row.get("month"), row.get("day"))
        assert key in expected
        assert row["runoff_sum"] == expected[key]["runoff_sum"]
        assert row["sediment_sum"] == expected[key]["sediment_sum"]
        ordered_keys.append(key)
    assert ordered_keys == sorted(ordered_keys)


def test_filter_numeric_cast(tmp_path: Path) -> None:
    rel = "landuse/landuse.parquet"
    table = pa.table(
            {
                "TopazID": [1, 2, 3],
                "key": pa.array([43, 44, 45], type=pa.int64()),
                "cancov": pa.array([0.5, 0.8, 0.4], type=pa.float32()),
            }
        )

    _write_parquet(tmp_path / rel, table)
    _write_catalog_entries(tmp_path, [rel])

    catalog = DatasetCatalog.load(tmp_path / "_query_engine" / "catalog.json")
    run_context = RunContext(runid=str(tmp_path), base_dir=tmp_path, scenario=None, catalog=catalog)

    payload = QueryRequest(
        datasets=[{"path": rel, "alias": "landuse"}],
        columns=[
            "landuse.TopazID AS topaz_id",
            "landuse.key",
            "landuse.cancov",
        ],
        filters=[
            {"column": "landuse.key", "operator": "=", "value": "43"},
            {"column": "landuse.cancov", "operator": "<", "value": 0.6},
        ],
        include_sql=True,
    )

    result = run_query(run_context, payload)
    assert result.row_count == 1
    row = result.records[0]
    assert row.get("landuse.key", row.get("key")) == 43
    assert "WHERE landuse.key = 43" in (result.sql or "")

    payload_invalid = QueryRequest(
        datasets=[{"path": rel, "alias": "landuse"}],
        filters=[
            {"column": "landuse.key", "operator": "=", "value": "forest"},
        ],
    )

    with pytest.raises(ValueError):
        run_query(run_context, payload_invalid)


def test_filter_between_in_null(tmp_path: Path) -> None:
    rel = "data/filters.parquet"
    table = pa.table(
        {
            "id": [1, 2, 3, 4],
            "score": [5, 7, 9, 12],
            "category": ["A", "B", "C", "A"],
            "note": [None, "present", None, ""],
        }
    )
    _write_parquet(tmp_path / rel, table)
    _write_catalog_entries(tmp_path, [rel])

    catalog = DatasetCatalog.load(tmp_path / "_query_engine" / "catalog.json")
    run_context = RunContext(runid=str(tmp_path), base_dir=tmp_path, scenario=None, catalog=catalog)

    payload = QueryRequest(
        datasets=[{"path": rel, "alias": "data"}],
        columns=["data.id AS row_id", "data.score", "data.category"],
        filters=[
            {"column": "data.score", "operator": "BETWEEN", "value": [6, 10]},
            {"column": "data.category", "operator": "IN", "value": ["A", "C"]},
            {"column": "data.note", "operator": "IS NULL", "value": None},
        ],
    )

    result = run_query(run_context, payload)
    assert result.row_count == 1
    assert result.records[0]["row_id"] == 3

    payload_not_in = QueryRequest(
        datasets=[{"path": rel, "alias": "data"}],
        filters=[{"column": "data.category", "operator": "NOT IN", "value": ["A"]}],
    )

    result_not_in = run_query(run_context, payload_not_in)
    categories = {row.get("data.category", row.get("category")) for row in result_not_in.records}
    assert categories == {"B", "C"}


def test_build_plan_for_geojson(tmp_path: Path) -> None:
    landuse_rel = "landuse/landuse.parquet"
    geo_rel = "geo/points.geojson"

    landuse_table = pa.table(
        {
            "TopazID": [1, 2, 3],
            "desc": ["A", "B", "C"],
        }
    )
    _write_parquet(tmp_path / landuse_rel, landuse_table)

    geo_path = tmp_path / geo_rel
    geo_path.parent.mkdir(parents=True, exist_ok=True)
    geo_path.write_text(
        json.dumps(
            {
                "type": "FeatureCollection",
                "features": [
                    {
                        "type": "Feature",
                        "properties": {"topaz_id": 1, "name": "Alpha"},
                        "geometry": {"type": "Point", "coordinates": [0.0, 0.0]},
                    },
                    {
                        "type": "Feature",
                        "properties": {"topaz_id": 2, "name": "Beta"},
                        "geometry": {"type": "Point", "coordinates": [1.0, 1.0]},
                    },
                ],
            }
        )
    )

    _write_catalog_entries(tmp_path, [landuse_rel])
    catalog_path = tmp_path / "_query_engine" / "catalog.json"
    catalog_data = json.loads(catalog_path.read_text())
    catalog_data["files"].append(
        {
            "path": geo_rel,
            "extension": ".geojson",
            "size_bytes": geo_path.stat().st_size,
            "modified": "2024-01-01T00:00:00Z",
            "schema": {
                "fields": [
                    {"name": "topaz_id", "type": "INT64"},
                    {"name": "name", "type": "VARCHAR"},
                    {"name": "geometry", "type": "GEOMETRY"},
                ]
            },
        }
    )
    catalog_path.write_text(json.dumps(catalog_data), encoding="utf-8")

    catalog = DatasetCatalog.load(catalog_path)

    payload = QueryRequest(
        datasets=[
            {"path": landuse_rel, "alias": "landuse"},
            {"path": geo_rel, "alias": "geo"},
        ],
        joins=[
            {"left": "landuse", "right": "geo", "left_on": ["TopazID"], "right_on": ["topaz_id"]},
        ],
        columns=[
            "landuse.TopazID AS topaz_id",
            "geo.name",
            "ST_AsGeoJSON(geo.geometry) AS geometry_json",
        ],
    )

    plan = build_query_plan(payload, catalog)
    assert "ST_Read" in plan.sql
    assert plan.requires_spatial is True
