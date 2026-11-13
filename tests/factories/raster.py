"""Small real GDAL inputs for upload-boundary integration tests."""
from pathlib import Path


def sbs_raster_bytes(path: Path, *, nodata_only: bool = False) -> bytes:
    import numpy as np
    from osgeo import gdal, osr
    dataset = gdal.GetDriverByName('GTiff').Create(str(path), 2, 2, 1, gdal.GDT_Byte)
    spatial_reference = osr.SpatialReference()
    spatial_reference.ImportFromEPSG(32611)
    dataset.SetProjection(spatial_reference.ExportToWkt())
    dataset.SetGeoTransform((500000, 30, 0, 4500000, 0, -30))
    band = dataset.GetRasterBand(1)
    band.SetNoDataValue(255)
    band.WriteArray(np.full((2, 2), 255 if nodata_only else 2, dtype=np.uint8))
    band = None
    dataset = None
    return path.read_bytes()


def raster_bytes(path: Path, *, driver: str, spill: bool = False) -> bytes:
    """Write a small real raster with the requested GDAL driver."""
    import numpy as np
    from osgeo import gdal, osr

    options = ["USE_SPILL=YES"] if spill else []
    side = 200 if spill else 2
    dataset = gdal.GetDriverByName(driver).Create(
        str(path), side, side, 1, gdal.GDT_Float32, options=options
    )
    spatial_reference = osr.SpatialReference()
    spatial_reference.ImportFromEPSG(32611)
    dataset.SetProjection(spatial_reference.ExportToWkt())
    dataset.SetGeoTransform((500000, 30, 0, 4500000, 0, -30))
    dataset.GetRasterBand(1).WriteArray(
        np.ones((side, side), dtype=np.float32)
    )
    dataset = None
    return path.read_bytes()
