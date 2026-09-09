"""Generate/check explicitly labeled pseudo-BARC256 fixtures; ADR-0060."""
import hashlib
import json
from pathlib import Path

import numpy as np
import rasterio


def sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main():
    root = Path(__file__).resolve().parent
    output = root / 'pseudo_barc256'
    source_manifest = json.loads((root / 'manifest.json').read_text())
    records = []
    for entry in source_manifest['files']:
        source = root / entry['path']
        assert sha256(source) == entry['sha256'], f'Source identity mismatch: {source}'
        target = output / f'{source.stem}_pseudo_barc256.tif'
        with rasterio.open(source) as src:
            original = src.read(1, masked=True)
            values = original.data.astype(np.float64)
            valid = ~np.ma.getmaskarray(original) & np.isfinite(values)
            scaled = (values[valid] + 275.) / 5.
            expected = np.zeros(src.shape, dtype=np.uint8)
            expected[valid] = np.floor(np.clip(scaled, 0, 255)).astype(np.uint8)
            if not target.exists():
                with rasterio.Env(GDAL_TIFF_INTERNAL_MASK=True):
                    with rasterio.open(target, 'w', driver='GTiff', height=src.height,
                                       width=src.width, count=1, dtype='uint8', crs=src.crs,
                                       transform=src.transform, compress='deflate', nodata=None) as dst:
                        dst.write(expected, 1)
                        dst.write_mask(valid.astype(np.uint8) * 255)
                        dst.update_tags(PRODUCT='PSEUDO_BARC256', FIELD_VALIDATED='NO',
                                        SOURCE_SHA256=entry['sha256'],
                                        CONVERSION='floor(clip((source_dNBR_x1000+275)/5,0,255))')
            with rasterio.open(target) as dst:
                assert dst.crs == src.crs and dst.transform == src.transform and dst.shape == src.shape
                assert dst.dtypes == ('uint8',) and dst.nodata is None
                assert np.array_equal(dst.read(1), expected)
                assert np.array_equal(dst.read_masks(1) > 0, valid)
            assert sha256(source) == entry['sha256']
            records.append({'source':entry['path'], 'source_sha256':entry['sha256'],
                            'output':target.name, 'output_sha256':sha256(target),
                            'shape':list(src.shape), 'crs':str(src.crs),
                            'transform':list(src.transform)[:6], 'valid_cells':int(valid.sum()),
                            'missing_cells':int((~valid).sum()), 'clipped_below_0':int((scaled<0).sum()),
                            'clipped_above_255':int((scaled>255).sum()),
                            'valid_range':[int(expected[valid].min()),int(expected[valid].max())]})
    manifest = {'schema_version':1, 'product':'pseudo_barc256', 'field_validated':False,
                'source_units':'dNBR_x1000', 'conversion':'floor(clip((source+275)/5,0,255))',
                'nodata':'internal mask; no reserved byte value',
                'rights':'Derived from CC0 USGS fixtures', 'files':records}
    manifest_path = output / 'manifest.json'
    if manifest_path.exists():
        assert json.loads(manifest_path.read_text()) == manifest
    else:
        manifest_path.write_text(json.dumps(manifest,indent=2)+'\n')
    print(json.dumps(records,indent=2))


if __name__ == '__main__':
    main()
