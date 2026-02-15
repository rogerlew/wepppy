from __future__ import annotations

import json
from pathlib import Path

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from wepppy.tools.migrations.landuse import migrate_landuse_parquet
from wepppy.tools.migrations.runner import check_migrations_needed
from wepppy.tools.migrations.soils import migrate_soils_nodb_meta, migrate_soils_parquet
from wepppy.tools.migrations.watershed import migrate_watersheds

pytestmark = pytest.mark.integration


def test_landuse_parquet_skips_unbuilt_nodb(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    landuse_nodb = run_dir / "landuse.nodb"
    landuse_nodb.write_text(
        json.dumps(
            {
                "py/object": "wepppy.nodb.landuse.Landuse",
                "domlc_d": None,
                "managements": None,
            }
        ),
        encoding="utf-8",
    )

    applied, message = migrate_landuse_parquet(str(run_dir), dry_run=True)

    assert applied is True
    assert "not built" in message

    status = check_migrations_needed(str(run_dir))
    entry = next(item for item in status["migrations"] if item["name"] == "landuse_parquet")
    assert entry["would_apply"] is False


def test_landuse_parquet_dry_run_when_built(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    landuse_nodb = run_dir / "landuse.nodb"
    landuse_nodb.write_text(
        json.dumps(
            {
                "py/object": "wepppy.nodb.landuse.Landuse",
                "domlc_d": {"1": "42"},
                "managements": {"42": {"py/object": "wepppy.wepp.management.managements.ManagementSummary"}},
            }
        ),
        encoding="utf-8",
    )

    applied, message = migrate_landuse_parquet(str(run_dir), dry_run=True)

    assert applied is True
    assert "Would generate landuse parquet" in message


def test_soils_parquet_skips_unbuilt_nodb(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    soils_nodb = run_dir / "soils.nodb"
    soils_nodb.write_text(
        json.dumps(
            {
                "py/object": "wepppy.nodb.soils.Soils",
                "domsoil_d": None,
                "soils": None,
            }
        ),
        encoding="utf-8",
    )

    applied, message = migrate_soils_parquet(str(run_dir), dry_run=True)

    assert applied is True
    assert "not built" in message


def test_soils_parquet_dry_run_when_built(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    soils_nodb = run_dir / "soils.nodb"
    soils_nodb.write_text(
        json.dumps(
            {
                "py/object": "wepppy.nodb.soils.Soils",
                "domsoil_d": {"1": "1689257"},
                "soils": {"1689257": {"py/object": "wepppy.soils.ssurgo.ssurgo.SoilSummary"}},
            }
        ),
        encoding="utf-8",
    )

    applied, message = migrate_soils_parquet(str(run_dir), dry_run=True)

    assert applied is True
    assert "Would generate soils parquet" in message


def test_landuse_parquet_normalization_does_not_write_index(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    landuse_parquet = run_dir / "landuse.parquet"
    df = pd.DataFrame({"TopazID": [1], "WeppID": [2], "name": ["test"], "area": [123.0]})
    df.to_parquet(landuse_parquet, index=False)

    applied, _ = migrate_landuse_parquet(str(run_dir), dry_run=False)
    assert applied is True

    updated = pd.read_parquet(landuse_parquet)
    assert "topaz_id" in updated.columns
    assert "TopazID" not in updated.columns
    assert "WeppID" not in updated.columns
    assert "area" in updated.columns
    assert updated["area"].iloc[0] == 123.0
    assert "index" not in updated.columns
    assert "__index_level_0__" not in updated.columns


def test_soils_parquet_normalization_does_not_write_index(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    soils_parquet = run_dir / "soils.parquet"
    df = pd.DataFrame({"TopazID": [1], "WeppID": [2], "mukey": ["123"], "area": [456.0]})
    df.to_parquet(soils_parquet, index=False)

    applied, _ = migrate_soils_parquet(str(run_dir), dry_run=False)
    assert applied is True

    updated = pd.read_parquet(soils_parquet)
    assert "topaz_id" in updated.columns
    assert "TopazID" not in updated.columns
    assert "WeppID" not in updated.columns
    assert "area" in updated.columns
    assert updated["area"].iloc[0] == 456.0
    assert "index" not in updated.columns
    assert "__index_level_0__" not in updated.columns


def test_soils_nodb_meta_detects_legacy_meta_fn(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    soils_parquet = run_dir / "soils.parquet"
    pq.write_table(pa.table({"topaz_id": [1], "mukey": ["1"]}), soils_parquet)

    soils_nodb = run_dir / "soils.nodb"
    soils_nodb.write_text(
        json.dumps(
            {
                "py/object": "wepppy.nodb.soils.Soils",
                "soils": {"1": {"_meta_fn": "legacy.json"}},
            }
        ),
        encoding="utf-8",
    )

    applied, message = migrate_soils_nodb_meta(str(run_dir), dry_run=True)

    assert applied is True
    assert "Would clear legacy _meta_fn attributes" in message


def test_watershed_backfill_creates_parquets(tmp_path: Path) -> None:
    run_dir = tmp_path / "run"
    run_dir.mkdir()
    watershed_nodb = run_dir / "watershed.nodb"
    centroid = {"px": [1, 2], "lnglat": [-116.0, 46.0]}
    watershed_nodb.write_text(
        json.dumps(
            {
                "py/state": {
                    "_subs_summary": {
                        "1": {
                            "topaz_id": 1,
                            "slope_scalar": 0.1,
                            "length": 100.0,
                            "width": 10.0,
                            "direction": 90.0,
                            "aspect": 180.0,
                            "area": 1000.0,
                            "elevation": 500.0,
                            "centroid": centroid,
                            "wepp_id": 1,
                        }
                    },
                    "_chns_summary": {
                        "1": {
                            "topaz_id": 1,
                            "slope_scalar": 0.2,
                            "length": 50.0,
                            "width": 5.0,
                            "direction": 45.0,
                            "order": 1,
                            "aspect": 90.0,
                            "area": 500.0,
                            "elevation": 400.0,
                            "centroid": centroid,
                            "wepp_id": 1,
                            "chn_enum": 1,
                        }
                    },
                    "_fps_summary": {
                        "1": {
                            "flow_1_1": {
                                "topaz_id": 1,
                                "slope_scalar": 0.3,
                                "length": 25.0,
                                "width": 2.0,
                                "direction": 30.0,
                                "aspect": 60.0,
                                "area": 200.0,
                                "elevation": 300.0,
                                "centroid": centroid,
                            }
                        }
                    },
                }
            }
        ),
        encoding="utf-8",
    )

    applied, _ = migrate_watersheds(str(run_dir), dry_run=False)
    assert applied is True

    assert (run_dir / "watershed.hillslopes.parquet").exists()
    assert (run_dir / "watershed.channels.parquet").exists()
    assert (run_dir / "watershed.flowpaths.parquet").exists()
