"""Independent valid-state and native failure QA; disposable retained artifacts only."""
import errno
import json
import os
from pathlib import Path
from unittest.mock import patch
from uuid import uuid4
from zipfile import ZipFile

import pandas as pd
import pytest
from osgeo import ogr

from tests.nodb.mods.test_features_export_dependency_tracker import _catalog_with_attr_source
from tests.nodb.mods.test_features_export_freshness import export_source, _execute
from wepppy.nodb.mods.features_export import service
from wepppy.nodb.mods.features_export.dependency_tracker import build_dependency_snapshot
from wepppy.nodb.mods.features_export.planner import resolve_export_plan


ARTIFACTS = Path(__file__).parent
ROOT = ARTIFACTS / "features_qa_inputs" / uuid4().hex[:12]
ROOT.mkdir(parents=True)
results = {"fixture_root": str(ROOT), "uid": os.getuid(), "gid": os.getgid()}

with pytest.MonkeyPatch.context() as mp:
    source = export_source.__wrapped__(ROOT, mp)
    original = _execute(ROOT, "original", "geopackage")
    original_archive = ROOT / original["artifact_relpath"]
    producer_manifest = original_archive.parent / "manifest.json"
    producer_bytes = producer_manifest.read_bytes()
    archive_bytes = original_archive.read_bytes()
    before = source.stat()
    source.write_bytes(source.read_bytes())
    os.utime(source, ns=(before.st_atime_ns, before.st_mtime_ns + 2_000_000_000))
    hit = _execute(ROOT, "same-byte-restoration", "geopackage")
    hit_manifest = service.load_job_manifest(ROOT, "same-byte-restoration")
    companion = service.co_create_post_wepp_geodatabase_artifact(
        ROOT, source_job_id="same-byte-restoration", source_job_result=hit,
    )
    companion_archive = ROOT / companion["artifact_relpath"]
    with ZipFile(companion_archive) as archive:
        companion_manifest = json.loads(archive.read("manifest.json"))
        gdb = next(name.split("/", 1)[0] for name in archive.namelist() if ".gdb/" in name)
    dataset = ogr.Open(f"/vsizip/{companion_archive}/{gdb}")
    value = dict(next(iter(dataset.GetLayer(0))).items())["value"]
    results["same_byte_cache_hit_companion"] = {
        "cache_hit": hit["cache_hit"], "producer_job": hit["source_job_id"],
        "archive_unchanged": original_archive.read_bytes() == archive_bytes,
        "producer_manifest_unchanged": producer_manifest.read_bytes() == producer_bytes,
        "job_manifest_has_run_context": "run_context" in hit_manifest,
        "companion_run_context": companion_manifest["run_context"],
        "companion_value": value,
        "companion_source_artifact": companion_manifest["source_artifact_id"],
        "producer_artifact": original["artifact_id"],
    }
    accepted = companion_archive.read_bytes()
    before_dirs = set((ROOT / "export/features/artifacts").iterdir())
    from wepppy.nodb.mods.features_export.exporters import geodatabase
    with patch.object(geodatabase.shutil, "make_archive", side_effect=OSError(
        errno.ENOSPC, "QA injected packaging ENOSPC after real native GDB creation",
    )):
        try:
            service.co_create_post_wepp_geodatabase_artifact(
                ROOT, source_job_id="same-byte-restoration", source_job_result=hit,
            )
        except Exception as exc:
            # Diagnostic boundary: retain exact native failure evidence.
            failure = {"type": type(exc).__name__, "message": str(exc)}
        else:
            raise AssertionError("Expected injected packaging failure")
    candidates = set((ROOT / "export/features/artifacts").iterdir()) - before_dirs
    results["native_packaging_failure"] = {
        "failure": failure,
        "accepted_archive_unchanged": companion_archive.read_bytes() == accepted,
        "candidate_members": {str(path.relative_to(ROOT)): sorted(str(p.relative_to(path)) for p in path.rglob("*"))
                              for path in candidates},
    }

parent = ROOT / "parent"
child = parent / "_pups/omni/scenarios/child"
child.mkdir(parents=True)
(parent / "geometry.geojson").write_bytes((ROOT / "geometry.geojson").read_bytes())
pd.DataFrame({"id": [1], "value": [36.0]}).to_parquet(child / "attrs.parquet", index=False)
catalog = _catalog_with_attr_source(layer_id="test.attributes", geometry_locator={
    "kind": "path_template", "value": "../../../../geometry.geojson",
})
with patch.object(service, "load_layer_catalog", return_value=catalog):
    result = _execute(child, "parent-source", "parquet")
    with ZipFile(child / result["artifact_relpath"]) as archive:
        manifest = json.loads(archive.read("manifest.json"))
    results["parent_native_export"] = {"cache_hit": result["cache_hit"], "entries": manifest["dependency_snapshot"]["entries"]}

directory = ROOT / "directory.gdb"
directory.mkdir()
(directory / "member").write_bytes(b"native-placeholder")
catalog = _catalog_with_attr_source(layer_id="test.attributes", geometry_locator={
    "kind": "relpath", "value": "directory.gdb",
})
plan = resolve_export_plan({"format": "parquet", "units": "si", "layers": ["test.attributes"]}, catalog)
snapshot = build_dependency_snapshot(plan, catalog, ROOT, content_hash_mode="sha256")
results["directory_snapshot_only"] = [entry.to_mapping() for entry in snapshot.entries]

(ARTIFACTS / "features_implementation_qa_probe.json").write_text(json.dumps(results, indent=2) + "\n")
print(json.dumps(results, indent=2))
