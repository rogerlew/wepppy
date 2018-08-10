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

from collections import OrderedDict

from datetime import datetime, timedelta
import io
import math

import shutil

# non-standard
import jsonpickle
import numpy as np
import pandas as pd
from scipy import stats


# wepppy submodules
from wepppy.wepp.out import TotalWatSed, Chanwb, Ebe

from .base import NoDbBase
from .wepp import Wepp


def validate(Qm, Qo):
    assert Qm.shape == Qo.shape
    assert len(Qo.shape) == 1


def nse(Qm, Qo):
    validate(Qm, Qo)

    return float(1.0 - np.sum((Qm - Qo) ** 2.0) / \
                       np.sum((Qo - np.mean(Qo)) ** 2.0))

def r_square(Qm, Qo):
    validate(Qm, Qo)

    slope, intercept, r_value, p_value, std_err = stats.linregress(Qm, Qo)
    return float(r_value ** 2.0)


def dv(Qm, Qo):
    validate(Qm, Qo)

    return float(np.mean((Qo - Qm) / Qo * 100.0))


def mse(Qm, Qo):
    validate(Qm, Qo)

    n = len(Qo)
    return float(np.mean((Qo - Qm) ** 2.0))


class ObservedNoDbLockedException(Exception):
    pass


class Observed(NoDbBase):
    """
    Manager that keeps track of project details
    and coordinates access of NoDb instances.
    """
    __name__ = 'Observed'

    measures = ['Streamflow (mm)',
                'Sed. Del (kg)',
                'Total P (kg)',
                'Soluble Reactive P (kg)',
                'Particulate P (kg)']

    def __init__(self, wd, cfg_fn):
        super(Observed, self).__init__(wd, cfg_fn)

        self.lock()

        # noinspection PyBroadException
        try:
            config = self.config
            self.results = None

            if not _exists(self.observed_dir):
                os.mkdir(self.observed_dir)

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
        with open(_join(wd, 'observed.nodb')) as fp:
            db = jsonpickle.decode(fp.read())
            assert isinstance(db, Observed), db

            if _exists(_join(wd, 'READONLY')):
                return db

            if os.path.abspath(wd) != os.path.abspath(db.wd):
                db.wd = wd
                db.lock()
                db.dump_and_unlock()

            return db

    @property
    def _nodb(self):
        return _join(self.wd, 'observed.nodb')

    @property
    def _lock(self):
        return _join(self.wd, 'observed.nodb.lock')

    def read_observed_fn(self, fn):
        with open(fn) as fp:
            textdata = fp.read()
            self.parse_textdata(textdata)

    def parse_textdata(self, textdata):

        self.lock()

        # noinspection PyBroadException
        try:
            with io.StringIO(textdata) as fp:
                df = pd.read_csv(fp)

            assert 'Date' in df

            yrs, mos, das, juls = [], [], [], []
            for d in df['Date']:
                mo, da, yr = d.split('/')
                mo = int(mo)
                da = int(da)
                yr = int(yr)
                jul = (datetime(yr, mo, da) - datetime(yr, 1, 1)).days

                yrs.append(yr)
                mos.append(mo)
                das.append(da)
                juls.append(jul)

            df['Year'] = yrs
            df['Month'] = mos
            df['Day'] = das
            df['Julian'] = juls

            df.to_csv(self.observed_fn)
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def has_observed(self):
        return _exists(self.observed_fn)

    @property
    def has_results(self):
        return self.results is not None

    def calc_model_fit(self):
        assert self.has_observed

        results = OrderedDict()
        df = pd.read_csv(self.observed_fn)

        #
        # Hillslopes
        #

        # load hilslope simulation results
        wepp = Wepp.getInstance(self.wd)
        totwatsed_fn = _join(self.output_dir, 'totalwatsed.txt')
        totwatsed = TotalWatSed(totwatsed_fn, wepp.baseflow_opts,
                                phosOpts=wepp.phosphorus_opts)
        sim = totwatsed.d
        year0 = sorted(set(sim['Year']))[0]
        results['Hillslopes'] = self.run_measures(df, sim, 'Hillslopes')

        #
        # Channels
        #

        ebe = Ebe(_join(self.output_dir, 'ebe_pw0.txt'))
        chanwb = Chanwb(_join(self.output_dir, 'chanwb.out'))

        sim = ebe.df
        sim['Year'] = sim['year'] + year0 - 1
        sim['Streamflow (mm)'] = chanwb.calc_streamflow(totwatsed.wsarea)

        results['Channels'] = self.run_measures(df, sim, 'Channels')

        self.lock()

        # noinspection PyBroadException
        try:
            self.results = results

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    def run_measures(self, obs, sim, hillorChannel):

        results = OrderedDict()
        for m in self.measures:
            if m not in obs:
                continue

            res = self.run_measure(obs, sim, m, hillorChannel)

            results[m] = res

        return results

    def run_measure(self, obs, sim, measure, hillorChannel):
        sim_dates = dict([((int(yr), int(mo), int(da)), i) for i, (yr, mo, da) in
                          enumerate(zip(sim['Year'], sim['mo'], sim['da']))])

        years = sorted(set(int(yr) for yr in obs['Year']))
        wtr_yr_d = dict((yr, i) for i, yr in enumerate(years))
        last_yr = years[-1]

        Qm, Qo, dates = [], [], []
        Qm_yearly, Qo_yearly = np.zeros(len(years)), np.zeros(len(years))

        for i, v in enumerate(obs[measure]):
            if math.isnan(v):
                continue

            jul = int(obs['Julian'][i])
            mo = int(obs['Month'][i])
            da = int(obs['Day'][i])
            yr = int(obs['Year'][i])

            j = sim_dates.get((yr, mo, da), None)

            if j is None:
                continue

            Qm.append(sim[measure][j])
            Qo.append(v)
            dates.append(str(obs['Date'][i]))

            wtr_yr = yr

            if jul > 273:
                wtr_yr += 1

            if wtr_yr <= last_yr:
                k = wtr_yr_d[wtr_yr]
                Qm_yearly[k] += Qm[-1]
                Qo_yearly[k] += Qo[-1]

        self._write_measure(Qm, Qo, dates, measure, hillorChannel, 'Daily')
        self._write_measure(Qm_yearly, Qo_yearly, years, measure, hillorChannel, 'Yearly')

        Qm = np.array(Qm)
        Qo = np.array(Qo)

        return OrderedDict([
            ('Daily', OrderedDict([
                ('NSE', nse(Qm, Qo)),
                ('R^2', r_square(Qm, Qo)),
                ('DV', dv(Qm, Qo)),
                ('MSE', mse(Qm, Qo))])),
            ('Yearly', OrderedDict([
                ('NSE', nse(Qm_yearly, Qo_yearly)),
                ('R^2', r_square(Qm_yearly, Qo_yearly)),
                ('DV', dv(Qm_yearly, Qo_yearly)),
                ('MSE', mse(Qm_yearly, Qo_yearly))
            ]))
        ])

    def _write_measure(self, Qm, Qo, dates, measure, hillorChannel, dailyorYearly):
        assert len(Qm) == len(Qo)
        assert len(Qm) == len(dates)

        fn = '%s-%s-%s.csv' % (hillorChannel, measure, dailyorYearly)
        fn = fn.replace(' ', '_')
        fn = _join(self.observed_dir, fn)
        with open(fn, 'w') as fn:
            fn.write('date,Modeled,Observed\n')

            for m, o, d in zip(Qm, Qo, dates):
                fn.write('%s,%f,%f\n' % (d, m, o))
