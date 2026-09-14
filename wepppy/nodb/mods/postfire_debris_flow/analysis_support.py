"""Exact common spatial support for new production predictor manifests."""
import numpy as np
import rasterio

__all__ = ['POLICY', 'write_valid_mask']
POLICY = 'common_valid_v1'


def write_valid_mask(path, grid, domain, valid):
    if domain.shape != valid.shape or not np.any(domain) or np.any(valid & ~domain):
        raise ValueError('Invalid common analysis support')
    values = np.full(domain.shape, 255, dtype=np.uint8)
    values[domain] = 0
    values[valid] = 1
    with rasterio.open(path, 'w', driver='GTiff', height=domain.shape[0], width=domain.shape[1],
                       count=1, dtype='uint8', nodata=255, crs=grid['crs'],
                       transform=rasterio.Affine(*grid['transform']), compress='deflate') as target:
        target.write(values, 1)
    with rasterio.open(path) as check:
        if not np.array_equal(check.read(1), values):
            raise ValueError('Valid mask readback differs')
    total, count = int(domain.sum()), int(valid.sum())
    return dict(total_cells=total, valid_cells=count, excluded_cells=total-count,
                valid_fraction=count/total, policy=POLICY, mask='valid_mask.tif')
