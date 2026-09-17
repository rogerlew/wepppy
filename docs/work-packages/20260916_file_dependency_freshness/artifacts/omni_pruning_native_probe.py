"""Native C07 byte-change probe; completion receipt deliberately stays fixed.

This demonstrates the cache mechanism, not an ordinary writer workflow that
omits completion. All GDAL/WBT inputs and outputs are disposable.
"""
import json
from pathlib import Path
from tempfile import TemporaryDirectory

import numpy as np
from osgeo import gdal, osr
from wepppy.nodb.mods.omni.omni_contrast_build_service import OmniContrastBuildService
from wepppy.rq.topo_utils import _prune_stream_order


def write(path, values):
    ds = gdal.GetDriverByName("GTiff").Create(str(path), 7, 7, 1, gdal.GDT_Float32)
    ds.SetGeoTransform((500000, 30, 0, 4400000, 0, -30))
    spatial = osr.SpatialReference()
    spatial.ImportFromEPSG(32611)
    ds.SetProjection(spatial.ExportToWkt())
    ds.GetRasterBand(1).SetNoDataValue(-9999)
    ds.GetRasterBand(1).WriteArray(values.astype(np.float32))
    ds = None


def read(path):
    return gdal.Open(str(path)).ReadAsArray()


with TemporaryDirectory(prefix="omni-pruning-freshness-") as temporary:
    root = Path(temporary)
    flow = np.zeros((7, 7))
    stream = np.zeros((7, 7))
    for row, col, direction in [(0, 1, 4), (1, 2, 4), (0, 5, 16), (1, 4, 16),
                                 (2, 3, 8), (3, 3, 8), (4, 3, 8), (5, 3, 8), (6, 3, 0)]:
        flow[row, col] = direction
        stream[row, col] = 1
    write(root / "flovec.tif", flow)
    write(root / "netful.tif", stream)
    source = {"flovec": root / "flovec.tif", "netful": root / "netful.tif"}
    service = OmniContrastBuildService()
    generated = service._stream_order_generated_paths(source["netful"], root, 1)
    receipt = min(path.stat().st_mtime for path in source.values()) - 10
    service._maybe_prune_stream_order(_prune_stream_order, source, 1, True)
    original = read(generated["pruned_streams"])
    stream[0, 5] = stream[1, 4] = 0
    write(root / "netful.tif", stream)
    needs_prune = service._stream_order_needs_prune(generated, receipt)
    service._maybe_prune_stream_order(_prune_stream_order, source, 1, needs_prune)
    reused = read(generated["pruned_streams"])
    _prune_stream_order(source["flovec"], source["netful"], 1, overwrite_netful=False)
    fresh = read(generated["pruned_streams"])
    result = {
        "completion_receipt_unchanged": True, "needs_prune": needs_prune,
        "original_retained_stream_cells": int(np.sum(original > 0)),
        "reused_retained_stream_cells": int(np.sum(reused > 0)),
        "fresh_native_retained_stream_cells": int(np.sum(fresh > 0)),
        "ordinary_writer_missing_receipt": "not established by this experiment",
    }
    print(json.dumps(result, indent=2))
    assert needs_prune is False
    assert np.array_equal(original, reused)
    assert not np.array_equal(reused, fresh)
