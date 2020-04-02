
import sys

sys.path.append('/workdir/wepppy/')

from os.path import exists as _exists
from os.path import join as _join
from os.path import split as _split
import os
import shutil
import csv

import numpy as np
import numpy.ma as ma
import matplotlib.pyplot as plt

from osgeo import gdal, osr, ogr
import pyproj

from wepppy.all_your_base import (
    wgs84_proj4,
    read_raster,
    haversine,
    RasterDatasetInterpolator,
    RDIOutOfBoundsException
)
from wepppy.all_your_base import shapefile
from wepppy.nodb import (
    Ron,
    Topaz,
    Watershed,
    Landuse, LanduseMode,
    Soils, SoilsMode,
    Baer,
    Climate, ClimateSpatialMode,
    Wepp,
    Ash, AshPost
)
from wepppy.wepp.out import TotalWatSed
from wepppy.export import arc_export


outlet_locs = {
    '17': (150.3171, -33.8460),
    '20': (150.1857, -33.8344),
    '25': (150.26653, -33.85829),
    '36': (150.3402, -33.8555),
    '61': (150.1706178, -33.8001780),
    '77': (150.2862, -33.9157),
    '79': (150.2081, -33.8857),
    '90': (150.2512, -33.9382),
    '93': (149.982951, -33.946560),
    '94': (150.2458, -33.9468),
    '95': (150.239374, -33.955644),
    '97': (150.4612056, -33.9600595),
    '123': (150.203247, -34.003217),
    '137': (150.400806, -34.059555),
    '138': (150.155435, -34.040962),
    '175': (150.39048083081883, -34.158819193986396),
    '177': (150.454035, -34.135170),
    '199': (150.3474, -34.2182),
    '201': (150.23246, -34.22814),
    '206': (150.320811, -34.184367),
    '218': (150.3476, -34.2643),
    '222': (150.21148, -34.27796),
    '225': (150.344941, -34.276337),
    '232': (150.38096, -34.20016),
    '233': (149.93706, -34.301980),
    '240': (149.963453, -34.316187),
    '241': (150.22782, -34.25704),
    '252': (150.14092, -34.30062),
    '258': (150.02938, -34.36450)
}

blacklist = [
    '33',   # might be too flat channel map has drainage from over ridge
    '178',  # in gwc_sbs6 map, area needs to be delineated from interface
    '259',  # a large bounding box around the subcatchments
    '262',  # not actually a subcatchment
]

chn_routing_err_topaz_pars = {
    '198': dict(csa=10.1, mcl=200.2),
    '175': dict(csa=30, mcl=200.0)
}


def build_mask(points, georef_fn):

    # This function is based loosely off of Frank's tests for
    # gdal.RasterizeLayer.
    # https://svn.osgeo.org/gdal/trunk/autotest/alg/rasterize.py

    # open the reference
    # we use this to find the size, projection,
    # spatial reference, and geotransform to
    # project the subcatchment to
    ds = gdal.Open(georef_fn)

    pszProjection = ds.GetProjectionRef()
    if pszProjection is not None:
        srs = osr.SpatialReference()
        if srs.ImportFromWkt(pszProjection) == gdal.CE_None:
            pszPrettyWkt = srs.ExportToPrettyWkt(False)


    geoTransform = ds.GetGeoTransform()

    # initialize a new raster in memory
    driver = gdal.GetDriverByName('MEM')
    target_ds = driver.Create('',
                              ds.RasterXSize,
                              ds.RasterYSize,
                              1, gdal.GDT_Byte)
    target_ds.SetGeoTransform(geoTransform)
    target_ds.SetProjection(pszProjection)

    # close the reference
    ds = None

    # Create a memory layer to rasterize from.
    rast_ogr_ds = ogr.GetDriverByName('Memory') \
        .CreateDataSource('wrk')
    rast_mem_lyr = rast_ogr_ds.CreateLayer('poly', srs=srs)

    # Add a polygon.
    coords = ','.join(['%f %f' % (lng, lat) for lng, lat in points])
    wkt_geom = 'POLYGON((%s))' % coords
    feat = ogr.Feature(rast_mem_lyr.GetLayerDefn())
    feat.SetGeometryDirectly(ogr.Geometry(wkt=wkt_geom))
    rast_mem_lyr.CreateFeature(feat)

    # Run the rasterization algorithm
    err = gdal.RasterizeLayer(target_ds, [1], rast_mem_lyr,
                              burn_values=[255])
    rast_ogr_ds = None
    rast_mem_lyr = None

    band = target_ds.GetRasterBand(1)
    data = band.ReadAsArray().T

    # find nonzero indices and return
    mask = -1 * (data / 255.0) + 1
    m, n = mask.shape

    for i in range(1, m-1):
        for j in range(1, n-1):
            cnt = np.sum(mask[i-1:1+1, j-1:j+1])
            if cnt > 6:
                mask[i, j] = 1

    return mask


