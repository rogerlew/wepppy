"""Replay isolated non-postfire baseline probes with wctl exec weppcloud python.

Writes disposable files only. Imports actual production predicates/cache code.
The D-Tale fingerprint is extracted from its AST to avoid requiring the separate
D-Tale service dependency graph; that case proves the predicate, not its route.
"""
from __future__ import annotations

import ast
import json
import os
from pathlib import Path
import tempfile

import numpy as np
from osgeo import gdal

from wepppy.nodb._derived_build import file_signature
from wepppy.nodb.core.landuse import Landuse
from wepppy.nodb.mods.baer import sbs_map
from wepppy.nodb.mods.features_export import dependency_tracker as dep
from wepppy.nodb.mods.geneva.collaborators.hru_map_geometry_service import GenevaHruMapGeometryService
from wepppy.nodb.mods.geneva.collaborators.hsg_assignment_service import _is_current_auto_burn_artifact
from wepppy.nodb.mods.omni.omni_contrast_build_service import OmniContrastBuildService
from wepppy.wepp.reports.hillslope_watbal import HillslopeWatbalReport
from wepppy.weppcloud.utils.assets import resolve_controllers_gl_build_id


def main() -> None:
    result = {"uid": os.getuid(), "gid": os.getgid(), "groups": os.getgroups()}
    with tempfile.TemporaryDirectory(prefix="freshness-review-", dir="/workdir/wepppy") as work:
        wd = Path(work)
        path = wd / "input.bin"
        path.write_bytes(b"AAAA")
        before = path.stat()

        def entry(mode: str):
            return dep._build_entry_for_relpath(
                relpath=path.name, wd_path=wd, layer_id="probe", output_layer_id="probe",
                dependency_role="source", dependency_id="probe", content_hash_mode=mode,
            )

        signatures = {
            "derived": file_signature(path),
            "features_metadata": entry("none"),
            "features_hash": entry("sha256"),
            "landuse": Landuse._mofe_pair_count_file_signature(str(path)),
            "sbs": sbs_map._summary_cache_key(str(path)),
        }
        path.write_bytes(b"BBBB")
        os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns))
        result["equal_size_restored_mtime"] = {
            "changed_bytes": path.read_bytes() == b"BBBB",
            "ctime_changed": path.stat().st_ctime_ns != before.st_ctime_ns,
            "derived_signature_unchanged": signatures["derived"] == file_signature(path),
            "features_metadata_unchanged": signatures["features_metadata"] == entry("none"),
            "features_hash_detects_change": signatures["features_hash"] != entry("sha256"),
            "landuse_signature_unchanged": signatures["landuse"] == Landuse._mofe_pair_count_file_signature(str(path)),
            "sbs_signature_unchanged": signatures["sbs"] == sbs_map._summary_cache_key(str(path)),
        }
        hashed_before_touch = entry("sha256")
        os.utime(path, ns=(before.st_atime_ns, before.st_mtime_ns + 1_000_000_000))
        result["features_hash_touch"] = {
            "digest_same": hashed_before_touch.content_hash_value == entry("sha256").content_hash_value,
            "fingerprint_changes": dep.dependency_fingerprint([hashed_before_touch], catalog_signature="probe") != dep.dependency_fingerprint([entry("sha256")], catalog_signature="probe"),
        }

        cache, source, legend = (wd / name for name in ("cache", "source", "legend"))
        source.write_bytes(b"OLD")
        legend.write_bytes(b"OLD")
        cache.write_bytes(b"CACHE")
        for candidate in (source, legend):
            os.utime(candidate, ns=(1_000_000_000, 1_000_000_000))
        os.utime(cache, ns=(2_000_000_000, 2_000_000_000))
        source.write_bytes(b"NEW")
        os.utime(source, ns=(1_000_000_000, 1_000_000_000))
        result["restored_source_time"] = {
            "geneva_geometry_not_stale": not GenevaHruMapGeometryService()._is_cache_stale(cache, source, legend),
            "geneva_burn_current": _is_current_auto_burn_artifact(target_path=cache, source_path=source, bound_tif=legend),
            "hillslope_cache_not_stale": not HillslopeWatbalReport._source_is_newer_than_cache(source, cache),
            "omni_cache_not_stale": not OmniContrastBuildService._is_stale(cache, 1.0),
        }

        assets = wd / "controllers-gl.js"
        assets.write_text("/* Build date: 2026-09-16T00:00:00Z */\n")
        asset_stat = assets.stat()
        old_build = resolve_controllers_gl_build_id(assets)
        assets.write_text("/* Build date: 2026-09-17T00:00:00Z */\n")
        os.utime(assets, ns=(asset_stat.st_atime_ns, asset_stat.st_mtime_ns))
        result["assets"] = {"stale_build_id_returned": resolve_controllers_gl_build_id(assets) == old_build}

        source_tree = ast.parse(Path("wepppy/webservices/dtale/dtale.py").read_text())
        predicate = next(node for node in source_tree.body if isinstance(node, ast.FunctionDef) and node.name == "_fingerprint")
        namespace = {"Path": Path}
        exec(compile(ast.Module(body=[predicate], type_ignores=[]), "dtale._fingerprint", "exec"), namespace)
        fingerprint = namespace["_fingerprint"]
        old_fingerprint = fingerprint(path)
        prior = path.stat()
        path.write_bytes(b"CCCC")
        os.utime(path, ns=(prior.st_atime_ns, prior.st_mtime_ns))
        result["dtale"] = {"predicate_only_unchanged_fingerprint": fingerprint(path) == old_fingerprint}

        raster = wd / "severity.tif"
        ds = gdal.GetDriverByName("GTiff").Create(str(raster), 3, 2, 1, gdal.GDT_Byte)
        ds.GetRasterBand(1).WriteArray(np.ones((2, 3), dtype=np.uint8))
        ds = None
        sbs_map._summarize_sbs_raster_cached.cache_clear()
        old_summary = sbs_map._summarize_sbs_raster(str(raster))
        raster_stat = raster.stat()
        ds = gdal.Open(str(raster), gdal.GA_Update)
        ds.GetRasterBand(1).WriteArray(np.full((2, 3), 2, dtype=np.uint8))
        ds = None
        os.utime(raster, ns=(raster_stat.st_atime_ns, raster_stat.st_mtime_ns))
        cached_summary = sbs_map._summarize_sbs_raster(str(raster))
        direct_summary = sbs_map._summarize_sbs_raster_rust(str(raster))
        result["sbs_native_cache"] = {
            "same_size": raster.stat().st_size == raster_stat.st_size,
            "old_summary": old_summary,
            "cached_summary": cached_summary,
            "direct_summary": direct_summary,
            "stale_summary_reused": old_summary == cached_summary and cached_summary != direct_summary,
        }
    print(json.dumps(result, indent=2, default=str))


if __name__ == "__main__":
    main()
