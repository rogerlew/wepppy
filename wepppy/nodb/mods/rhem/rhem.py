
# standard library
import os
from os.path import join as _join
from os.path import exists as _exists

from concurrent.futures import ThreadPoolExecutor, wait, FIRST_COMPLETED

from glob import glob

import shutil
from time import sleep

# non-standard

from wepppy.all_your_base import NCPU
from wepppy.topo.watershed_abstraction import SlopeFile

from wepppy.nodb.core import *
from wepppy.nodb.base import NoDbBase
from wepppy.nodb.mods.rangeland_cover import RangelandCover
from wepppy.rhem import make_parameter_file, make_hillslope_run, run_hillslope
from wepppy.climates.cligen import ClimateFile
from .rhempost import RhemPost

__all__ = [
    'RhemNoDbLockedException',
    'Rhem',
]


class RhemNoDbLockedException(Exception):
    pass


class Rhem(NoDbBase):
    __name__ = 'Rhem'

    filename = 'rhem.nodb'

    def __init__(self, wd, cfg_fn, run_group=None, group_name=None):
        super(Rhem, self).__init__(wd, cfg_fn, run_group=run_group, group_name=group_name)

        with self.locked():
            rhem_dir = self.rhem_dir
            if not _exists(rhem_dir):
                os.mkdir(rhem_dir)

            self.clean()

        RhemPost(wd, cfg_fn)

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
    def has_run(self):
        return len(glob(_join(self.output_dir, '*.sum'))) > 0

    #
    # hillslopes
    #
    def prep_hillslopes(self):
        self.logger.info('Ceaning runs and output dir... ')
        self.clean()

        self.logger.info('Prepping Hillslopes... ')

        wd = self.wd

        watershed = Watershed.getInstance(wd)

        soils = Soils.getInstance(wd)
        rangeland_covers = RangelandCover.getInstance(wd)
        climate = Climate.getInstance(self.wd)
        cli_dir = self.cli_dir
        wat_dir = self.wat_dir
        runs_dir = self.runs_dir
        out_dir = self.output_dir

        for topaz_id in watershed._subs_summary:
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
                                         width=watershed.width_of(topaz_id),
                                         model_version='WEPPcloud')

            stm_fn = _join(runs_dir, 'hill_{}.stm'.format(topaz_id))

            cli_summary = climate.sub_summary(topaz_id)
            cli_path = _join(cli_dir, cli_summary['cli_fn'])
            climate_file = ClimateFile(cli_path)
            climate_file.make_storm_file(stm_fn)

            run_fn = _join(runs_dir, 'hill_{}.run'.format(topaz_id))
            make_hillslope_run(run_fn, par_fn, stm_fn, _join(out_dir, 'hill_{}.sum'.format(topaz_id)), scn_name)

    def clean(self):
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

        self.logger.info('Running Hillslopes\n')
        watershed = Watershed.getInstance(self.wd)
        runs_dir = os.path.abspath(self.runs_dir)

        with ThreadPoolExecutor(NCPU) as pool:
            futures = []

            def oncomplete(rhemrun):
                status, _id, elapsed_time = rhemrun.result()
                assert status
                self.logger.info('  {} completed run in {}s\n'.format(_id, elapsed_time))

            sub_n = watershed.sub_n
            for i, topaz_id in enumerate(watershed._subs_summary):
                self.logger.info(f'  submitting topaz={topaz_id} (hill {i+1} of {sub_n})\n')
                self.logger.info(f'      runs_dir: {runs_dir}\n')

                futures.append(pool.submit(run_hillslope, topaz_id, runs_dir))
                futures[-1].add_done_callback(oncomplete)

            futures_n = len(futures)
            count = 0
            pending = set(futures)
            while pending:
                done, pending = wait(pending, timeout=30, return_when=FIRST_COMPLETED)

                if not done:
                    # RHEM runs may take a while; log so we notice if they hang entirely.
                    self.logger.warning('  RHEM hillslopes still running after 30 seconds; continuing to wait.')
                    continue

                for future in done:
                    try:
                        future.result()
                        count += 1
                        self.logger.info(f'  ({count}/{futures_n}) hillslopes completed)')
                    except Exception as exc:
                        for remaining in pending:
                            remaining.cancel()
                        self.logger.error(f'  RHEM hillslope failed with an error: {exc}')
                        raise

        self.logger.info('Running RhemPost... ')
        rhempost = RhemPost.getInstance(self.wd)
        rhempost.run_post()

        arc_export(self.wd)

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
