# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew.gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.
import math
import os
from os.path import join as _join

# non-standard
import jsonpickle
import numpy as np

# wepppy
from wepppy.climates.noaa_precip_freqs_client import fetch_pf

# wepppy submodules
from wepppy.nodb.base import NoDbBase
from wepppy.nodb.watershed import Watershed
from wepppy.nodb.soils import Soils
from wepppy.nodb.topaz import Topaz
from wepppy.nodb.landuse import Landuse


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

    def __init__(self, wd, cfg_fn):
        super(DebrisFlow, self).__init__(wd, cfg_fn)

        self.lock()

        # noinspection PyBroadException
        try:
            # config = self.config
            self.pf = None
            self.I = None
            self.T = None
            self.durations = None
            self.rec_intervals = None
            self.volume = None
            self.prob_occurrence = None

            self.rpt_rec_intervals = [2, 5, 10, 25, 50, 100, 200]
            self.rpt_durations = ['15-min', '30-min', '60-min', '2-hour', '3-hour', '6-hour', '12-hour',
                                  '24-hour', '2-day', '3-day', '4-day', '7-day']
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
        with open(_join(wd, 'debris_flow.nodb')) as fp:
            db = jsonpickle.decode(fp.read())
            assert isinstance(db, DebrisFlow), db

            if os.path.abspath(wd) != os.path.abspath(db.wd):
                db.wd = wd
                db.lock()
                db.dump_and_unlock()

            return db

    @property
    def _nodb(self):
        return _join(self.wd, 'debris_flow.nodb')

    @property
    def _lock(self):
        return _join(self.wd, 'debris_flow.nodb.lock')

    def fetch_precip_data(self):

        self.lock()

        # noinspection PyBroadException
        try:
            watershed = Watershed.getInstance(self.wd)
            lng, lat = watershed.centroid
            pf = fetch_pf(lat=lat, lng=lng)
            if pf is not None:

                T = np.array(pf['quantiles']) * 25.4
                I = np.array(pf['quantiles']) * 25.4
                durations = pf['durations']
                rec_intervals = pf['rec_intervals']

                for i, d in enumerate(durations):
                    hours = _duration_in_hours(d)
                    I[i, :] /= hours

                self.pf = pf
                self.I = I.tolist()
                self.T = T.tolist()
                self.durations = durations
                self.rec_intervals = rec_intervals

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    def run_debris_flow(self):
        self.lock()

        # noinspection PyBroadException
        try:
            wd = self.wd
            soils = Soils.getInstance(wd)
            topaz = Topaz.getInstance(wd)
            landuse = Landuse.getInstance(wd)

            A = topaz.area_gt30
            A_pct = 100 * A / topaz.wsarea
            A /= 1000 * 1000  # to km^2

            sbs_coverage = landuse.sbs_coverage
            B = sbs_coverage['moderate'] * topaz.wsarea + \
                sbs_coverage['high'] * topaz.wsarea
            B_pct = 100 * B / topaz.wsarea
            B /= 1000 * 1000  # to km^2
            C = soils.clay_pct
            LL = 13.25
            R = topaz.ruggedness

            self.A = A
            self.B = B
            self.A_pct = A_pct
            self.B_pct = B_pct
            self.C = C
            self.LL = LL
            self.R = R

            self.dump_and_unlock()

            self.fetch_precip_data()

            if self.T is not None and self.I is not None:
                self.lock()

                T = np.array(self.T)
                I = np.array(self.I)

                # where
                # A (in km2) is the area of the basin having slopes greater than or equal to 30%,
                # B (in km2) is the area of the basin burned at high and moderate severity,
                # T (in mm) is the total storm rainfall, and 0.3 is a bias correction that changes
                # the predicted estimate from a median to a mean value (Helsel and Hirsch, 2002).
                v = np.exp(7.2 + 0.6 * math.log(A) + 0.7 * B ** 0.5 + 0.2 * T ** 0.5 + 0.3)

                # where
                # %A is the percentage of the basin area with gradients greater than or equal to 30%,
                # R is basin ruggedness,
                # %B is the percentage of the basin area burned at high and moderate severity,
                # I is average storm rainfall intensity (in mm/h),
                # C is clay content (in %),
                # LL is the liquid limit
                x = -0.7 + 0.03 * A_pct - 1.6 * R + 0.06 * B_pct + 0.07 * I + 0.2 * C - 0.4 * LL
                prob_occurrence = np.exp(x) / (1.0 + np.exp(x))

                self.volume = v.tolist()
                self.prob_occurrence = prob_occurrence.tolist()

                self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise
