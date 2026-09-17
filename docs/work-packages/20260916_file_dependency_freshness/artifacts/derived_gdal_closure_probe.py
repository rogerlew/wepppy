"""Read-only implementation review; mutate disposable native raster fixtures only.

Run: wctl exec weppcloud python <this file>
"""
import hashlib
import json
import os
from pathlib import Path
from tempfile import TemporaryDirectory

from osgeo import gdal, osr
from wepppyo3.raster_characteristics import identify_median_single_raster_key


def fingerprint(paths):
    return [
        (str(path), path.stat().st_size, path.stat().st_mtime_ns,
         hashlib.sha256(path.read_bytes()).hexdigest())
        for path in sorted(map(Path, paths))
    ]


def create_raster(path, value):
    dataset = gdal.GetDriverByName("GTiff").Create(str(path), 2, 2, 1, gdal.GDT_Int32)
    spatial = osr.SpatialReference()
    spatial.ImportFromEPSG(32611)
    dataset.SetProjection(spatial.ExportToWkt())
    dataset.SetGeoTransform((500000, 30, 0, 5000000, 0, -30))
    dataset.GetRasterBand(1).Fill(value)
    dataset = None


gdal.UseExceptions()
with TemporaryDirectory(prefix="derived-gdal-closure-review-") as wd:
    root = Path(wd)
    base, inner, outer, key = (root / name for name in
                              ("base.tif", "inner.vrt", "outer.vrt", "subwta.tif"))
    create_raster(base, 3)
    create_raster(key, 101)
    dataset = gdal.Translate(str(inner), str(base), format="VRT")
    dataset = None
    # Translate can flatten VRTs, so construct a genuine second reference level.
    outer.write_text(inner.read_text().replace("base.tif", "inner.vrt"))
    dataset = gdal.Open(str(outer))
    listed_before = dataset.GetFileList()
    pixels_before = dataset.ReadRaster().hex()
    dataset = None
    signature_before = fingerprint(listed_before)
    native_before = identify_median_single_raster_key(
        key_fn=str(key), parameter_fn=str(outer), band_indx=1
    )
    original_stat = base.stat()
    dataset = gdal.Open(str(base), gdal.GA_Update)
    dataset.GetRasterBand(1).Fill(7)
    dataset = None
    os.utime(base, ns=(original_stat.st_atime_ns, original_stat.st_mtime_ns))
    dataset = gdal.Open(str(outer))
    listed_after = dataset.GetFileList()
    pixels_after = dataset.ReadRaster().hex()
    dataset = None
    native_after = identify_median_single_raster_key(
        key_fn=str(key), parameter_fn=str(outer), band_indx=1
    )
    result = {
        "gdal_version": gdal.VersionInfo(),
        "reported_members": [Path(path).name for path in listed_before],
        "base_member_omitted": str(base) not in listed_before,
        "listed_members_and_signatures_unchanged": (
            listed_before == listed_after and signature_before == fingerprint(listed_after)
        ),
        "base_size_and_mtime_restored": (
            (base.stat().st_size, base.stat().st_mtime_ns) ==
            (original_stat.st_size, original_stat.st_mtime_ns)
        ),
        "pixels_changed": pixels_before != pixels_after,
        "native_before": native_before,
        "native_after": native_after,
    }
    print(json.dumps(result, indent=2))
    assert result["base_member_omitted"]
    assert result["listed_members_and_signatures_unchanged"]
    assert result["base_size_and_mtime_restored"]
    assert result["pixels_changed"] and native_before != native_after
