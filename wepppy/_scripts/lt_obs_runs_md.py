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
        dict(wd='Watershed_11_General',
             extent=[-120.23197174072267, 38.9348437659246, -120.05619049072267, 39.07144530820888],
             map_center=[-120.14408111572267, 39.003177506910475],
             map_zoom=12,
             outlet=[-120.12006459240162, 39.05139598278608],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(wd='Blackwood_BC1_10336660', # 2900 ha
             extent=[-120.32329559326173, 38.99944220958143, -120.08296966552736, 39.18596539075659],
             map_center=[-120.20313262939455, 39.09276546806873],
             map_zoom=12,
             outlet=[-120.16359931399549, 39.1067786663636],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(wd='Ward_WC8_10336676', # 2500 ha
             extent=[-120.32329559326173, 38.99944220958143, -120.08296966552736, 39.18596539075659],
             map_center=[-120.20313262939455, 39.09276546806873],
             map_zoom=12,
             outlet=[-120.16243964836231, 39.13566898208961],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(wd='Ward_WC3A_10336674', # 1200 ha
             extent=[-120.32329559326173, 38.99944220958143, -120.08296966552736, 39.18596539075659],
             map_center=[-120.20313262939455, 39.09276546806873],
             map_zoom=12,
             outlet=[-120.21151127568125, 39.140908230609],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(wd='Ward_WC7A_10336675', # 2300 ha
             extent=[-120.32329559326173, 38.99944220958143, -120.08296966552736, 39.18596539075659],
             map_center=[-120.20313262939455, 39.09276546806873],
             map_zoom=12,
             outlet=[-120.18012105488953, 39.13609842384552],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(wd='General_GC1_10336645', # 1900 ha
             extent=[-120.27626037597658, 38.91561302513129, -120.03593444824219, 39.102357437817595],
             map_center=[-120.15609741210939, 39.00904686141452],
             map_zoom=12,
             outlet=[-120.11945708143868, 39.0515611447876],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(wd='Third_TH1_10336698', # 1600 ha
             extent=[-120.04760742187501, 39.16839998800286, -119.80728149414064, 39.35447606884594],
             map_center=[-119.92744445800783, 39.261499771230774],
             map_zoom=12,
             outlet=[-119.94713185797971, 39.239460705991355],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(wd='Incline_IN1_10336700', # 1700 ha
             extent=[-120.04760742187501, 39.16839998800286, -119.80728149414064, 39.35447606884594],
             map_center=[-119.92744445800783, 39.261499771230774],
             map_zoom=12,
             outlet=[-119.94500218172628, 39.2404858227834],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(wd='Incline_IN2_103366995', # 1100 ha
             extent=[-120.04760742187501, 39.16839998800286, -119.80728149414064, 39.35447606884594],
             map_center=[-119.92744445800783, 39.261499771230774],
             map_zoom=12,
             outlet=[-119.9363418106362, 39.247825177642596],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(wd='Incline_IN3_103366993', # 740 ha
             extent=[-120.04760742187501, 39.16839998800286, -119.80728149414064, 39.35447606884594],
             map_center=[-119.92744445800783, 39.261499771230774],
             map_zoom=12,
             outlet=[-119.92333603737366, 39.259102789262066],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(wd='Glenbrook_GL1_10336730', # 1100 ha
             extent=[-120.01396179199219, 39.019450429324046, -119.77363586425783, 39.20592074849823],
             map_center=[-119.89379882812501, 39.11274726579313],
             map_zoom=12,
             outlet=[-119.93952733643079, 39.08804461546371],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(wd='Logan_LH1_10336740', # 530 ha
             extent=[-120.01396179199219, 39.019450429324046, -119.77363586425783, 39.20592074849823],
             map_center=[-119.89379882812501, 39.11274726579313],
             map_zoom=12,
             outlet=[-119.93525510941215, 39.066581990025206],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(wd='Edgewood_ED1_10336765', # 1500 ha
             extent=[-120.06202697753908, 38.87045372777545, -119.8217010498047, 39.05731715424236],
             map_center=[-119.94186401367189, 38.963947050281696],
             map_zoom=12,
             outlet=[-119.9473174499335, 38.96815479608907],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(wd='Edgewood_ED3_103367585', # 810 ha
             extent=[-120.06202697753908, 38.87045372777545, -119.8217010498047, 39.05731715424236],
             map_center=[-119.94186401367189, 38.963947050281696],
             map_zoom=12,
             outlet=[-119.91621901571327, 38.966795890171],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(wd='EagleRock_ED5_103367592', # 170 ha
             extent=[-120.06202697753908, 38.87045372777545, -119.8217010498047, 39.05731715424236],
             map_center=[-119.94186401367189, 38.963947050281696],
             map_zoom=12,
             outlet=[-119.9286017453026, 38.96063649735145],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(wd='Edgewood_ED9_10336760', # 1500 ha
             extent=[-120.06202697753908, 38.87045372777545, -119.8217010498047, 39.05731715424236],
             map_center=[-119.94186401367189, 38.963947050281696],
             map_zoom=12,
             outlet=[-119.93597579595921, 38.96623572688885],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(wd='Trout_TC1_10336790', # 11000 ha
             extent=[-120.22338867187501, 38.65012583524745, -119.74273681640626, 39.02451827974919],
             map_center=[-119.98306274414064, 38.83756825896614],
             map_zoom=11,
             outlet=[-119.99412900886539, 38.940182494695605],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(wd='Trout_TC2_10336775', # 6000 ha
             extent=[-120.22338867187501, 38.65012583524745, -119.74273681640626, 39.02451827974919],
             map_center=[-119.98306274414064, 38.83756825896614],
             map_zoom=11,
             outlet=[-119.96905263318025, 38.90331807733495],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(wd='Trout_TC3_10336770', # 1900 ha
             extent=[-120.22338867187501, 38.65012583524745, -119.74273681640626, 39.02451827974919],
             map_center=[-119.98306274414064, 38.83756825896614],
             map_zoom=11,
             outlet=[-119.95864268958819, 38.86358847838675],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(wd='Trout_TC4_10336780', # 9500 ha
             extent=[-120.22338867187501, 38.65012583524745, -119.74273681640626, 39.02451827974919],
             map_center=[-119.98306274414064, 38.83756825896614],
             map_zoom=11,
             outlet=[-119.97248698683775, 38.920163661887436],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(wd='Upper_UT1_10336610', # 14000 ha
             extent=[-120.22338867187501, 38.65012583524745, -119.74273681640626, 39.02451827974919],
             map_center=[-119.98306274414064, 38.83756825896614],
             map_zoom=11,
             outlet=[-120.00218219772862, 38.937957400165246],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8,
             csa=10),
        dict(wd='Upper_UT3_103366092', # 10000 ha
             extent=[-120.14476776123048, 38.68711770472172, -119.90444183349611, 38.874463110537214],
             map_center=[-120.0246047973633, 38.78085193143006],
             map_zoom=12,
             outlet=[-120.02621875188274, 38.848528516714254],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8,
             csa=10),
        dict(wd='Upper_UT5_10336580', # 3700 ha
             extent=[-120.14476776123048, 38.68711770472172, -119.90444183349611, 38.874463110537214],
             map_center=[-120.0246047973633, 38.78085193143006],
             map_zoom=12,
             outlet=[-120.01938354230705, 38.79700284460229],
             landuse=None,
             cs=30, erod=0.000001,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1100.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8)
    ]

    scenarios = [
             # dict(wd='SimFire.202008.kikrcs.chn_cs{cs}_fccsFuels_obs_cli',
             #      landuse=None,
             #      lc_lookup_fn='ki5krcs.csv',
             #      cfg='lt-fire'),
             # dict(wd='SimFire.202008.kikrcs.chn_cs{cs}_landisFuels_obs_cli',
             #      landuse=None,
             #      lc_lookup_fn='ki5krcs.csv',
             #      cfg='lt-fire-future'),
             # dict(wd='SimFire.202008.kikrcs.chn_cs{cs}_landisFuels_fut_cli_A2',
             #      landuse=None,
             #      lc_lookup_fn='ki5krcs.csv',
             #      cfg='lt-fire-future',
             #      climate='future'),
               dict(wd='CurCond.202008.cl532.ki5krcs.chn_cs{cs}',
                    landuse=None,
                    lc_lookup_fn='ki5krcs.csv'),
             # dict(wd='PrescFireS.202008.kikrcs.chn_cs{cs}',
             #      landuse=[(not_shrub_selector, 110), (shrub_selector, 122)],
             #      lc_lookup_fn='ki5krcs.csv'),
             # dict(wd='LowSevS.202008.kikrcs.chn_cs{cs}',
             #      landuse=[(not_shrub_selector, 106), (shrub_selector, 121)],
             #      lc_lookup_fn='ki5krcs.csv'),
             # dict(wd='ModSevS.202008.kikrcs.chn_cs{cs}',
             #      landuse=[(not_shrub_selector, 118), (shrub_selector, 120)],
             #      lc_lookup_fn='ki5krcs.csv'),
             # dict(wd='HighSevS.202008.kikrcs.chn_cs{cs}',
             #      landuse=[(not_shrub_selector, 105), (shrub_selector, 119)],
             #      lc_lookup_fn='ki5krcs.csv'),
             # dict(wd='Thinn96.202008.kikrcs.chn_cs{cs}',
             #      landuse=[(not_shrub_selector, 123)],
             #      lc_lookup_fn='ki5krcs.csv'),
             # dict(wd='Thinn93.202008.kikrcs.chn_cs{cs}',
             #      landuse=[(not_shrub_selector, 115)],
             #      lc_lookup_fn='ki5krcs.csv'),
             # dict(wd='Thinn85.202008.kikrcs.chn_cs{cs}',
             #      landuse=[(not_shrub_selector, 117)],
             #      lc_lookup_fn='ki5krcs.csv'),
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
