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

from glob import glob


# non-standard
import jsonpickle
import numpy as np

# wepppy
from wepppy.wepp.out import TotalWatSed2

# wepppy submodules
from .base import NoDbBase


class WeppPostNoDbLockedException(Exception):
    pass


class WeppPost(NoDbBase):
    """
    Manager that keeps track of project details
    and coordinates access of NoDb instances.
    """
    __name__ = 'WeppPost'

    def __init__(self, wd, cfg_fn):
        super(WeppPost, self).__init__(wd, cfg_fn)

        self.lock()

        # noinspection PyBroadException
        try:
            self._hill_areas = {}
            self._chn_areas = {}
            self._wsarea = None
            self._outletchn = None

            self._days = None
            self._months = None
            self._julians = None
            self._years = None
            self._ndays = None
            self._hill_streamflow = None
            self._chn_streamflow = None

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
        with open(_join(wd, 'wepppost.nodb')) as fp:
            db = jsonpickle.decode(fp.read())
            assert isinstance(db, WeppPost), db

            if _exists(_join(wd, 'READONLY')):
                db.wd = os.path.abspath(wd)
                return db

            if os.path.abspath(wd) != os.path.abspath(db.wd):
                db.wd = wd
                db.lock()
                db.dump_and_unlock()

            return db

    @property
    def _nodb(self):
        return _join(self.wd, 'wepppost.nodb')

    @property
    def _lock(self):
        return _join(self.wd, 'wepppost.nodb.lock')

    def run_post(self):

        self.lock()

        # noinspection PyBroadException
        try:
            output_dir = self.output_dir

            chnwb_fn = _join(output_dir, 'chnwb.txt')

            _chn_areas = {}
            with open(chnwb_fn) as fp:
                i = 0
                while 1:
                    line = fp.readline()
                    if i > 24:
                        line = line.split()
                        chn_enum, area = int(line[0]), float(line[-1])

                        if str(chn_enum) in _chn_areas:
                            break
                        else:
                            _chn_areas[str(chn_enum)] = area

                    i += 1

            wat_fns = glob(_join(output_dir, 'H*.wat.dat'))
            n = len(wat_fns)
            assert n > 0

            for wepp_id in range(1, n + 1):
                assert _exists(_join(output_dir, 'H{}.wat.dat'.format(wepp_id)))

            _hill_areas = {}
            for wepp_id in range(1, n + 1):
                wat_fn = _join(output_dir, 'H{}.wat.dat'.format(wepp_id))

                with open(wat_fn) as wat_fp:
                    ofe = None
                    for i, line in enumerate(wat_fp.readlines()):
                        if i == 23:
                            line = line.split()
                            ofe, area = int(line[0]), float(line[-1])
                            _hill_areas[str(wepp_id)] = area
                        elif i == 24:
                            assert ofe == 1, 'Multiple ofes not supported'
                            break

            ebe_fn = _join(output_dir, 'ebe_pw0.txt')

            _days, _months, _years = [], [], []
            with open(ebe_fn) as fp:
                for line in fp.readlines()[9:]:
                    _days.append(int(line[0:5]))
                    _months.append(int(line[5:10]))
                    _years.append(int(line[10:16]))

            chanwb_fn = _join(output_dir, 'chanwb.out')

            _julians = []
            with open(chanwb_fn) as fp:
                for line in fp.readlines()[11:]:
                    _julians.append(int(line[6:13]))

            self._outletchn = int(line[21:28])

            if len(_julians) == 0:
                raise IOError('chanwb.out does not contain data')

            if len(_days) == 0:
                raise IOError('ebe_pw0.txt does not contain data')

            assert len(_julians) == len(_days), (len(_julians), len(_days))

            self._chn_areas = _chn_areas
            self._hill_areas = _hill_areas
            self._wsarea = float(sum(_hill_areas.values()))

            self._days = _days
            self._months = _months
            self._years = _years
            self._julians = _julians
            self._ndays = len(self._julians)
            self._hill_streamflow = None
            self._chn_streamflow = None
            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    def export_streamflow(self, fn, source='Hillslopes', exclude_yr_indxs=(0, 1), stacked=False):
        ndays = self._ndays
        if source == 'Channel':
            data = self.chn_streamflow
        else:
            data = self.hill_streamflow

        fp = open(fn, 'w')
        fp.write('date,Runoff,Baseflow,Lateral Flow\n')

        runoff = data['Daily Runoff (mm)']
        latqcc = data['Daily Lateral Flow (mm)']
        baseflow = data['Daily Baseflow (mm)']

        assert ndays == len(runoff)
        assert ndays == len(latqcc)
        assert ndays == len(baseflow)

        exclude_years = []
        if exclude_yr_indxs is not None:
            years = sorted(set(self._years))
            for indx in exclude_yr_indxs:
                exclude_years.append(years[indx])

        for yr, mo, da, r, lf, b in zip(self._years, self._months, self._days, runoff, latqcc, baseflow):
            if yr in exclude_years:
                continue

            d = '%04i%02i%02i' % (yr, mo, da)

            if stacked:
                lf += b
                r += lf

            fp.write('{},{},{},{}\n'.format(d, r, b, lf))
        fp.close()

    def get_indx(self, year, day=None, month=None, julian=None):
        years = self._years
        months = self._months
        days = self._days
        julians = self._julians

        indx = np.where(np.array(years) == year)[0]
        i0 = indx[0]
        iend = indx[-1]+1

        if julian is not None:
            a = np.argwhere(np.array(julians[i0:iend]) == julian)[0][0]

            return i0 + a

        if month is not None:
            jndx = np.where(np.array(months[i0:iend]) == month)[0]
            j0 = jndx[0]
            jend = jndx[-1]+1

            if month == 2 and day == 29:
                a = jend
            else:
                a = np.argwhere(np.array(days[j0:jend]) == day)[0][0]

            return i0 + j0 + a

    @property
    def hill_streamflow(self):
        if self._hill_streamflow is None:
            self._calc_hill_streamflow()
        return self._hill_streamflow

    def _calc_hill_streamflow(self):
        watsed = TotalWatSed2(self.wd)
        watsed_d = watsed.d

        # noinspection PyDictCreation
        self._hill_streamflow = {}
        self._hill_streamflow['Daily Runoff (mm)'] = watsed_d['Runoff (mm)']
        self._hill_streamflow['Daily Sediment (tonne/ha)'] = watsed_d['Sed Del Density (tonne/ha)']
        self._hill_streamflow['Daily Lateral Flow (mm)'] = watsed_d['Lateral Flow (mm)']
        self._hill_streamflow['Daily Baseflow (mm)'] = watsed_d['Baseflow (mm)']

        if 'Total P (kg)' in watsed_d:
            self._hill_streamflow['Daily Total P (kg)'] = watsed_d['Total P (kg)']

        if 'Particulate P (kg)' in watsed_d:
            self._hill_streamflow['Daily Particulate P (kg)'] = watsed_d['Particulate P (kg)']

        if 'Soluble Reactive P (kg)' in watsed_d:
            self._hill_streamflow['Daily Soluble Reactive P (kg)'] = watsed_d['Soluble Reactive P (kg)']

        if 'Sed Del (tonne)' in watsed_d:
            self._hill_streamflow['Daily Sed Del (tonne/day)'] = watsed_d['Sed Del (tonne)']

        for k in self._hill_streamflow:
            self._hill_streamflow[k] = [float(v) for v in self._hill_streamflow[k]]

    @property
    def chn_streamflow(self):
        if self._chn_streamflow is None:
            self._calc_channel_streamflow()
        return self._chn_streamflow

    def _calc_channel_streamflow(self):
        output_dir = self.output_dir
        ndays = self._ndays
        wsarea = self._wsarea
        ws_ha = wsarea / 10000.0

        chanwb_fn = _join(output_dir, 'chanwb.out')

        runoff = []
        with open(chanwb_fn) as fp:
            for i, line in enumerate(fp.readlines()):
                if i < 11:
                    continue

                runoff.append(float(line[46:63]) / wsarea * 1000.0)

        assert len(runoff) == ndays

        ebe_fn = _join(output_dir, 'ebe_pw0.txt')

        sed_yield, solub_reactive_p, particulate_p, total_p = [], [], [], []
        with open(ebe_fn) as fp:
            for line in fp.readlines()[9:]:
                line = line.split()
                day, mo, year, p, _runoff, peak_runoff, _sed_yield, _solub_reactive_p, _particulate_p, _total_p = \
                    line[:10]

                sed_yield.append(float(_sed_yield) / 1000.0 / ws_ha)
                solub_reactive_p.append(float(_solub_reactive_p))
                particulate_p.append(float(_particulate_p))
                total_p.append(float(_total_p))

        assert len(sed_yield) == ndays
        assert len(solub_reactive_p) == ndays
        assert len(particulate_p) == ndays
        assert len(total_p) == ndays

        chnwb_fn = _join(output_dir, 'chnwb.txt')

        outletchn = self._outletchn
        latqcc = []
        baseflow = []
        with open(chnwb_fn) as fp:
            i = 0
            while 1:
                line = fp.readline()
                if line == '':
                    break

                if i > 24:
                    chn_enum = int(line[0:6])

                    if chn_enum == outletchn:
                        latqcc.append(float(line[104:112]))
                        baseflow.append(float(line[180:191]))

                i += 1

        assert len(latqcc) == ndays
        assert len(baseflow) == ndays

        self.lock()
        self._chn_streamflow = {
            'Daily Runoff (mm)': runoff,
            'Daily Sediment (tonne/ha)': sed_yield,
            'Daily Soluble Reactive P (kg)': solub_reactive_p,
            'Daily Particulate P (kg)': particulate_p,
            'Daily Total P (kg)': total_p,
            'Daily Lateral Flow (mm)': latqcc,
            'Daily Baseflow (mm)': baseflow
        }
        self.dump_and_unlock()
