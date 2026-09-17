"""Disposable SQLite committed changes with real restored timestamps, no sleeps."""
import json
import os
from pathlib import Path
import sqlite3
from tempfile import TemporaryDirectory

from tests.nodb.mods.test_postfire_debris_flow_production_soils import database
from wepppy.nodb.mods.postfire_debris_flow.production import _source_snapshots_current
from wepppy.nodb.mods.postfire_debris_flow.production_soils import inventory


with TemporaryDirectory(prefix="postfire-sqlite-collision-") as temporary:
    root = Path(temporary)
    (root / "soils").mkdir()
    path = database(root / "soils/ssurgo_tabular_cache.sqlite")
    original = path.stat()
    collisions = 0
    false_current = 0
    connection = sqlite3.connect(path)
    try:
        mode = connection.execute("PRAGMA journal_mode").fetchone()[0]
        for index in range(300):
            connection.execute("UPDATE chorizon SET hzdepb_r=100")
            connection.commit()
            os.utime(path, ns=(original.st_atime_ns, original.st_mtime_ns))
            before = inventory(root)
            connection.execute("UPDATE chorizon SET hzdepb_r=101")
            connection.commit()
            os.utime(path, ns=(original.st_atime_ns, original.st_mtime_ns))
            after = inventory(root)
            assert connection.execute("SELECT hzdepb_r FROM chorizon").fetchone()[0] == 101
            collisions += before == after
            accepted = {"selections": {"soil_inputs": before}, "files": {}, "content_sha256": {}}
            current = {**accepted, "selections": {"soil_inputs": after}}
            false_current += _source_snapshots_current(accepted, current)
    finally:
        connection.close()
    print(json.dumps({"iterations": 300, "journal_mode": mode,
          "same_complete_inventory_after_committed_row_change": collisions,
          "accepted_source_false_current": false_current,
          "mtime_restored_by_probe": True, "filesystem": "canonical container temporary directory"},
          indent=2, sort_keys=True))
