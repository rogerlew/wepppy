"""Actual consumer/native baselines on retained disposable package fixtures.

Run with wctl exec weppcloud python <this path>. No production/test edits.
Landuse binds lightweight owner objects and disables persistence/notifications;
its cache, management summaries, native pair counting and area calculation run.
Geneva uses real artifact IO, rasterio vectorization and raster_stacker.
"""
from contextlib import nullcontext
from copy import deepcopy
import hashlib
import json
import logging
import os
from pathlib import Path
from types import SimpleNamespace
import traceback
import uuid

import numpy as np
import rasterio
from rasterio.transform import from_origin

from wepppy.nodb.core.landuse import Landuse, count_intersecting_raster_key_pairs
from wepppy.nodb.mods.geneva.collaborators.artifact_io import GenevaArtifactIO
from wepppy.nodb.mods.geneva.collaborators.hru_map_geometry_service import GenevaHruMapGeometryService
from wepppy.nodb.mods.geneva.collaborators.hsg_assignment_service import GenevaHsgAssignmentService
from wepppy.wepp.management import load_map


ARTIFACTS = Path(__file__).parent
ROOT = ARTIFACTS / "c03_c05_c06_inputs" / uuid.uuid4().hex[:12]
ROOT.mkdir(parents=True)


def raster(path, values, *, transform=None):
    path.parent.mkdir(parents=True, exist_ok=True)
    array = np.array(values, dtype="int32")
    with rasterio.open(path, "w", driver="GTiff", width=array.shape[1],
                       height=array.shape[0], count=1, dtype="int32", nodata=0,
                       crs="EPSG:32611", transform=transform or from_origin(500000, 5000060, 30, 30)) as dst:
        dst.write(array, 1)


def observed(path):
    with rasterio.open(path) as src:
        return {"values": src.read(1).tolist(), "transform": list(src.transform),
                "crs": str(src.crs)}


def restore_mtime(path, version):
    os.utime(path, ns=(version.st_atime_ns, version.st_mtime_ns))
    return {"same_size": path.stat().st_size == version.st_size,
            "same_mtime": path.stat().st_mtime_ns == version.st_mtime_ns}


def c03():
    root = ROOT / "c03"
    subwta, mofe = root / "subwta.tif", root / "mofe.tif"
    raster(subwta, [[11, 11], [11, 11]])
    raster(mofe, [[1, 1], [1, 2]])
    owners = SimpleNamespace(subwta=str(subwta), mofe_map=str(mofe),
                             hillslope_area=lambda topaz_id: 0.36)
    class ProbeLanduse(Landuse):
        @property
        def watershed_instance(self):
            return owners
        @property
        def ron_instance(self):
            return SimpleNamespace(cellsize=30.0)
        @property
        def wepp_instance(self):
            return SimpleNamespace(_multi_ofe=True)
    landuse = ProbeLanduse.__new__(ProbeLanduse)
    landuse.wd = str(root)
    landuse._mapping = None
    keys = list(load_map())[:2]
    landuse.domlc_d = {"11": keys[0]}
    landuse.domlc_mofe_d = {"11": {"1": keys[0], "2": keys[1]}}
    landuse.managements = None
    landuse.logger = logging.getLogger("c03-disposable-probe")
    landuse.locked = lambda: nullcontext()
    landuse.dump_landuse_parquet = lambda: None
    landuse.trigger = lambda *args, **kwargs: None
    def build():
        landuse.build_managements()
        return {"counts": deepcopy(landuse._mofe_pair_count_cache),
                "managements": {key: {"area_ha": summary.area, "pct": summary.pct_coverage}
                                for key, summary in landuse.managements.items()}}
    first = build()
    original = mofe.stat()
    (root / "mofe-before.tif").write_bytes(mofe.read_bytes())
    raster(mofe, [[1, 2], [2, 2]])
    metadata = restore_mtime(mofe, original)
    cached = build()
    actual_counts = count_intersecting_raster_key_pairs(
        key_fn=str(subwta), key2_fn=str(mofe), ignore_channels=False,
        ignore_keys=None, ignore_keys2=None,
    )
    landuse._invalidate_mofe_pair_count_cache(reason="disposable-probe-control")
    fresh = build()
    return {"metadata": metadata, "first": first, "cached_after_rewrite": cached,
            "direct_native_counts": actual_counts, "after_invalidation": fresh,
            "scope": "Actual build_managements/native output; owner bindings and persistence hooks isolated"}


def geneva_at(root):
    return SimpleNamespace(wd=str(root), artifact_io=GenevaArtifactIO())


