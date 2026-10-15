"""Strict M6 readback through public WMesque from a deployed runtime."""
import json
import os
from pathlib import Path
import pwd
import shutil
import tempfile
import urllib.error
import urllib.request

import numpy as np
from osgeo import gdal

from wepppy.all_your_base.geo.webclients.wmesque import wmesque_retrieve

BASE = "https://wepp.cloud/webservices/wmesque2"
DATASET = "tenerife/136_MDT25_TF"
BBOX = [-16.65, 28.25, -16.60, 28.30]

assert not os.environ.get("WMESQUE_ENDPOINTS", "").strip()
assert os.environ.get("WMESQUE_SYNC_ENABLED", "false").lower() == "false"
assert shutil.which("ssh") and shutil.which("rsync")
identity = pwd.getpwuid(os.getuid())
with urllib.request.urlopen(BASE + "/catalog/manifest", timeout=30) as response:
    catalog = json.load(response)
revision = catalog["datasets"][DATASET]
result = {"uid": os.getuid(), "gid": os.getgid(), "user": identity.pw_name,
          "revision": revision, "sync_enabled": False, "rasters": {}}

with tempfile.TemporaryDirectory(prefix="wmesque-m6-") as temporary:
    for dataset, bbox, pin in (
        (DATASET, BBOX, revision),
        ("nlcd/2019", [-116.41414278909173, 45.24670016201569,
                       -116.33870536206356, 45.29989121596863], None),
    ):
        output = Path(temporary) / (dataset.replace("/", "-") + ".tif")
        assert wmesque_retrieve(dataset, bbox, str(output), 30,
                                expected_revision=pin) == 1
        raster = gdal.Open(str(output))
        assert raster is not None and raster.GetProjection()
        pixels = raster.ReadAsArray()
        assert pixels.size and np.isfinite(pixels).all()
        metadata = json.loads(Path(str(output) + ".meta").read_text())
        assert metadata["wmesque_retrieve"]["wmesque_endpoint"] == BASE
        assert metadata["wmesque"].get("revision") == pin
        result["rasters"][dataset] = {
            "shape": list(pixels.shape), "range": [float(pixels.min()), float(pixels.max())],
            "nodata": raster.GetRasterBand(1).GetNoDataValue(),
            "geotransform": raster.GetGeoTransform(), "revision": pin,
        }
        raster = None

    # An existing caller need not supply a revision; wrong pins fail explicitly.
    query = "/retrieve/" + DATASET + "/?bbox=-16.65,28.25,-16.60,28.30&cellsize=30&format=GTiff"
    with urllib.request.urlopen(BASE + query, timeout=120) as response:
        output = Path(temporary) / "legacy-caller.tif"
        output.write_bytes(response.read())
    raster = gdal.Open(str(output))
    assert raster.RasterXSize == 161 and raster.RasterYSize == 187
    raster = None
    try:
        urllib.request.urlopen(BASE + query + "&expected_revision=" + "0" * 64, timeout=30)
    except urllib.error.HTTPError as error:
        assert error.code == 409
    else:
        raise AssertionError("Wrong revision unexpectedly succeeded")
result["legacy_unpinned_request"] = "passed"
result["wrong_revision_status"] = 409
print(json.dumps(result, indent=2))
