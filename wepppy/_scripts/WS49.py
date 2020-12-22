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
        dict(watershed='49_Eagle_Creek',  # Watershed_18
             extent=[-120.22579193115236, 38.826603057341515, -119.98546600341798, 39.01358193815758],
             map_center=[-120.10562896728517, 38.92015408680781],
             map_zoom=12,
             outlet=[-120.10700793337516, 38.95312733140358],
             landuse=None,
             cs=45, erod=0.000001,
             surf_runoff=0.004, lateral_flow=0.005, baseflow=0.006, sediment=1300.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8)
    ]

    scenarios = [
               dict(scenario='SimFire.fccsFuels_obs_cli',
                    landuse=None,
                    lc_lookup_fn='ki5krcs.csv',
                    cfg='lt-fire-snow',
                    climate='copyCurCond'),
               dict(scenario='SimFire.landisFuels_obs_cli',
                    landuse=None,
                    lc_lookup_fn='ki5krcs.csv',
                    cfg='lt-fire-future-snow',
                    climate='copyCurCond'),
               dict(scenario='SimFire.landisFuels_fut_cli_A2',
                    landuse=None,
                    lc_lookup_fn='ki5krcs.csv',
                    cfg='lt-fire-future-snow',
                    climate='future'),
               dict(scenario='CurCond',
                    landuse=None,
                    lc_lookup_fn='ki5krcs.csv'),
               dict(scenario='PrescFire',
                    landuse=[(not_shrub_selector, 110), (shrub_selector, 122)],
                    lc_lookup_fn='ki5krcs.csv',
                    climate='copyCurCond'),
               dict(scenario='LowSev',
                    landuse=[(not_shrub_selector, 106), (shrub_selector, 121)],
                    lc_lookup_fn='ki5krcs.csv',
                    climate='copyCurCond'),
               dict(scenario='ModSev',
                    landuse=[(not_shrub_selector, 118), (shrub_selector, 120)],
                    lc_lookup_fn='ki5krcs.csv',
                    climate='copyCurCond'),
               dict(scenario='HighSev',
                    landuse=[(not_shrub_selector, 105), (shrub_selector, 119)],
                    lc_lookup_fn='ki5krcs.csv',
                    climate='copyCurCond'),
               dict(scenario='Thinn96',
                    landuse=[(not_shrub_selector, 123)],
                    lc_lookup_fn='ki5krcs.csv',
                    climate='copyCurCond'),
               dict(scenario='Thinn93',
                    landuse=[(not_shrub_selector, 115)],
                    lc_lookup_fn='ki5krcs.csv',
                    climate='copyCurCond'),
               dict(scenario='Thinn85',
                    landuse=[(not_shrub_selector, 117)],
                    lc_lookup_fn='ki5krcs.csv',
                    climate='copyCurCond'),  # <- EXAMPLE FOR COPYING CLIMATE
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
            projects[-1]['wd'] = 'lt_202012_%s_%s' % (watershed['watershed'], scenario['scenario'])

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
            topaz = Topaz.getInstance(wd)
            topaz.build_channels(csa=5, mcl=60)
            topaz.set_outlet(*outlet)
            sleep(0.5)

            log_print('building subcatchments')
            topaz.build_subcatchments()

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
                src_wd = 'lt_202010_%s_%s' % (watershed, climate_mode[4:])
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
