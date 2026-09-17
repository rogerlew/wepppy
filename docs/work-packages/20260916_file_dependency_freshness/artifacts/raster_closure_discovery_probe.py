"""Characterize owned GDAL discovery for directories and virtual filesystem files."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from zipfile import ZipFile
from osgeo import gdal

with TemporaryDirectory(prefix='raster-closure-') as temporary:
    root = Path(temporary)
    raster = root / 'source.tif'
    dataset = gdal.GetDriverByName('GTiff').Create(str(raster), 2, 2, 1, gdal.GDT_Byte)
    dataset.GetRasterBand(1).Fill(25)
    dataset = None
    zipped = root / 'source.zip'
    with ZipFile(zipped, 'w') as archive:
        archive.write(raster, arcname='source.tif')
    zarr = root / 'source.zarr'
    dataset = gdal.GetDriverByName('Zarr').Create(str(zarr), 2, 2, 1, gdal.GDT_Byte)
    dataset.GetRasterBand(1).Fill(25)
    dataset = None
    names = [str(raster), f'/vsizip/{zipped}/source.tif', str(zarr)]
    results = []
    for name in names:
        dataset = gdal.Open(name)
        files = dataset.GetFileList()
        dataset = None
        info = gdal.VSIStatL(name)
        results.append({'name': name.replace(str(root), '<temporary>'),
                        'files': [member.replace(str(root), '<temporary>') for member in files or []],
                        'vsi_size': info.size if info else None,
                        'vsi_mtime': info.mtime if info else None,
                        'vsi_mode': info.mode if info else None,
                        'identified': gdal.IdentifyDriver(name).ShortName})
    results.append({'directory_members': [str(path.relative_to(root)) for path in sorted(zarr.rglob('*')) if path.is_file()]})
    print(json.dumps(results, indent=2))
