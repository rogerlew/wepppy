# standard library
import os

from os.path import join as _join
from os.path import exists as _exists
from os.path import split as _split

from subprocess import Popen, PIPE
from datetime import datetime
import time

import pickle

from glob import glob

import shutil

# non-standard
import jsonpickle

import numpy as np

from osgeo import osr
from osgeo import gdal
from osgeo.gdalconst import *

import wepppy

# wepppy
from wepppy.wepp.runner import (
    make_hillslope_run,
    run_hillslope,
    make_flowpath_run,
    run_flowpath,
    make_watershed_run,
    run_watershed
)
from wepppy.wepp.management import (
    get_channel,
    merge_managements,
)

from wepppy.all_your_base import isfloat, read_arc, wgs84_proj4, parse_datetime
from wepppy.wepp.out import Loss, Ebe, PlotFile, Chnwb
from wepppy.wepp.stats import ChannelWatbal, HillslopeWatbal, ReturnPeriods

# wepppy submodules
from wepppy.wepp.stats.frq_flood import FrqFlood
from .base import NoDbBase, TriggerEvents
from .landuse import Landuse, LanduseMode
from .soils import Soils, SoilsMode
from .climate import Climate, ClimateMode
from .watershed import Watershed
from .topaz import Topaz
from .wepppost import  WeppPost


class BaseflowOpts(object):
    def __init__(self):
        """
        Stores the coeffs that go into gwcoeff.txt
        """
        # Initial groundwater storage (mm)
        self.gwstorage = 200 
        
        # Baseflow coefficient (per day)
        self.bfcoeff = 0.04

        # Deep seepage coefficient (per day)        
        self.dscoeff = 0 
        
        # Watershed groundwater baseflow threshold area (ha)
        self.bfthreshold = 1 

    def parse_inputs(self, kwds):
        self.gwstorage = float(kwds['gwstorage'])
        self.bfcoeff = float(kwds['bfcoeff'])
        self.dscoeff = float(kwds['dscoeff'])
        self.bfthreshold = float(kwds['bfthreshold'])
        
    @property
    def contents(self):
        return ( 
            '{0.gwstorage}\tInitial groundwater storage (mm)\n'
            '{0.bfcoeff}\tBaseflow coefficient (per day)\n'
            '{0.dscoeff}\tDeep seepage coefficient (per day)\n'
            '{0.bfthreshold}\tWatershed groundwater baseflow threshold area (ha)\n\n'
            .format(self) 
        )


def validate_phosphorus_txt(fn):

    with open(fn) as fp:
        lines = fp.readlines()
    lines = [L for L in lines if not L.strip() == '']
    if 'Phosphorus concentration' != lines[0].strip():
        return False
     
    opts = [isfloat(L.split()[0]) for L in lines[1:]]
    if len(opts) != 4:
        return False
        
    if not all(opts):
        return False
        
    return True


class PhosphorusOpts(object):
    def __init__(self):
        # Surface runoff concentration (mg/l)
        self.surf_runoff = None  # 0.0118000004441
        
        # Subsurface lateral flow concentration (mg/l)
        self.lateral_flow = None  # 0.0109999999404
        
        # Baseflow concentration (mg/l)
        self.baseflow = None  # 0.0196000002325
        
        # Sediment concentration (mg/kg)
        self.sediment = None  # 1024

    def parse_inputs(self, kwds):
        # noinspection PyBroadException
        try:
            self.surf_runoff = float(kwds['surf_runoff'])
            self.lateral_flow = float(kwds['lateral_flow'])
            self.baseflow = float(kwds['baseflow'])
            self.sediment = float(kwds['sediment'])
        except Exception:
            pass
    
    @property
    def isvalid(self):
        return isfloat(self.surf_runoff) and \
               isfloat(self.lateral_flow) and \
               isfloat(self.baseflow) and \
               isfloat(self.sediment)
        
    @property
    def contents(self):
        return ( 
            'Phosphorus concentration\n'
            '{0.surf_runoff}\tSurface runoff concentration (mg/l)\n'
            '{0.lateral_flow}\tSubsurface lateral flow concentration (mg/l)\n'
            '{0.baseflow}\tBaseflow concentration (mg/l)\n'
            '{0.sediment}\tSediment concentration (mg/kg)\n\n'
            .format(self) 
        )

    def asdict(self):
        return dict(surf_runoff=self.surf_runoff,
                    lateral_flow=self.lateral_flow,
                    baseflow=self.baseflow,
                    sediment=self.sediment)


