from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists

from glob import glob

import numpy as np


from wepppy.nodb import Watershed
from wepppy.all_your_base.geo import read_raster

from osgeo import osr
from osgeo import gdal
from osgeo.gdalconst import *


if __name__ == "__main__":
    from pprint import pprint

    wd = '/geodata/weppcloud_runs/lighter-than-air-rebound/'


    # rasterized skid trial map
    skid, transform, proj = read_raster(_join(wd, 'salvage', 'skid.tif'), dtype=np.int32)

    # skid trails in map
    skidids = set(skid.flatten())
    print(skidids)

    # get watershed instance
    watershed = Watershed.getInstance(wd)

    # open subwta map
    subwta, transform, _proj = read_raster(watershed.subwta, dtype=np.int32)

    # make sure the skid trail map is aligned with the subwta map
    assert skid.shape == subwta.shape, (skid.shape, subwta.shape)


    topaz_ids = set(subwta.flatten())

    # remove zeros (outside subcatchments)
    if 0 in topaz_ids:
        topaz_ids.remove(0)

    # remove channels
    topaz_ids = [topid for topid in topaz_ids if not str(topid).endswith('4')]

    for topaz_id in topaz_ids:
        print(topaz_id)
        indx, indy = np.where(subwta == topaz_id)
        px_count = len(indx)

        npys = glob(_join(wd, 'watershed', 'flowpaths', f'{topaz_id},*.npy'))

        print(px_count, len(npys))


    import sys
    sys.exit()

    # find where the skid trials cross subcatchments
    skid_subwta_x = {}
    for skidid in skidids:
        indices = np.where(skid == skidid)
        print(len(indices[0]))
        topaz_ids = set(subwta[indices])

        # remove zeros (outside subcatchments)
        if 0 in topaz_ids:
            topaz_ids.remove(0)

        # remove channels
        topaz_ids = [topid for topid in topaz_ids if not str(topid).endswith('4')]
        skid_subwta_x[skidid] = topaz_ids
    pprint(skid_subwta_x)      
        
    # iterate over the crossing and find the flowpaths that drain onto the skid trails
    flowpaths = {}
    up = np.zeros(skid.shape, dtype=np.int32)
    for skidid in skid_subwta_x:
        skid_indices = np.where(skid == skidid)
        skid_indices = set([(x, y) for x, y in zip(*skid_indices)])

        flowpaths[skidid] = {}
        print('skidid', skidid)
        for topaz_id in skid_subwta_x[skidid]:
            print('  topaz_id', topaz_id)
            _flowpaths = watershed.fps_summary(topaz_id)
            for fp_id, fp_summary in _flowpaths.items():
                x = False
                for i, coord in enumerate(fp_summary.coords):
                    if coord in skid_indices:
                        x = True
                        break
                if x:
                    _coords = fp_summary.coords[:i+1]
                    if len(_coords) > 2:
                        _coords = flowpaths[skidid][fp_id] = fp_summary.coords[:i+1]
                        _indx, _indy = np.array(_coords).T
                        up[_indx, _indy] = skidid

                print(f'    flowpath {fp_id} ({x})' )

#    pprint(flowpaths)

    print(up.shape)

    up_fn = _join(wd, 'salvage', 'up.tif')
    num_cols, num_rows = up.shape
    driver = gdal.GetDriverByName("GTiff")
    dst = driver.Create(up_fn, num_cols, num_rows,
                        1, GDT_Int32)

    srs = osr.SpatialReference()
    srs.ImportFromProj4(proj)
    wkt = srs.ExportToWkt()

    dst.SetProjection(wkt)
    dst.SetGeoTransform(transform)
    band = dst.GetRasterBand(1)
    band.WriteArray(up.T)
    del dst  # Writes and closes file
