"""Disposable real SQLite and Climate export/readiness characterization.

Run with wctl run-pytest <this file> -v -s. Assertions confirm remaining defects.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import sqlite3

import pandas as pd
import pytest

from tests.nodb.mods.test_postfire_debris_flow_production import owner_project, prepared_inputs
from tests.nodb.mods.test_postfire_debris_flow_production_soils import database
from tests.nodb.test_climate_artifact_export_service import _write_minimal_cli
from wepppy.nodb.mods.postfire_debris_flow import production as production
from wepppy.nodb.mods.postfire_debris_flow.production_soils import inventory
from wepppy.nodb.mods.postfire_debris_flow.soil_snapshot import snapshot_cache, verify_snapshot

pytestmark = pytest.mark.integration


@pytest.mark.parametrize("operation", ["link", "chmod", "touch", "replace", "vacuum", "checkpoint", "unrelated_table"])
def test_sqlite_equal_science_changes_accepted_identity(tmp_path, operation):
    (tmp_path / "soils").mkdir()
    path = database(tmp_path / "soils/ssurgo_tabular_cache.sqlite")
    connection = None
    if operation == "checkpoint":
        connection = sqlite3.connect(path)
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("UPDATE chorizon SET hzdepb_r=125")
        connection.commit()
    try:
        before_inventory = inventory(tmp_path)
        before = snapshot_cache(path, tmp_path / "before")
        bytes_before = hashlib.sha256(path.read_bytes()).hexdigest()
        if operation == "link":
            os.link(path, tmp_path / "alias.sqlite")
        elif operation == "chmod":
            path.chmod(0o600)
        elif operation == "touch":
            current = path.stat()
            os.utime(path, ns=(current.st_atime_ns, current.st_mtime_ns + 1_000_000_000))
        elif operation == "replace":
            other = tmp_path / "replacement.sqlite"
            shutil.copy2(path, other)
            os.replace(other, path)
        elif operation == "vacuum":
            with sqlite3.connect(path) as writer:
                writer.execute("VACUUM")
        elif operation == "checkpoint":
            connection.execute("PRAGMA wal_checkpoint(TRUNCATE)")
        elif operation == "unrelated_table":
            with sqlite3.connect(path) as writer:
                writer.execute("CREATE TABLE unused_audit (note TEXT)")
                writer.execute("INSERT INTO unused_audit VALUES ('not consumed by M3')")
        after = snapshot_cache(path, tmp_path / "after")
        after_inventory = inventory(tmp_path)
        accepted = {"selections": {"soil_inputs": before_inventory}, "files": {}, "content_sha256": {}}
        current = {**accepted, "selections": {"soil_inputs": after_inventory}}
        equal_science = all(before[key] == after[key] for key in ("source_schema", "logical_sha256"))
        result = {"operation": operation, "logical_rows_and_schema_equal": equal_science,
                  "main_bytes_equal": bytes_before == hashlib.sha256(path.read_bytes()).hexdigest(),
                  "raw_state_changed": before["source_state"] != after["source_state"],
                  "inventory_changed": before_inventory != after_inventory,
                  "accepted_source_current": production._source_snapshots_current(accepted, current)}
        print("SOIL " + json.dumps(result, sort_keys=True))
        assert equal_science and before_inventory != after_inventory
        assert not result["accepted_source_current"]
        with pytest.raises(ValueError, match="changed after snapshot"):
            verify_snapshot(path, before, tmp_path / "strict-recheck")
    finally:
        if connection is not None:
            connection.close()


def test_climate_touch_and_restored_time_rewrite(owner_project):
    from wepppy.nodb.core import Climate
    from wepppy.nodb.core.climate_artifact_export_service import ClimateArtifactExportService
    from wepppy.climates.cligen import ClimateFile

    root, _ = owner_project
    climate = Climate.getInstance(str(root))
    cli = Path(climate.cli_dir) / climate.cli_fn
    _write_minimal_cli(cli)
    parquet = ClimateArtifactExportService().export_cli_parquet(climate)
    assert parquet is not None
    table_before = pd.read_parquet(parquet)
    snapshot = production.sources(root)[4]
    assert production.sources(root)[2]["climate"]
    before = cli.stat()
    old_bytes = cli.read_bytes()
    parquet_time = parquet.stat().st_mtime_ns
    os.utime(cli, ns=(before.st_atime_ns, parquet_time + 1_000_000_000))
    touched = production.sources(root)
    print("CLIMATE " + json.dumps({"operation": "touch", "bytes_equal": cli.read_bytes() == old_bytes,
          "ready": touched[2]["climate"], "accepted_source_current": production._source_snapshots_current(snapshot, touched[4])}))
    assert not touched[2]["climate"]
    assert production._source_snapshots_current(snapshot, touched[4])
    changed = old_bytes.replace(b"1980   4.0  0.50", b"1980   8.0  0.50")
    assert changed != old_bytes and len(changed) == len(old_bytes)
    cli.write_bytes(changed)
    os.utime(cli, ns=(before.st_atime_ns, before.st_mtime_ns))
    rewritten = production.sources(root)
    actual_cli = ClimateFile(str(cli)).as_dataframe(calc_peak_intensities=True)
    result = {"operation": "restored_time_rewrite", "ready": rewritten[2]["climate"],
              "active_cli_first_precip": float(actual_cli.iloc[0]["prcp"]),
              "parquet_first_precip": float(table_before.iloc[0]["prcp"]),
              "parquet_unchanged": pd.read_parquet(parquet).equals(table_before),
              "accepted_source_current": production._source_snapshots_current(snapshot, rewritten[4])}
    print("CLIMATE " + json.dumps(result, sort_keys=True))
    assert result["ready"] and result["active_cli_first_precip"] != result["parquet_first_precip"]
    assert result["parquet_unchanged"] and not result["accepted_source_current"]