class WeppNoDbLockedException(Exception):
    pass


class Wepp(NoDbBase):
    __name__ = 'Wepp'

    def __init__(self, wd, cfg_fn):
        super(Wepp, self).__init__(wd, cfg_fn)

        self.lock()

        # noinspection PyBroadException
        try:
            wepp_dir = self.wepp_dir
            if not _exists(wepp_dir):
                os.mkdir(wepp_dir)

            self.phosphorus_opts = PhosphorusOpts()
            self.baseflow_opts = BaseflowOpts()
            self.run_flowpaths = False
            self.wepp_ui = False
            self.loss_grid_d_path = None
            self.status_log = _join(self.runs_dir, 'status.log')

            self.clean()

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise
    #
    # Required for NoDbBase Subclass
    #

    # noinspection PyPep8Naming
    @staticmethod
    def getInstance(wd):
        with open(_join(wd, 'wepp.nodb')) as fp:
            db = jsonpickle.decode(fp.read())
            assert isinstance(db, Wepp)

            if os.path.abspath(wd) != os.path.abspath(db.wd):
                db.wd = wd
                db.lock()
                db.dump_and_unlock()

            return db

    @property
    def _nodb(self):
        return _join(self.wd, 'wepp.nodb')

    @property
    def _lock(self):
        return _join(self.wd, 'wepp.nodb.lock')

    def parse_inputs(self, kwds):
        self.lock()

        # noinspection PyBroadException
        try:
            self.baseflow_opts.parse_inputs(kwds)
            self.phosphorus_opts.parse_inputs(kwds)
            
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise
            
    @property
    def has_run(self):
        output_dir = self.output_dir
        loss_pw0 = _join(output_dir, 'loss_pw0.txt')
        return _exists(loss_pw0)

    #
    # Log methods, TODO: make Mixin
    #
    def _calc_log_elapsed(self):
        with open(self.status_log) as fp:
            lines = fp.readlines()
            r0 = parse_datetime(lines[0])
            t0 = parse_datetime(lines[-1])

        r_elapsed = datetime.now() - r0
        t_elapsed = datetime.now() - t0

        return r_elapsed, t_elapsed, lines[-1]

    def get_log_last(self):
        r_elapsed, t_elapsed, s = self._calc_log_elapsed()

        if s.strip().endswith('...'):
            return '{} ({}s | {}s)'.format(s, t_elapsed.total_seconds(), r_elapsed.total_seconds())
        else:
            return s

    def log(self, msg):
        t0 = datetime.strftime(datetime.now(), '%Y-%m-%dT%H:%M:%S.%f')
        with open(self.status_log, 'a') as fp:
            fp.write('[{}] {}'.format(t0, msg))

    def log_done(self):
        r_elapsed, t_elapsed, s = self._calc_log_elapsed()

        with open(self.status_log, 'a') as fp:
            fp.write('done. ({}s | {}s)\n'.format(t_elapsed.total_seconds(), r_elapsed.total_seconds()))

    #
    # hillslopes
    #
    def prep_hillslopes(self):
        self.log('Prepping Hillslopes... ')
    
        translator = Watershed.getInstance(self.wd).translator_factory()
        
        # get translator
        self._prep_slopes(translator)
        self._prep_managements(translator)
        self._prep_soils(translator)
        self._prep_climates(translator)
        self._make_hillslope_runs(translator)
        self._prep_frost()
        self._prep_phosphorus()
        self._prep_baseflow()
        self._prep_wepp_ui()

        self.log_done()

    def _prep_wepp_ui(self):
        fn = _join(self.runs_dir, 'wepp_ui.txt')

        if self.wepp_ui:
            with open(fn, 'w') as fp:
                fp.write('')
        else:
            if _exists(fn):
                os.remove(fn)

    def _prep_frost(self):
        fn = _join(self.runs_dir, 'frost.txt')
        with open(fn, 'w') as fp:
            fp.write('1  1  1\n')
            fp.write('1.0   1.0  1.0   0.5\n\n')
        
    def _prep_phosphorus(self):

        # noinspection PyMethodFirstArgAssignment
        self = self.getInstance(self.wd)
        
        fn = _join(self.runs_dir, 'phosphorus.txt')
        if self.phosphorus_opts.isvalid:
            with open(fn, 'w') as fp:
                fp.write(self.phosphorus_opts.contents)
        
        if _exists(fn):
            if not validate_phosphorus_txt(fn):
                os.remove(fn)
                
    def _prep_baseflow(self):
        fn = _join(self.runs_dir, 'gwcoeff.txt')
        with open(fn, 'w') as fp:
            fp.write(self.baseflow_opts.contents)
            
    def clean(self):
        try:
            if _exists(self.status_log):
                os.remove(self.status_log)
        except:
            self.status_log = _join(self.runs_dir, 'status.log')

        runs_dir = self.runs_dir
        if not _exists(runs_dir):
            os.mkdir(runs_dir)
            
        output_dir = self.output_dir
        if not _exists(output_dir):
            os.mkdir(output_dir)

        plot_dir = self.plot_dir
        if not _exists(plot_dir):
            os.mkdir(plot_dir)
            
        stats_dir = self.stats_dir
        if not _exists(stats_dir):
            os.mkdir(stats_dir)

        fp_runs_dir = self.fp_runs_dir
        if not _exists(fp_runs_dir):
            os.makedirs(fp_runs_dir)

        fp_output_dir = self.fp_output_dir
        if not _exists(fp_output_dir):
            os.mkdir(fp_output_dir)
            
    def _prep_slopes(self, translator):
        watershed = Watershed.getInstance(self.wd)
        wat_dir = self.wat_dir
        runs_dir = self.runs_dir
        fp_runs_dir = self.fp_runs_dir
        
        for topaz_id, _ in watershed.sub_iter():
            wepp_id = translator.wepp(top=int(topaz_id))
            
            src_fn = _join(wat_dir, 'hill_{}.slp'.format(topaz_id))
            dst_fn = _join(runs_dir, 'p%i.slp' % wepp_id)
            shutil.copyfile(src_fn, dst_fn)

            # use getattr for old runs that don't have a run_flowpaths attribute
            if getattr(self, 'run_flowpaths', False):
                for fp in watershed.fps_summary(topaz_id):
                    fn = '{}.slp'.format(fp)
                    src_fn = _join(wat_dir, fn)
                    dst_fn = _join(fp_runs_dir, fn)
                    shutil.copyfile(src_fn, dst_fn)
            
    def _prep_managements(self, translator):
        landuse = Landuse.getInstance(self.wd)
        years = Climate.getInstance(self.wd).input_years
        watershed = Watershed.getInstance(self.wd)
        runs_dir = self.runs_dir
        fp_runs_dir = self.fp_runs_dir

        for topaz_id, man_summary in landuse.sub_iter():
            wepp_id = translator.wepp(top=int(topaz_id))
            dst_fn = _join(runs_dir, 'p%i.man' % wepp_id)

            management = man_summary.get_management()
            multi = management.build_multiple_year_man(years)
            fn_contents = str(multi)

            with open(dst_fn, 'w') as fp:
                fp.write(fn_contents)

            if getattr(self, 'run_flowpaths', False):
                for fp in watershed.fps_summary(topaz_id):
                    dst_fn = _join(fp_runs_dir, '{}.man'.format(fp))

                    with open(dst_fn, 'w') as fp:
                        fp.write(fn_contents)

    def _prep_soils(self, translator):
        soils = Soils.getInstance(self.wd)
        soils_dir = self.soils_dir
        watershed = Watershed.getInstance(self.wd)
        runs_dir = self.runs_dir
        fp_runs_dir = self.fp_runs_dir

        for topaz_id, soil in soils.sub_iter():
            wepp_id = translator.wepp(top=int(topaz_id))
            src_fn = _join(soils_dir, soil.fname)
            dst_fn = _join(runs_dir, 'p%i.sol' % wepp_id)
            shutil.copyfile(src_fn, dst_fn)

            if getattr(self, 'run_flowpaths', False):
                for fp in watershed.fps_summary(topaz_id):
                    dst_fn = _join(fp_runs_dir, '{}.sol'.format(fp))
                    shutil.copyfile(src_fn, dst_fn)

    def _prep_climates(self, translator):
        watershed = Watershed.getInstance(self.wd)
        climate = Climate.getInstance(self.wd)
        cli_dir = self.cli_dir
        runs_dir = self.runs_dir
        fp_runs_dir = self.fp_runs_dir

        if climate.climate_mode == ClimateMode.Localized:
            for topaz_id, cli_fn in climate.sub_cli_fns.items():
                wepp_id = translator.wepp(top=int(topaz_id))
                dst_fn = _join(runs_dir, 'p%i.cli' % wepp_id)
                cli_path = _join(cli_dir, cli_fn)
                shutil.copyfile(cli_path, dst_fn)

                if getattr(self, 'run_flowpaths', False):
                    for fp in watershed.fps_summary(topaz_id):
                        dst_fn = _join(fp_runs_dir, '{}.cli'.format(fp))
                        shutil.copyfile(cli_path, dst_fn)

        else:
            for topaz_id, _ in watershed.sub_iter():
                wepp_id = translator.wepp(top=int(topaz_id))
                dst_fn = _join(runs_dir, 'p%i.cli' % wepp_id)
                cli_path = _join(cli_dir, climate.cli_fn)
                shutil.copyfile(cli_path, dst_fn)

                if getattr(self, 'run_flowpaths', False):
                    for fp in watershed.fps_summary(topaz_id):
                        dst_fn = _join(fp_runs_dir, '{}.cli'.format(fp))
                        shutil.copyfile(cli_path, dst_fn)
                
    def _make_hillslope_runs(self, translator):
        watershed = Watershed.getInstance(self.wd)
        runs_dir = self.runs_dir
        fp_runs_dir = self.fp_runs_dir
        years = Climate.getInstance(self.wd).input_years

        for topaz_id, _ in watershed.sub_iter():
            wepp_id = translator.wepp(top=int(topaz_id))
            
            make_hillslope_run(wepp_id, years, runs_dir)

            if getattr(self, 'run_flowpaths', False):
                for fp in watershed.fps_summary(topaz_id):
                    make_flowpath_run(fp, years, fp_runs_dir)

    def run_hillslopes(self):
        self.log('Running Hillslopes\n')
        translator = Watershed.getInstance(self.wd).translator_factory()
        watershed = Watershed.getInstance(self.wd)
        topaz = Topaz.getInstance(self.wd)
        runs_dir = os.path.abspath(self.runs_dir)
        fp_runs_dir = self.fp_runs_dir

        if getattr(self, 'run_flowpaths', False):
            # data structure to contain flowpath soil loss results
            # keys are (x, y) pixel locations
            # values are lists of soil loss/deposition from flow paths
            loss_grid_d = {}

        sub_n = watershed.sub_n
        for i, (topaz_id, _) in enumerate(watershed.sub_iter()):
            self.log('  topaz={} (hill {} of {})... '.format(topaz_id, i+1, sub_n))

            wepp_id = translator.wepp(top=int(topaz_id))
            assert run_hillslope(wepp_id, runs_dir)

            self.log_done()

            # run flowpaths if specified
            if getattr(self, 'run_flowpaths', False):

                # iterate over the flowpath ids
                fps_summary = watershed.fps_summary(topaz_id)
                fp_n = len(fps_summary)
                for j, fp in enumerate(fps_summary):
                    self.log('    flowpath={} (hill {} of {}, fp {} of {})... '.format(fp, i+1, sub_n, j + 1, fp_n))

                    # run wepp for flowpath
                    assert run_flowpath(fp, fp_runs_dir)

                    # read plot file data
                    plo = PlotFile(_join(self.fp_output_dir, '%s.plot.dat' % fp))

                    # interpolate soil loss to cell locations of flowpath
                    d = fps_summary[fp].distance_p
                    loss = plo.interpolate(d)

                    # store non-zero values in loss_grid_d
                    for L, coord in zip(loss, fps_summary[fp].coords):
                        if L != 0.0:
                            if coord in loss_grid_d:
                                loss_grid_d[coord].append(L)
                            else:
                                loss_grid_d[coord] = [L]

                    self.log_done()

        if getattr(self, 'run_flowpaths', False):
            self.log('Processing flowpaths... ')

            self._pickle_loss_grid_d(loss_grid_d)
            self.make_loss_grid()

            self.log_done()

    def _pickle_loss_grid_d(self, loss_grid_d):
        plot_dir = self.plot_dir
        loss_grid_d_path = _join(plot_dir, 'loss_grid_d.pickle')

        with open(loss_grid_d_path, 'wb') as fp:
            pickle.dump(loss_grid_d, fp)

        self.lock()

        # noinspection PyBroadException
        try:
            self.loss_grid_d_path = loss_grid_d_path
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def loss_grid_d(self):
        loss_grid_d_path = self.loss_grid_d_path

        assert loss_grid_d_path is not None
        assert _exists(loss_grid_d_path)

        with open(loss_grid_d_path, 'rb') as fp:
            _loss_grid_d = pickle.load(fp)

        return _loss_grid_d

    #
    # watershed
    #    
    def prep_watershed(self):
        self.log('Prepping Watershed... ')

        watershed = Watershed.getInstance(self.wd)
        translator = watershed.translator_factory()

        self._prep_structure(translator)
        self._prep_channel_slopes()
        self._prep_channel_chn(translator)
        self._prep_impoundment()
        self._prep_channel_soils(translator)
        self._prep_channel_climate(translator)
        self._prep_channel_input()
        self._prep_watershed_managements(translator)
        self._make_watershed_run(translator)

        self.log_done()

    def _prep_structure(self, translator):
        watershed = Watershed.getInstance(self.wd)
        structure = watershed.structure
        runs_dir = self.runs_dir
        
        s = ['99.1']
        for L in structure:
            s2 = "2    {} {} {}   "\
                 .format(*[translator.wepp(top=v) for v in L[1:4]])
                
            s2 += "{} {} {}   {} {} {}"\
                  .format(*[translator.wepp(top=v) for v in L[4:]])
