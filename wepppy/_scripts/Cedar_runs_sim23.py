# 07/13/2023
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
from os.path import abspath
from wepppy.nodb.mods.locations.lt.selectors import *
from wepppy.wepp.out import TotalWatSed2
from wepppy.wepp.management import pmetpara_prep
from wepppy.export import arc_export

from osgeo import gdal, osr
gdal.UseExceptions()

wd = None

def log_print(msg):
    global wd

    now = datetime.now()
    print('[{now}] {wd}: {msg}'.format(now=now, wd=wd, msg=msg))


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

    cmd = ['rsync', '-av', '--progress',
           "--exclude='wepp/run/*'",
           "--exclude='wepp/output/*'",
           run_left, run_right]

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


watersheds = [
    dict(watershed='s1_wic',  # https://wepp.cloud/weppcloud/runs/mdobre-cacophonous-quietness/disturbed9002/
         extent=[-121.92146301269533, 47.35882737383059, -121.7743492126465, 47.45838885710576],
         map_center=[-121.84790611267091, 47.40863164034139],
         map_zoom=13,
         outlet=[-121.85359995091603, 47.39429263474839]),
    dict(watershed='s1_nft',  # https://wepp.cloud/weppcloud/runs/mdobre-archetypal-fanatic/disturbed9002/
         extent=[-121.83997901831334, 47.34161840105769, -121.73595385269267, 47.412061467380916],
         map_center=[-121.78796643550302, 47.37685169774973],
         map_zoom=13.5,
         outlet=[-121.81245648245134, 47.36291951809481]),
    dict(watershed='s1_sec',  # https://wepp.cloud/weppcloud/runs/mdobre-ordained-shaper/disturbed9002/
         extent=[-121.63358688354494, 47.26583445929678, -121.48647308349611, 47.36557142825728],
         map_center=[-121.56002998352052, 47.315726474956],
         map_zoom=13,
         outlet=[-121.55198541508884, 47.34189168148399]),
    dict(watershed='s1_sfc',  # https://wepp.cloud/weppcloud/runs/mdobre-exhausting-orthopedist/disturbed9002/
         extent=[-121.57453536987306, 47.247542522268006, -121.42742156982423, 47.34731397887758],
         map_center=[-121.50097846984865, 47.29745178296298],
         map_zoom=13,
         outlet=[-121.52069413953039, 47.31234591614018]),
    dict(watershed='s1_roc',  #
         extent=[-121.98066182689482, 47.331006803006154, -121.77261149565352, 47.47182716593643],
         map_center=[-121.87663666127418, 47.40146403519697],
         map_zoom=13,
         outlet=[-121.91726398079759, 47.39862796686496]),
#    dict(watershed='s2_lndsbrg_taylor_nfcedar',
#         # https://dev.wepp.cloud/weppcloud/runs/mdobre-inferential-extinction/seattle-snow-9002/
#         extent=[-121.99356079101564, 47.2256304876291, -121.40510559082033, 47.623752267682875],
#         map_center=[-121.69933319091798, 47.42506775601176],
#         map_zoom=11,
#         outlet=[-121.95094509772274, 47.39363218598862]),
    dict(watershed='s2_nft',  # https://wepp.cloud/weppcloud/runs/mdobre-archetypal-fanatic/disturbed9002/
         extent=[-121.83997901831334, 47.34161840105769, -121.73595385269267, 47.412061467380916],
         map_center=[-121.78796643550302, 47.37685169774973],
         map_zoom=13.5,
         outlet=[-121.81245648245134, 47.36291951809481]),
    dict(watershed = 's2_mft',  # https://wepp.cloud/weppcloud/runs/mdobre-side-to-side-jeep/disturbed9002/
         extent = [-121.82309318170107, 47.31286874576608, -121.67597938165224, 47.412516989668774],
         map_center = [-121.74953628167665, 47.362716395737955],
         map_zoom = 13,
         outlet = [-121.81628353988306, 47.36115943845854]),
    dict(watershed = 's2_nfc',  # https://wepp.cloud/weppcloud/runs/mdobre-stuck-stillness/disturbed9002/
         extent = [-121.7003718233316, 47.159136372259844, -121.28427116084903, 47.441316895540446],
         map_center = [-121.49232149209031, 47.300414891137216],
         map_zoom = 14,
         outlet = [-121.51813244535413, 47.31358160555894])
]

