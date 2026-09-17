"""Native controls for Geneva's proposed atomic output publication."""
import json
import os
from pathlib import Path

import numpy as np
from osgeo import gdal, osr
import rasterio

from wepppy.all_your_base.geo import raster_stacker


def raster(path, value):
    ds = gdal.GetDriverByName("GTiff").Create(str(path), 2, 2, 1, gdal.GDT_Byte)
    ds.SetGeoTransform((500000, 30, 0, 5000000, 0, -30))
    spatial = osr.SpatialReference()
    spatial.ImportFromEPSG(32611)
    ds.SetProjection(spatial.ExportToWkt())
    ds.GetRasterBand(1).Fill(value)
    ds = None


def external_mask(path):
    with gdal.config_option("GDAL_TIFF_INTERNAL_MASK", "NO"):
        ds = gdal.Open(str(path), gdal.GA_Update)
        ds.GetRasterBand(1).CreateMaskBand(gdal.GMF_PER_DATASET)
        ds.GetRasterBand(1).GetMaskBand().Fill(0)
        ds = None
    assert Path(str(path) + ".msk").exists()


def state(path):
    with rasterio.open(path) as ds:
        return {"pixels": ds.read(1).tolist(), "mask": ds.read_masks(1).tolist(),
                "files": ds.files, "driver": ds.driver}


def test_direct_native_rebuild_versus_atomic_candidate_with_prior_mask(tmp_path):
    source, bound = tmp_path / "source.tif", tmp_path / "bound.tif"
    direct, replaced = tmp_path / "direct.tif", tmp_path / "replaced.tif"
    candidate = tmp_path / "candidate.tif"
    raster(source, 3)
    raster(bound, 1)
    for target in (direct, replaced):
        raster(target, 1)
        external_mask(target)
    raster_stacker(source, bound, direct, resample="near")
    raster_stacker(source, bound, candidate, resample="near")
    os.replace(candidate, replaced)
    record = {"direct_native": state(direct), "atomic_candidate": state(replaced)}
    Path(__file__).with_suffix(".json").write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record))
    assert record["direct_native"]["pixels"] == record["atomic_candidate"]["pixels"]
    assert record["direct_native"]["mask"] == record["atomic_candidate"]["mask"]
