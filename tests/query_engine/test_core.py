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
            "topaz_id": pa.array([1, 2, 3], type=pa.int32()),
            "landuse": ["Forest", "Pasture", "Urban"],
        }
    )
    soils_table = pa.table(
        {
            "topaz_id": pa.array([1, 2, 4], type=pa.int32()),
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
            {"left": "landuse", "right": "soils", "on": ["topaz_id"]},
        ],
        columns=[
            "landuse.topaz_id AS topaz_id",
            "landuse.landuse AS landuse",
            "soils.soil_texture AS soil_texture",
        ],
    )
    result = run_query(run_context, payload)

    assert result.row_count == 2  # topaz_id 1 and 2 join successfully
    assert result.records == [
        {"topaz_id": 1, "landuse": "Forest", "soil_texture": "Loam"},
        {"topaz_id": 2, "landuse": "Pasture", "soil_texture": "Sandy"},
    ]


def test_run_query_join_with_spaces(tmp_path: Path) -> None:
    loss_rel = "wepp/output/interchange/loss_pw0.chn.parquet"
    chn_rel = "watershed/channels.parquet"

    loss_table = pa.table(
        {
            "Channels and Impoundments": [1, 2, 3],
            "Value": ["a", "b", "c"],
        }
    )
    chn_table = pa.table(
        {
            "Channel Number": [1, 4, 5],
            "Name": ["Channel A", "Channel B", "Channel C"],
        }
    )

    _write_parquet(tmp_path / loss_rel, loss_table)
    _write_parquet(tmp_path / chn_rel, chn_table)
    _write_catalog_entries(tmp_path, [loss_rel, chn_rel])

    catalog = DatasetCatalog.load(tmp_path / "_query_engine" / "catalog.json")
    run_context = RunContext(runid=str(tmp_path), base_dir=tmp_path, scenario=None, catalog=catalog)

    payload = QueryRequest(
        datasets=[
            {"path": loss_rel, "alias": "loss"},
            {"path": chn_rel, "alias": "chn"},
        ],
        joins=[
            {
                "left": "loss",
                "right": "chn",
                "left_on": ["Channels and Impoundments"],
                "right_on": ["Channel Number"],
            },
        ],
        columns=[
            'loss."Channels and Impoundments" AS loss_channel',
            'chn."Channel Number" AS chn_channel',
            "chn.Name AS name",
        ],
    )

    result = run_query(run_context, payload)

    assert result.row_count == 1
    assert result.records == [
        {"loss_channel": 1, "chn_channel": 1, "name": "Channel A"},
    ]


def test_run_query_aggregation(tmp_path: Path) -> None:
    rel = "wepp/output/interchange/pass_daily.parquet"
    table = pa.table(
        {
            "wepp_id": [10, 11, 10, 11],
            "year": [2020, 2020, 2020, 2020],
            "month": [6, 6, 7, 7],
            "sim_day_index": [1, 1, 31, 31],
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
            "pass.sim_day_index AS sim_day_index",
        ],
        group_by=["year", "month", "sim_day_index"],
        aggregations=[
            {"fn": "sum", "column": "pass.runoff", "alias": "runoff_sum"},
            {"fn": "sum", "column": "pass.sediment", "alias": "sediment_sum"},
        ],
        order_by=["year", "month", "sim_day_index"],
        include_sql=True,
    )
    result = run_query(run_context, payload)

    assert result.row_count == 2
    assert result.sql is not None
    assert "ORDER BY year, month, sim_day_index" in result.sql
    expected = {
        (2020, 6, 1): {"runoff_sum": 3.0, "sediment_sum": 0.6},
        (2020, 7, 31): {"runoff_sum": 7.0, "sediment_sum": 0.5},
    }
    ordered_keys = []
    for row in result.records:
        key = (row.get("year"), row.get("month"), row.get("sim_day_index"))
        assert key in expected
        assert row["runoff_sum"] == expected[key]["runoff_sum"]
        assert row["sediment_sum"] == expected[key]["sediment_sum"]
        ordered_keys.append(key)
    assert ordered_keys == sorted(ordered_keys)


def test_filter_numeric_cast(tmp_path: Path) -> None:
    rel = "landuse/landuse.parquet"
    table = pa.table(
        {
            "topaz_id": pa.array([1, 2, 3], type=pa.int32()),
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
            "landuse.topaz_id AS topaz_id",
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
            "topaz_id": pa.array([1, 2, 3], type=pa.int32()),
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
            {"left": "landuse", "right": "geo", "left_on": ["topaz_id"], "right_on": ["topaz_id"]},
        ],
        columns=[
            "landuse.topaz_id AS topaz_id",
            "geo.name",
            "ST_AsGeoJSON(geo.geometry) AS geometry_json",
        ],
    )

    plan = build_query_plan(payload, catalog)
    assert "ST_Read" in plan.sql
    assert plan.requires_spatial is True


