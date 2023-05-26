# 04/21/2023
import os
import sys

from copy import deepcopy
from subprocess import Popen, PIPE
from glob import glob
import shutil
from os.path import exists as _exists
from os.path import split as _split
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
from wepppy.wepp.out import TotalWatSed2
from wepppy.export import arc_export

from osgeo import gdal, osr
gdal.UseExceptions()

wd = None


def log_print(msg):
    global wd

    now = datetime.now()
    print('[{now}] {wd}: {msg}'.format(now=now, wd=wd, msg=msg))


xxx = 80 ## TODO: Define this


def fork(runid, new_runid):

    wd = _join('/geodata/weppcloud_runs/', runid)
    new_wd = _join('/geodata/weppcloud_runs/', new_runid)

    log_print(' done.\n\nCopying files...'.format(new_wd))

    run_left = wd
    if not run_left.endswith('/'):
        run_left += '/'

    run_right = new_wd
    if not run_right.endswith('/'):
        run_right += '/'

    cmd = ['rsync', '-av', '--progress', run_left, run_right]

    log_print( '\n   cmd: {}\n'.format(' '.join(cmd)))

    p = Popen(cmd, stdout=PIPE, stderr=PIPE)

    while p.poll() is None:
        output = p.stdout.readline()
        log_print(output.decode('UTF-8'))

    p.wait()

    log_print( 'done copying files.\n\nSetting wd in .nodbs...\n')

    # replace the runid in the nodb files
    nodbs = glob(_join(new_wd, '*.nodb'))
    for fn in nodbs:
        log_print( '  {fn}...'.format(fn=fn))
        with open(fn) as fp:
            s = fp.read()

        s = s.replace(runid, new_runid)
        with open(fn, 'w') as fp:
            fp.write(s)

        log_print( ' done.\n')

    log_print( ' done setting wds.\n\nCleanup locks, READONLY, PUBLIC...\n')

    # delete any active locks
    locks = glob(_join(new_wd, '*.lock'))
    for fn in locks:
        os.remove(fn)

    fn = _join(new_wd, 'READONLY')
    if _exists(fn):
        os.remove(fn)

    fn = _join(new_wd, 'PUBLIC')
    if _exists(fn):
        os.remove(fn)

    log_print( ' done.\n')


