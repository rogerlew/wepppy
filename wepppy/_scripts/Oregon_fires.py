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

from wepppy.wepp.soils.utils import modify_ksat
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
            'N_Santiam_abvEvans_14181900': 1,
            'N_Santiam_abvEvans_14181900': 1,
            'N_Santiam_abvEvans_14181900': 1
        },
        'daymet': {
            'N_Santiam_abvEvans_14181900': 1,
            'N_Santiam_abvEvans_14181900': 1,
            'N_Santiam_abvEvans_14181900': 1
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
             extent=[-122.61085510253908, 44.88457998727908, -122.13020324707033, 45.224128104219425],
             map_center = [-122.3705291748047, 45.05460605505183],
             map_zoom = 11,
             outlet = [-122.471488220428, 45.0879999089735],
             landuse=None,
             cs=100, erod=0.000001,
             csa=10, mcl=100,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1000.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.75, ksat=0.05),
        dict(watershed='Riverside_2',
             extent=[-122.40554809570314, 44.92543221016552, -121.92489624023439, 45.26473839929064],
             map_center = [-122.16522216796876, 45.09533731309455],
             map_zoom = 11,
             outlet = [-122.226748748065, 45.1958857733451],
             landuse=None,
             cs=100, erod=0.000001,
             csa=10, mcl=100,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1000.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.75, ksat=0.05),
        dict(watershed='Riverside_3',
             extent=[-122.40554809570314, 44.92543221016552, -121.92489624023439, 45.26473839929064],
             map_center = [-122.16522216796876, 45.09533731309455],
             map_zoom = 11,
             outlet = [-122.152497304551, 45.1548514514498],
             landuse=None,
             cs=100, erod=0.000001,
             csa=10, mcl=100,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1000.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.75, ksat=0.05),
#        dict(watershed='Beachie_1_large', # redo the channel delineation
#             extent=[-122.64381408691408, 44.807660241989545, -122.16316223144533, 45.14766341500922],
#             map_center = [-122.4034881591797, 44.97791383818193],
#             map_zoom = 11,
#             outlet = [-122.479826383954, 45.0093080106265],
#             landuse=None,
#             cs=100, erod=0.000001,
#             csa=10, mcl=100,
#             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1000.0,
#             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
#             mid_season_crop_coeff=0.95, p_coeff=0.75, ksat=0.05),
        
