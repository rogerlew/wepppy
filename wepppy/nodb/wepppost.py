
import os
from os.path import exists as _exists
from os.path import join as _join
from os.path import join as _split

from glob import glob

import shutil

# non-standard
import jsonpickle
import numpy as np

# wepppy
import wepppy
from wepppy.all_your_base import (
    isint
)

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
            config = self.config
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
                    L = fp.readline()
                    if i > 24:
                        L = L.split()
                        chn_enum, area = int(L[0]), float(L[-1])

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
                    for i, L in enumerate(wat_fp.readlines()):
                        if i == 23:
                            L = L.split()
                            ofe, area = int(L[0]), float(L[-1])
                            _hill_areas[str(wepp_id)] = area
                        elif i == 24:
                            assert ofe == 1, 'Multiple ofes not supported'
                            break

            ebe_fn = _join(output_dir, 'ebe_pw0.txt')

            _days, _months, _years = [], [], []
            with open(ebe_fn) as fp:
                for L in fp.readlines()[9:]:
                    _days.append(int(L[0:5]))
                    _months.append(int(L[5:10]))
                    _years.append(int(L[10:16]))

            chanwb_fn = _join(output_dir, 'chanwb.out')

            _julians = []
            with open(chanwb_fn) as fp:
                for L in fp.readlines()[11:]:
                    _julians.append(int(L[6:13]))

            self._outletchn = int(L[21:28])

            assert len(_julians) == len(_days)

            self._chn_areas = _chn_areas
            self._hill_areas = _hill_areas
            self._wsarea = float(sum(_hill_areas.values()))

            self._days = _days
            self._months = _months
            self._years = _years
            self._julians = _julians
            self._ndays = len(self._julians)

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def dates(self):
        return ['%04i%02i%02i' % (yr, mo, da) for yr, mo, da in zip(self._years, self._months, self._days)]

    def export_streamflow(self, fn, source='Channel'):
        ndays = self._ndays
        if source == 'Channel':
            assert self._chn_streamflow is not None
            data = self._chn_streamflow

        else:
            assert self._hill_streamflow is not None
            data = self._hill_streamflow

        fp = open(fn, 'w')
        fp.write('date,Runoff,Baseflow,Lateral Flow\n')

        dates = self.dates
        runoff = data['Daily Runoff (mm)']
        latqcc = data['Daily Lateral Flow (mm)']
        baseflow = data['Daily Baseflow (mm)']

        assert ndays == len(dates)
        assert ndays == len(runoff)
        assert ndays == len(latqcc)
        assert ndays == len(baseflow)

        for d, r, l, b in zip(dates, runoff, latqcc, baseflow):
            fp.write('{},{},{},{}\n'.format(d, r, b, l))
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

    def calc_hill_streamflow(self):
        ndays = self._ndays
        hill_areas = self._hill_areas
        wsarea = self._wsarea
        ws_ha = wsarea / 10000.0
        assert isint(ndays)

        output_dir = self.output_dir

        ebe_fns = glob(_join(output_dir, 'H*.ebe.dat'))
        n = len(ebe_fns)
        assert n > 0, 'run does not contain hill event outputs'

        for wepp_id in range(1, n + 1):
            assert _exists(_join(output_dir, 'H{}.ebe.dat'.format(wepp_id)))

        runoff = np.zeros((ndays,))
        sediment = np.zeros((ndays,))

        for wepp_id in range(1, n + 1):
            wat_fn = _join(output_dir, 'H{}.ebe.dat'.format(wepp_id))
            area = hill_areas[str(wepp_id)]

            with open(wat_fn) as wat_fp:
                for i, L in enumerate(wat_fp.readlines()):
                    if i < 3:
                        continue

                    day, mo, year, Precp, Runoff, IR_det, Av_det, \
                    Mx_det, Point, Av_dep, Max_dep, Point, SedDel, ER = L.split()

                    day, mo, year = int(day), int(mo), int(year)
                    indx = self.get_indx(year, day=day, month=mo)
                    runoff[indx] += float(Runoff) * 0.001 * area
                    sediment[indx] += float(SedDel) * area * 0.001

        runoff /= self._wsarea
        runoff *= 1000

        wat_fns = glob(_join(output_dir, 'H*.wat.dat'))
        n = len(wat_fns)
        assert n > 0, 'run does not contain hill wat outputs'

        for wepp_id in range(1, n + 1):
            assert _exists(_join(output_dir, 'H{}.wat.dat'.format(wepp_id)))

        latqcc = np.zeros((ndays,))

        for wepp_id in range(1, n + 1):
            wat_fn = _join(output_dir, 'H{}.wat.dat'.format(wepp_id))
            area = hill_areas[str(wepp_id)]

            with open(wat_fn) as wat_fp:
                for i, L in enumerate(wat_fp.readlines()):
                    if i < 23:
                        continue

                    latqcc[i-23] += float(L[104:112]) * 0.001 * area

        latqcc /= self._wsarea
        latqcc *= 1000

        self.lock()
        self._hill_streamflow = {
            'Daily Runoff (mm)': [float(v) for v in runoff],
            'Daily Sediment (tonne/ha)': [float(v) for v in sediment],
            'Daily Lateral Flow (mm)': [float(v) for v in latqcc]}
        self.dump_and_unlock()

    def calc_channel_streamflow(self):
        output_dir = self.output_dir
        ndays = self._ndays
        wsarea = self._wsarea
        ws_ha = wsarea / 10000.0

        chanwb_fn = _join(output_dir, 'chanwb.out')

        runoff = []
        with open(chanwb_fn) as fp:
            for i, L in enumerate(fp.readlines()):
                if i < 11:
                    continue

                runoff.append(float(L[46:63]) / wsarea * 1000.0)

        assert len(runoff) == ndays

        ebe_fn = _join(output_dir, 'ebe_pw0.txt')

        sed_yield, solub_reactive_p, particulate_p, total_p = [], [], [], []
        with open(ebe_fn) as fp:
            for L in fp.readlines()[9:]:
                day, mo, year, p, _runoff, peak_runoff, _sed_yield, _solub_reactive_p, _particulate_p, _total_p = \
                L.split()

                sed_yield.append(float(_sed_yield) / 1000.0 / ws_ha)
                solub_reactive_p.append(float(_solub_reactive_p) / ws_ha)
                particulate_p.append(float(_particulate_p) / ws_ha)
                total_p.append(float(_total_p) / ws_ha)

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
                L = fp.readline()
                if L == '':
                    break

                if i > 24:
                    chn_enum = int(L[0:6])

                    if chn_enum == outletchn:
                        latqcc.append(float(L[104:112]))
                        baseflow.append(float(L[180:191]))

                i += 1

        assert len(latqcc) == ndays
        assert len(baseflow) == ndays

        self.lock()
        self._chn_streamflow = {
            'Daily Runoff (mm)': runoff,
            'Daily Sediment (tonne/ha)': sed_yield,
            'Daily Soluble Reactive P (kg/ha)': solub_reactive_p,
            'Daily Particulate P (kg/ha)': particulate_p,
            'Daily Total P (kg/ha)': total_p,
            'Daily Lateral Flow (mm)': latqcc,
            'Daily Baseflow (mm)': baseflow }
        self.dump_and_unlock()

if __name__ == "__main__":
    wd = '/geodata/weppcloud_runs/43bc959e-59b9-4e50-b44a-145abe338bc5/'
#    wd = '/geodata/weppcloud_runs/Blackwood_forStats/'
    post = WeppPost.getInstance(wd)
    #post.calc_hill_streamflow()
    post.calc_channel_streamflow()