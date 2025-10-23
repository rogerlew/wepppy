
# Rangeland Hydrology and Erosion Model (RHEM) NoDb controller.
"""RHEM hillslope controller.

This module prepares and executes RHEM hillslope simulations for each TOPAZ
subcatchment. It derives slope files from watershed abstractions, merges soils
and rangeland cover attributes, emits RHEM parameter/storm files, and runs the
Fortran executable in parallel. Outputs feed the `RhemPost` processor and are
consumed by WEPP management generation.

Key inputs:
* Watershed topology (`SlopeFile`, widths) plus soils and rangeland cover
  summaries.
* CLIGEN climate files selected by the Climate controller.

Outputs and integrations:
* Parameter, storm, and run files inside `rhem/runs`.
* RHEM output summaries (`*.sum`) in `rhem/output` consumed by `RhemPost`.
* Optional WEPP hillslope runs triggered via `run_wepp_hillslopes`.
"""

from __future__ import annotations

import os
import shutil
from concurrent.futures import FIRST_COMPLETED, Future, ThreadPoolExecutor, wait
from glob import glob
from os.path import exists as _exists
from os.path import join as _join
from time import sleep

from typing import Any, Dict, Optional, Set, Tuple

from wepppy.all_your_base import NCPU
from wepppy.climates.cligen import ClimateFile
from wepppy.nodb.base import NoDbBase
from wepppy.nodb.core import Climate, Soils, Watershed, Wepp
from wepppy.nodb.mods.rangeland_cover import RangelandCover
from wepppy.rhem import make_hillslope_run, make_parameter_file, run_hillslope
from wepppy.topo.watershed_abstraction import SlopeFile

from .rhempost import RhemPost

__all__ = [
    'RhemNoDbLockedException',
    'Rhem',
]

CoverValues = Dict[str, float]
RhemRunResult = Tuple[bool, str, float]


class RhemNoDbLockedException(Exception):
    pass


class Rhem(NoDbBase):
    __name__ = 'Rhem'

    filename = 'rhem.nodb'

    def __init__(
        self,
        wd: str,
        cfg_fn: str,
        run_group: Optional[str] = None,
        group_name: Optional[str] = None
    ) -> None:
        super().__init__(wd, cfg_fn, run_group=run_group, group_name=group_name)

        with self.locked():
            rhem_dir = self.rhem_dir
            if not _exists(rhem_dir):
                os.mkdir(rhem_dir)

            self.clean()

        RhemPost(wd, cfg_fn)

    @property
    def rhem_dir(self) -> str:
        return _join(self.wd, 'rhem')

    @property
    def runs_dir(self) -> str:
        return _join(self.wd, 'rhem', 'runs')

    @property
    def output_dir(self) -> str:
        return _join(self.wd, 'rhem', 'output')

    @property
    def has_run(self) -> bool:
        return len(glob(_join(self.output_dir, '*.sum'))) > 0

    #
    # hillslopes
    #
    def prep_hillslopes(self) -> None:
        self.logger.info('Ceaning runs and output dir... ')
        self.clean()

        self.logger.info('Prepping Hillslopes... ')

        wd = self.wd

        watershed = Watershed.getInstance(wd)

        soils = Soils.getInstance(wd)
        rangeland_covers = RangelandCover.getInstance(wd)
        covers_map = rangeland_covers.covers
        if covers_map is None:
            raise RhemNoDbLockedException('Rangeland cover data is not available; run the RangelandCover mod first.')
        climate = Climate.getInstance(self.wd)
        cli_dir = self.cli_dir
        wat_dir = self.wat_dir
        runs_dir = self.runs_dir
        out_dir = self.output_dir

        for topaz_id in watershed._subs_summary:
            mukey = soils.domsoil_d[topaz_id]
            soil_texture = soils.soils[mukey].texture

            if watershed.abstraction_backend == 'peridot':
                slp_fn = _join(wat_dir, f'slope_files/hillslopes/hill_{topaz_id}.slp')
            else:
                slp_fn = _join(wat_dir, f'hill_{topaz_id}.slp')

            slp = SlopeFile(slp_fn)
            cover: CoverValues = covers_map[topaz_id]

            scn_name = f'hill_{topaz_id}'
            par_fn = make_parameter_file(
                scn_name=scn_name,
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
                model_version='WEPPcloud'
            )

            stm_fn = _join(runs_dir, f'hill_{topaz_id}.stm')

            cli_summary: Dict[str, Any] = climate.sub_summary(topaz_id)
            cli_path = _join(cli_dir, cli_summary['cli_fn'])
            climate_file = ClimateFile(cli_path)
            climate_file.make_storm_file(stm_fn)

            run_fn = _join(runs_dir, f'hill_{topaz_id}.run')
            make_hillslope_run(
                run_fn,
                par_fn,
                stm_fn,
                _join(out_dir, f'hill_{topaz_id}.sum'),
                scn_name
            )

    def clean(self) -> None:
        runs_dir = self.runs_dir
        if _exists(runs_dir):
            try:
                shutil.rmtree(runs_dir)
            except FileNotFoundError:
                sleep(10.0)
                shutil.rmtree(runs_dir, ignore_errors=True)

        os.makedirs(runs_dir, exist_ok=True)

        output_dir = self.output_dir
        if _exists(output_dir):
            try:
                shutil.rmtree(output_dir)
            except FileNotFoundError:
                sleep(10.0)
                shutil.rmtree(output_dir, ignore_errors=True)

        os.makedirs(output_dir, exist_ok=True)

    def run_hillslopes(self) -> None:
        from wepppy.export import arc_export

        self.logger.info('Running Hillslopes\n')
        watershed = Watershed.getInstance(self.wd)
        runs_dir = os.path.abspath(self.runs_dir)

        with ThreadPoolExecutor(NCPU) as pool:
            futures: list[Future[RhemRunResult]] = []

            def oncomplete(rhemrun: Future[RhemRunResult]) -> None:
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
            pending: Set[Future[RhemRunResult]] = set(futures)
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

    def report_loss(self) -> None:
        raise NotImplementedError

    def report_return_periods(self) -> None:
        raise NotImplementedError

    def run_wepp_hillslopes(self) -> None:
        wepp = Wepp.getInstance(self.wd)
        wepp.prep_hillslopes()
        wepp.run_hillslopes()
