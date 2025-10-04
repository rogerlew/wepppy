# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

import math
import os
from os.path import join as _join
from os.path import exists as _exists

from copy import deepcopy

# non-standard
import numpy as np

# wepppy
from wepppy.all_your_base import isfloat
from wepppy.climates import noaa_precip_freqs_client
from wepppy.climates import holden_wrf_atlas

# wepppy submodules
from wepppy.nodb.base import NoDbBase
from wepppy.nodb.core import *
from wepppy.nodb.mods.baer import Baer
from wepppy.nodb.mods.disturbed import Disturbed
from wepppy.nodb.redis_prep import RedisPrep, TaskEnum


def _duration_in_hours(duration):
    x, unit = duration.split('-')
    x = float(x)
    assert unit in ['min', 'hour', 'day']
    if unit == 'min':
        return x / 60.0
    elif unit == 'day':
        return x * 24.0
    return x


class DebrisFlowNoDbLockedException(Exception):
    pass


# noinspection PyPep8Naming
class DebrisFlow(NoDbBase):
    """
    Manager that keeps track of project details
    and coordinates access of NoDb instances.
    """
    __name__ = 'DebrisFlow'

    filename = 'debris_flow.nodb'

    def __init__(self, wd, cfg_fn, run_group=None, group_name=None):
        super(DebrisFlow, self).__init__(wd, cfg_fn, run_group=run_group, group_name=group_name)

        with self.locked():
            # config = self.config
            self.I = None
            self.T = None
            self.durations = None
            self.rec_intervals = None
            self.volume = None
            self.prob_occurrence = None
            self._datasource = None

            self.A = None
            self.B = None
            self.A_pct = None
            self.B_pct = None
            self.C = None
            self.LL = None
            self.R = None
            self.wsarea = None

    def fetch_precip_data(self):
        with self.locked():
            self.T = {}
            self.I = {}
            self.durations = {}
            self.rec_intervals = {}

            watershed = Watershed.getInstance(self.wd)
            lng, lat = watershed.centroid
            pf = noaa_precip_freqs_client.fetch_pf(lat=lat, lng=lng)
            if pf is not None:
                _datasource = 'NOAA'

                self.T[_datasource] = np.array(pf['quantiles']) * 25.4
                self.I[_datasource] = np.array(pf['quantiles']) * 25.4
                self.durations[_datasource] = pf['durations']
                self.rec_intervals[_datasource] = pf['rec_intervals']

                for i, d in enumerate(self.durations[_datasource]):
                    hours = _duration_in_hours(d)
                    self.I[_datasource][i, :] /= hours

                self.I[_datasource] = self.I[_datasource].tolist()
                self.T[_datasource] = self.T[_datasource].tolist()

                self._datasource = _datasource

            pf = holden_wrf_atlas.fetch_pf(lat=lat, lng=lng)
            if pf is not None:
                _datasource = 'Holden WRF Atlas'

                self.T[_datasource] = np.array(pf['precips'])
                self.I[_datasource] = np.array(pf['precips'])
                self.durations[_datasource] = pf['durations']
                self.rec_intervals[_datasource] = pf['rec_intervals']

                shape = (len(self.durations[_datasource]), len(self.rec_intervals[_datasource]))

                self.T[_datasource].resize(shape)
                self.I[_datasource].resize(shape)

                for i, d in enumerate(self.durations[_datasource]):
                    hours = _duration_in_hours(d)
                    self.I[_datasource][i, :] /= hours

                if self._datasource is None:
                    self._datasource = _datasource

                self.I[_datasource] = self.I[_datasource].tolist()
                self.T[_datasource] = self.T[_datasource].tolist()

    @property
    def datasource(self):
        return getattr(self, '_datasource', 'NOAA')

    @property
    def datasources(self):
        if self.I is None:
            return None

        return self.I.keys()

    def run_debris_flow(self, cc=None, ll=None, req_datasource=None):
        with self.locked():
            wd = self.wd
            soils = Soils.getInstance(wd)
            watershed = Watershed.getInstance(wd)
            ron = Ron.getInstance(wd)

            if 'baer' in ron.mods:
                baer = Baer.getInstance(wd)
            else:
                disturbed = Disturbed.getInstance(wd)

            A = watershed.area_gt30
            A_pct = 100 * A / watershed.wsarea
            A /= 1000 * 1000  # to km^2

            try:
                sbs_coverage = baer.sbs_coverage
            except:
                sbs_coverage = disturbed.sbs_coverage

            B = sbs_coverage['moderate'] * watershed.wsarea + \
                sbs_coverage['high'] * watershed.wsarea
            B_pct = 100 * B / watershed.wsarea
            B /= 1000 * 1000  # to km^2

            if cc is not None:
                assert isfloat(cc)
                cc = float(cc)
                assert cc >= 0.0
                assert cc <= 100.0
                C = cc
            else:
                C = getattr(soils, "clay_pct", None)

            if not isfloat(C):
                C = 7.0

            if ll is not None:
                assert isfloat(ll)
                ll = float(ll)
                assert ll >= 0.0
                assert ll <= 100.0
                LL = ll
            else:
                LL = getattr(soils, "liquid_limit", None)

            if not isfloat(LL):
                LL = 13.25

            R = watershed.ruggedness

            self.A = A
            self.B = B
            self.A_pct = A_pct
            self.B_pct = B_pct
            self.C = C
            self.LL = LL
            self.R = R
            self.wsarea = watershed.wsarea

        self.fetch_precip_data()

        if self.T is None or self.I is None:
            raise DebrisFlowNoDbLockedException("No precipitation data found. Please run fetch_precip_data() first.")

        with self.locked():
            self.volume = {}
            self.prob_occurrence = {}

            for _datasource in self.T:

                T = np.array(self.T[_datasource])
                I = np.array(self.I[_datasource])

                # where
                # A (in km2) is the area of the basin having slopes greater than or equal to 30%,
                # B (in km2) is the area of the basin burned at high and moderate severity,
                # T (in mm) is the total storm rainfall, and 0.3 is a bias correction that changes
                # the predicted estimate from a median to a mean value (Helsel and Hirsch, 2002).
                v = np.exp(7.2 + 0.6 * math.logger.info(A) + 0.7 * B ** 0.5 + 0.2 * T ** 0.5 + 0.3)

                # where
                # %A is the percentage of the basin area with gradients greater than or equal to 30%,
                # R is basin ruggedness,
                # %B is the percentage of the basin area burned at high and moderate severity,
                # I is average storm rainfall intensity (in mm/h),
                # C is clay content (in %),
                # LL is the liquid limit
                x = -0.7 + 0.03 * A_pct - 1.6 * R + 0.06 * B_pct + 0.07 * I + 0.2 * C - 0.4 * LL
                prob_occurrence = np.exp(x) / (1.0 + np.exp(x))

                self.volume[_datasource] = deepcopy(v.tolist())
                self.prob_occurrence[_datasource] = deepcopy(prob_occurrence.tolist())

            if req_datasource is not None:
                assert req_datasource in self.volume
                self._datasource = req_datasource

        try:
            prep = RedisPrep.getInstance(self.wd)
            prep.timestamp(TaskEnum.run_debris)
        except FileNotFoundError:
            pass