scenarios = [
    dict(scenario='s1',
         condition='und'),
    dict(scenario='s2',
#         base_project='mdobre-inferential-extinction',
         condition='und'),
    dict(scenario='s1',
         condition='hs1',
         sbs_map='/workdir/wepppy/wepppy/nodb/mods/locations/seattle/sim23/s1_hs1_remapped.tif'),
    dict(scenario='s1',
         condition='hs2',
         sbs_map='/workdir/wepppy/wepppy/nodb/mods/locations/seattle/sim23/s1_hs2_remapped.tif'),
    dict(scenario='s1',
         condition='hs3',
         default_landuse='high_severity'),
    dict(scenario='s2',
         condition='hs',
         default_landuse='high_severity'),
#         sbs_map='/workdir/wepppy/wepppy/nodb/mods/locations/seattle/sim23/s2_hs_remapped.tif'),
    dict(scenario='s2',
         condition='sbs_eagle',
         sbs_map='/workdir/wepppy/wepppy/nodb/mods/locations/seattle/sim23/s2_sbs_eagle.tif'),
    dict(scenario='s2',
         condition='sbs_norse',
         sbs_map='/workdir/wepppy/wepppy/nodb/mods/locations/seattle/sim23/s2_sbs_norse.tif')
]

general = dict(
    climate_mode='daymet_prism',
    cfg='cedar23',
    default_landuse=None,
    sbs_map=None,
    base_project=None
)

"""
XX    Use disturbed (old Lake Tahoe) config
XX    Topaz params 60/5
XX   Daymet with prism revisions, multiple climates: 1980-2022
XX    Run hourly seepage (wepp_ui)
XX    Run snow with rain/snow threshold = 0
XX    Run pmetpara kcb = 0.55 p = 0.6,
XX    Baseflow: 200/0.04/0.0,1.0
XX    Use tcr.txt: 20/190/0.0005/1.0 this needs to be created
XX    Bedrock: 0.01
XX    Pollutant: 0.007/0.008,0.009/3000
XX    WEPP version: latest

Run undisturbed then copy climates



"""

skip_completed = False

projects = []
wc = sys.argv[-1]
if '.py' in wc:
    wc = None

for scenario in scenarios:
    for watershed in watersheds:
        _scenario = scenario['scenario']
        _condition = scenario['condition']
        _watershed = watershed['watershed']

        if not _watershed.startswith(_scenario):
            continue

        projects.append(deepcopy(watershed))
        projects[-1].update(general)
        projects[-1].update(scenario)
        projects[-1]['wd'] = f"{_watershed}_{_condition}"


if __name__ == '__main__':

    os.chdir('/geodata/weppcloud_runs/')


    failed = open('failed', 'w')
    for proj in projects:

        wd = proj['wd']
        extent = proj['extent']
        map_center = proj['map_center']
        map_zoom = proj['map_zoom']
        outlet = proj['outlet']
        default_landuse = proj['default_landuse']
        cfg = proj['cfg']
        climate_mode = proj['climate_mode']

        watershed = proj['watershed']
        scenario = proj['scenario']
        condition = proj['condition']
        sbs_map = proj['sbs_map']
        base_project = proj['base_project']

        if wc is not None:
            if not wc in wd:
                continue

        wd = abspath(wd)


        if base_project is None:
            if condition != 'und':
                base_project = f"{watershed}_und"

        if skip_completed and base_project is None:
            if _exists(_join(wd, 'export', 'arcmap', 'channels.shp')):
                log_print('has channels.shp... skipping.')
                continue

        if _exists(wd) and base_project is None:
            log_print('cleaning dir')
            shutil.rmtree(wd)

        if not base_project:
            os.mkdir(wd)

            log_print('initializing project')
            ron = Ron(wd, "%s.cfg" % cfg)
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

        ron.name = watershed
        ron.scenario = condition

        # landuse
        if default_landuse is not None:
            log_print(f'setting default landuse: {default_landuse}')

            if default_landuse == 'high_severity':
                from wepppy.nodb.mods import Disturbed
                disturbed = Disturbed.getInstance(wd)
                sbs_fn = disturbed.build_uniform_sbs()
                disturbed.validate(sbs_fn)

            else:
                raise NotImplementedError

        elif sbs_map is not None:

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

        if base_project is not None and False:
            pass
        elif climate_mode == 'daymet_prism':

            log_print('building daymet_prism climate')
            climate = Climate.getInstance(wd)
            stations = climate.find_closest_stations()
            climate.climatestation = stations[0]['id']

            climate.climate_mode = ClimateMode.Observed
            climate.climate_spatialmode = ClimateSpatialMode.Multiple
            climate.set_observed_pars(start_year=1980, end_year=2022)
            climate.build(verbose=1)
        elif climate_mode == 'future':
            log_print('building future climate')
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
            log_print('building vanilla climate')
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
        wepp.clean()

        wepp.parse_inputs(proj)

        wepp.prep_hillslopes()

        log_print('running hillslopes')
        wepp.run_hillslopes()

        log_print('prepping watershed')
        wepp = Wepp.getInstance(wd)
        wepp.prep_watershed()
        pmetpara_prep(wepp.runs_dir, wepp.pmet_kcb, wepp.pmet_rawp)

        log_print('running watershed')
        wepp.run_watershed()
