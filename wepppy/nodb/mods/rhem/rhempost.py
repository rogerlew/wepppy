# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

import os
from os.path import exists as _exists
from os.path import join as _join
from os.path import split as _split

from glob import glob

import shutil

# non-standard
import jsonpickle
import numpy as np

# wepppy submodules
from wepppy.nodb.watershed import Watershed
from wepppy.nodb.base import NoDbBase

from wepppy.rhem.out import RhemOutput, RhemSummary

class RhemPostNoDbLockedException(Exception):
    pass


class RhemPost(NoDbBase):
    """
    Manager that keeps track of project details
    and coordinates access of NoDb instances.
    """
    __name__ = 'RhemPost'

    def __init__(self, wd, cfg_fn):
        super(RhemPost, self).__init__(wd, cfg_fn)

        self.lock()

        # noinspection PyBroadException
        try:
            config = self.config
            self.hill_summaries = None
            self.periods = None
            self.watershed_annuals = None
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
        with open(_join(wd, 'rhempost.nodb')) as fp:
            db = jsonpickle.decode(fp.read())
            assert isinstance(db, RhemPost), db

            if _exists(_join(wd, 'READONLY')):
                return db

            if os.path.abspath(wd) != os.path.abspath(db.wd):
                db.wd = wd
                db.lock()
                db.dump_and_unlock()

            return db

    @property
    def _nodb(self):
        return _join(self.wd, 'rhempost.nodb')

    @property
    def _lock(self):
        return _join(self.wd, 'rhempost.nodb.lock')

    def run_post(self):
        from wepppy.nodb import Rhem

        wd = self.wd
        self.lock()

        # noinspection PyBroadException
        try:
            output_dir = self.output_dir
            watershed = Watershed.getInstance(wd)
            rhem = Rhem.getInstance(wd)
            out_dir = rhem.output_dir

            hill_summaries = {}
            total_area = 0.0

            runoff = 0.0
            soil_yield = 0.0
            soil_loss = 0.0
            precip = 0.0

            periods = None
            ret_rain = None
            ret_runoff = None
            ret_yield = None
            ret_loss = None

            for topaz_id, summary in watershed.sub_iter():
                area_ha = summary.area / 10000
                total_area += area_ha
                summary_fn = _join(out_dir, 'hill_{}.sum'.format(topaz_id))
                hill_summaries[topaz_id] = RhemSummary(summary_fn, area_ha)

                runoff += hill_summaries[topaz_id].annuals['Avg-Runoff (m^3/yr)']
                soil_yield += hill_summaries[topaz_id].annuals['Avg-SY (tonne/yr)']
                soil_loss += hill_summaries[topaz_id].annuals['Avg-Soil-Loss (tonne/yr)']
                precip += hill_summaries[topaz_id].annuals['Avg. Precipitation (m^3/yr)']

                if ret_rain is None:
                    ret_rain = np.array(hill_summaries[topaz_id].return_freqs['Rain (m^3)'])
                else:
                    ret_rain += np.array(hill_summaries[topaz_id].return_freqs['Rain (m^3)'])

                if ret_runoff is None:
                    ret_runoff = np.array(hill_summaries[topaz_id].return_freqs['Runoff (m^3)'])
                else:
                    ret_runoff += np.array(hill_summaries[topaz_id].return_freqs['Runoff (m^3)'])

                if ret_yield is None:
                    ret_yield = np.array(hill_summaries[topaz_id].return_freqs['Sediment-Yield (tonne)'])
                else:
                    ret_yield += np.array(hill_summaries[topaz_id].return_freqs['Sediment-Yield (tonne)'])

                if ret_loss is None:
                    ret_loss = np.array(hill_summaries[topaz_id].return_freqs['Soil-Loss (tonne)'])
                else:
                    ret_loss += np.array(hill_summaries[topaz_id].return_freqs['Soil-Loss (tonne)'])

                if periods is None:
                    periods = [v for v in hill_summaries[topaz_id].ret_freq_periods]

            self.hill_summaries = hill_summaries
            self.watershed_annuals = {'Avg-Runoff (m^3/yr)': runoff,
                                      'Avg-Runoff (mm/yr)': runoff / (total_area * 10000) * 1000,
                                      'Avg-SY (tonne/yr)': soil_yield,
                                      'Avg-SY (tonne/ha/yr)': soil_yield/ total_area,
                                      'Avg-Soil-Loss (tonne/yr)': soil_loss,
                                      'Avg-Soil-Loss (tonne/ha/yr)': soil_loss / total_area,
                                      'Avg. Precipitation (m^3/yr)': precip,
                                      'Avg. Precipitation (mm/yr)': precip / (total_area * 10000) * 1000}

            self.ret_freq_periods = periods
            watershed_ret_freqs = {'Rain (m^3)': ret_rain,
                                   'Rain (mm)': ret_rain / (total_area * 10000) * 1000,
                                   'Runoff (m^3)': ret_runoff,
                                   'Runoff (mm)': ret_runoff / (total_area * 10000) * 1000,
                                   'Sediment-Yield (tonne)': ret_yield,
                                   'Sediment-Yield (tonne/ha)': ret_yield / total_area,
                                   'Soil-Loss (tonne)': ret_loss,
                                   'Soil-Loss (tonne/ha)': ret_loss / total_area}

            for k in watershed_ret_freqs:
                watershed_ret_freqs[k] = [float(v) for v in watershed_ret_freqs[k]]

            self.watershed_ret_freqs = watershed_ret_freqs

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    def query_sub_val(self, measure):
        _measure = measure.strip().lower()
        key = None
        if _measure == 'runoff':
            key = 'Avg-Runoff (mm/yr)'
        elif _measure == 'sed_yield':
            key = 'Avg-SY (tonne/ha/yr)'
        elif _measure == 'soil_loss':
            key = 'Avg-Soil-Loss (tonne/ha/yr)'
        assert key is not None

        hill_summaries = self.hill_summaries

        d = {}
        for topaz_id in hill_summaries:
            d[str(topaz_id)] = dict(
                topaz_id=topaz_id,
                value=hill_summaries[topaz_id].annuals[key])
        return d
