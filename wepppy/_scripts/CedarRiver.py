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
from wepppy.export import arc_export

from osgeo import gdal, osr
gdal.UseExceptions()

if __name__ == '__main__':
    projects = [dict(wd='Cedar_River',
                     extent=[-121.77108764648439, 47.163108130899104, -121.29043579101564, 47.4889049944156],
                     map_center = [-121.49574279785158, 47.277365616965646],
                     map_zoom = 11,
                     outlet = [-121.62271296763015, 47.36246108025578],
                     landuse=None,
                     cs=100, erod=0.000001),
                dict(wd='Tolt_NorthFork',
                     extent=[-121.90086364746095, 47.56216409801383, -121.4202117919922, 47.88549944643875],
                     map_center=[-121.66053771972658, 47.72408264363561],
                     map_zoom=11,
                     outlet=[-121.78852559978455, 47.71242486609417],
                     landuse=None,
                     cs=100, erod=0.000001),
                dict(wd='Taylor_Creek',
                     extent=[-121.8981170654297, 47.26199018174824, -121.65779113769533, 47.424835479167825],
                     map_center=[-121.77795410156251, 47.34347562236255],
                     map_zoom=11,
                     outlet=[-121.84644704748708, 47.386266378562375],
                     landuse=None,
                     cs=100, erod=0.000001)
                 ]
    for proj in projects:
        wd = proj['wd']
        extent = proj['extent']
        map_center = proj['map_center']
        map_zoom = proj['map_zoom']
        outlet = proj['outlet']
        default_landuse = proj['landuse']

        if _exists(wd):
            print()
            shutil.rmtree(wd)
        os.mkdir(wd)

        #ron = Ron(wd, "lt-fire.cfg")
        #ron = Ron(wd, "lt.cfg")
        ron = Ron(wd, "0.cfg")
        ron.name = wd
        ron.set_map(extent, map_center, zoom=map_zoom)
        ron.fetch_dem()

        topaz = Topaz.getInstance(wd)
        topaz.build_channels(csa=10, mcl=100)
        topaz.set_outlet(*outlet)
        sleep(0.5)
        topaz.build_subcatchments()

        wat = Watershed.getInstance(wd)
        wat.abstract_watershed()
        translator = wat.translator_factory()
        topaz_ids = [top.split('_')[1] for top in translator.iter_sub_ids()]
        print('topaz_ids:', topaz_ids)

        landuse = Landuse.getInstance(wd)
        landuse.mode = LanduseMode.Gridded
        landuse.build()
        landuse = Landuse.getInstance(wd)


        # 105 - Tahoe High severity fire
        # topaz_ids is a list of string ids e.g. ['22', '23']
        if default_landuse is not None:
            landuse.modify(topaz_ids, default_landuse)

        soils = Soils.getInstance(wd)
        soils.mode = SoilsMode.Gridded
        soils.build()



        climate = Climate.getInstance(wd)
        stations = climate.find_closest_stations()
        climate.input_years = 27
        climate.climatestation = stations[0]['id']

        climate.climate_mode = ClimateMode.Observed
        climate.climate_spatialmode = ClimateSpatialMode.Multiple
        climate.set_observed_pars(start_year=1990, end_year=2016)

        climate.build(verbose=1)

        wepp = Wepp.getInstance(wd)
        wepp.prep_hillslopes()
        wepp.run_hillslopes()

        wepp = Wepp.getInstance(wd)
        wepp.prep_watershed(erodibility=proj['erod'], critical_shear=proj['cs'])
        wepp.run_watershed()
        loss_report = wepp.report_loss()

        fn = _join(ron.export_dir, 'totalwatsed.csv')

        totwatsed = TotalWatSed(_join(ron.output_dir, 'totalwatsed.txt'),
                                wepp.baseflow_opts, wepp.phosphorus_opts)
        totwatsed.export(fn)
        assert _exists(fn)


        print(loss_report.out_tbl)

        arc_export(wd)
