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
        dict(wd='Watershed_1',
             extent=[-120.25497436523439, 39.072244930479926, -120.0146484375, 39.25857565711887],
             map_center=[-120.1348114013672, 39.165471994238374],
             map_zoom=12,
             outlet=[-120.09757304843217, 39.19773527084747],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(wd='Watershed_2',
             extent=[-120.25497436523439, 39.072244930479926, -120.0146484375, 39.25857565711887],
             map_center=[-120.1348114013672, 39.165471994238374],
             map_zoom=12,
             outlet=[-120.11460381632118, 39.18896973503106],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(wd='Watershed_3',
             extent=[-120.25497436523439, 39.072244930479926, -120.0146484375, 39.25857565711887],
             map_center=[-120.1348114013672, 39.165471994238374],
             map_zoom=12,
             outlet=[-120.12165282292143, 39.18644160172608],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(wd='Watershed_4',
             extent=[-120.20605087280275, 39.15083019711799, -120.08588790893556, 39.243953257043124],
             map_center=[-120.14596939086915, 39.19740715574304],
             map_zoom=13,
             outlet=[-120.12241504431637, 39.181379503672105],
             # outlet=[-120.1233, 39.1816],  # [-120.12241504431637, 39.181379503672105],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(wd='Watershed_5',
             extent=[-120.25222778320314, 39.102091011833686, -120.01190185546876, 39.28834275351453],
             map_center=[-120.13206481933595, 39.19527859633793],
             map_zoom=12,
             outlet=[-120.1402884859731, 39.175919130374645],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(wd='Watershed_6',
             extent=[-120.25222778320314, 39.102091011833686, -120.01190185546876, 39.28834275351453],
             map_center=[-120.13206481933595, 39.19527859633793],
             map_zoom=12,
             outlet=[-120.14460408169862, 39.17224134827233],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(wd='Watershed_7_Ward_10336676',
             extent=[-120.32329559326173, 38.99944220958143, -120.08296966552736, 39.18596539075659],
             map_center=[-120.20313262939455, 39.09276546806873],
             map_zoom=12,
             outlet=[-120.16243964836231, 39.13566898208961],
             landuse=None,
             cs=70, erod=0.000001,
             surf_runoff=0.004, lateral_flow=0.005, baseflow=0.006, sediment=1200.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(wd='Watershed_8',
             extent=[-120.29102325439453, 39.02451827974919, -120.11524200439455, 39.16094667321639],
             map_center=[-120.20313262939455, 39.09276546806873],
             map_zoom=12,
             outlet=[-120.16237493339143, 39.12864047715305],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(wd='Watershed_9_Blackwood_10336660',
             extent=[-120.32329559326173, 38.99944220958143, -120.08296966552736, 39.18596539075659],
             map_center=[-120.20313262939455, 39.09276546806873],
             map_zoom=12,
             outlet=[-120.16359931399549, 39.1067786663636],
             landuse=None,
             cs=10, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1000.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(wd='Watershed_10',
             extent=[-120.29102325439453, 39.02451827974919, -120.11524200439455, 39.16094667321639],
             map_center=[-120.20313262939455, 39.09276546806873],
             map_zoom=12,
             outlet=[-120.14140904093959, 39.07218260362715],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(wd='Watershed_11_General_10336645',
             extent=[-120.27626037597658, 38.91561302513129, -120.03593444824219, 39.102357437817595],
             map_center=[-120.15609741210939, 39.00904686141452],
             map_zoom=12,
             outlet=[-120.11945708143868, 39.0515611447876],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.002, lateral_flow=0.003, baseflow=0.004, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(wd='Watershed_12_Meeks',
             extent=[-120.23197174072267, 38.9348437659246, -120.05619049072267, 39.07144530820888],
             map_center=[-120.14408111572267, 39.003177506910475],
             map_zoom=12,
             outlet=[-120.12452021800915, 39.036407051851995],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(wd='Watershed_13',
             extent=[-120.23197174072267, 38.9348437659246, -120.05619049072267, 39.07144530820888],
             map_center=[-120.14408111572267, 39.003177506910475],
             map_zoom=12,
             outlet=[-120.11884807004954, 39.02163646138702],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(wd='Watershed_14',
             extent=[-120.23197174072267, 38.9348437659246, -120.05619049072267, 39.07144530820888],
             map_center=[-120.14408111572267, 39.003177506910475],
             map_zoom=12,
             outlet=[-120.12066635447759, 39.01951924517021],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(wd='Watershed_15',
             extent=[-120.15652656555177, 38.98636711600028, -120.09644508361818, 39.033052785617535],
             map_center=[-120.12648582458498, 39.00971380270266],
             map_zoom=14,
             outlet=[-120.10916060023823, 39.004865203316534],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(wd='Watershed_16',
             extent=[-120.23197174072267, 38.9348437659246, -120.05619049072267, 39.07144530820888],
             map_center=[-120.14408111572267, 39.003177506910475],
             map_zoom=12,
             outlet=[-120.10472536830764, 39.002638030718146],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(wd='Watershed_17',
             extent=[-120.23197174072267, 38.9348437659246, -120.05619049072267, 39.07144530820888],
             map_center=[-120.14408111572267, 39.003177506910475],
             map_zoom=12,
             outlet=[-120.10376442165887, 39.00072228304711],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(wd='Watershed_18',
             extent=[-120.22579193115236, 38.826603057341515, -119.98546600341798, 39.01358193815758],
             map_center=[-120.10562896728517, 38.92015408680781],
             map_zoom=12,
             outlet=[-120.10700793337516, 38.95312733140358],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(wd='Watershed_19',
             extent=[-120.22579193115236, 38.826603057341515, -119.98546600341798, 39.01358193815758],
             map_center=[-120.10562896728517, 38.92015408680781],
             map_zoom=12,
             outlet=[-120.09942499965612, 38.935371421937056],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(wd='Watershed_20',
             extent=[-120.14305114746095, 38.877536817489165, -120.02288818359376, 38.97102081360566],
             map_center=[-120.08296966552736, 38.924294213302424],
             map_zoom=13,
             outlet=[-120.07227563388808, 38.940891230590054],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
    ]

    scenarios = [
               dict(wd='SimFire.202008.kikrcs.chn_cs{cs}_fccsFuels_obs_cli',
                    landuse=None,
                    cfg='lt-fire'),
               dict(wd='SimFire.202008.kikrcs.chn_cs{cs}_landisFuels_obs_cli',
                    landuse=None,
                   cfg='lt-fire-future'),
               dict(wd='SimFire.202008.kikrcs.chn_cs{cs}_landisFuels_fut_cli_A2',
                    landuse=None,
                    cfg='lt-fire-future',
                    climate='future'),
               dict(wd='CurCond.202008.cl532.ki5krcs.chn_cs{cs}',
                    landuse=None,
                    lc_lookup_fn='ki5krcs.csv'),
               dict(wd='PrescFireS.202008.kikrcs.chn_cs{cs}',
                    landuse=[(not_shrub_selector, 110), (shrub_selector, 122)]),
               dict(wd='LowSevS.202008.kikrcs.chn_cs{cs}',
                    landuse=[(not_shrub_selector, 106), (shrub_selector, 121)]),
               dict(wd='ModSevS.202008.kikrcs.chn_cs{cs}',
                    landuse=[(not_shrub_selector, 118), (shrub_selector, 120)]),
               dict(wd='HighSevS.202008.kikrcs.chn_cs{cs}',
                    landuse=[(not_shrub_selector, 105), (shrub_selector, 119)]),
               dict(wd='Thinn96.202008.kikrcs.chn_cs{cs}',
                    landuse=[(not_shrub_selector, 123)]),
               dict(wd='Thinn93.202008.kikrcs.chn_cs{cs}',
                    landuse=[(not_shrub_selector, 115)]),
               dict(wd='Thinn85.202008.kikrcs.chn_cs{cs}',
                    landuse=[(not_shrub_selector, 117)]),
                ]

    projects = []

    wc = sys.argv[-1]
    if '.py' in wc:
        wc = None

    for scenario in scenarios:
        for watershed in watersheds:
            projects.append(deepcopy(watershed))
            projects[-1]['cfg'] = scenario.get('cfg', 'lt')
            projects[-1]['landuse'] = scenario['landuse']
            projects[-1]['lc_lookup_fn'] = scenario.get('lc_lookup_fn', 'landSoilLookup.csv')
            projects[-1]['climate'] = scenario.get('climate', 'observed')
            projects[-1]['wd'] = ('lt_%s_%s' % (watershed['wd'], scenario['wd'])).format(cs=watershed['cs'])

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

            if wc is not None:
                if not wc in wd:
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
            wat.abstract_watershed(cell_width=None)
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
                climate.input_years = 27
                climate.climatestation = stations[0]['id']

                climate.climate_mode = ClimateMode.Observed
                climate.climate_spatialmode = ClimateSpatialMode.Multiple
                climate.set_observed_pars(start_year=1990, end_year=2016)
            elif climate_mode == 'future':
                climate = Climate.getInstance(wd)
                stations = climate.find_closest_stations()
                climate.input_years = 27
                climate.climatestation = stations[0]['id']

                climate.climate_mode = ClimateMode.Future
                climate.climate_spatialmode = ClimateSpatialMode.Single
                climate.set_future_pars(start_year=2018, end_year=2018+27)
                #climate.set_orig_cli_fn(_join(climate._future_clis_wc, 'Ward_Creek_A2.cli'))
            elif climate_mode == 'vanilla':
                climate = Climate.getInstance(wd)
                stations = climate.find_closest_stations()
                climate.input_years = 30
                climate.climatestation = stations[0]['id']

                climate.climate_mode = ClimateMode.Vanilla
                climate.climate_spatialmode = ClimateSpatialMode.Single
                #climate.set_orig_cli_fn(_join(climate._future_clis_wc, 'Ward_Creek_A2.cli'))
            else:
                raise Exception("Unknown climate_mode")

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
