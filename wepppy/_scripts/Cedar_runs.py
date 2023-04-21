# 04/21/2023
import os
import sys

from copy import deepcopy

import shutil
from os.path import exists as _exists
from pprint import pprint
from time import time
from time import sleep
from datetime import datetime

import wepppy
from wepppy.nodb import (
    Ron, Topaz, Watershed, Landuse, Soils, Climate, Wepp, SoilsMode, ClimateMode, ClimateSpatialMode, LanduseMode
)
from wepppy.nodb.mods.locations import LakeTahoe

from os.path import join as _join
from wepppy.nodb.mods.locations.lt.selectors import *
from wepppy.wepp.out import TotalWatSed
from wepppy.export import arc_export

from osgeo import gdal, osr
gdal.UseExceptions()

wd = None


def log_print(msg):
    global wd

    now = datetime.now()
    print('[{now}] {wd}: {msg}'.format(now=now, wd=wd, msg=msg))


if __name__ == '__main__':

    os.chdir('/geodata/weppcloud_runs/')

    watersheds = [
        dict(watershed='1_UpperCedar_xtr',  # https://wepp.cloud/weppcloud/runs/mdobre-fantastic-mold/seattle-snow/
             extent=[-121.63453841993181, 47.35650394734622, -121.59114402470502, 47.38589262290145],
             map_center=[-121.61284122231841, 47.37120033220608],
             map_zoom=14,
             outlet=[-121.62308696441698, 47.36793659945937],
             landuse=None,
             csa=5, mcl = 60,
             cs=xxx, erod=0.000001,
             surf_runoff=0.004, lateral_flow=0.005, baseflow=0.006, sediment=1200.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),

        dict(watershed='2_GreenPointCreek',  # https://wepp.cloud/weppcloud/runs/mdobre-dynamic-forwarding/seattle-snow/
             extent=[-121.70139312744142, 47.37539527495085, -121.64002418518068, 47.416937456635445],
             map_center=[-121.67070865631105, 47.39617045965992],
             map_zoom=14,
             outlet=[-121.67706729648484, 47.38777491609873],
             landuse=None,
             cs=xxx, erod=0.000001,
             surf_runoff=0.004, lateral_flow=0.005, baseflow=0.006, sediment=1200.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
             
        dict(watershed='3_OtterCreek',  # https://wepp.cloud/weppcloud/runs/mdobre-agoraphobic-groundhog/seattle-snow/
             extent=[-121.72353744506837, 47.38568219399679, -121.66216850280763, 47.42721626822998],
             map_center=[-121.69285297393799, 47.40645332485671],
             map_zoom=14,
             outlet=[-121.7010412712851, 47.40375120707198],
             landuse=None,
             cs=xxx, erod=0.000001,
             surf_runoff=0.004, lateral_flow=0.005, baseflow=0.006, sediment=1200.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
             
        dict(watershed='4_DamburatCreek',  # https://dev.wepp.cloud/weppcloud/runs/mdobre-glaucous-highbrow/seattle-snow/#climate-options
             extent=[-121.73563957214357, 47.394979376658505, -121.67427062988283, 47.436506122332865],
             map_center=[-121.7049551010132, 47.41574684312695],
             map_zoom=14,
             outlet=[-121.71642018687456, 47.4090264976976],
             landuse=None,
             cs=xxx, erod=0.000001,
             surf_runoff=0.004, lateral_flow=0.005, baseflow=0.006, sediment=1200.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
                          
        dict(watershed='SteeleCreek',  # https://dev.wepp.cloud/weppcloud/runs/mdobre-dun-colored-thumbnail/seattle-snow/ 
             extent=[-121.85527326670098, 47.39702726773113, -121.76848447624735, 47.455743079989006],
             map_center=[-121.81187887147415, 47.42639336086452],
             map_zoom=13,
             outlet=[-121.8196462708747, 47.411647646852316],
             landuse=None,
             cs=xxx, erod=0.000001,
             surf_runoff=0.004, lateral_flow=0.005, baseflow=0.006, sediment=1200.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
                          
        dict(watershed='TaylorCreek',  # https://dev.wepp.cloud/weppcloud/runs/mdobre-incidental-exhibitor/seattle-snow/
             extent=[-121.93038940429689, 47.27946192115735, -121.68491363525392, 47.44573629035491],
             map_center=[-121.80765151977539, 47.3626646139612],
             map_zoom=12,
             outlet=[-121.84810259063217, 47.38690390950939],
             landuse=None,
             cs=xxx, erod=0.000001,
             surf_runoff=0.004, lateral_flow=0.005, baseflow=0.006, sediment=1200.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
                          
        dict(watershed='RackCreek',  # https://dev.wepp.cloud/weppcloud/runs/mdobre-macroscopic-mule/seattle-snow/
             extent=[-121.81873700666384, 47.319323353341154, -121.64515942575657, 47.43686262163456],
             map_center=[-121.73194821621021, 47.378125740135424],
             map_zoom=12,
             outlet=[-121.72235036496633, 47.39182498187038],
             landuse=None,
             cs=xxx, erod=0.000001,
             surf_runoff=0.004, lateral_flow=0.005, baseflow=0.006, sediment=1200.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
                          
        dict(watershed='ShotgunCreek',  # https://dev.wepp.cloud/weppcloud/runs/mdobre-allopathic-laird/seattle-snow/
             extent=[-121.81024020200407, 47.3125753955728, -121.63666262109679, 47.43012968899888],
             map_center=[-121.72345141155041, 47.37138529557367],
             map_zoom=12,
             outlet=[-121.70761572206875, 47.380969758293595],
             landuse=None,
             cs=xxx, erod=0.000001,
             surf_runoff=0.004, lateral_flow=0.005, baseflow=0.006, sediment=1200.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
                          
        dict(watershed='BoulderCreek',  # https://dev.wepp.cloud/weppcloud/runs/mdobre-nuclear-monument/seattle-snow/
             extent=[-121.78887680743084, 47.28870375392173, -121.61529922652359, 47.406311187359705],
             map_center=[-121.70208801697721, 47.34754022617904],
             map_zoom=12,
             outlet=[-121.69605779736114, 47.36507371353041],
             landuse=None,
             cs=xxx, erod=0.000001,
             surf_runoff=0.004, lateral_flow=0.005, baseflow=0.006, sediment=1200.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
                          
        dict(watershed='Rex',  # https://dev.wepp.cloud/weppcloud/runs/mdobre-idealized-boredom/seattle-snow/
             extent=[-121.77658081054689, 47.25430078914495, -121.53110504150392, 47.42065432071321],
             map_center=[-121.6538429260254, 47.33754306785725],
             map_zoom=12,
             outlet=[-121.66379704464829, 47.35082660159635],
             landuse=None,
             cs=xxx, erod=0.000001,
             surf_runoff=0.004, lateral_flow=0.005, baseflow=0.006, sediment=1200.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
                          
        dict(watershed='WalshLake',  # https://dev.wepp.cloud/weppcloud/runs/mdobre-circumpolar-thunderclap/seattle-snow/
             extent=[-121.96925183206595, 47.35222786660658, -121.79567425115869, 47.469693845801274],
             map_center=[-121.88246304161231, 47.410993605703396],
             map_zoom=12,
             outlet=[-121.92447280149537, 47.40126033793729],
             landuse=None,
             cs=xxx, erod=0.000001,
             surf_runoff=0.004, lateral_flow=0.005, baseflow=0.006, sediment=1200.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
                          
        dict(watershed='RockCreek',  # https://dev.wepp.cloud/weppcloud/runs/mdobre-deafened-tantalum/seattle-snow/
             extent=[-121.95133209228517, 47.37649961666246, -121.82859420776367, 47.45954949060109],
             map_center=[-121.88996315002443, 47.418040928043936],
             map_zoom=13,
             outlet=[-121.9015742124714, 47.40239293772682],
             landuse=None,
             cs=xxx, erod=0.000001,
             surf_runoff=0.004, lateral_flow=0.005, baseflow=0.006, sediment=1200.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
                          
        dict(watershed='UpperCedar',  # https://dev.wepp.cloud/weppcloud/runs/mdobre-inattentive-iconography/seattle-snow/
             extent=[-121.66568756103517, 47.24730946320093, -121.4202117919922, 47.413684985326825],
             map_center=[-121.54294967651369, 47.3305627384955],
             map_zoom=12,
             outlet=[-121.62248883359838, 47.362422391792755],
             landuse=None,
             cs=xxx, erod=0.000001,
             surf_runoff=0.004, lateral_flow=0.005, baseflow=0.006, sediment=1200.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
                          
        dict(watershed='LowerCedarEast',  # https://dev.wepp.cloud/weppcloud/runs/mdobre-kiln-dried-exponential/seattle-snow/
             extent=[-121.88913910241645, 47.33725885529981, -121.71556152150916, 47.45475818016082],
             map_center=[-121.8023503119628, 47.396041268667254],
             map_zoom=12,
             outlet=[-121.84627671566402, 47.39467807072394],
             landuse=None,
             cs=xxx, erod=0.000001,
             surf_runoff=0.004, lateral_flow=0.005, baseflow=0.006, sediment=1200.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
             
        dict(watershed='Name',  #
             extent=[-121.88913910241645, 47.33725885529981, -121.71556152150916, 47.45475818016082],
             map_center=[-121.8023503119628, 47.396041268667254],
             map_zoom=12,
             outlet=[-121.84627671566402, 47.39467807072394],
             landuse=None,
             cs=xxx, erod=0.000001,
             surf_runoff=0.004, lateral_flow=0.005, baseflow=0.006, sediment=1200.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(watershed='Name',  #
             extent=[-121.88913910241645, 47.33725885529981, -121.71556152150916, 47.45475818016082],
             map_center=[-121.8023503119628, 47.396041268667254],
             map_zoom=12,
             outlet=[-121.84627671566402, 47.39467807072394],
             landuse=None,
             cs=xxx, erod=0.000001,
             surf_runoff=0.004, lateral_flow=0.005, baseflow=0.006, sediment=1200.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(watershed='Name',  #
             extent=[-121.88913910241645, 47.33725885529981, -121.71556152150916, 47.45475818016082],
             map_center=[-121.8023503119628, 47.396041268667254],
             map_zoom=12,
             outlet=[-121.84627671566402, 47.39467807072394],
             landuse=None,
             cs=xxx, erod=0.000001,
             surf_runoff=0.004, lateral_flow=0.005, baseflow=0.006, sediment=1200.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(watershed='Name',  # 
             extent=[-121.88913910241645, 47.33725885529981, -121.71556152150916, 47.45475818016082],
             map_center=[-121.8023503119628, 47.396041268667254],
             map_zoom=12,
             outlet=[-121.84627671566402, 47.39467807072394],
             landuse=None,
             cs=xxx, erod=0.000001,
             surf_runoff=0.004, lateral_flow=0.005, baseflow=0.006, sediment=1200.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
             
    ]

    scenarios = [
               dict(scenario='CurCond',
                    landuse=None,
                    lc_lookup_fn='ki5krcs.csv'),
               dict(scenario='SBS',
                    landuse=None,
                    lc_lookup_fn='ki5krcs.csv',
                    cfg='lt-fire-snow-caldor')
    ]

    skip_completed = True

    projects = []

    wc = sys.argv[-1]
    if '.py' in wc:
        wc = None

    for scenario in scenarios:
        for watershed in watersheds:
            projects.append(deepcopy(watershed))
            projects[-1]['cfg'] = scenario.get('cfg', 'lt-wepp_bd16b69-snow')
            projects[-1]['landuse'] = scenario['landuse']
            projects[-1]['lc_lookup_fn'] = scenario.get('lc_lookup_fn', 'landSoilLookup.csv')
            projects[-1]['climate'] = scenario.get('climate', 'observed')
            projects[-1]['scenario'] = scenario['scenario']
            projects[-1]['wd'] = 'lt_Caldor_%s_%s' % (watershed['watershed'], scenario['scenario'])

    failed = open('failed', 'w')
    for proj in projects:
        try:
            wd = proj['wd']
            extent = proj['extent']
            map_center = proj['map_center']
            map_zoom = proj['map_zoom']
            outlet = proj['outlet']
            default_landuse = proj['landuse']
            cfg = proj['cfg']
            climate_mode = proj['climate']
            lc_lookup_fn = proj['lc_lookup_fn']

            watershed = proj['watershed']
            scenario = proj['scenario']

            if wc is not None:
                if not wc in wd:
                    continue

            if skip_completed:
                if _exists(_join(wd, 'export', 'arcmap', 'channels.shp')):
                    log_print('has channels.shp... skipping.')
                    continue

            log_print('cleaning dir')
            if _exists(wd):
                print()
                shutil.rmtree(wd)
            os.mkdir(wd)

            log_print('initializing project')
            ron = Ron(wd, "%s.cfg" % cfg)
            ron.name = wd
            ron.set_map(extent, map_center, zoom=map_zoom)

            log_print('fetching dem')
            ron.fetch_dem()

            log_print('building channels')
            wat = Watershed.getInstance(wd)
            wat.build_channels(csa=5, mcl=60)
            wat.set_outlet(*outlet)
            sleep(0.5)

            log_print('building subcatchments')
            wat.build_subcatchments()

            log_print('abstracting watershed')
            wat = Watershed.getInstance(wd)
            wat.abstract_watershed()
            translator = wat.translator_factory()
            topaz_ids = [top.split('_')[1] for top in translator.iter_sub_ids()]

            log_print('building landuse')
            landuse = Landuse.getInstance(wd)
            landuse.mode = LanduseMode.Gridded
            landuse.build()
            landuse = Landuse.getInstance(wd)

            # 105 - Tahoe High severity fire
            # topaz_ids is a list of string ids e.g. ['22', '23']
            if default_landuse is not None:
                log_print('setting default landuse')

                tops = []

                for selector, dom in default_landuse:
                    _topaz_ids = selector(landuse, None)
                    bare_tops = bare_or_sodgrass_or_bunchgrass_selector(landuse, None)
                    _topaz_ids = [top for top in _topaz_ids if top not in bare_tops]

                    landuse.modify(_topaz_ids, dom)
                    tops.extend(_topaz_ids)

            log_print('building soils')
            if _exists(_join(wd, 'lt.nodb')):
                lt = LakeTahoe.getInstance(wd)
                lt.lc_lookup_fn = lc_lookup_fn

            soils = Soils.getInstance(wd)
            soils.mode = SoilsMode.Gridded
            soils.build()

            log_print('building climate')

            if climate_mode == 'observed':
                climate = Climate.getInstance(wd)
                stations = climate.find_closest_stations()
                climate.input_years = 30
                climate.climatestation = stations[0]['id']

                climate.climate_mode = ClimateMode.Observed
                climate.climate_spatialmode = ClimateSpatialMode.Multiple
                climate.set_observed_pars(start_year=1990, end_year=2019)
            elif climate_mode == 'future':
                climate = Climate.getInstance(wd)
                stations = climate.find_closest_stations()
                climate.input_years = 30
                climate.climatestation = stations[0]['id']

                climate.climate_mode = ClimateMode.Future
                climate.climate_spatialmode = ClimateSpatialMode.Single
                climate.set_future_pars(start_year=2018, end_year=2018 + 30)
                # climate.set_orig_cli_fn(_join(climate._future_clis_wc, 'Ward_Creek_A2.cli'))
            elif climate_mode == 'vanilla':
                climate = Climate.getInstance(wd)
                stations = climate.find_closest_stations()
                climate.input_years = 30
                climate.climatestation = stations[0]['id']

                climate.climate_mode = ClimateMode.Vanilla
                climate.climate_spatialmode = ClimateSpatialMode.Single
                # climate.set_orig_cli_fn(_join(climate._future_clis_wc, 'Ward_Creek_A2.cli'))
            elif 'copy' in climate_mode:
                src_wd = 'lt_Caldor_%s_%s' % (watershed, climate_mode[4:])
                shutil.rmtree(_join(wd, 'climate'))
                shutil.copytree(_join(src_wd, 'climate'), _join(wd, 'climate'))
                with open(_join(src_wd, 'climate.nodb')) as fp:
                    contents = fp.read()

                with open(_join(wd, 'climate.nodb'), 'w') as fp:
                    fp.write(contents.replace(src_wd, wd))

            else:
                raise Exception("Unknown climate_mode")
                
            if 'copy' not in climate_mode:
                climate.build(verbose=1)

            log_print('prepping wepp')
            wepp = Wepp.getInstance(wd)
            wepp.parse_inputs(proj)

            wepp.prep_hillslopes()

            log_print('running hillslopes')
            wepp.run_hillslopes()

            log_print('prepping watershed')
            wepp = Wepp.getInstance(wd)
            wepp.prep_watershed(erodibility=proj['erod'], critical_shear=proj['cs'])
            wepp._prep_pmet(mid_season_crop_coeff=proj['mid_season_crop_coeff'], p_coeff=proj['p_coeff'])

            log_print('running watershed')
            wepp.run_watershed()

            log_print('generating loss report')
            loss_report = wepp.report_loss()

            log_print('generating totalwatsed report')
            fn = _join(ron.export_dir, 'totalwatsed.csv')

            totwatsed = TotalWatSed(_join(ron.output_dir, 'totalwatsed.txt'),
                                    wepp.baseflow_opts, wepp.phosphorus_opts)
            totwatsed.export(fn)
            assert _exists(fn)

            log_print('exporting arcmap resources')
            arc_export(wd)
        except:
            failed.write('%s\n' % wd)
            raise