#                .format(*[translator.chn_enum(top=v) for v in L[4:]])
                
            s.append(s2)
            
        with open(_join(runs_dir, 'pw0.str'), 'w') as fp:
            fp.write('\n'.join(s) + '\n')
            
    def _prep_channel_slopes(self):
        wat_dir = self.wat_dir
        runs_dir = self.runs_dir
        
        shutil.copyfile(_join(wat_dir, 'channels.slp'),
                        _join(runs_dir, 'pw0.slp'))
                        
    def _prep_channel_chn(self, translator):
        assert translator is not None

        watershed = Watershed.getInstance(self.wd)
        runs_dir = self.runs_dir
        
        chn_n = watershed.chn_n

        fp = open(_join(runs_dir, 'pw0.chn'), 'w')
        fp.write('99.1\r\n{chn_n}\r\n4\r\n1.500000\r\n'
                 .format(chn_n=chn_n))
        
        for topaz_id, chn_summary in watershed.chn_iter():
            chn_key = chn_summary.channel_type
            chn_d = get_channel(chn_key)
            contents = chn_d['contents']
            fp.write(contents)
            fp.write('\n')
        fp.close()
        
    def _prep_impoundment(self):
        runs_dir = self.runs_dir
        with open(_join(runs_dir, 'pw0.imp'), 'w') as fp:
            fp.write('99.1\n0\n')

    def _prep_channel_input(self):

        wat = Watershed.getInstance(self.wd)
        chn_n = wat.chn_n
        sub_n = wat.sub_n
        total = chn_n + sub_n

        runs_dir = self.runs_dir
        with open(_join(runs_dir, 'chan.inp'), 'w') as fp:
            fp.write('1 600\n0\n1\n{}\n'.format(total))

    def _prep_channel_soils(self, translator):
        soils = Soils.getInstance(self.wd)
        soils_dir = self.soils_dir
        runs_dir = self.runs_dir
        
        chn_n = Watershed.getInstance(self.wd).chn_n
        
        # build list of soils
        soil_c = []
        for topaz_id, soil in soils.chn_iter():
            soil_c.append((translator.chn_enum(top=int(topaz_id)), soil))
        soil_c.sort(key=lambda x: x[0])
        
        versions = []
        for chn_enum, soil in soil_c:
            soil_fn = _join(soils_dir, soil.fname)
            lines = open(soil_fn).readlines()
            version = lines[0].replace('#', '').strip()
            versions.append(version)
            
        versions = set(versions)
        if len(versions) > 1:
            raise Exception('Do not know how to merge '
                            'soils of different versions')

        if len(versions) == 0:
            raise Exception('Could not find any soils for channels.')

        version = versions.pop()
            
        if '7778' in version:
            # iterate over soils and append them together
            fp = open(_join(runs_dir, 'pw0.sol'), 'w')
            fp.write('7778.0\ncomments: soil file\n{chn_n} 1\n'
                     .format(chn_n=chn_n))
            i = 0
            for chn_enum, soil in soil_c:
                soil_fn = _join(soils_dir, soil.fname)
                lines = open(soil_fn).readlines()
                for i, line in enumerate(lines):
                    line = ''.join([v.strip() for v in line.split()])
                    if line == '11':
                        break
                        