def c05():
    root = ROOT / "c05"
    geneva = geneva_at(root)
    io = geneva.artifact_io
    source = io.resolve_path(geneva.wd, "hru_map.tif")
    legend = io.resolve_path(geneva.wd, "hru_map_legend.json")
    feature = io.resolve_path(geneva.wd, "hru_map_features.wgs.geojson")
    rows = [{"hru_value": i, "hru_id": f"hru{i}", "landuse_class": 42,
             "hsg_group": "B", "burn_severity_class": "low"} for i in (1, 2)]
    io.write_json(geneva.wd, "hru_map_legend.json", {"schema_version": 1, "rows": rows})
    raster(source, [[1, 1], [1, 1]])
    service = GenevaHruMapGeometryService()
    def query():
        payload = service.query_feature_collection(geneva)
        return {"properties": [f["properties"] for f in payload["feature_collection"]["features"]],
                "bounds": payload["bounds_wgs84"], "count": payload["feature_count"]}
    first = query()
    version = source.stat()
    (root / "hru-before.tif").write_bytes(source.read_bytes())
    raster(source, [[2, 2], [2, 2]])
    metadata = restore_mtime(source, version)
    cached_raster = query()
    service._materialize_feature_collection_from_raster(geneva, source_path=source)
    fresh_raster = query()
    version = legend.stat()
    (root / "legend-before.json").write_bytes(legend.read_bytes())
    rows[1]["hru_id"] = "alt2"
    io.write_json(geneva.wd, "hru_map_legend.json", {"schema_version": 1, "rows": rows})
    legend_metadata = restore_mtime(legend, version)
    cached_legend = query()
    service._materialize_feature_collection_from_raster(geneva, source_path=source)
    fresh_legend = query()
    # Real external validity mask: verify the main raster bytes are unchanged.
    with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=False):
        with rasterio.open(source, "r+") as ds:
            ds.write_mask(np.full((2, 2), 255, dtype="uint8"))
    service._materialize_feature_collection_from_raster(geneva, source_path=source)
    before_mask = query()
    version = source.stat()
    main_sha = hashlib.sha256(source.read_bytes()).hexdigest()
    with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=False):
        with rasterio.open(source, "r+") as ds:
            ds.write_mask(np.array([[255, 0], [255, 0]], dtype="uint8"))
    restore_mtime(source, version)
    cached_mask = query()
    service._materialize_feature_collection_from_raster(geneva, source_path=source)
    fresh_mask = query()
    return {"raster_metadata": metadata, "first": first, "cached_raster": cached_raster,
            "fresh_raster": fresh_raster, "legend_metadata": legend_metadata,
            "cached_legend": cached_legend, "fresh_legend": fresh_legend,
            "external_mask": {"sidecar_exists": Path(str(source) + ".msk").is_file(),
                "main_sha_unchanged": hashlib.sha256(source.read_bytes()).hexdigest() == main_sha,
                "before": before_mask, "cached": cached_mask, "fresh": fresh_mask}}


def c06():
    root = ROOT / "c06"
    geneva = geneva_at(root)
    source, bound, alternate = root / "burn.tif", root / "bound.tif", root / "alternate.tif"
    raster(source, [[1, 1], [1, 1]])
    raster(bound, [[1, 1], [1, 1]])
    raster(alternate, [[3, 3], [3, 3]])
    service = GenevaHsgAssignmentService()
    def build(path):
        return Path(service._materialize_auto_burn_severity(
            geneva, source_path=str(path), bound_tif=str(bound),
        ))
    target = build(source)
    first = observed(target)
    (root / "aligned-before.tif").write_bytes(target.read_bytes())
    version = source.stat()
    raster(source, [[2, 2], [2, 2]])
    metadata = restore_mtime(source, version)
    cached = observed(build(source))
    os.utime(target, ns=(0, 0))
    fresh = observed(build(source))
    os.utime(alternate, ns=(version.st_atime_ns, version.st_mtime_ns))
    changed_source_cached = observed(build(alternate))
    os.utime(target, ns=(0, 0))
    changed_source_fresh = observed(build(alternate))
    version = bound.stat()
    raster(bound, [[1, 1], [1, 1]], transform=from_origin(500030, 5000060, 30, 30))
    bound_metadata = restore_mtime(bound, version)
    bound_cached = observed(build(alternate))
    os.utime(target, ns=(0, 0))
    bound_fresh = observed(build(alternate))
    return {"source_metadata": metadata, "first": first, "cached_after_rewrite": cached,
            "fresh_after_rewrite": fresh, "different_source_cached": changed_source_cached,
            "different_source_fresh": changed_source_fresh, "bound_metadata": bound_metadata,
            "changed_bound_cached": bound_cached, "changed_bound_fresh": bound_fresh}


results = {"fixture_root": str(ROOT), "uid": os.getuid(), "gid": os.getgid()}
for name, function in (("C03", c03), ("C05", c05), ("C06", c06)):
    try:
        results[name] = function()
    except Exception as exc:
        # Probe boundary: retain exact independent-consumer failure and continue.
        results[name] = {"blocked": type(exc).__name__, "message": str(exc),
                         "traceback": traceback.format_exc()}
    (ARTIFACTS / "c03_c05_c06_native_probe.json").write_text(json.dumps(results, indent=2) + "\n")
print(json.dumps(results, indent=2))
