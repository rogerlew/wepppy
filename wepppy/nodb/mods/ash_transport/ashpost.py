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
from copy import deepcopy

import shutil

# non-standard
import jsonpickle
import numpy as np
import pandas as pd

from wepppy.all_your_base import (
    isfloat,
    isint,
    YearlessDate,
    probability_of_occurrence,
    weibull_series
)

from wepppy.nodb.base import NoDbBase


class AshPostNoDbLockedException(Exception):
    pass


class AshPost(NoDbBase):
    """
    Manager that keeps track of project details
    and coordinates access of NoDb instances.
    """
    __name__ = 'AshPost'

    def __init__(self, wd, cfg_fn):
        super(AshPost, self).__init__(wd, cfg_fn)

        self.lock()

        # noinspection PyBroadException
        try:
            config = self.config

            self.summary_stats = None
            self.reservoir_stats = None
            self.pw0_stats = None
            self._ash_out = None

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
        with open(_join(wd, 'ashpost.nodb')) as fp:
            db = jsonpickle.decode(fp.read())
            assert isinstance(db, AshPost), db

            if _exists(_join(wd, 'READONLY')):
                return db

            if os.path.abspath(wd) != os.path.abspath(db.wd):
                db.wd = wd
                db.lock()
                db.dump_and_unlock()

            return db

    @property
    def _nodb(self):
        return _join(self.wd, 'ashpost.nodb')

    @property
    def _lock(self):
        return _join(self.wd, 'ashpost.nodb.lock')

    @property
    def ash_out(self):
        return self._ash_out

    def run_post(self, recurrence=(100, 50, 20, 10, 5, 2.5, 1)):
        ash_fns = glob(_join(self.ash_dir, '*_ash.csv'))
        if len(ash_fns) == 0:
            return

        self.lock()

        # noinspection PyBroadException
        try:

            self._run_recurrence(recurrence=recurrence)
            self._run_reservoir_report(recurrence=recurrence)
            self._run_ash_out()
            self._run_pw0()
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def meta(self):
        from wepppy.nodb import Ash
        ash = Ash.getInstance(self.wd)
        return ash.meta

    @property
    def fire_date(self):
        from wepppy.nodb import Ash
        ash = Ash.getInstance(self.wd)
        return ash.fire_date

    def _run_ash_out(self):
        from wepppy.nodb import Watershed

        watershed = Watershed.getInstance(self.wd)
        translator = watershed.translator_factory()
        meta = self.meta

        ash_out = {}
        for topaz_id, ss in watershed._subs_summary.items():
            wepp_id = translator.wepp(top=topaz_id)
            burnclass = meta[str(topaz_id)]['burn_class']

            ash_out[topaz_id] = {}
            ash_out[topaz_id]['burnclass'] = burnclass
            if burnclass <= 1:
                ash_out[topaz_id]['water_transport (kg/ha)'] = 0.0
                ash_out[topaz_id]['wind_transport (kg/ha)'] = 0.0
                ash_out[topaz_id]['ash_transport (kg/ha)'] = 0.0
            else:
                fn = _join(self.ash_dir,  'H{}_ash_stats_per_year_water.csv'.format(wepp_id))
                with open(fn) as fp:
                    df = pd.read_csv(fp)
                    series = df['cum_water_transport (tonne/ha)']
                    ash_out[topaz_id]['water_transport (kg/ha)'] = 1000 * float(np.mean(series))

                fn = _join(self.ash_dir, 'H{}_ash_stats_per_year_wind.csv'.format(wepp_id))
                with open(fn) as fp:
                    df = pd.read_csv(fp)
                    series = df['cum_wind_transport (tonne/ha)']
                    ash_out[topaz_id]['wind_transport (kg/ha)'] = 1000 * float(np.mean(series))

                fn = _join(self.ash_dir, 'H{}_ash_stats_per_year_ash.csv'.format(wepp_id))
                with open(fn) as fp:
                    df = pd.read_csv(fp)
                    series = df['cum_ash_transport (tonne/ha)']
                    ash_out[topaz_id]['ash_transport (kg/ha)'] = 1000 * float(np.mean(series))

        self._ash_out = ash_out

    def _run_recurrence(self, recurrence):
        """
        builds recurrence interval and annuals report for the watershed

        :param recurrence:
        :return:
        """
        from wepppy.nodb import Watershed

        wd = self.wd
        ash_dir = self.ash_dir
        fire_date = self.fire_date
        watershed = Watershed.getInstance(wd)
        translator = watershed.translator_factory()
        meta = self.meta

        water = []
        wind = []
        ash = []
        cum_water = []
        cum_wind = []
        cum_ash = []
        precip = []

        for topaz_id, sub in watershed.sub_iter():
            wepp_id = translator.wepp(top=topaz_id)
            ash_fn = _join(ash_dir, 'H{wepp_id}_ash.csv'.format(wepp_id=wepp_id))

            # unburned landuses won't have ash outputs
            if _exists(ash_fn):
                df = pd.read_csv(ash_fn)
                water.append(df['ash_delivery_by_water (tonne)'].to_numpy())
                wind.append(df['ash_delivery_by_wind (tonne)'].to_numpy())
                ash.append(df['ash_delivery (tonne)'].to_numpy())
                cum_water.append(df['cum_ash_delivery_by_water (tonne)'].to_numpy())
                cum_wind.append(df['cum_ash_delivery_by_wind (tonne)'].to_numpy())
                cum_ash.append(df['cum_ash_delivery (tonne)'].to_numpy())
                precip.append(df['precip (mm)'].to_numpy())

        water = np.array(water)
        water = np.sum(water, axis=0)
        wind = np.array(wind)
        wind = np.sum(wind, axis=0)
        ash = np.array(ash)
        ash = np.sum(ash, axis=0)
        precip = np.array(precip)
        precip = np.sum(precip, axis=0)

        cum_water = np.array(cum_water)
        cum_water = np.sum(cum_water, axis=0)
        cum_wind = np.array(cum_wind)
        cum_wind = np.sum(cum_wind, axis=0)
        cum_ash = np.array(cum_ash)
        cum_ash = np.sum(cum_ash, axis=0)

        df = deepcopy(df)
        df['ash_delivery_by_water (tonne)'] = pd.Series(water, index=df.index)
        df['ash_delivery_by_wind (tonne)'] = pd.Series(wind, index=df.index)
        df['ash_delivery (tonne)'] = pd.Series(ash, index=df.index)
        df['precip (mm)'] = pd.Series(precip, index=df.index)

        df['cum_ash_delivery_by_water (tonne)'] = pd.Series(cum_water, index=df.index)
        df['cum_ash_delivery_by_wind (tonne)'] = pd.Series(cum_wind, index=df.index)
        df['cum_ash_delivery (tonne)'] = pd.Series(cum_ash, index=df.index)

        breaks = []    # list of indices of new fire years
        last_day = fire_date.yesterday
        for i, _row in df.iterrows():
            if _row.mo == last_day.month and _row.da == last_day.day:
                breaks.append(i)  # record the index for the new year

        yr_df = df.loc[[brk for brk in breaks],
                       ['year',
                        'cum_ash_delivery_by_water (tonne)',
                        'cum_ash_delivery_by_wind (tonne)',
                        'cum_ash_delivery (tonne)']]

        num_fire_years = len(breaks)

        annuals = {}
        for measure in ['cum_ash_delivery_by_water (tonne)',
                        'cum_ash_delivery_by_wind (tonne)',
                        'cum_ash_delivery (tonne)']:

            annuals[measure] = []
            yr_df.sort_values(by=measure, ascending=False, inplace=True)

            data = []
            colnames = ['year', measure, 'probability', 'rank', 'return_interval']
            for j, (i, _row) in enumerate(yr_df.iterrows()):
                val = _row[measure]

                if val == 0.0:
                    break

                rank = j + 1
                ri = (num_fire_years + 1) / rank
                prob = probability_of_occurrence(ri, 1.0)
                data.append([int(_row.year), float(val), float(prob), int(rank), float(ri)])
                annuals[measure].append(dict(zip(colnames, data[-1])))

            _df = pd.DataFrame(data, columns=colnames)
            _df.to_csv(_join(ash_dir, '%s_ash_stats_per_year_%s.csv' % ('pw0', measure.replace(' (tonne)', ''))),
                       index=False)

        num_days = len(df.da)
        return_periods = {}
        for measure in ['ash_delivery_by_wind (tonne)', 'ash_delivery_by_water (tonne)', 'ash_delivery (tonne)']:
            return_periods[measure] = {}
            df.sort_values(by=measure, ascending=False, inplace=True)

            data = []
            for j, (i, _row) in enumerate(df.iterrows()):
                val = _row[measure]

                if val == 0.0:
                    break

                dff = _row['days_from_fire (days)']
                rank = j + 1
                ri = (num_days + 1) / rank
                ri /= 365.25
                prob = probability_of_occurrence(ri, 1.0)
                data.append([int(_row.year), int(_row.mo), int(_row.da), dff, val, prob, rank, ri, _row['precip (mm)']])

            _df = pd.DataFrame(data,
                               columns=['year', 'mo', 'da', 'days_from_fire',
                                        measure, 'probability', 'rank', 'return_interval', 'precip'])
            _df.to_csv(_join(ash_dir, '%s_ash_stats_per_event_%s.csv' % ('pw0', measure.replace(' (tonne)', ''))),
                       index=False)

            rec = weibull_series(recurrence, num_fire_years)

            num_events = len(_df.da)
            for retperiod in recurrence:
                if retperiod not in rec:
                    return_periods[measure][retperiod] = None
                else:
                    indx = rec[retperiod]
                    if indx >= num_events:
                        return_periods[measure][retperiod] = None
                    else:
                        _row = dict(_df.loc[indx, :])
                        for _m in _row:
                            if _m in ('year', 'mo', 'da', 'days_from_fire', 'rank'):
                                _row[_m] = int(_row[_m])
                            elif isfloat(_row[_m]):
                                _row[_m] = float(_row[_m])
                            else:
                                _row[_m] = str(_row[_m])

                        return_periods[measure][retperiod] = _row

        sev_water = {burn_class: [] for burn_class in range(1, 5)}
        sev_wind = {burn_class: [] for burn_class in range(1, 5)}
        sev_ash = {burn_class: [] for burn_class in range(1, 5)}
        sev_cum_water = {burn_class: [] for burn_class in range(1, 5)}
        sev_cum_wind = {burn_class: [] for burn_class in range(1, 5)}
        sev_cum_ash = {burn_class: [] for burn_class in range(1, 5)}

        for topaz_id, sub in watershed.sub_iter():
            wepp_id = translator.wepp(top=topaz_id)
            ash_fn = _join(ash_dir, 'H{wepp_id}_ash.csv'.format(wepp_id=wepp_id))
            burn_class = meta[topaz_id]['burn_class']

            # unburned landuses won't have ash outputs
            if _exists(ash_fn):
                df = pd.read_csv(ash_fn)
                sev_water[burn_class].append(df['ash_delivery_by_water (tonne)'].to_numpy())
                sev_wind[burn_class].append(df['ash_delivery_by_wind (tonne)'].to_numpy())
                sev_ash[burn_class].append(df['ash_delivery (tonne)'].to_numpy())
                sev_cum_water[burn_class].append(df['cum_ash_delivery_by_water (tonne)'].to_numpy())
                sev_cum_wind[burn_class].append(df['cum_ash_delivery_by_wind (tonne)'].to_numpy())
                sev_cum_ash[burn_class].append(df['cum_ash_delivery (tonne)'].to_numpy())

        # burn_class report
        sev_annuals = {burn_class: {} for burn_class in range(1, 5)}
        for burn_class in range(1, 5):
            sev_water[burn_class] = np.array(sev_water[burn_class])
            sev_water[burn_class] = np.sum(sev_water[burn_class], axis=0)
            sev_wind[burn_class] = np.array(sev_wind[burn_class])
            sev_wind[burn_class] = np.sum(sev_wind[burn_class], axis=0)
            sev_ash[burn_class] = np.array(sev_ash[burn_class])
            sev_ash[burn_class] = np.sum(sev_ash[burn_class], axis=0)

            sev_cum_water[burn_class] = np.array(sev_cum_water[burn_class])
            sev_cum_water[burn_class] = np.sum(sev_cum_water[burn_class], axis=0)
            sev_cum_wind[burn_class] = np.array(sev_cum_wind[burn_class])
            sev_cum_wind[burn_class] = np.sum(sev_cum_wind[burn_class], axis=0)
            sev_cum_ash[burn_class] = np.array(sev_cum_ash[burn_class])
            sev_cum_ash[burn_class] = np.sum(sev_cum_ash[burn_class], axis=0)

            df = deepcopy(df)
            df['ash_delivery_by_water (tonne)'] = pd.Series(sev_water[burn_class], index=df.index)
            df['ash_delivery_by_wind (tonne)'] = pd.Series(sev_wind[burn_class], index=df.index)
            df['ash_delivery (tonne)'] = pd.Series(sev_ash[burn_class], index=df.index)

            df['cum_ash_delivery_by_water (tonne)'] = pd.Series(sev_cum_water[burn_class], index=df.index)
            df['cum_ash_delivery_by_wind (tonne)'] = pd.Series(sev_cum_wind[burn_class], index=df.index)
            df['cum_ash_delivery (tonne)'] = pd.Series(sev_cum_ash[burn_class], index=df.index)

            breaks = []  # list of indices of new fire years
            last_day = fire_date.yesterday
            for i, _row in df.iterrows():
                if _row.mo == last_day.month and _row.da == last_day.day:
                    breaks.append(i)  # record the index for the new year

            yr_df = df.loc[[brk for brk in breaks],
                           ['year',
                            'cum_ash_delivery_by_water (tonne)',
                            'cum_ash_delivery_by_wind (tonne)',
                            'cum_ash_delivery (tonne)']]

            num_fire_years = len(breaks)

            for measure in ['cum_ash_delivery_by_water (tonne)',
                            'cum_ash_delivery_by_wind (tonne)',
                            'cum_ash_delivery (tonne)']:

                sev_annuals[burn_class][measure] = []
                yr_df.sort_values(by=measure, ascending=False, inplace=True)

                data = []
                colnames =['year', measure, 'probability', 'rank', 'return_interval']
                for j, (i, _row) in enumerate(yr_df.iterrows()):
                    val = _row[measure]

                    if val == 0.0:
                        break

                    rank = j + 1
                    ri = (num_fire_years + 1) / rank
                    prob = probability_of_occurrence(ri, 1.0)
                    data.append([int(_row.year), float(val), float(prob), int(rank), float(ri)])
                    sev_annuals[burn_class][measure].append(dict(zip(colnames, data[-1])))

                _df = pd.DataFrame(data, columns=colnames)
                _df.to_csv(_join(ash_dir, '%s_burn_class=%i,ash_stats_per_year_%s.csv' %
                                 ('pw0', burn_class, measure.replace(' (tonne)', ''))),
                           index=False)

        self.summary_stats = dict(recurrence=recurrence,
                                  return_periods=return_periods,
                                  annuals=annuals,
                                  sev_annuals=sev_annuals)

    def _run_reservoir_report(self, recurrence=(100, 50, 20, 10, 5, 2.5, 1)):
        """
        builds recurrence interval and annuals report for the watershed

        :param recurrence:
        :return:
        """
        from wepppy.nodb import Watershed

        wd = self.wd
        ash_dir = self.ash_dir
        fire_date = self.fire_date
        watershed = Watershed.getInstance(wd)
        translator = watershed.translator_factory()
        meta = self.meta

        water = {2: [], 3: [], 4: []}
        cum_water = {2: [], 3: [], 4: []}

        for topaz_id, sub in watershed.sub_iter():
            wepp_id = translator.wepp(top=topaz_id)
            ash_fn = _join(ash_dir, 'H{wepp_id}_ash.csv'.format(wepp_id=wepp_id))

            # unburned landuses won't have ash outputs
            if _exists(ash_fn):
                burn_class = meta[topaz_id]['burn_class']
                df = pd.read_csv(ash_fn)
                water[burn_class].append(df['ash_delivery_by_water (tonne)'].to_numpy())
                cum_water[burn_class].append(df['cum_ash_delivery_by_water (tonne)'].to_numpy())

        df = deepcopy(df)

        for burn_class in [2, 3, 4]:
            water[burn_class] = np.array(water[burn_class])
            water[burn_class] = np.sum(water[burn_class], axis=0)

            cum_water[burn_class] = np.array(cum_water[burn_class])
            cum_water[burn_class] = np.sum(cum_water[burn_class], axis=0)

            df['burn_class={},ash_delivery_by_water (tonne)'.format(burn_class)] = \
                pd.Series(water[burn_class], index=df.index)
            df['burn_class={},cum_ash_delivery_by_water (tonne)'.format(burn_class)] = \
                pd.Series(cum_water[burn_class], index=df.index)

        breaks = []    # list of indices of new fire years
        last_day = fire_date.yesterday
        for i, _row in df.iterrows():
            if _row.mo == last_day.month and _row.da == last_day.day:
                breaks.append(i)  # record the index for the new year

        num_fire_years = len(breaks)
        num_days = len(df.da)

        return_periods = {2: {}, 3: {}, 4: {}}
        for burn_class in [2, 3, 4]:
            measure = 'burn_class={},ash_delivery_by_water (tonne)'.format(burn_class)
            df.sort_values(by=measure, ascending=False, inplace=True)

            data = []
            for j, (i, _row) in enumerate(df.iterrows()):
                val = _row[measure]

                if val == 0.0:
                    break

                dff = _row['days_from_fire (days)']
                rank = j + 1
                ri = (num_days + 1) / rank
                ri /= 365.25
                prob = probability_of_occurrence(ri, 1.0)
                data.append([int(_row.year), int(_row.mo), int(_row.da), dff, val, prob, rank, ri])

            _df = pd.DataFrame(data,
                               columns=['year', 'mo', 'da', 'days_from_fire',
                                        measure, 'probability', 'rank', 'return_interval'])
            _df.to_csv(_join(ash_dir, '%s_burnclass=%i,ash_stats_per_event_%s.csv' %
                             ('pw0', burn_class, measure.replace(' (tonne)', ''))), index=False)

            rec = weibull_series(recurrence, num_fire_years)

            num_events = len(_df.da)
            actual_reccurence = []
            for retperiod in recurrence:
                if retperiod not in rec:
                    return_periods[burn_class][retperiod] = {'value': 0.0}
                else:
                    indx = rec[retperiod]
                    if indx >= num_events:
                        return_periods[burn_class][retperiod] = {'value': 0.0}
                    elif indx != -1:
                        _row = dict(_df.loc[indx, :])

                        for _m in _row:
                            if _m in ('year', 'mo', 'da', 'days_from_fire', 'rank'):
                                _row[_m] = int(_row[_m])
                            elif isfloat(_row[_m]):
                                _row[_m] = float(_row[_m])
                            else:
                                _row[_m] = str(_row[_m])

                        _row['value'] = _row['burn_class={},ash_delivery_by_water (tonne)'.format(burn_class)]

                        return_periods[burn_class][retperiod] = _row

                actual_reccurence.append(retperiod)

        self.reservoir_stats = dict(reccurence=actual_reccurence,
                                    return_periods=return_periods)

    def _run_pw0(self):
        pw0_stats = {}
        for key, src in zip(['total', 'water', 'wind'],  ['', '_by_water', '_by_wind']):
            pw0_stats[key] = {}
            for burnclass in [1, 2, 3, 4]:
                fn = _join(self.ash_dir,
                           'pw0_burn_class={burnclass},ash_stats_per_year_cum_ash_delivery{src}.csv'
                           .format(burnclass=burnclass, src=src))

                if not _exists(fn):
                    v = 0.0
                else:
                    with open(fn) as fp:
                        df = pd.read_csv(fp)
                        series = df['cum_ash_delivery{src} (tonne)'.format(src=src)]
                        v = float(np.mean(series))

                pw0_stats[key][str(burnclass)] = v

        self.pw0_stats = pw0_stats
