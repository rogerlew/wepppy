import os
import sys
from datetime import date

import shutil
from os.path import exists as _exists
from os.path import split as _split
from time import sleep
from copy import deepcopy

from wepppy.nodb import (
    Ron, Topaz, Watershed, Landuse, Soils, Climate, Wepp, WeppPost, SoilsMode, ClimateMode, ClimateSpatialMode, LanduseMode, Ash, AshPost
)
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
            'Riverside_1': 1,
            'Riverside_2': 1,
            'Riverside_3': 1,
            'Beachie_1_burned': 1,
            'Beachie_2_14181900': 1,
            'Lionshead_1_14092750': 1,
            'Lionshead_2': 1,
            'Lionshead_3_14092750': 1,
            'Lionshead_4_14090400': 1,
            'Holiday_1_14163000': 1,
            'Archie_1_14319835': 1,
            'Archie_2_14319830': 1
        },
        'daymet': {
            'Riverside_1': 1,
            'Riverside_2': 1,
            'Riverside_3': 1,
            'Beachie_1_burned': 1,
            'Beachie_2_14181900': 1,
            'Lionshead_1_14092750': 1,
            'Lionshead_2': 1,
            'Lionshead_3_14092750': 1,
            'Lionshead_4_14090400': 1,
            'Holiday_1_14163000': 1,
            'Archie_1_14319835': 1,
            'Archie_2_14319830': 1
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
        dict(watershed='Riverside_1',
             fire_name='riverside',
             fire_date = '9/8',
             extent=[-122.61085510253908, 44.88457998727908, -122.13020324707033, 45.224128104219425],
             map_center=[-122.3705291748047, 45.05460605505183],
             map_zoom=11,
             outlet=[-122.471488220428, 45.0879999089735],
             landuse=None,
             cs=100, erod=0.000001,
             csa=10, mcl=100,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1000.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.75),
        dict(watershed='Riverside_2',
             fire_name='riverside',
             fire_date='9/8',
             extent=[-122.40554809570314, 44.92543221016552, -121.92489624023439, 45.26473839929064],
             map_center=[-122.16522216796876, 45.09533731309455],
             map_zoom=11,
             outlet=[-122.226748748065, 45.1958857733451],
             landuse=None,
             cs=100, erod=0.000001,
             csa=10, mcl=100,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1000.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.75),
        dict(watershed='Riverside_3',
             fire_name='riverside',
             fire_date='9/8',
             extent=[-122.40554809570314, 44.92543221016552, -121.92489624023439, 45.26473839929064],
             map_center=[-122.16522216796876, 45.09533731309455],
             map_zoom=11,
             outlet=[-122.152497304551, 45.1548514514498],
             landuse=None,
             cs=100, erod=0.000001,
             csa=10, mcl=100,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1000.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.75),
#        dict(watershed='Beachie_1_large', # redo the channel delineation
#             extent=[-122.64381408691408, 44.807660241989545, -122.16316223144533, 45.14766341500922],
#             map_center=[-122.4034881591797, 44.97791383818193],
#             map_zoom=11,
#             outlet=[-122.479826383954, 45.0093080106265],
#             landuse=None,
#             cs=100, erod=0.000001,
#             csa=10, mcl=100,
#             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1000.0,
#             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
#             mid_season_crop_coeff=0.95, p_coeff=0.75),
        
#        dict(watershed='Beachie_1_unburned',    # use later to compare to the burned watershed
#             extent=[-122.64381408691408, 44.807660241989545, -122.16316223144533, 45.14766341500922],
#             map_center=[-122.4034881591797, 44.97791383818193],
#             map_zoom=11,
#             outlet=[-122.410935185803, 44.9607590015012],
#             landuse=None,
#             cs=100, erod=0.000001,
#             csa=10, mcl=100,
#             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1000.0,
#             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
#             mid_season_crop_coeff=0.95, p_coeff=0.75),
        dict(watershed='Beachie_1',
             fire_name='beachie',
             fire_date='8/16',
             extent=[-122.64381408691408, 44.807660241989545, -122.16316223144533, 45.14766341500922],
             map_center=[-122.4034881591797, 44.97791383818193],
             map_zoom=11,
             outlet=[-122.411445868674, 44.9579350096451],
             landuse=None,
             cs=100, erod=0.000001,
             csa=10, mcl=100,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1000.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.75),
        dict(watershed='Beachie_2_14181900',
             fire_name='beachie',
             fire_date='8/16',
             extent=[-122.47764587402345, 44.66621116365773, -121.9969940185547, 45.007049561342136],
             map_center=[-122.23731994628908, 44.836882368166805],
             map_zoom=12,
             outlet=[-122.353487187526, 44.8362914731821],
             landuse=None,
             cs=100, erod=0.000001,
             csa=10, mcl=100,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1000.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.75),
        
        dict(watershed='Holiday_1_14163000', #has streamflow data until 1990
             fire_name='holiday',
             fire_date='9/16',
             extent=[-122.67402648925783, 43.97206324099821, -122.19337463378908, 44.31697048369679],
             map_center=[-122.43370056152345, 44.14476875978378],
             map_zoom=11,
             outlet=[-122.573316683899, 44.1459419535277],
             landuse=None,
             cs=100, erod=0.000001,
             csa=10, mcl=100,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1000.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.75),

              ]

    scenarios = [
        dict(wd='CurCond.gridmet',
             landuse=None,
             cli_mode='observed', cfg='disturbed',
             clean=True, build_soils=True, build_landuse=True, build_climates=True),
        dict(wd='SBS.gridmet',
             landuse=None,
             cli_mode='observed', cfg='or-disturbed-{fire_name}-fire',
             clean=True, build_soils=True, build_landuse=True, build_climates=True)]

    wc = sys.argv[-1]
    if '.py' in wc:
        wc = None

    projects = []
    for scenario in scenarios:
        for watershed in watersheds:
            projects.append(deepcopy(watershed))
            
            projects[-1]['cfg'] = scenario['cfg'].replace('{fire_name}', watershed.get('fire_name', ''))
            projects[-1]['landuse'] = scenario['landuse']
            projects[-1]['cli_mode'] = scenario.get('cli_mode', 'observed')
            projects[-1]['clean'] = scenario['clean']
            projects[-1]['build_soils'] = scenario['build_soils']
            projects[-1]['build_landuse'] = scenario['build_landuse']
            projects[-1]['build_climates'] = scenario['build_climates']
            projects[-1]['watershed'] = watershed['watershed']
            projects[-1]['scenario'] = scenario['wd']
            projects[-1]['wd'] = 'oregon_2020_fires_v1_{watershed}_{scenario}' \
                .format(watershed=watershed['watershed'], scenario=scenario['wd'])

    for proj in projects:
        config = proj['cfg']
        watershed_name = proj['watershed']
        wd = proj['wd']

        log_print(wd)
        if wc is not None:
            if not wc in wd:
                continue

        watershed = proj['watershed']
        scenario = proj['scenario']

        # make sure the watershed matches the fire scenarios
        if scenario.startswith('SBS-'):
            _fire = scenario.split('-')[1].split('.')[0]
            if not watershed.startswith(_fire):
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
         
        fire_date = proj['fire_date']
     
        if clean:
            if _exists(wd):
                shutil.rmtree(wd)
            os.mkdir(wd)

            ron = Ron(wd, config + '.cfg')
            ron.name = wd
            ron.set_map(extent, map_center, zoom=map_zoom)
            ron.fetch_dem()

            watershed = Watershed.getInstance(wd)
            log_print('building channels')
            watershed.build_channels(csa=csa, mcl=mcl)

            log_print('building subcatchments')
            watershed.set_outlet(*outlet)
            watershed.build_subcatchments()

            log_print('abstracting watershed')
            watershed.abstract_watershed()
            translator = watershed.translator_factory()
            topaz_ids = [top.split('_')[1] for top in translator.iter_sub_ids()]

        else:
            ron = Ron.getInstance(wd)
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
                climate.set_observed_pars(start_year=1990, end_year=2017)

                climate.build(verbose=1)

            elif 'gridmet' in wd:
                log_print('building gridmet')
                stations = climate.find_closest_stations()
                climate.climatestation = stations[0]['id']

                climate.climate_mode = ClimateMode.GridMetPRISM
                climate.climate_spatialmode = ClimateSpatialMode.Multiple
                climate.set_observed_pars(start_year=1980, end_year=2020)

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

        wepppost = WeppPost.getInstance(wd)
        wepppost.run_post()
     
        if 'SBS' in scenario:
            ash = Ash.getInstance(wd)
            ash.run_ash(fire_date=fire_date)

            ashpost = AshPost.getInstance(wd)
            ashpost.run_post()

        arc_export(wd)

