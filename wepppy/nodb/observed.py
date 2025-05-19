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

from datetime import datetime, timedelta
import io
import math

import shutil

# non-standard
import jsonpickle
import numpy as np
import pandas as pd

# wepppy submodules
from wepppy.wepp.out import TotalWatSed2, Chanwb, Ebe
from wepppy.all_your_base.hydro.objective_functions import calculate_all_functions

from .base import NoDbBase
from .redis_prep import RedisPrep, TaskEnum


def validate(Qm, Qo):
    assert Qm.shape == Qo.shape
    assert len(Qo.shape) == 1


class ObservedNoDbLockedException(Exception):
    pass


class Observed(NoDbBase):
    """
    Manager that keeps track of project details
    and coordinates access of NoDb instances.
    """
    __name__ = 'Observed'

    measures = ['Streamflow (mm)',
                'Sed Del (kg)',
                'Total P (kg)',
                'Soluble Reactive P (kg)',
                'Particulate P (kg)']

    def __init__(self, wd, cfg_fn):
        super(Observed, self).__init__(wd, cfg_fn)

        self.lock()

        # noinspection PyBroadException
        try:
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
    def getInstance(wd='.', allow_nonexistent=False, ignore_lock=False):
        filepath = _join(wd, 'observed.nodb')

        if not os.path.exists(filepath):
            if allow_nonexistent:
                return None
            else:
                raise FileNotFoundError(f"'{filepath}' not found!")

        with open(filepath) as fp:
            db = jsonpickle.decode(fp.read())
            assert isinstance(db, Observed), db

        if _exists(_join(wd, 'READONLY')) or ignore_lock:
            db.wd = os.path.abspath(wd)
            return db

        if os.path.abspath(wd) != os.path.abspath(db.wd):
            db.wd = wd
            db.lock()
            db.dump_and_unlock()

        return db

    @staticmethod
    def getInstanceFromRunID(runid, allow_nonexistent=False, ignore_lock=False):
        from wepppy.weppcloud.utils.helpers import get_wd
        return Observed.getInstance(
            get_wd(runid), allow_nonexistent=allow_nonexistent, ignore_lock=ignore_lock)

    @property
    def _status_channel(self):
        return f'{self.runid}:observed'

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

        results = {}
        df = pd.read_csv(self.observed_fn)

        #
        # Hillslopes
        #

        # load hilslope simulation results
        totwatsed = TotalWatSed2(self.wd)
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
        sim['Month'] = sim['mo']
        sim['Day'] = sim['da']
        sim['Streamflow (mm)'] = chanwb.calc_streamflow(totwatsed.wsarea)

        # TODO: Use chan.out for daily dischange

        results['Channels'] = self.run_measures(df, sim, 'Channels')

        self.lock()

        # noinspection PyBroadException
        try:
            self.results = results

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

        try:
            prep = RedisPrep.getInstance(self.wd)
            prep.timestamp(TaskEnum.run_observed)
        except FileNotFoundError:
            pass

    @property
    def stat_names(self):
        measure0 = list(self.results['Hillslopes'].keys())[0]
        return list(self.results['Hillslopes'][measure0]['Daily'].keys())

    def run_measures(self, obs, sim, hillorChannel):

        results = {}
        for m in self.measures:
            if m not in obs:
                continue

            res = self.run_measure(obs, sim, m, hillorChannel)

            results[m] = res

        return results

    def run_measure(self, obs, sim, measure, hillorChannel):
        sim_dates = dict([((int(yr), int(mo), int(da)), i) for i, (yr, mo, da) in
                              enumerate(zip(sim['Year'], sim['Month'], sim['Day']))])

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

        validate(Qo, Qm)
        validate(Qo_yearly, Qm_yearly)

        return dict([
            ('Daily', dict(calculate_all_functions(Qo, Qm))),
            ('Yearly', dict(calculate_all_functions(Qo_yearly, Qm_yearly)))
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