if __name__ == '__main__':

    os.chdir('/geodata/weppcloud_runs/')

    watersheds = [
        dict(watershed='AllCedar',  # https://dev.wepp.cloud/weppcloud/runs/mdobre-inferential-extinction/seattle-snow-9002/
#             base_project='mdobre-inferential-extinction',
             extent=[-121.99356079101564, 47.2256304876291, -121.40510559082033, 47.623752267682875],
             map_center=[-121.69933319091798, 47.42506775601176],
             map_zoom=11,
             outlet=[-121.95094509772274, 47.39363218598862],
             landuse=None,
             csa=5.0001, mcl = 60,
             cs=80, erod=0.000001,
             surf_runoff=0.004, lateral_flow=0.005, baseflow=0.006, sediment=1200.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8,
             ksub=0.01),

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
                          
        dict(watershed='5_SteeleCreek',  # https://dev.wepp.cloud/weppcloud/runs/mdobre-dun-colored-thumbnail/seattle-snow/ 
             extent=[-121.85527326670098, 47.39702726773113, -121.76848447624735, 47.455743079989006],
             map_center=[-121.81187887147415, 47.42639336086452],
             map_zoom=13,
             outlet=[-121.8196462708747, 47.411647646852316],
             landuse=None,
             cs=xxx, erod=0.000001,
             surf_runoff=0.004, lateral_flow=0.005, baseflow=0.006, sediment=1200.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
                          
        dict(watershed='6_TaylorCreek',  # https://dev.wepp.cloud/weppcloud/runs/mdobre-incidental-exhibitor/seattle-snow/
             extent=[-121.93038940429689, 47.27946192115735, -121.68491363525392, 47.44573629035491],
             map_center=[-121.80765151977539, 47.3626646139612],
             map_zoom=12,
             outlet=[-121.84810259063217, 47.38690390950939],
             landuse=None,
             cs=xxx, erod=0.000001,
             surf_runoff=0.004, lateral_flow=0.005, baseflow=0.006, sediment=1200.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
                          
        dict(watershed='7_RackCreek',  # https://dev.wepp.cloud/weppcloud/runs/mdobre-macroscopic-mule/seattle-snow/
             extent=[-121.81873700666384, 47.319323353341154, -121.64515942575657, 47.43686262163456],
             map_center=[-121.73194821621021, 47.378125740135424],
             map_zoom=12,
             outlet=[-121.72235036496633, 47.39182498187038],
             landuse=None,
             cs=xxx, erod=0.000001,
             surf_runoff=0.004, lateral_flow=0.005, baseflow=0.006, sediment=1200.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
                          
        dict(watershed='8_ShotgunCreek',  # https://dev.wepp.cloud/weppcloud/runs/mdobre-allopathic-laird/seattle-snow/
             extent=[-121.81024020200407, 47.3125753955728, -121.63666262109679, 47.43012968899888],
             map_center=[-121.72345141155041, 47.37138529557367],
             map_zoom=12,
             outlet=[-121.70761572206875, 47.380969758293595],
             landuse=None,
             cs=xxx, erod=0.000001,
             surf_runoff=0.004, lateral_flow=0.005, baseflow=0.006, sediment=1200.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
                          
        dict(watershed='9_BoulderCreek',  # https://dev.wepp.cloud/weppcloud/runs/mdobre-nuclear-monument/seattle-snow/
             extent=[-121.78887680743084, 47.28870375392173, -121.61529922652359, 47.406311187359705],
             map_center=[-121.70208801697721, 47.34754022617904],
             map_zoom=12,
             outlet=[-121.69605779736114, 47.36507371353041],
             landuse=None,
             cs=xxx, erod=0.000001,
             surf_runoff=0.004, lateral_flow=0.005, baseflow=0.006, sediment=1200.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
                          
        dict(watershed='10_Rex',  # https://dev.wepp.cloud/weppcloud/runs/mdobre-idealized-boredom/seattle-snow/
             extent=[-121.77658081054689, 47.25430078914495, -121.53110504150392, 47.42065432071321],
             map_center=[-121.6538429260254, 47.33754306785725],
             map_zoom=12,
             outlet=[-121.66379704464829, 47.35082660159635],
             landuse=None,
             cs=xxx, erod=0.000001,
             surf_runoff=0.004, lateral_flow=0.005, baseflow=0.006, sediment=1200.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
                          
        dict(watershed='11_WalshLake',  # https://dev.wepp.cloud/weppcloud/runs/mdobre-circumpolar-thunderclap/seattle-snow/
             extent=[-121.96925183206595, 47.35222786660658, -121.79567425115869, 47.469693845801274],
             map_center=[-121.88246304161231, 47.410993605703396],
             map_zoom=12,
             outlet=[-121.92447280149537, 47.40126033793729],
             landuse=None,
             cs=xxx, erod=0.000001,
             surf_runoff=0.004, lateral_flow=0.005, baseflow=0.006, sediment=1200.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
                          
        dict(watershed='12_RockCreek',  # https://dev.wepp.cloud/weppcloud/runs/mdobre-deafened-tantalum/seattle-snow/
             extent=[-121.95133209228517, 47.37649961666246, -121.82859420776367, 47.45954949060109],
             map_center=[-121.88996315002443, 47.418040928043936],
             map_zoom=13,
             outlet=[-121.9015742124714, 47.40239293772682],
             landuse=None,
             cs=xxx, erod=0.000001,
             surf_runoff=0.004, lateral_flow=0.005, baseflow=0.006, sediment=1200.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
                          
        dict(watershed='13_UpperCedar',  # https://dev.wepp.cloud/weppcloud/runs/mdobre-inattentive-iconography/seattle-snow/
             extent=[-121.66568756103517, 47.24730946320093, -121.4202117919922, 47.413684985326825],
             map_center=[-121.54294967651369, 47.3305627384955],
             map_zoom=12,
             outlet=[-121.62248883359838, 47.362422391792755],
             landuse=None,
             cs=xxx, erod=0.000001,
             surf_runoff=0.004, lateral_flow=0.005, baseflow=0.006, sediment=1200.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
                          
        dict(watershed='14_LowerCedarEast',  # https://dev.wepp.cloud/weppcloud/runs/mdobre-kiln-dried-exponential/seattle-snow/
             extent=[-121.88913910241645, 47.33725885529981, -121.71556152150916, 47.45475818016082],
             map_center=[-121.8023503119628, 47.396041268667254],
             map_zoom=12,
             outlet=[-121.84627671566402, 47.39467807072394],
             landuse=None,
             cs=xxx, erod=0.000001,
             surf_runoff=0.004, lateral_flow=0.005, baseflow=0.006, sediment=1200.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
             
        dict(watershed='15_Watershed',  #
             extent=[-121.88913910241645, 47.33725885529981, -121.71556152150916, 47.45475818016082],
             map_center=[-121.8023503119628, 47.396041268667254],
             map_zoom=12,
             outlet=[-121.84627671566402, 4739467807072394],
             landuse=None,
             cs=xxx, erod=0.000001,
             surf_runoff=0.004, lateral_flow=0.005, baseflow=0.006, sediment=1200.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),

        dict(watershed='16_Watershed',  #
             extent=[-121.88913910241645, 47.33725885529981, -121.71556152150916, 47.45475818016082],
             map_center=[-121.8023503119628, 47.396041268667254],
             map_zoom=12,
             outlet=[-121.84627671566402, 47.39467807072394],
             landuse=None,
             cs=xxx, erod=0.000001,
             surf_runoff=0.004, lateral_flow=0.005, baseflow=0.006, sediment=1200.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),

        dict(watershed='17_Watershed',  #
             extent=[-121.88913910241645, 47.33725885529981, -121.71556152150916, 47.45475818016082],
             map_center=[-121.8023503119628, 47.396041268667254],
             map_zoom=12,
             outlet=[-121.84627671566402, 47.39467807072394],
             landuse=None,
             cs=xxx, erod=0.000001,
             surf_runoff=0.004, lateral_flow=0.005, baseflow=0.006, sediment=1200.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.8),

        dict(watershed='18_Watershed',  #
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
            cfg='seattle-snow-9002'),
        dict(scenario='HighSev',
            base_project='Cedar23_AllCedar_CurCond',
            landuse='high_severity',
            cfg='seattle-snow-9002'),
        dict(scenario='SimFire',
            base_project='Cedar23_AllCedar_CurCond',
            landuse=None,
            sbs_map='/workdir/wepppy/wepppy/nodb/mods/locations/seattle/simfire/SBS_pred_Norse_CedarRiver_all.tif',
            cfg='seattle-snow-9002')
    ]

    skip_completed = True
    projects = []
    prefix = 'Cedar23'
    wc = sys.argv[-1]
    if '.py' in wc:
        wc = None

    for scenario in scenarios:
        for watershed in watersheds:
            projects.append(deepcopy(watershed))
            projects[-1]['landuse'] =scenario['landuse']
            projects[-1]['lc_lookup_fn'] = scenario.get('lc_lookup_fn', 'landSoilLookup.csv')
            projects[-1]['climate'] = scenario.get('climate', 'observed')
            projects[-1]['base_project'] = watershed.get('base_project')
            base_project = scenario.get('base_project')
            if base_project is not None:
                projects[-1]['base_project'] = base_project
            projects[-1]['scenario'] = scenario['scenario']
            projects[-1]['cfg'] = scenario['cfg']
            projects[-1]['sbs_map'] = scenario.get('sbs_map')
            _watershed = watershed['watershed']
            _scenario = scenario['scenario']
            projects[-1]['wd'] = f"{prefix}_{_watershed}_{_scenario}"

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
            base_project = proj['base_project']
            sbs_map = proj['sbs_map']

            if wc is not None:
                if not wc in wd:
                    continue

            if skip_completed and base_project is None:
                if _exists(_join(wd, 'export', 'arcmap', 'channels.shp')):
                    log_print('has channels.shp... skipping.')
                    continue

            log_print('cleaning dir')
            if _exists(wd) and base_project is None:
                print()
                shutil.rmtree(wd)

            if not base_project:
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
            else:
                log_print(f'forking {base_project}')
                fork(base_project, wd)
                ron = Ron.getInstance(wd)
                wat = Watershed.getInstance(wd)
                translator = wat.translator_factory()
                topaz_ids = [top.split('_')[1] for top in translator.iter_sub_ids()]

            if default_landuse is not None:
                log_print(f'setting default landuse: {default_landuse}')

                if default_landuse == 'high_severity':
                    from wepppy.nodb.mods import Disturbed
                    disturbed = Disturbed.getInstance(wd)
                    sbs_fn = disturbed.build_uniform_sbs()
                    disturbed.validate(sbs_fn)

                else:
                    raise NotImplementedError

            if sbs_map is not None:

                sbs_dir, sbs_fn = _split(sbs_map)

                from wepppy.nodb.mods import Disturbed
                disturbed = Disturbed.getInstance(wd)

                shutil.copyfile(sbs_map,  _join(disturbed.disturbed_dir, sbs_fn))
                disturbed.validate(_join(disturbed.disturbed_dir, sbs_fn))

            log_print('building landuse')
            landuse = Landuse.getInstance(wd)
            landuse.mode = LanduseMode.Gridded
            landuse.build()
            landuse = Landuse.getInstance(wd)

            soils = Soils.getInstance(wd)
            soils.mode = SoilsMode.Gridded
            soils.build()

            log_print('building climate')

            if base_project is not None:
                pass
            elif climate_mode == 'observed':
                climate = Climate.getInstance(wd)
                stations = climate.find_closest_stations()
                climate.input_years = 43
                climate.climatestation = stations[0]['id']

                climate.climate_mode = ClimateMode.GridMetPRISM
                climate.climate_spatialmode = ClimateSpatialMode.Multiple
                climate.set_observed_pars(start_year=1980, end_year=2022)
                climate.build(verbose=1)
            elif climate_mode == 'future':
                climate = Climate.getInstance(wd)
                stations = climate.find_closest_stations()
                climate.input_years = 30
                climate.climatestation = stations[0]['id']

                climate.climate_mode = ClimateMode.Future
                climate.climate_spatialmode = ClimateSpatialMode.Single
                climate.set_future_pars(start_year=2018, end_year=2018 + 30)
                climate.build(verbose=1)
                # climate.set_orig_cli_fn(_join(climate._future_clis_wc, 'Ward_Creek_A2.cli'))
            elif climate_mode == 'vanilla':
                climate = Climate.getInstance(wd)
                stations = climate.find_closest_stations()
                climate.input_years = 30
                climate.climatestation = stations[0]['id']

                climate.climate_mode = ClimateMode.Vanilla
                climate.climate_spatialmode = ClimateSpatialMode.Single
                climate.build(verbose=1)
                # climate.set_orig_cli_fn(_join(climate._future_clis_wc, 'Ward_Creek_A2.cli'))
            else:
                raise Exception("Unknown climate_mode")

            log_print('prepping wepp')
            wepp = Wepp.getInstance(wd)
            wepp.parse_inputs(proj)

            wepp.prep_hillslopes()

            log_print('running hillslopes')
            wepp.run_hillslopes()

            log_print('prepping watershed')
            wepp = Wepp.getInstance(wd)
            wepp.prep_watershed(erodibility=proj['erod'], critical_shear=proj['cs'])
            wepp._prep_pmet(kcb=proj['mid_season_crop_coeff'], rawp=proj['p_coeff'])

            log_print('running watershed')
            wepp.run_watershed()


        except:
            failed.write('%s\n' % wd)
            raise