def test_build_plan_with_computed_columns(tmp_path: Path) -> None:
    rel = "stream/data.parquet"
    table = pa.table(
        {
            "year": [2020, 2020],
            "month": [1, 1],
            "day_of_month": [1, 2],
            "value": [1.0, 2.0],
        }
    )
    _write_parquet(tmp_path / rel, table)
    _write_catalog_entries(tmp_path, [rel])
    catalog_path = tmp_path / "_query_engine" / "catalog.json"
    catalog = DatasetCatalog.load(catalog_path)

    payload = QueryRequest(
        datasets=[{"path": rel, "alias": "stream"}],
        columns=["stream.year"],
        computed_columns=[
            {
                "alias": "flow_date",
                "date_parts": {
                    "year": "stream.year",
                    "month": "stream.month",
                    "day": "stream.day_of_month",
                },
            }
        ],
    )

    plan = build_query_plan(payload, catalog)
    assert "MAKE_DATE(stream.year" in plan.sql
    assert "AS flow_date" in plan.sql


def test_run_query_timeseries_reshape(tmp_path: Path) -> None:
    rel = "wepp/output/interchange/totalwatsed3.parquet"
    data_dir = (tmp_path / rel).parent
    data_dir.mkdir(parents=True, exist_ok=True)

    schema = pa.schema(
        [
            pa.field("year", pa.int16()),
            pa.field("month", pa.int8()),
            pa.field("day_of_month", pa.int8()),
            pa.field("Precipitation", pa.float64()).with_metadata({b"units": b"mm"}),
            pa.field("Rain+Melt", pa.float64()).with_metadata({b"units": b"mm"}),
            pa.field("Runoff", pa.float64()).with_metadata({b"units": b"mm", b"description": b"Daily runoff depth"}),
        ]
    )
    table = pa.Table.from_arrays(
        [
            pa.array([2000, 2000, 2001], type=pa.int16()),
            pa.array([1, 1, 1], type=pa.int8()),
            pa.array([1, 2, 1], type=pa.int8()),
            pa.array([1.0, 2.0, 3.0]),
            pa.array([1.5, 1.2, 2.5]),
            pa.array([0.4, 0.5, 0.6]),
        ],
        schema=schema,
    )
    pq.write_table(table, tmp_path / rel)
    _write_catalog_entries(tmp_path, [rel])
    catalog = DatasetCatalog.load(tmp_path / "_query_engine" / "catalog.json")

    run_context = RunContext(runid=str(tmp_path), base_dir=tmp_path, scenario=None, catalog=catalog)

    payload = QueryRequest(
        datasets=[{"path": rel, "alias": "tw3"}],
        columns=[
            "tw3.year AS year",
            "tw3.\"Precipitation\"",
            "tw3.\"Rain+Melt\"",
            "tw3.Runoff",
        ],
        computed_columns=[
            {
                "alias": "flow_date",
                "date_parts": {
                    "year": "tw3.year",
                    "month": "tw3.month",
                    "day": "tw3.day_of_month",
                },
            }
        ],
        order_by=["flow_date"],
        include_schema=True,
        reshape={
            "type": "timeseries",
            "index": {"column": "flow_date", "key": "date"},
            "year_column": "year",
            "exclude_year_indexes": [0],
            "series": [
                {
                    "column": "Runoff",
                    "key": "runoff",
                    "label": "Runoff",
                    "group": "flow",
                    "color": "#123456",
                    "units": "mm",
                    "description": "Daily runoff depth",
                },
                {
                    "column": "Precipitation",
                    "key": "precip",
                    "label": "Precipitation",
                    "group": "meteo",
                    "units": "mm",
                    "description": "Daily precipitation depth",
                },
            ],
            "compact": True,
        },
    )

    result = run_query(run_context, payload)

    assert result.records == []
    assert result.row_count == 1
    assert result.schema is not None
    assert result.formatted is not None

    formatted = result.formatted
    assert formatted["index"]["values"] == ["2001-01-01"]
    runoff_series = next(series for series in formatted["series"] if series["id"] == "runoff")
    assert runoff_series["values"] == [0.6]
    assert runoff_series["units"] == "mm"
    assert runoff_series["description"] == "Daily runoff depth"
    assert formatted["excluded_years"] == [2000]
