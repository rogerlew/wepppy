"""Rasterize the archived final polygons to the matching 30 m fixture grid."""
import argparse
import json
from pathlib import Path
import tempfile
import zipfile

from osgeo import gdal, ogr, osr

from import_archive import ARCHIVE_SHA256, PREFIX, URL, digest


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    args = parser.parse_args()
    if digest(args.archive) != ARCHIVE_SHA256:
        raise ValueError('Archive identity mismatch')
    gdal.UseExceptions()
    ogr.UseExceptions()
    root = Path(__file__).resolve().parent
    target = root / 'wallow_finalsoilburnseverity.tif'
    if target.exists():
        raise FileExistsError(target)
    reference = gdal.Open(str(root / 'wallow_20110623_barc4_alb.tif'))
    sources = []
    with zipfile.ZipFile(args.archive) as archive, tempfile.TemporaryDirectory() as temporary:
        for extension in ('.shp', '.shx', '.dbf', '.prj'):
            name = 'wallow_finalsoilburnseverity' + extension
            path = Path(temporary) / name
            path.write_bytes(archive.read(PREFIX + name))
            sources.append({'member': PREFIX + name, 'sha256': digest(path)})
        vector = ogr.Open(str(Path(temporary) / 'wallow_finalsoilburnseverity.shp'))
        layer = vector.GetLayer()
        crs = osr.SpatialReference(wkt=reference.GetProjection())
        if not layer.GetSpatialRef().IsSame(crs):
            raise ValueError('Vector and reference CRS differ')
        counts = {}
        for feature in layer:
            code = feature.GetField('GRIDCODE')
            if code not in (0, 1, 2, 3, 4):
                raise ValueError(f'Unexpected GRIDCODE: {code}')
            counts[str(code)] = counts.get(str(code), 0) + 1
        layer.ResetReading()
        output = gdal.GetDriverByName('GTiff').Create(
            str(target), reference.RasterXSize, reference.RasterYSize, 1,
            gdal.GDT_Byte, options=['COMPRESS=DEFLATE', 'TILED=YES'])
        output.SetGeoTransform(reference.GetGeoTransform())
        output.SetProjection(reference.GetProjection())
        band = output.GetRasterBand(1)
        band.Fill(0)
        band.SetNoDataValue(0)
        band.SetRasterColorTable(reference.GetRasterBand(1).GetRasterColorTable())
        gdal.RasterizeLayer(output, [1], layer, options=['ATTRIBUTE=GRIDCODE'])
        output.SetMetadata({'SOURCE_ARCHIVE_SHA256': ARCHIVE_SHA256,
                            'SOURCE_MEMBER': PREFIX + 'wallow_finalsoilburnseverity.shp',
                            'SOURCE_ATTRIBUTE': 'GRIDCODE'})
        band = None
        output = None
    result = gdal.Open(str(target))
    if (result.GetGeoTransform(), result.GetProjection(), result.RasterXSize, result.RasterYSize) != (
            reference.GetGeoTransform(), reference.GetProjection(), reference.RasterXSize, reference.RasterYSize):
        raise ValueError('Output grid differs from reference')
    import numpy as np
    values, pixels = np.unique(result.ReadAsArray(), return_counts=True)
    record = {'archive_url': URL, 'archive_sha256': ARCHIVE_SHA256, 'sources': sources,
              'path': target.name, 'sha256': digest(target), 'attribute': 'GRIDCODE',
              'classes': {'0': 'background/NoData', '1': 'unchanged/very low', '2': 'low', '3': 'moderate', '4': 'high'},
              'rasterization': 'GDAL default pixel-center rule; source feature order; no ALL_TOUCHED',
              'grid_reference': 'wallow_20110623_barc4_alb.tif',
              'grid_reference_sha256': digest(root / 'wallow_20110623_barc4_alb.tif'),
              'feature_counts': counts, 'pixel_counts': {str(v): int(n) for v, n in zip(values, pixels)},
              'nodata': 0, 'gdal_version': gdal.VersionInfo('--version')}
    (root / 'wallow_finalsoilburnseverity.manifest.json').write_text(json.dumps(record, indent=2) + '\n')
    print(json.dumps(record, indent=2))


if __name__ == '__main__':
    main()
