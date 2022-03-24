import os
import shutil
from os.path import exists as _exists
from pprint import pprint
from time import time
from time import sleep

import wepppy
from wepppy.nodb import *
from os.path import join as _join
from wepppy.wepp.out import TotalWatSed

from osgeo import gdal, osr
gdal.UseExceptions()

if __name__ == '__main__':
    projects = [
                dict(wd='Test_Watershed_15',
                     extent=[-120.15652656555177, 38.98636711600028, -120.09644508361818, 39.033052785617535],
                     map_center=[-120.12648582458498, 39.00971380270266],
                     map_zoom=14,
                     outlet=[-120.10916060023823, 39.004865203316534],
                     landuse=None,
                     cs=50, erod=0.000001, chn_chn_wepp_width=1.0),
                 ]
    for proj in projects:
        wd = proj['wd']
        extent = proj['extent']
        map_center = proj['map_center']
        map_zoom = proj['map_zoom']
        outlet = proj['outlet']
        default_landuse = proj['landuse']

        if _exists(wd):
            shutil.rmtree(wd)
            
        print('making directory')
        os.mkdir(wd)

        print('initializing project')
        ron = Ron(wd, "disturbed.cfg")
        ron.name = wd
        ron.set_map(extent, map_center, zoom=map_zoom)
        
        print('fetching dem')
        ron.fetch_dem()

        print('building channels')
        wat = Watershed.getInstance(wd)
        wat.build_channels(csa=5, mcl=60)
        
        print('setting outlet')
        wat.set_outlet(*outlet)
        
        print('building subcatchments')
        wat.build_subcatchments()

        print('abstracting watershed')
        wat.abstract_watershed()
        translator = wat.translator_factory()
        topaz_ids = [top.split('_')[1] for top in translator.iter_sub_ids()]

        print('building landuse')
        landuse = Landuse.getInstance(wd)
        landuse.mode = LanduseMode.Gridded
        landuse.build()
        landuse = Landuse.getInstance(wd)

        print('building soils')
        soils = Soils.getInstance(wd)
        soils.mode = SoilsMode.Gridded
        soils.build()

        print('building climate')
        climate = Climate.getInstance(wd)
        stations = climate.find_closest_stations()
        climate.climatestation = stations[0]['id']

        climate.climate_mode = ClimateMode.Vanilla
        climate.climate_spatialmode = ClimateSpatialMode.Single

        climate.build(verbose=1)

        print('running wepp')
        wepp = Wepp.getInstance(wd)
        wepp.prep_hillslopes()
        wepp.run_hillslopes()

        wepp = Wepp.getInstance(wd)
        wepp.prep_watershed(erodibility=proj['erod'], critical_shear=proj['cs'])
        wepp.run_watershed()
       
        print('running post wepp processing')
        loss_report = wepp.report_loss()

        fn = _join(ron.export_dir, 'totalwatsed.csv')

        totwatsed = TotalWatSed(_join(ron.output_dir, 'totalwatsed.txt'),
                                wepp.baseflow_opts, wepp.phosphorus_opts)
        totwatsed.export(fn)
        assert _exists(fn)

        print(loss_report.out_tbl)
