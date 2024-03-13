# non-standard

# wepppy

from wepppy.all_your_base import NCPU

from wepppy.topo.watershed_abstraction import SlopeFile


# wepppy submodules
from wepppy.nodb.mixins.log_mixin import LogMixin
from wepppy.nodb.base import NoDbBase
from wepppy.nodb.mods import RangelandCover
from wepppy.nodb.watershed import Watershed
from wepppy.nodb.soils import Soils
from wepppy.nodb.climate import Climate

from wepppy.nodb.wepp import Wepp

# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

# standard library
import os
from os.path import join as _join
from os.path import exists as _exists

from concurrent.futures import ThreadPoolExecutor, wait, FIRST_EXCEPTION

from glob import glob

import shutil
from time import sleep

# non-standard
import jsonpickle

# wepppy

from wepppy.rhem import make_parameter_file, make_hillslope_run, run_hillslope

from wepppy.climates.cligen import ClimateFile

from .rhempost import RhemPost


class RhemNoDbLockedException(Exception):
    pass


class Rhem(NoDbBase, LogMixin):
    __name__ = 'Rhem'

    def __init__(self, wd, cfg_fn):
        super(Rhem, self).__init__(wd, cfg_fn)

        self.lock()

        # noinspection PyBroadException
        try:
            rhem_dir = self.rhem_dir
            if not _exists(rhem_dir):
                os.mkdir(rhem_dir)

            self.clean()

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def rhem_dir(self):
        return _join(self.wd, 'rhem')

    @property
    def runs_dir(self):
        return _join(self.wd, 'rhem', 'runs')

    @property
    def output_dir(self):
        return _join(self.wd, 'rhem', 'output')

    @property
    def status_log(self):
        return os.path.abspath(_join(self.runs_dir, 'status.log'))

    #
    # Required for NoDbBase Subclass
    #

    # noinspection PyPep8Naming
    @staticmethod
    def getInstance(wd):
        with open(_join(wd, 'rhem.nodb')) as fp:
            db = jsonpickle.decode(fp.read())
            assert isinstance(db, Rhem)

            if _exists(_join(wd, 'READONLY')):
                db.wd = os.path.abspath(wd)
                return db

            if os.path.abspath(wd) != os.path.abspath(db.wd):
                db.wd = wd
                db.lock()
                db.dump_and_unlock()

            return db

    @property
    def _status_channel(self):
        return f'{self.runid}:rhem'

    @property
    def _nodb(self):
        return _join(self.wd, 'rhem.nodb')

    @property
    def _lock(self):
        return _join(self.wd, 'rhem.nodb.lock')

    @property
    def has_run(self):
        return len(glob(_join(self.output_dir, '*.sum'))) > 0

    #
    # hillslopes
    #
    def prep_hillslopes(self):
        self.log('Ceaning runs and output dir... ')
        self.clean()
        self.log_done()

        self.log('Prepping Hillslopes... ')

        wd = self.wd

        watershed = Watershed.getInstance(wd)

        soils = Soils.getInstance(wd)
        rangeland_covers = RangelandCover.getInstance(wd)
        climate = Climate.getInstance(self.wd)
        cli_dir = self.cli_dir
        wat_dir = self.wat_dir
        runs_dir = self.runs_dir
        out_dir = self.output_dir

        for topaz_id, summary in watershed.sub_iter():
            mukey = soils.domsoil_d[topaz_id]
            soil_texture = soils.soils[mukey].texture

            if watershed.abstraction_backend == 'peridot':
                slp_fn = _join(wat_dir, 'slope_files/hillslopes/hill_{}.slp'.format(topaz_id))
            else:
                slp_fn = _join(wat_dir, 'hill_{}.slp'.format(topaz_id))

            slp = SlopeFile(slp_fn)
            cover = rangeland_covers.covers[topaz_id]

            scn_name = 'hill_{}'.format(topaz_id)
            par_fn = make_parameter_file(scn_name=scn_name,
                                         out_dir=runs_dir,
                                         soil_texture=soil_texture,
                                         moisture_content=0.25,
                                         bunchgrass_cover=cover['bunchgrass'],
                                         forbs_cover=cover['forbs'],
                                         shrubs_cover=cover['shrub'],
                                         sodgrass_cover=cover['sodgrass'],
                                         rock_cover=cover['rock'],
                                         basal_cover=cover['basal'],
                                         litter_cover=cover['litter'],
                                         cryptogams_cover=cover['cryptogams'],
                                         slope_length=slp.length,
                                         slope_steepness=slp.slope_scalar,
                                         sl=slp.slopes,
                                         sx=slp.distances,
                                         width=summary.width,
                                         model_version='WEPPcloud')

            stm_fn = _join(runs_dir, 'hill_{}.stm'.format(topaz_id))

            cli_summary = climate.sub_summary(topaz_id)
            cli_path = _join(cli_dir, cli_summary['cli_fn'])
            climate_file = ClimateFile(cli_path)
            climate_file.make_storm_file(stm_fn)

            run_fn = _join(runs_dir, 'hill_{}.run'.format(topaz_id))
            make_hillslope_run(run_fn, par_fn, stm_fn, _join(out_dir, 'hill_{}.sum'.format(topaz_id)), scn_name)

        self.log_done()

    def clean(self):
        if _exists(self.status_log):
            os.remove(self.status_log)

        runs_dir = self.runs_dir
        if _exists(runs_dir):
            try:
                shutil.rmtree(runs_dir)
            except FileNotFoundError:
                sleep(10.0)
                shutil.rmtree(runs_dir, ignore_errors=True)

        os.makedirs(runs_dir)

        output_dir = self.output_dir
        if _exists(output_dir):
            try:
                shutil.rmtree(output_dir)
            except FileNotFoundError:
                sleep(10.0)
                shutil.rmtree(output_dir, ignore_errors=True)

        os.makedirs(output_dir)

    def run_hillslopes(self):
        from wepppy.export import arc_export

        self.log('Running Hillslopes\n')
        watershed = Watershed.getInstance(self.wd)
        runs_dir = os.path.abspath(self.runs_dir)

        pool = ThreadPoolExecutor(NCPU)
        futures = []

        def oncomplete(rhemrun):
            status, _id, elapsed_time = rhemrun.result()
            assert status
            self.log('  {} completed run in {}s\n'.format(_id, elapsed_time))

        sub_n = watershed.sub_n
        for i, (topaz_id, _) in enumerate(watershed.sub_iter()):
            self.log(f'  submitting topaz={topaz_id} (hill {i+1} of {sub_n})\n')
            self.log(f'      runs_dir: {runs_dir}\n')

#            run_hillslope(topaz_id, runs_dir)
#            self.log(f'  {topaz_id} completed run\n')

            futures.append(pool.submit(lambda p: run_hillslope(*p), (topaz_id, runs_dir)))
            futures[-1].add_done_callback(oncomplete)

        wait(futures, return_when=FIRST_EXCEPTION)

        self.log('Running RhemPost... ')
        rhempost = RhemPost.getInstance(self.wd)
        rhempost.run_post()

        arc_export(self.wd)

#        self.run_wepp_hillslopes()
        self.log_done()

    def report_loss(self):
        output_dir = self.output_dir

        raise NotImplementedError

    def report_return_periods(self):
        output_dir = self.output_dir

        raise NotImplementedError

    def run_wepp_hillslopes(self):
        wepp = Wepp.getInstance(self.wd)
        wepp.prep_hillslopes()
        wepp.run_hillslopes()

