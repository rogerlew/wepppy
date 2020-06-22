import os
import shutil
from os.path import exists as _exists
from os.path import split as _split
from pprint import pprint
from time import time
from time import sleep
from copy import deepcopy

import wepppy
from wepppy.soils.utils import modify_ksat
from wepppy.nodb import *
from os.path import join as _join
from wepppy.wepp.out import TotalWatSed
from wepppy.export import arc_export

from wepppy.nodb.mods.portland.livneh_daily_observed import LivnehDataManager
from wepppy.nodb.mods.portland.bedrock import BullRunBedrock

from osgeo import gdal, osr
gdal.UseExceptions()

from .utils import *

if __name__ == '__main__':

    lvdm = LivnehDataManager()

    projects = [
               dict(wd='SouthFork',
                    extent=[-122.22908020019533, 45.268121280142886, -121.74842834472658, 45.60539133629575],
                    map_center=[-121.98875427246095, 45.43700828867391],
                    map_zoom=11,
                    outlet=[-122.1083333, 45.444722],
                    landuse=None,
                    cs=50, erod=0.000001,
                    csa=5, mcl=65),
               dict(wd='CedarCreek',
                    extent=[-122.22908020019533, 45.268121280142886, -121.74842834472658, 45.60539133629575],
                    map_center=[-121.98875427246095, 45.43700828867391],
                    map_zoom=11,
                    outlet=[-122.03486546021158, 45.45789702345389],
                    landuse=None,
                    cs=50, erod=0.000001,
                    csa=5, mcl=65),
                dict(wd='BlazedAlder',
                     extent=[-122.22908020019533, 45.268121280142886, -121.74842834472658, 45.60539133629575],
                     map_center=[-121.98875427246095, 45.43700828867391],
                     map_zoom=11,
                     outlet=[-121.89124077457025, 45.45220046527376],
                     landuse=None,
                     cs=50, erod=0.000001,
                     csa=5, mcl=65),
                dict(wd='FirCreek',
                     extent=[-122.22908020019533, 45.268121280142886, -121.74842834472658, 45.60539133629575],
                     map_center=[-121.98875427246095, 45.43700828867391],
                     map_zoom=11,
                     outlet=[-122.02581486422827, 45.47989113970676],
                     landuse=None,
                     cs=50, erod=0.000001,
                     csa=5, mcl=65),
                dict(wd='BRnearMultnoma',
                     extent=[-122.22908020019533, 45.268121280142886, -121.74842834472658, 45.60539133629575],
                     map_center=[-121.98875427246095, 45.43700828867391],
                     map_zoom=11,
                     outlet=[-122.01099283401598, 45.498468197226025],
                     landuse=None,
                     cs=50, erod=0.000001,
                     csa=10, mcl=100),
               dict(wd='NorthFork',
                     extent=[-122.22908020019533, 45.268121280142886, -121.74842834472658, 45.60539133629575],
                     map_center=[-121.98875427246095, 45.43700828867391],
                     map_zoom=11,
                     outlet=[-122.03554486123724, 45.49455561832556],
                     landuse=None,
                     cs=50, erod=0.000001,
                     csa=10, mcl=100),
                dict(wd='LittleSandy',
                     extent=[-122.22908020019533, 45.268121280142886, -121.74842834472658, 45.60539133629575],
                     map_center=[-121.98875427246095, 45.43700828867391],
                     map_zoom=11,
                     outlet=[-122.17147271631961, 45.415421615033246],
                     landuse=None,
                     cs=50, erod=0.000001,
                     csa=10, mcl=100)
               ]


    scenarios = [
               dict(wd='CurCond.2020.cl532.chn_cs{cs}',
                    landuse=None),
               dict(wd='PrescFireS.2020.chn_cs{cs}',
                    landuse=[(not_shrub_selector, 110), (shrub_selector, 122)]),
               dict(wd='LowSevS.2020.chn_cs{cs}',
                    landuse=[(not_shrub_selector, 106), (shrub_selector, 121)]),
               dict(wd='ModSevS.2020.chn_cs{cs}',
                    landuse=[(not_shrub_selector, 118), (shrub_selector, 120)]),
               dict(wd='HighSevS.2020.chn_cs{cs}',
                    landuse=[(not_shrub_selector, 105), (shrub_selector, 119)]),
                ]
    v = 'linveh_closest'
    config = 'portland.cfg'
    top_pars=((10,100),)
    erod_pars = ((10, 1e-6), (10, 0.3), (100, 1e-6), (100, 0.3))
    for proj in projects:
        extent = proj['extent']
        map_center = proj['map_center']
        map_zoom = proj['map_zoom']
        outlet = proj['outlet']
        default_landuse = proj['landuse']

        for csa, mcl in top_pars:
            for cs, erod in erod_pars:
                wd = '{wd}_{v}_csa{csa}_mcl{mcl}_cs{cs}_erod{erod}'\
                .format(wd=proj['wd'], v=v, csa=csa, mcl=mcl, cs=cs, erod=erod)

                print(wd)

                if _exists(wd):
                    print()
                    shutil.rmtree(wd)
                os.mkdir(wd)

                #ron = Ron(wd, "lt-fire.cfg")
                #ron = Ron(wd, "lt.cfg")
                ron = Ron(wd, config)
                ron.name = wd
                ron.set_map(extent, map_center, zoom=map_zoom)
                ron.fetch_dem()

                topaz = Topaz.getInstance(wd)
                topaz.build_channels(csa=csa, mcl=mcl)
                topaz.set_outlet(*outlet)
                sleep(0.5)
                topaz.build_subcatchments()

                watershed = Watershed.getInstance(wd)
                watershed.abstract_watershed()
                translator = watershed.translator_factory()
                topaz_ids = [top.split('_')[1] for top in translator.iter_sub_ids()]

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

                bullrun_bedrock = BullRunBedrock()
                _domsoil_d = soils.domsoil_d
                _soils = soils.soils
                for topaz_id, ss in watershed._subs_summary.items():
                    lng, lat = ss.centroid.lnglat

                    bedrock = bullrun_bedrock.get_bedrock(lng, lat)
                    ksat = bedrock['ksat']
                    bedrock_name = bedrock['Unit_Name'].replace(' ', '_')

                    dom = _domsoil_d[str(topaz_id)]
                    soil = deepcopy(_soils[dom])

                    dom = '{dom}-{bedrock_name}'.format(dom=dom, bedrock_name=bedrock_name)
                    src_soil_fn = _join(soil.soils_dir, soil.fname)
                    dst_soil_fn = _join(soil.soils_dir, '{dom}.sol'.format(dom=dom))
                    modify_ksat(src_soil_fn, dst_soil_fn, ksat)

                    soil.fn = '{dom}.sol'.format(dom=dom)
                    _domsoil_d[str(topaz_id)] = dom
                    _soils[dom] = soil

                soils.lock()
                soils.domsoil_d = _domsoil_d
                soils.soils = _soils
                soils.dump_and_unlock()
                soils = Soils.getInstance(wd)

                climate = Climate.getInstance(wd)
                climate.climate_mode = ClimateMode.ObservedDb
                climate.climate_spatialmode = ClimateSpatialMode.Multiple
                climate.input_years = 21

                stations = climate.find_closest_stations()
                climate.input_years = 100
                climate.climatestation = stations[0]['id']

                climate.climate_mode = ClimateMode.ObservedDb
                climate.climate_spatialmode = ClimateSpatialMode.Multiple

                climate.build(verbose=1)
                # build a climate for the channels.

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

                wepp = Wepp.getInstance(wd)
                wepp.prep_hillslopes()
                wepp.run_hillslopes()

                wepp = Wepp.getInstance(wd)
                wepp.prep_watershed(erodibility=erod, critical_shear=cs)
                wepp.run_watershed()
                loss_report = wepp.report_loss()

                fn = _join(ron.export_dir, 'totalwatsed.csv')

                totwatsed = TotalWatSed(_join(ron.output_dir, 'totalwatsed.txt'),
                                        wepp.baseflow_opts, wepp.phosphorus_opts)
                totwatsed.export(fn)
                assert _exists(fn)

                arc_export(wd)