#                fp.write(''.join(lines[i+1:]) + '\n')
                fp.write("""\
Bidart_1 MPM 1 0.02 0.75 4649000 0.20854 100.000
400	1.5	0.5	1	0.242	0.1145	66.8	7	3	11.3	20
1 10000 0.0001
""")
                    
            fp.close()
            
        else:
            # iterate over soils and append them together
            fp = open(_join(runs_dir, 'pw0.sol'), 'w')
            fp.write('2006.2\ncomments: soil file\n{chn_n} 1\n'
                     .format(chn_n=chn_n))
            for chn_enum, soil in soil_c:
                soil_fn = _join(soils_dir, soil.fname)
                lines = open(soil_fn).readlines()
                lines = [line for line in lines if not line.strip().startswith('#')]
                        
                fp.write(''.join(lines[3:6]))
                    
            fp.close()
        
    def _prep_watershed_managements(self, translator):
        landuse = Landuse.getInstance(self.wd)
        runs_dir = self.runs_dir
    
        years = Climate.getInstance(self.wd).input_years

        """
        # build list of managements
        mans_c = []
        for topaz_id, man in landuse.chn_iter():
            man_obj = get_management(man.key)
            chn_enum = translator.chn_enum(top=int(topaz_id))
            mans_c.append((chn_enum, man_obj))
            
        # sort list of (chn_enum, Management) by chn_enum
        mans_c.sort(key=lambda x: x[0]) 
        mans_c = [v for k, v in mans_c]  # <- list of Management
        
        if len(mans_c) > 1:
            chn_man = merge_managements(mans_c)
        else:
            chn_man = mans_c[0]
            
        """
        keys = [man.key for topaz_id, man in landuse.chn_iter()]
        from collections import Counter
        mankey = Counter(keys).most_common()[0][0]

        chn_man = landuse.managements[str(mankey)].get_management()
        if len(keys) > 1:
            chn_man.make_multiple_ofe(len(keys))

        if years > 1:
            multi = chn_man.build_multiple_year_man(years)
            fn_contents = str(multi)
        else:
            fn_contents = str(chn_man)

        with open(_join(runs_dir, 'pw0.man'), 'w') as fp:
            fp.write(fn_contents)

    def _prep_channel_climate(self, translator):
        assert translator is not None

        runs_dir = self.runs_dir
        climate = Climate.getInstance(self.wd)
        dst_fn = _join(runs_dir, 'pw0.cli')
        cli_path = _join(self.cli_dir, climate.cli_fn)
        shutil.copyfile(cli_path, dst_fn)
    
    def _make_watershed_run(self, translator):
        runs_dir = self.runs_dir
        wepp_ids = list(translator.iter_wepp_sub_ids())
        wepp_ids.sort()
        years = Climate.getInstance(self.wd).input_years
        make_watershed_run(years, wepp_ids, runs_dir)
        
    def run_watershed(self):
        wd  = self.wd
        self.log('Running Watershed... ')

        runs_dir = self.runs_dir
        assert run_watershed(runs_dir)

        for fn in glob(_join(self.runs_dir, '*.out')):
            dst_path = _join(self.output_dir, _split(fn)[1])
            shutil.move(fn, dst_path)

        if not _exists(_join(wd, 'wepppost.nodb')):
            WeppPost(wd, '0.cfg')

        self.log_done()

        self.log('Running WeppPost... ')
        wepppost = WeppPost.getInstance(wd)
        wepppost.run_post()
        self.log_done()

        self.log('Calculating hill streamflow measures... ')
        wepppost.calc_hill_streamflow()
        self.log_done()

        self.log('Calculating channel streamflow measures... ')
        wepppost.calc_channel_streamflow()
        self.log_done()

    def report_loss(self):
        output_dir = self.output_dir
        loss_pw0 = _join(output_dir, 'loss_pw0.txt')
        return Loss(loss_pw0, self.wd)

    def report_return_periods(self):
        output_dir = self.output_dir
        loss_pw0 = _join(output_dir, 'loss_pw0.txt')
        loss_rpt = Loss(loss_pw0, self.wd)

        ebe_pw0 = _join(output_dir, 'ebe_pw0.txt')
        ebe_rpt = Ebe(ebe_pw0)

        return ReturnPeriods(ebe_rpt, loss_rpt)

    def report_frq_flood(self):
        output_dir = self.output_dir
        loss_pw0 = _join(output_dir, 'loss_pw0.txt')
        loss_rpt = Loss(loss_pw0, self.wd)

        ebe_pw0 = _join(output_dir, 'ebe_pw0.txt')
        ebe_rpt = Ebe(ebe_pw0)

        return FrqFlood(ebe_rpt, loss_rpt)

    def report_hill_watbal(self):
        return HillslopeWatbal(self.wd)

    def report_chn_watbal(self):
        return ChannelWatbal(self.wd)

    def set_run_flowpaths(self, state):
        assert state in [True, False]

        self.lock()

        # noinspection PyBroadException
        try:
            self.run_flowpaths = state
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    def set_hourly_seepage(self, state):
        assert state in [True, False]

        self.lock()

        # noinspection PyBroadException
        try:
            self.wepp_ui = state
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise
        
    def query_sub_val(self, measure):
        wd = self.wd
        translator = Watershed.getInstance(wd).translator_factory()
        output_dir = self.output_dir
        loss_pw0 = _join(output_dir, 'loss_pw0.txt')
        report = Loss(loss_pw0, self.wd)
        
        d = {}
        for row in report.hill_tbl:
            topaz_id = translator.top(wepp=row['Hillslopes'])
            d[str(topaz_id)] = dict(
                topaz_id=topaz_id,
                value=row[measure]
            )
        
        return d

    def make_loss_grid(self):
        bound, transform, proj = read_arc(self.bound_arc, dtype=np.int32)

        num_cols, num_rows = bound.shape
        loss_grid = np.zeros((num_cols, num_rows))

        _loss_grid_d = self.loss_grid_d
        for (x, y) in _loss_grid_d:
            loss = np.mean(np.array(_loss_grid_d[(x, y)]))
            loss_grid[x, y] = loss

        indx = np.where(bound == 0.0)
        loss_grid[indx] = -9999

        loss_grid_path = _join(self.plot_dir, 'loss.tif')
        driver = gdal.GetDriverByName("GTiff")
        dst = driver.Create(loss_grid_path, num_cols, num_rows,
                            1, GDT_Float32)

        srs = osr.SpatialReference()
        srs.ImportFromProj4(proj)
        wkt = srs.ExportToWkt()

        dst.SetProjection(wkt)
        dst.SetGeoTransform(transform)
        band = dst.GetRasterBand(1)
        band.SetNoDataValue(-1e38)
        band.WriteArray(loss_grid.T)
        del dst

        assert _exists(loss_grid_path)

        loss_grid_wgs = _join(self.plot_dir, 'loss.WGS.tif')

        if _exists(loss_grid_wgs):
            os.remove(loss_grid_wgs)
            time.sleep(1)

        cmd = ['gdalwarp', '-t_srs', wgs84_proj4,
               '-srcnodata', '-9999', '-dstnodata', '-9999',
               '-r', 'near', loss_grid_path, loss_grid_wgs]
        p = Popen(cmd, stdin=PIPE, stdout=PIPE, stderr=PIPE)
        p.wait()

        assert _exists(loss_grid_wgs)