class WatershedBoundaryDataset:
    def __init__(self, shp, prefix='au', rebuild=False):

        sf = shapefile.Reader(shp)
        header = [field[0] for field in sf.fields][1:]

        """
        Field name: the name describing the data at this column index.
        Field type: the type of data at this column index. Types can be: Character, Numbers, Longs, Dates, or Memo.
        Field length: the length of the data found at this column index.
        Decimal length: the number of decimal places found in Number fields.
        """
#        shapes = sf.shapes()
#        print(len(shapes))
#        records = sf.records()
#        print(len(records))

        gwc = RasterDatasetInterpolator('/geodata/weppcloud_runs/au/gwc_dnbr_barc4_utm.tif')
        # gwc2 = RasterDatasetInterpolator('gwc_sbs2.tif')
        # gwc6 = RasterDatasetInterpolator('gwc_sbs6.tif')

        fp_hill = open('%s_hill_summary.csv' % prefix, 'w')
        csv_wtr = csv.DictWriter(fp_hill, fieldnames=('huc', 'topaz_id', 'wepp_id',
                                                      'length', 'width', 'area',
                                                      'slope',
                                                      'centroid_lng',
                                                      'centroid_lat',
                                                      'landuse',
                                                      'soil_texture',
                                                      'sbs',
                                                      'ash_wind_transport',
                                                      'ash_water_transport',
                                                      'ash_transport'))
        csv_wtr.writeheader()

        fails = 0
        for i, shape in enumerate(sf.iterShapes()):
            record = {k: v for k, v in zip(header, sf.record(i))}
            # print(record)
            huc12 = str(record['ID'])
            print(huc12)

            if huc12 in blacklist:
                print('in blacklist, skipping', huc12)
                continue

            bbox = shape.bbox
            _y = haversine((bbox[0], bbox[1]), (bbox[0], bbox[3])) * 1000
            _x = haversine((bbox[0], bbox[1]), (bbox[2], bbox[1])) * 1000

            sqm2 = _y * _x
            if sqm2 < 30 * 30 * 4:
                print('too small, skipping', huc12)
                continue

            wd = _join('/geodata/weppcloud_runs/', prefix, huc12)

            if _exists(wd):
                if _exists(_join(wd, 'dem', 'topaz', 'SUBWTA.ARC')):
                    print('already delineated, skipping', huc12)
                    continue

                shutil.rmtree(wd)
            os.mkdir(wd)

            print('initializing nodbs')
            ron = Ron(wd, "au-fire.cfg")
            #ron = Ron(wd, "au.cfg")

            # ron = Ron(wd, "0.cfg")
            ron.name = wd

            print('setting map')
            pad = max(abs(bbox[0] - bbox[2]), abs(bbox[1] - bbox[3])) * 0.4
            map_center = (bbox[0] + bbox[2]) / 2.0,  (bbox[1] + bbox[3]) / 2.0
            l, b, r, t = bbox
            bbox = [l - pad, b - pad, r + pad, t + pad]
            print('bbox', bbox)
            ron.set_map(bbox, map_center, zoom=13)

            print('fetching dem')
            ron.fetch_dem()

            print('setting topaz parameters')
            topaz = Topaz.getInstance(wd)

            print('building channels')
            topaz_pars = chn_routing_err_topaz_pars.get(huc12, dict(csa=10, mcl=200))
            topaz.build_channels(**topaz_pars)

            print('find raster indices')
            # print('"', topaz.utmproj4, '"')
            utm_proj = pyproj.Proj(topaz.utmproj4)
            wgs_proj = pyproj.Proj(wgs84_proj4)
            points = [pyproj.transform(wgs_proj, utm_proj, lng, lat) for lng, lat in shape.points]
            mask = build_mask(points, ron.dem_fn)
            # plt.figure()
            # plt.imshow(mask)
            # plt.colorbar()
            # plt.savefig(_join(topaz.topaz_wd, 'mask.png'))

            if huc12 in outlet_locs:
                out_lng, out_lat = outlet_locs[huc12]
                rdi = RasterDatasetInterpolator(ron.dem_fn)
                px, py = rdi.get_px_coord_from_lnglat(out_lng, out_lat)
                print('px, py', px, py)
                dem, transform, proj = read_raster(ron.dem_fn)
                min_elev = dem[px, py]

            else:
                print('loading channel map')
                channels, _, _ = read_raster(topaz.netful_arc)
                mask[np.where(channels == 0)] = 1

                plt.figure()
                plt.imshow(mask)
                plt.colorbar()
                plt.savefig(_join(topaz.topaz_wd, 'mask.png'))
                plt.close()

                print('finding lowest point in HUC')
                dem, transform, proj = read_raster(ron.dem_fn)
                print(mask.shape, dem.shape)
                print(np.sum(mask))
                demma = ma.masked_array(dem, mask=mask)
                plt.figure()
                plt.imshow(demma)
                plt.colorbar()
                plt.savefig(_join(topaz.topaz_wd, 'demma.png'))
                plt.close()

                min_elev = np.min(demma)
                px, py = np.unravel_index(np.argmin(demma), demma.shape)
                px = int(px)
                py = int(py)

            print(min_elev, px, py, px/dem.shape[0], py/dem.shape[1])

            print('building subcatchments')
            topaz.set_outlet(px, py, pixelcoords=True)
            try:
                topaz.build_subcatchments()
            except:
                fails += 1
                raise

            print('abstracting watershed')
            wat = Watershed.getInstance(wd)
            wat.abstract_watershed(cell_width=None)
            translator = wat.translator_factory()
            topaz_ids = [top.split('_')[1] for top in translator.iter_sub_ids()]

            # is_gwc2 = is_gwc6 = False

            for topaz_id, hill_summary in wat.sub_iter():
                print(topaz_id)
                _wat = hill_summary.as_dict()
                # _landuse = landuse_summaries[str(topaz_id)]
                # _soils = soils_summaries[str(topaz_id)]

                _centroid_lng, _centroid_lat = _wat['centroid']

                # try:
                #     _sbs2 = gwc2.get_location_info(_centroid_lng, _centroid_lat, method='near')
                #     if _sbs2 < 0:
                #         _sbs2 = None
                # except RDIOutOfBoundsException:
                #     _sbs2 = None
                #
                # try:
                #     _sbs6 = gwc6.get_location_info(_centroid_lng, _centroid_lat, method='near')
                #     if _sbs6 < 0:
                #         _sbs6 = None
                # except RDIOutOfBoundsException:
                #     _sbs6 = None
                #
                # if _sbs2 is None and _sbs6 is None:
                #     _sbs = 0
                #
                # elif _sbs2 is not None:
                #     _sbs = _sbs2
                #     is_gwc2 = True
                #
                # else:
                #     _sbs = _sbs6
                #     is_gwc6 = True

                # _d = dict(huc=huc12, topaz_id=int(topaz_id), wepp_id=_wat['wepp_id'],
                #           length=_wat['length'], width=_wat['width'], area=_wat['area'],
                #           slope=_wat['slope_scalar'],
                #           centroid_lng=_centroid_lng,
                #           centroid_lat=_centroid_lat,
                #           landuse=_landuse['key'],
                #           soil_texture=_soils['simple_texture'],
                #           sbs=_sbs)
                # csv_wtr.writerow(_d)

            # if not is_gwc2 and not is_gwc6:
            #     continue

            baer = Baer.getInstance(wd)
            # if is_gwc2:
            #     shutil.copyfile('gwc_sbs2.tif', _join(baer.baer_dir, 'gwc_sbs2.tif'))
            #     baer.validate('gwc_sbs2.tif')
            # if is_gwc6:
            #     shutil.copyfile('gwc_sbs6.tif', _join(baer.baer_dir, 'gwc_sbs6.tif'))
            #     baer.validate('gwc_sbs6.tif')

            shutil.copyfile('/geodata/weppcloud_runs/au/gwc_dnbr_barc4_utm.tif',
                       _join(baer.baer_dir, 'gwc_dnbr_barc4_utm.tif'))
            baer.validate('gwc_dnbr_barc4_utm.tif')

            print('building landuse')
            landuse = Landuse.getInstance(wd)
            landuse.mode = LanduseMode.Gridded
            landuse.build()
            landuse = Landuse.getInstance(wd)
            landuse_summaries = landuse.subs_summary

            print('building soils')
            soils = Soils.getInstance(wd)
            soils.mode = SoilsMode.Gridded
            soils.build()
            soils_summaries = soils.subs_summary

            print('building climate')
            climate = Climate.getInstance(wd)
            stations = climate.find_au_heuristic_stations()
            climate.input_years = 100
            climate.climatestation = stations[0]['id']
            climate.climate_spatialmode = ClimateSpatialMode.Single
            climate.build(verbose=True)

            print('prepping wepp')
            wepp = Wepp.getInstance(wd)
            wepp.prep_hillslopes()

            print('running hillslopes')
            wepp.run_hillslopes()

            print('prepping watershed')
            wepp = Wepp.getInstance(wd)
            wepp.prep_watershed()

            print('running watershed')
            wepp.run_watershed()

            print('generating loss report')
            loss_report = wepp.report_loss()

            print('generating totalwatsed report')
            fn = _join(ron.export_dir, 'totalwatsed.csv')

            totwatsed = TotalWatSed(_join(ron.output_dir, 'totalwatsed.txt'),
                                    wepp.baseflow_opts, wepp.phosphorus_opts)
            totwatsed.export(fn)
            assert _exists(fn)

            ash = Ash.getInstance(wd)
            ash.run_ash(fire_date='8/4', ini_white_ash_depth_mm=16.5625, ini_black_ash_depth_mm=17.166666666666668)

            ashpost = AshPost.getInstance(wd)

            ash_summary = ashpost.summary_stats
            if ash_summary is not None:
                _recurrence = ash_summary['recurrence']
                _return_periods = ash_summary['return_periods']
                _annuals = ash_summary['annuals']
                _sev_annuals = ash_summary['sev_annuals']
                ash_out = ashpost.ash_out

                for topaz_id, hill_summary in wat.sub_iter():
                    print(topaz_id)
                    _wat = hill_summary.as_dict()
                    _landuse = landuse_summaries[str(topaz_id)]
                    _soils = soils_summaries[str(topaz_id)]
                    _centroid_lng, _centroid_lat = _wat['centroid']

                    _d = dict(huc=huc12, topaz_id=int(topaz_id), wepp_id=_wat['wepp_id'],
                              length=_wat['length'], width=_wat['width'], area=_wat['area'],
                              slope=_wat['slope_scalar'],
                              centroid_lng=_centroid_lng,
                              centroid_lat=_centroid_lat,
                              landuse=_landuse['key'],
                              soil_texture=_soils['simple_texture'],
                              ash_wind_transport=ash_out[str(topaz_id)]['wind_transport (kg/ha)'],
                              ash_water_transport=ash_out[str(topaz_id)]['water_transport (kg/ha)'],
                              ash_transport=ash_out[str(topaz_id)]['ash_transport (kg/ha)'])
                    csv_wtr.writerow(_d)

            print('exporting arcmap resources')
            arc_export(wd)

            print(fails, i+1)


if __name__ == "__main__":

    wbd = WatershedBoundaryDataset("gwc_subcatchments")

