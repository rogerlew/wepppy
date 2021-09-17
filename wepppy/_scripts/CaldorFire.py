import os
import sys
from datetime import date

import shutil
from os.path import exists as _exists
from os.path import split as _split
from time import sleep
from copy import deepcopy

from wepppy.nodb.mods.locations.lt.selectors import *
from wepppy.all_your_base import isfloat
from wepppy.nodb import (
    Ron, Topaz, Watershed, Landuse, Soils, Climate, Wepp, SoilsMode, ClimateMode, ClimateSpatialMode, LanduseMode
)
from wepppy.nodb.mods.locations import SeattleMod

from wepppy.wepp.soils.utils import modify_kslast
from os.path import join as _join
from wepppy.wepp.out import TotalWatSed
from wepppy.export import arc_export

from wepppy.climates.cligen import ClimateFile

from osgeo import gdal

gdal.UseExceptions()

from wepppy._scripts.utils import *

os.chdir('/geodata/weppcloud_runs/')

wd = None


def log_print(*msg):
    now = datetime.now()
    print('[{now}] {wd}: {msg}'.format(now=now, wd=wd, msg=', '.join(str(v) for v in msg)))


if __name__ == '__main__':

    precip_transforms = {
        'gridmet': {
            'VanTessel': 1
        },
        'daymet': {
            'VanTessel': 1
        }
    }


    def _daymet_cli_adjust(cli_dir, cli_fn, watershed):
        cli = ClimateFile(_join(cli_dir, cli_fn))

        cli.discontinuous_temperature_adjustment(date(2005, 11, 2))

        pp_scale = precip_transforms['daymet'][watershed]
        cli.transform_precip(offset=0, scale=pp_scale)

        cli.write(_join(cli_dir, 'adj_' + cli_fn))

        return 'adj_' + cli_fn


    def _gridmet_cli_adjust(cli_dir, cli_fn, watershed):
        cli = ClimateFile(_join(cli_dir, cli_fn))

        pp_scale = precip_transforms['gridmet'][watershed]
        cli.transform_precip(offset=0, scale=pp_scale)

        cli.write(_join(cli_dir, 'adj_' + cli_fn))

        return 'adj_' + cli_fn

    watersheds = [    
        dict(watershed='SF_Ameri_at_Kyburz',
             extent=[-120.41221618652345, 38.59648051509767, -119.9315643310547, 38.971154274048374],
             map_center=[-120.17189025878908, 38.78406349514289],
             map_zoom=11,
             outlet=[-120.29437175764512, 38.773877838147996],
             landuse=None,
             cs=19, erod=0.000001,
             csa=10, mcl=100,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1000.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.00,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(watershed='SilverForkAmerican',
             extent=[-120.43006896972658, 38.572327030541246, -119.94941711425783, 38.947127343262494],
             map_center=[-120.1897430419922, 38.759973241762665],
             map_zoom=10.5,
             outlet=[-120.31054126868311, 38.766854480972924],
             landuse=None,
             cs=19, erod=0.000001,
             csa=10, mcl=100,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1000.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.00,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(watershed='SlyParkCreek',
             extent=[-120.63840945649443, 38.57185501868103, -120.29853727010257, 38.837084488099194],
             map_center=[-120.46847336329851, 38.70459272819016],
             map_zoom=11,
             outlet=[-120.52169178412885, 38.73465718976626],
             landuse=None,
             cs=19, erod=0.000001,
             csa=10, mcl=100,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1000.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.00,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(watershed='CampCreek',
             extent=[-120.69923400878908, 38.47939467327645, -120.21858215332033, 38.85468129471517],
             map_center=[-120.4589080810547, 38.66728386136457],
             map_zoom=11,
             outlet=[-120.58761082559347, 38.68970719819895],
             landuse=None,
             cs=19, erod=0.000001,
             csa=10, mcl=100,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1000.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.00,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(watershed='NF_Cosumnes',
             extent=[-120.65460205078126, 38.48423226350894, -120.17395019531251, 38.8594935943241],
             map_center=[-120.41427612304689, 38.67210881558819],
             map_zoom=10.5,
             outlet=[-120.55489045109991, 38.661753859507265],
             landuse=None,
             cs=19, erod=0.000001,
             csa=10, mcl=100,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1000.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.00,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(watershed='SteelyForkCosumnes',
             extent=[-120.65460205078126, 38.48423226350894, -120.17395019531251, 38.8594935943241],
             map_center=[-120.41427612304689, 38.67210881558819],
             map_zoom=11,
             outlet=[-120.56374496501955, 38.61409506239855],
             landuse=None,
             cs=19, erod=0.000001,
             csa=10, mcl=100,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1000.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.00,
             mid_season_crop_coeff=0.95, p_coeff=0.8),
        dict(watershed='DogTownCreek',
             extent=[-120.74386596679689, 38.434766038944815, -120.26321411132814, 38.81028585091167],
             map_center=[-120.50354003906251, 38.62277173614524],
             map_zoom=10.5,
             outlet=[-120.54914240032107, 38.59471550851222],
             landuse=None,
             cs=19, erod=0.000001,
             csa=10, mcl=100,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1000.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.00,
             mid_season_crop_coeff=0.95, p_coeff=0.8)
              ]

    scenarios = [
         dict(wd='CurCond.gridmet', 
              landuse=None, 
              cli_mode='observed', 
              cfg='disturbed',
              clean=True, 
              build_soils=True, 
              build_landuse=True, 
              build_climates=True),
        dict(wd='SBS.gridmet',
             landuse=None,
             cfg='disturbed-caldor',
             cli_mode='copyCurCond.gridmet', 
             clean=True, 
             build_soils=True, 
             build_landuse=True, 
             build_climates=True),
    ]

    wc = sys.argv[-1]
    if '.py' in wc:
        wc = None

    projects = []
    for scenario in scenarios:
        for watershed in watersheds:
            projects.append(deepcopy(watershed))

            projects[-1]['cfg'] = scenario['cfg']
            projects[-1]['landuse'] = scenario['landuse']
            projects[-1]['cli_mode'] = scenario.get('cli_mode', 'observed')
            projects[-1]['clean'] = scenario['clean']
            projects[-1]['build_soils'] = scenario['build_soils']
            projects[-1]['build_landuse'] = scenario['build_landuse']
            projects[-1]['build_climates'] = scenario['build_climates']
            projects[-1]['wd'] = 'Caldor_{watershed}_{scenario}' \
                .format(watershed=watershed['watershed'], scenario=scenario['wd']) 

    for proj in projects:
        config = proj['cfg']
        watershed_name = proj['watershed']
        wd = proj['wd']

        log_print(wd)
        if wc is not None:
            if not wc in wd:
                continue

        extent = proj['extent']
        map_center = proj['map_center']
        map_zoom = proj['map_zoom']
        outlet = proj['outlet']
        default_landuse = proj['landuse']
        cli_mode = proj['cli_mode']

        csa = proj['csa']
        mcl = proj['mcl']
        cs = proj['cs']
        erod = proj['erod']

        clean = proj['clean']
        build_soils = proj['build_soils']
        build_landuse = proj['build_landuse']
        build_climates = proj['build_climates']

        if clean:
            if _exists(wd):
                shutil.rmtree(wd)
            os.mkdir(wd)

            ron = Ron(wd, config + '.cfg')
            ron.name = wd
            ron.set_map(extent, map_center, zoom=map_zoom)
            ron.fetch_dem()

            log_print('building channels')
            watershed = Watershed.getInstance(wd)
            watershed.build_channels(csa=csa, mcl=mcl)
            watershed.set_outlet(*outlet)
            sleep(0.5)

            log_print('building subcatchments')
            watershed.build_subcatchments()

            log_print('abstracting watershed')
            watershed = Watershed.getInstance(wd)
            watershed.abstract_watershed()
            translator = watershed.translator_factory()
            topaz_ids = [top.split('_')[1] for top in translator.iter_sub_ids()]

        else:
            ron = Ron.getInstance(wd)
            topaz = Topaz.getInstance(wd)
            watershed = Watershed.getInstance(wd)

        landuse = Landuse.getInstance(wd)
        if build_landuse:
            landuse.mode = LanduseMode.Gridded
            landuse.build()

        soils = Soils.getInstance(wd)
        if build_soils:
            log_print('building soils')
            soils.mode = SoilsMode.Gridded
            soils.build() 
            #soils.build_statsgo()

        climate = Climate.getInstance(wd)
        if build_climates:
            log_print('building climate')

        if cli_mode == 'observed':
            log_print('building observed')
            if 'daymet' in wd:
                stations = climate.find_closest_stations()
                climate.climatestation = stations[0]['id']

                climate.climate_mode = ClimateMode.Observed
                climate.climate_spatialmode = ClimateSpatialMode.Multiple
                climate.set_observed_pars(start_year=2000, end_year=2017)

                climate.build(verbose=1)

            elif 'gridmet' in wd:
                log_print('building gridmet')
                stations = climate.find_closest_stations()
                climate.climatestation = stations[0]['id']

                climate.climate_mode = ClimateMode.GridMetPRISM
                climate.climate_spatialmode = ClimateSpatialMode.Multiple
                climate.set_observed_pars(start_year=1990, end_year=1991)

                climate.build(verbose=1)

        elif cli_mode == 'future':
            log_print('building gridmet')
            stations = climate.find_closest_stations()
            climate.climatestation = stations[0]['id']

            climate.climate_mode = ClimateMode.Future
            climate.climate_spatialmode = ClimateSpatialMode.Multiple
            climate.set_future_pars(start_year=2006, end_year=2099)

            climate.build(verbose=1)

        elif cli_mode == 'PRISMadj':
            stations = climate.find_closest_stations()
            climate.climatestation = stations[0]['id']

            log_print('climate_station:', climate.climatestation)

            climate.climate_mode = ClimateMode.PRISM
            climate.climate_spatialmode = ClimateSpatialMode.Multiple
            climate.input_years = 100

            climate.build(verbose=1)

        elif cli_mode == 'vanilla':
            stations = climate.find_closest_stations()
            climate.climatestation = stations[0]['id']

            log_print('climate_station:', climate.climatestation)

            climate.climate_mode = ClimateMode.Vanilla
            climate.climate_spatialmode = ClimateSpatialMode.Single
            climate.input_years = 100

            climate.build(verbose=1)
        elif 'copy' in climate_mode:
            src_wd = 'Caldor_%s_%s' % (watershed, climate_mode[4:])
            shutil.rmtree(_join(wd, 'climate'))
            shutil.copytree(_join(src_wd, 'climate'), _join(wd, 'climate'))
            with open(_join(src_wd, 'climate.nodb')) as fp:
                contents = fp.read()

            with open(_join(wd, 'climate.nodb'), 'w') as fp:
                fp.write(contents.replace(src_wd, wd))

        log_print('running wepp')
        wepp = Wepp.getInstance(wd)
        wepp.parse_inputs(proj)

        wepp.prep_hillslopes()

        log_print('running hillslopes')
        wepp.run_hillslopes()

        wepp = Wepp.getInstance(wd)
        wepp.prep_watershed(erodibility=erod, critical_shear=cs)
        wepp._prep_pmet(mid_season_crop_coeff=proj['mid_season_crop_coeff'], p_coeff=proj['p_coeff'])
        wepp.run_watershed()
        loss_report = wepp.report_loss()

        log_print('running wepppost')
        fn = _join(ron.export_dir, 'totalwatsed.csv')

        totwatsed = TotalWatSed(_join(ron.output_dir, 'totalwatsed.txt'),
                                wepp.baseflow_opts, wepp.phosphorus_opts)
        totwatsed.export(fn)
        assert _exists(fn)

        arc_export(wd)
