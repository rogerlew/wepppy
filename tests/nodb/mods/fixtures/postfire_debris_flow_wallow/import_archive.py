"""Import selected Wallow final products; preserve source samples and provenance."""
import argparse
import hashlib
import json
from pathlib import Path
import tempfile
import zipfile

import numpy as np
import rasterio

ARCHIVE_SHA256 = '423eb8b0edf87a733a1d441d64e11295b6fb65db3c18c30b00bab250998ecaaf'
URL = 'https://edcintl.cr.usgs.gov/downloads/sciweb1/shared/MTBS_Fire/data/baer/Wallow_FinalSoilBurnSeverity.zip'
PREFIX = 'Wallow_FinalSoilBurnSeverity/FinalSoilBurnSeverity/'
RASTERS = ('wallow_20110623_barc4_alb.img', 'wallow_20110623_barc256_alb.img', 'wallow_dnbr.img')


def digest(path):
    h = hashlib.sha256()
    with path.open('rb') as stream:
        for block in iter(lambda: stream.read(1024*1024), b''):
            h.update(block)
    return h.hexdigest()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('archive', type=Path)
    args = parser.parse_args()
    assert digest(args.archive) == ARCHIVE_SHA256, 'Archive identity mismatch'
    root = Path(__file__).resolve().parent
    entries = []
    with zipfile.ZipFile(args.archive) as archive, tempfile.TemporaryDirectory() as temporary:
        for name in RASTERS:
            member = PREFIX + name
            source = Path(temporary) / name
            source.write_bytes(archive.read(member))
            target = root / Path(name).with_suffix('.tif')
            with rasterio.open(source, driver='HFA') as src:
                assert src.count == 1
                data, mask = src.read(1), src.read_masks(1)
                palette = src.colormap(1) if 'barc' in name else None
                if not target.exists():
                    with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=True):
                        with rasterio.open(target, 'w', driver='GTiff', width=src.width,
                                           height=src.height, count=1, dtype=src.dtypes[0],
                                           crs=src.crs, transform=src.transform, nodata=src.nodata,
                                           compress='deflate', predictor=3 if data.dtype.kind == 'f' else 2) as dst:
                            dst.write(data, 1)
                            dst.write_mask(mask)
                            if palette:
                                dst.write_colormap(1, {k: (*v[:3],255) for k,v in palette.items()})
                            dst.update_tags(SOURCE_ARCHIVE_SHA256=ARCHIVE_SHA256, SOURCE_MEMBER=member)
                with rasterio.open(target) as dst:
                    assert (dst.crs, dst.transform, dst.shape, dst.dtypes, dst.nodata) == (src.crs, src.transform, src.shape, src.dtypes, src.nodata)
                    assert np.array_equal(dst.read(1), data, equal_nan=True)
                    assert np.array_equal(dst.read_masks(1), mask)
                    if palette:
                        copied = dst.colormap(1)
                        assert all(copied[k][:3] == v[:3] for k,v in palette.items())
                valid = (mask > 0) & np.isfinite(data)
                record = {'path':target.name, 'source_member':member, 'source_sha256':digest(source),
                          'sha256':digest(target), 'bytes':target.stat().st_size,
                          'shape':list(src.shape), 'crs':str(src.crs), 'transform':list(src.transform)[:6],
                          'dtype':src.dtypes[0], 'nodata':src.nodata, 'valid_cells':int(valid.sum()),
                          'valid_range':[float(data[valid].min()),float(data[valid].max())]}
                if 'barc4' in name:
                    classes, counts = np.unique(data, return_counts=True)
                    record['class_counts'] = {str(k):int(v) for k,v in zip(classes,counts)}
                    record['classes'] = {'0':'unclassified/background','1':'unchanged/very low','2':'low','3':'moderate','4':'high'}
                if 'dnbr' in name:
                    record.update(scale_factor=.001,add_offset=0)
                entries.append(record)
        metadata = []
        for member, name in ((PREFIX+'FINAL_ Wallow_20110623_metadata_alb.txt','source_metadata.txt'),
                             ('Wallow_FinalSoilBurnSeverity/README_FinalBurnSeverity.txt','source_README.txt')):
            raw = archive.read(member)
            target = root/name
            if target.exists():
                assert target.read_bytes() == raw
            else:
                target.write_bytes(raw)
            metadata.append({'path':name,'source_member':member,'sha256':digest(target)})
    manifest = {'schema_version':1,'archive_url':URL,'archive_sha256':ARCHIVE_SHA256,
                'originator':'USDA Forest Service, Remote Sensing Applications Center',
                'rights':'Source metadata: no use restrictions except proper acknowledgment',
                'collection':'FinalSoilBurnSeverity','prefire_date':'2011-05-30','postfire_date':'2011-06-23',
                'conversion':'HFA to DEFLATE GeoTIFF; no sample/grid/mask changes; preserve palette RGB',
                'files':entries,'metadata':metadata}
    path=root/'manifest.json'
    if path.exists():
        assert json.loads(path.read_text()) == manifest
    else:
        path.write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(entries,indent=2))


if __name__ == '__main__':
    main()
