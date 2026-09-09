"""Validate final vendored CLI output against independent CRS transformation."""
import argparse
import json
from pathlib import Path

import numpy as np
import pandas as pd
from osgeo import gdal
from pyproj import Transformer

parser = argparse.ArgumentParser(description=__doc__)
parser.add_argument("root", type=Path)
args = parser.parse_args()
report = {}
for mode in ["topaz", "wbt", "fields"]:
    run = args.root / ("container-" + mode)
    raster = "dem/topaz/SUBWTA.ARC" if mode == "topaz" else "dem/wbt/subwta.tif"
    dataset = gdal.Open(str(run / raster))
    gt = dataset.GetGeoTransform()
    transformer = Transformer.from_crs(dataset.GetProjection(), 4326, always_xy=True)
    output = run / ("ag_fields/sub_fields" if mode == "fields" else "watershed")
    tables = list(output.glob("*.csv" if mode == "fields" else "*.parquet"))
    assert tables, mode
    for table in tables:
        rows = pd.read_csv(table) if mode == "fields" else pd.read_parquet(table)
        assert len(rows), table
        x = gt[0] + rows.centroid_px * gt[1] + rows.centroid_py * gt[2]
        y = gt[3] + rows.centroid_px * gt[4] + rows.centroid_py * gt[5]
        lon, lat = transformer.transform(x.to_numpy(), y.to_numpy())
        error = float(max(np.max(abs(rows.centroid_lon - lon)), np.max(abs(rows.centroid_lat - lat))))
        assert error < 1e-8, (table, error)
        report[mode + "/" + table.name] = {"rows": len(rows), "max_error_degrees": error}
print(json.dumps(report, indent=2))
