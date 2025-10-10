from __future__ import annotations

import json
from pathlib import Path

import pyarrow as pa
import pyarrow.parquet as pq

from wepppy.query_engine.catalog import DatasetCatalog
from wepppy.query_engine.context import RunContext
from wepppy.query_engine.core import run_query
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
        catalog_entry = {
            "path": rel_path,
            "extension": full_path.suffix or ".parquet",
            "size_bytes": full_path.stat().st_size,
            "modified": "2024-01-01T00:00:00Z",
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
    )
    result = run_query(run_context, payload)

    assert result.row_count == 2
    expected = {
        (2020, 6, 1): {"runoff_sum": 3.0, "sediment_sum": 0.6},
        (2020, 7, 1): {"runoff_sum": 7.0, "sediment_sum": 0.5},
    }
    for row in result.records:
        key = (row.get("year"), row.get("month"), row.get("day"))
        assert key in expected
        assert row["runoff_sum"] == expected[key]["runoff_sum"]
        assert row["sediment_sum"] == expected[key]["sediment_sum"]