#        dict(watershed='Beachie_1_unburned',    # use later to compare to the burned watershed
#             extent=[-122.64381408691408, 44.807660241989545, -122.16316223144533, 45.14766341500922],
#             map_center = [-122.4034881591797, 44.97791383818193],
#             map_zoom = 11,
#             outlet = [-122.410935185803, 44.9607590015012],
#             landuse=None,
#             cs=100, erod=0.000001,
#             csa=10, mcl=100,
#             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1000.0,
#             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
#             mid_season_crop_coeff=0.95, p_coeff=0.75, ksat=0.05),
        dict(watershed='Beachie_1_burned',
             extent=[-122.64381408691408, 44.807660241989545, -122.16316223144533, 45.14766341500922],
             map_center = [-122.4034881591797, 44.97791383818193],
             map_zoom = 11,
             outlet = [-122.411445868674, 44.9579350096451],
             landuse=None,
             cs=100, erod=0.000001,
             csa=10, mcl=100,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1000.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.75, ksat=0.05),
        dict(watershed='Beachie_2_14181900',
             extent=[-122.47764587402345, 44.66621116365773, -121.9969940185547, 45.007049561342136],
             map_center = [-122.23731994628908, 44.836882368166805],
             map_zoom = 12,
             outlet = [-122.353487187526, 44.8362914731821],
             landuse=None,
             cs=100, erod=0.000001,
             csa=10, mcl=100,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1000.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.75, ksat=0.05),
        
        dict(watershed='Lionshead_1_14092750', #has streamflow data until 2009
             extent=[-122.01793670654298, 44.675000833313895, -121.77761077880861, 44.84564611772204],
             map_center = [-121.8977737426758, 44.76038647589176],
             map_zoom = 12,
             outlet = [-121.97959390571, 44.7813047712734],
             landuse=None,
             cs=100, erod=0.000001,
             csa=10, mcl=100,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1000.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.75, ksat=0.05),
        dict(watershed='Lionshead_2', #has streamflow data at larger 14178000
             extent=[-122.12814331054689, 44.61735539205568, -121.88781738281251, 44.78817059580362],
             map_center = [-122.00798034667969, 44.70282599311735],
             map_zoom = 12,
             outlet = [-122.090392288611, 44.7049651420389],
             landuse=None,
             cs=100, erod=0.000001,
             csa=10, mcl=100,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1000.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.75, ksat=0.05),
        dict(watershed='Lionshead_3_14092750', #has streamflow data until 2020
             extent=[-121.82155609130861, 44.63543682256858, -121.58123016357423, 44.80619874687245],
             map_center = [-121.70139312744142, 44.72088078430762],
             map_zoom = 12,
             outlet = [-121.633965695813, 44.7498221140182],
             landuse=None,
             cs=100, erod=0.000001,
             csa=10, mcl=100,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1000.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.75, ksat=0.05),
        dict(watershed='Lionshead_4_14090400', #has streamflow data until 2009
             extent=[-121.82155609130861, 44.63543682256858, -121.58123016357423, 44.80619874687245],
             map_center = [-121.70139312744142, 44.72088078430762],
             map_zoom = 12,
             outlet = [-121.63999812761, 44.718836117739],
             landuse=None,
             cs=100, erod=0.000001,
             csa=10, mcl=100,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1000.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.75, ksat=0.05),

        dict(watershed='Holiday_1_14163000', #has streamflow data until 1990
             extent=[-122.67402648925783, 43.97206324099821, -122.19337463378908, 44.31697048369679],
             map_center = [-122.43370056152345, 44.14476875978378],
             map_zoom = 11,
             outlet = [-122.573316683899, 44.1459419535277],
             landuse=None,
             cs=100, erod=0.000001,
             csa=10, mcl=100,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1000.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.75, ksat=0.05),

        dict(watershed='Archie_1_14319835', 
             extent=[-123.16978454589845, 43.32193074630143, -122.92945861816408, 43.496518702067206],
             map_center = [-123.04962158203126, 43.4092876296596],
             map_zoom = 12,
             outlet = [-123.036900627977, 43.4228952716163],
             landuse=None,
             cs=100, erod=0.000001,
             csa=10, mcl=100,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1000.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.75, ksat=0.05),        
        dict(watershed='Archie_2_14319830 ', 
             extent=[-123.16978454589845, 43.32193074630143, -122.92945861816408, 43.496518702067206],
             map_center = [-123.04962158203126, 43.4092876296596],
             map_zoom = 12,
             outlet = [-123.039494386454, 43.422084007195],
             landuse=None,
             cs=100, erod=0.000001,
             csa=10, mcl=100,
             surf_runoff=0.003, lateral_flow=0.004, baseflow=0.005, sediment=1000.0,
             gwstorage=100, bfcoeff=0.04, dscoeff=0.00, bfthreshold=1.001,
             mid_season_crop_coeff=0.95, p_coeff=0.75, ksat=0.05),     
              ]
    scenarios = [
        dict(wd='CurCond.202009.cl532_gridmet.chn_cs{cs}',
             landuse=None,
             cli_mode='observed', clean=True, build_soils=True, build_landuse=True, build_climates=True,
             lc_lookup_fn='landSoilLookup.csv'),
#        dict(wd='ModSevS.202009.chn_cs{cs}',
#             landuse=[(not_shrub_selector, 118), (shrub_selector, 120)],
#             cli_mode='PRISMadj', clean=True, build_soils=True, build_landuse=True, build_climates=True,
#             lc_lookup_fn='landSoilLookup.csv'),
   ]

    wc = sys.argv[-1]
    if '.py' in wc:
        wc = None

    projects = []
    for scenario in scenarios:
        for watershed in watersheds:
            projects.append(deepcopy(watershed))
            
            projects[-1]['cfg'] = scenario.get('cfg', 'seattle-snow')
            projects[-1]['landuse'] = scenario['landuse']
            projects[-1]['cli_mode'] = scenario.get('cli_mode', 'observed')
            projects[-1]['clean'] = scenario['clean']
            projects[-1]['build_soils'] = scenario['build_soils']
            projects[-1]['build_landuse'] = scenario['build_landuse']
            projects[-1]['build_climates'] = scenario['build_climates']
            projects[-1]['lc_lookup_fn'] = scenario['lc_lookup_fn']
            projects[-1]['wd'] = 'oregon_{watershed}_{scenario}' \
                .format(watershed=watershed['watershed'], scenario=scenario['wd']) \
                .format(cs=watershed['cs'])

    for proj in projects:
        config = proj['cfg']
        watershed_name = proj['watershed']
        wd = proj['wd']
        ksat = proj['ksat']

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
        lc_lookup_fn = proj['lc_lookup_fn']

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
            topaz = Topaz.getInstance(wd)
            topaz.build_channels(csa=csa, mcl=mcl)
            topaz.set_outlet(*outlet)
            sleep(0.5)

            log_print('building subcatchments')
            topaz.build_subcatchments()

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
            landuse = Landuse.getInstance(wd)

            log_print('setting default landuses')

            if default_landuse is not None:
                log_print('setting default landuse')

                tops = []
                for selector, dom in default_landuse:
                    _topaz_ids = selector(landuse, None)
                    
                    bare_tops = bare_or_sodgrass_or_bunchgrass_selector(landuse, None)
                    _topaz_ids = [top for top in _topaz_ids if top not in bare_tops]
                    
                    landuse.modify(_topaz_ids, dom)
                    tops.extend(_topaz_ids)

        soils = Soils.getInstance(wd)
        if build_soils:
            log_print('building soils')
            soils.mode = SoilsMode.Gridded
            soils.build() 
            #soils.build_statsgo()

            soils = Soils.getInstance(wd)

            ksat_mod = 'f'

            _domsoil_d = soils.domsoil_d
            _soils = soils.soils
            for topaz_id, ss in watershed._subs_summary.items():
                lng, lat = ss.centroid.lnglat

                dom = _domsoil_d[str(topaz_id)]
                _soil = deepcopy(_soils[dom])

                _dom = '{dom}-{ksat_mod}' \
                    .format(dom=dom, ksat_mod=ksat_mod)
                
                if _dom not in _soils:
                    _soil_fn = '{dom}.sol'.format(dom=_dom)
                    log_print(_soil_fn)
                    src_soil_fn = _join(_soil.soils_dir, _soil.fname)
                    dst_soil_fn = _join(_soil.soils_dir, _soil_fn)
                    log_print(src_soil_fn, dst_soil_fn, ksat, _dom)
                    modify_ksat(src_soil_fn, dst_soil_fn, ksat)

                    _soil.fname = _soil_fn
                    _soils[_dom] = _soil

                _domsoil_d[str(topaz_id)] = _dom

            soils.lock()
            soils.domsoil_d = _domsoil_d
            soils.soils = _soils
            soils.dump_and_unlock()
            
            soils = Soils.getInstance(wd)

            if _exists(_join(wd, 'lt.nodb')):
                location = SeattleMod.getInstance(wd)
                location.modify_soils(default_wepp_type='Volcanic', lc_lookup_fn=lc_lookup_fn)

            climate = Climate.getInstance(wd)
            if build_climates:
                log_print('building climate')

            if cli_mode == 'observed':
                log_print('building observed')
                if 'linveh' in wd:
                    climate.climate_mode = ClimateMode.ObservedDb
                    climate.climate_spatialmode = ClimateSpatialMode.Multiple
                    climate.input_years = 21

                    climate.lock()
                    lng, lat = watershed.centroid

                    cli_path = lvdm.closest_cli(lng, lat)
                    _dir, cli_fn = _split(cli_path)
                    shutil.copyfile(cli_path, _join(climate.cli_dir, cli_fn))
                    climate.cli_fn = cli_fn

                    par_path = lvdm.par_path
                    _dir, par_fn = _split(par_path)
                    shutil.copyfile(par_path, _join(climate.cli_dir, par_fn))
                    climate.par_fn = par_fn

                    sub_par_fns = {}
                    sub_cli_fns = {}
                    for topaz_id, ss in watershed._subs_summary.items():
                        log_print(topaz_id)
                    lng, lat = ss.centroid.lnglat

                    cli_path = lvdm.closest_cli(lng, lat)
                    _dir, cli_fn = _split(cli_path)
                    run_cli_path = _join(climate.cli_dir, cli_fn)
                    if not _exists(run_cli_path):
                        shutil.copyfile(cli_path, run_cli_path)
                    sub_cli_fns[topaz_id] = cli_fn
                    sub_par_fns[topaz_id] = par_fn

                    climate.sub_par_fns = sub_par_fns
                    climate.sub_cli_fns = sub_cli_fns
                    climate.dump_and_unlock()

                elif 'daymet' in wd:
                    stations = climate.find_closest_stations()
                    climate.climatestation = stations[0]['id']

                    climate.climate_mode = ClimateMode.Observed
                    climate.climate_spatialmode = ClimateSpatialMode.Multiple
                    climate.set_observed_pars(start_year=1990, end_year=2017)

                    climate.build(verbose=1)

                    climate.lock()

                    cli_dir = climate.cli_dir
                    adj_cli_fn = _daymet_cli_adjust(cli_dir, climate.cli_fn, watershed_name)
                    climate.cli_fn = adj_cli_fn

                    for topaz_id in climate.sub_cli_fns:
                        adj_cli_fn = _daymet_cli_adjust(cli_dir, climate.sub_cli_fns[topaz_id], watershed_name)
                        climate.sub_cli_fns[topaz_id] = adj_cli_fn

                    climate.dump_and_unlock()

                elif 'gridmet' in wd:
                    log_print('building gridmet')
                    stations = climate.find_closest_stations()
                    climate.climatestation = stations[0]['id']

                    climate.climate_mode = ClimateMode.GridMetPRISM
                    climate.climate_spatialmode = ClimateSpatialMode.Multiple
                    climate.set_observed_pars(start_year=1980, end_year=2019)

                    climate.build(verbose=1)

                    climate.lock()
                    
                    cli_dir = climate.cli_dir
                    adj_cli_fn = _gridmet_cli_adjust(cli_dir, climate.cli_fn, watershed_name)
                    climate.cli_fn = adj_cli_fn

                    for topaz_id in climate.sub_cli_fns:
                        adj_cli_fn = _gridmet_cli_adjust(cli_dir, climate.sub_cli_fns[topaz_id], watershed_name)
                        climate.sub_cli_fns[topaz_id] = adj_cli_fn

                    climate.dump_and_unlock()

            elif cli_mode == 'future':
                log_print('building gridmet')
                stations = climate.find_closest_stations()
                climate.climatestation = stations[0]['id']

                climate.climate_mode = ClimateMode.Future
                climate.climate_spatialmode = ClimateSpatialMode.Multiple
                climate.set_future_pars(start_year=2006, end_year=2099)

                climate.build(verbose=1)

                climate.lock()

                cli_dir = climate.cli_dir
                adj_cli_fn = _gridmet_cli_adjust(cli_dir, climate.cli_fn, watershed_name)
                climate.cli_fn = adj_cli_fn

                for topaz_id in climate.sub_cli_fns:
                    adj_cli_fn = _gridmet_cli_adjust(cli_dir, climate.sub_cli_fns[topaz_id], watershed_name)
                    climate.sub_cli_fns[topaz_id] = adj_cli_fn

                climate.dump_and_unlock()

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

            arc_export(wd)
