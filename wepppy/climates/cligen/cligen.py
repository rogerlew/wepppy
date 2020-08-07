# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

import os
from os.path import join as _join
from os.path import exists as _exists
from os.path import split as _split

from subprocess import (
    Popen, PIPE
)

import numpy as np

import datetime
import subprocess
import shutil
import math
from copy import deepcopy
import sqlite3

import pandas as pd

from wepppy.all_your_base import (
    isfloat,
    clamp,
    elevationquery,
    haversine,
    RasterDatasetInterpolator,
    IS_WINDOWS
)

from wepppy.climates.metquery_client import (
    get_prism_monthly_tmin,
    get_prism_monthly_tmax,
    get_prism_monthly_ppt,
    get_eobs_monthly_tmin,
    get_eobs_monthly_tmax,
    get_eobs_monthly_ppt,
    get_agdc_monthly_tmin,
    get_agdc_monthly_tmax,
    get_agdc_monthly_ppt,
    get_daymet_prcp_pwd,
    get_daymet_prcp_pww,
    get_daymet_prcp_skew,
    get_daymet_prcp_std,
    get_daymet_prcp_mean,
    get_daymet_srld_mean,
    get_prism_monthly_tdmean,
    c_to_f

)


_thisdir = os.path.dirname(__file__)
_db = _join(_thisdir, '2015_stations.db')
_stations_dir = _join(_thisdir, '2015_par_files')
_bin_dir = _join(_thisdir, 'bin')


_rowfmt = lambda x: '\t'.join(['%0.2f' % v for v in x])


days_in_mo = np.array([31, 28.25, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])


def _row_formatter(values):
    """
    tasks a list of value and formats them as a string for .par files
    """
    s = []
    for v in values:
        v = float(v)
        if v < 1.0:
            s.append('  ' + '{0:.2f}'.format(v)[1:])
        elif v < 10.0:
            s.append(' {0:.2f}'.format(v))
        elif v > 10000.0:
            s.append('{0}'.format(int(v)))
        elif v > 1000.0:
            s.append('{0:.0f}'.format(v))
        elif v > 100.0:
            s.append('{0:.1f}'.format(v))
        else:
            s.append('{0:.2f}'.format(v))

    return ' '.join(s)


def cli2pat(prcp=50, dur=2, tp=0.3, ip=4, max_time=[10, 30, 60]):
    """
    Calculates peak intensities for 10, 30, and 60 minute intervals
    based on storm prcp, duration, tp, and ip.

    Ported from Correy Moffet's R code (Sourced through Bill Elliott).

    :param prcp: precip in mm
    :param dur:
    :param tp:
    :param ip:
    :param max_time:
    :return:
    """
    if prcp == 0 or dur == 0:
        return [0.0 for t in max_time]

    if tp <= 0.0:
        tp = 0.1

    the_b = lambda _b, _tp, _ip: (_ip - _ip * np.exp(-_b * _tp)) / _tp
    im = prcp/dur
    max_time = [t / 60.0 for t in max_time]
    peaks = len(max_time)
    last_b = 15
    b = 10
    while abs(b-last_b) > 0.000001:
        last_b = b
        b = the_b(b, tp, ip)

    if tp == 1:
        tp = 0.999

    d = b*tp/(1-tp)
    starts = [None for i in max_time]
    ends = [None for i in max_time]
    dur_peak = [None for i in max_time]
    I_peak = [None for i in max_time]
    for p in range(peaks):
        t_start = tp - max_time[p] / dur
        t_high = tp
        t_low = t_start
        t_end = tp
        i_start = ip * np.exp(b * (t_start - tp))
        i_end = ip
        while abs(i_start - i_end) > 0.000001:
            if i_start < i_end:
                t_low = t_start
            else:
                t_high = t_start
            t_start = (t_high + t_low) / 2
            t_end = t_start + max_time[p] / dur
            i_start = ip * np.exp(b * (t_start - tp))
            i_end = ip * np.exp(d * (tp - t_end))

        if t_start < 0:
            starts[p] = 0
            ends[p] = 1
        else:
            starts[p] = t_start
            ends[p] = t_end

        dur_peak[p] = ends[p] - starts[p]
        I_peak[p] = ((ip/b - ip/b * np.exp(b * (starts[p] - tp))) +
                     (ip/d - ip/d * np.exp(d * (tp - ends[p])))) * \
                    im / max(dur_peak[p], max_time[p] / dur)

    return I_peak


def _make_clinp(wd, cliver, years, cli_fname, par):
    """
    makes an input file that is passed as stdin to cligen
    """
    clinp = _join(wd, "clinp.txt")
    fid = open(clinp, "w")

    if cliver in ["5.2", "5.3"]:
        fid.write("5\n1\n{years}\n{cli_fname}\nn\n\n"
                  .format(years=years, cli_fname=cli_fname))
    else:
        fid.write("\n{par}\nn\n5\n1\n{years}\n{cli_fname}\nn\n\n"
                  .format(par=par, years=years, cli_fname=cli_fname))

    fid.close()

    assert _exists(clinp)

    return clinp


def df_to_prn(df, prn_fn, p_key, tmax_key, tmin_key):
    """
    creates a prn file containing daily timeseries data for input to
    cligen

    columns are formatted as
    {month} {day} {year} {p_in_tenthinches} {tmax} {tmin}
    """

    if 'mm' in p_key:
        df[p_key] /= 25.4

    df[p_key] *= 100.0
    df[p_key] = np.round(df[p_key])
    df[tmax_key] = np.round(c_to_f(df[tmax_key]))
    df[tmin_key] = np.round(c_to_f(df[tmin_key]))

    fp = open(prn_fn, 'w')
    mo, da, yr = 0, 0, 0
    p, tmax, tmin = '', '', ''
    for index, row in df.iterrows():

        mo, da, yr = int(row.month), int(row.day), int(row.year)
        p, tmax, tmin = row[p_key], row[tmax_key], row[tmin_key]

        if math.isnan(p) or math.isnan(tmax) or math.isnan(tmin):
            print('encountered nan df writing ', prn_fn)
            continue

        p, tmax, tmin = int(p), int(tmax), int(tmin)

        fp.write("{0:<5}{1:<5}{2:<5}{3:<5}{4:<5}{5:<5}\r\n"
                 .format(mo, da, yr, p, tmax, tmin))

        if mo == 12 and da == 30 and yr % 4 == 0:
            fp.write("{0:<5}{1:<5}{2:<5}{3:<5}{4:<5}{5:<5}\r\n"
                     .format(mo, da, yr, p, tmax, tmin))

    fp.close()


def build_gridmet_prn(gridmet_dir, start_year, end_year, prn_fn, verbose=False):

    fp = open(prn_fn, 'w')
    for year in range(start_year, end_year + 1):
        d = {}
        for var in ['pr', 'tmmn', 'tmmx']:
            fn = _join(gridmet_dir, '%s_%s.npy' % (var, str(year)))
            assert _exists(fn)
            d[var] = [float(x) for x in list(np.load(fn))]

        d['dates'] = [datetime.datetime(year, 1, 1) +
                      datetime.timedelta(i) for i, _ in enumerate(d['pr'])]

        d['pr'] = np.array(d['pr'])
        d['pr'] /= 25.4
        d['pr'] *= 100.0
        d['pr'] = np.round(d['pr'])

        d['tmmx'] = np.array(d['tmmx'])
        d['tmmx'] = np.round(c_to_f(d['tmmx']))
        d['tmmx'] = np.round(d['tmmx'])

        d['tmmn'] = np.array(d['tmmn'])
        d['tmmn'] = np.round(c_to_f(d['tmmn']))
        d['tmmn'] = np.round(d['tmmn'])

        for i, (pr, tmmn, tmmx, _date) in enumerate(zip(d['pr'], d['tmmn'], d['tmmx'], d['dates'])):
            #print(pr, tmmn, tmmx, _date)
            fp.write("{0:<5}{1:<5}{2:<5}{3:<5}{4:<5}{5:<5}\r\n"
                     .format(_date.month, _date.day, _date.year, int(pr), int(tmmx), int(tmmn)))
    fp.close()
    

def build_daymet_prn(lat, lng, observed_data, start_year, end_year, prn_fn, verbose=False,
                     discontinuous_temperature_adjustment_pars=None):

    fp = open(prn_fn, 'w')
    for year in range(start_year, end_year + 1):

        d = {}
        for varname in ['prcp', 'tmin', 'tmax']:
            if verbose:
                print(year, varname)

            fn = observed_data[(varname, year)]
            rdi = RasterDatasetInterpolator(fn)
            d[varname] = rdi.get_location_info(lng=lng, lat=lat, method='cubic')

        d['prcp'] = np.array(d['prcp'])
        d['prcp'] /= 25.4
        d['prcp'] *= 100.0
        d['prcp'] = np.round(d['prcp'])

        d['tmax'] = np.array(d['tmax'])
        d['tmax'] = np.round(c_to_f(d['tmax']))

        d['tmin'] = np.array(d['tmin'])
        d['tmin'] = np.round(c_to_f(d['tmin']))

        for i, (prcp, tmin, tmax) in enumerate(zip(d['prcp'], d['tmin'], d['tmax'])):
            _date = datetime.datetime(year, 1, 1) + datetime.timedelta(i)

            fp.write("{0:<5}{1:<5}{2:<5}{3:<5}{4:<5}{5:<5}\r\n"
                     .format(_date.month, _date.day, _date.year, int(prcp), int(tmax), int(tmin)))

        if year % 4 == 0:
            fp.write("{0:<5}{1:<5}{2:<5}{3:<5}{4:<5}{5:<5}\r\n"
                     .format(_date.month, _date.day, _date.year, int(prcp), int(tmax), int(tmin)))

    fp.close()


class ClimateFile(object):
    def __init__(self, cli_fn):

        self.cli_fn = cli_fn
        with open(cli_fn) as fp:
            lines = fp.readlines()

        _ = lines[4].split()
        self.lat = float(_[0])
        self.lng = float(_[1])
        self.elevation = float(_[2])

        i = 0
        for i, L in enumerate(lines):
            if 'da mo year' in L:
                break

        header = lines[:i]
        colnames = [v.strip() for v in lines[i].split()]

        assert ' '.join(colnames) == \
               'da mo year prcp dur tp ip tmax tmin rad w-vl w-dir tdew', colnames

        self.dtypes = [int, int, int, float, float, float, float,
                       float, float, float, float, float, float]
        self.data0line = i + 2
        self.lines = lines
        self.header = header
        self.colnames = colnames

    def discontinuous_temperature_adjustment(self, target_date: datetime.date):
        """
        adjusts tmax, tmin, and tdew with discontinuous observed climate datasets. e.g. climate station moved at
        a date or recalibrated.

        Data before the target date are adjusted as follows:
        tmax = tmax - tmax_diff
        tmin = tmin - tmin_diff

        if tdew > tmin:
            tdew = tmin
        where:
            tmax_diff = average tmax after date - average tmax before date
            tmin_diff = average tmin after date - average tmin before date

        :param target_date:
        :return:
        """

        assert isinstance(target_date, datetime.date)

        yr, mo, da = target_date.year, target_date.month, target_date.day
        df = self.as_dataframe()
        _dates = {(int(row.year), int(row.mo), int(row.da)): i for i, row in df.iterrows()}
        assert (yr, mo, da) in _dates
        indx = _dates[(yr, mo, da)]

        tmaxs = df.tmax.to_numpy()
        tmax_diff = np.mean(tmaxs[:indx]) - np.mean(tmaxs[indx:])
        tmaxs[:indx] -= tmax_diff

        tmins = df.tmin.to_numpy()
        tmin_diff = np.mean(tmins[:indx]) - np.mean(tmins[indx:])
        tmins[:indx] -= tmin_diff

        tdews = df.tdew.to_numpy()
        tdew_indx = np.where(tdews < tmins)
        tdews[tdew_indx] = tmins[tdew_indx]

        _dates = list(_dates.keys())
        self.replace_var('tmax', _dates, tmaxs)
        self.replace_var('tmin', _dates, tmins)
        self.replace_var('tdew', _dates, tdews)

    def transform_precip(self, offset: float, scale: float):
        """
        linearly transforms precipitation by:
        new_precip = offset + precip * scale

        :param offset:
        :param scale:
        :return:
        """
        df = self.as_dataframe()
        _dates = [(int(row.year), int(row.mo), int(row.da)) for i, row in df.iterrows()]

        try:
            prcp = df.prcp.to_numpy()
        except:
            prcp = df.prcp.values

        prcp = offset + prcp * scale
        self.replace_var('prcp', _dates, prcp)

    def replace_var(self, colname, dates, values):
        """
        supports the post processing of wepp files generated from
        daily observed or future data
        """
#        if colname in ['da', 'mo', 'year', 'prcp', 'tmax', 'tmin']:
#            raise ValueError('Cannot replace column "%s"' % colname)

        assert colname in self.colnames
        col_index = self.colnames.index(colname)

        d = dict(zip(dates, values))

        is_datetime = isinstance(dates[0], datetime.datetime)

        for i, L in enumerate(self.lines[self.data0line:]):
            row = [v.strip() for v in L.split()]
            if L.strip() == '':
                break

            assert len(row) == len(self.colnames), (len(row), row, len(self.colnames), self.colnames)

            day, month, year = [int(v) for v in row[:3]]

            if is_datetime:
                date = datetime.datetime(year, month, day)
            else:
                date = int(year), int(month), int(day)

            value = d.get(date, None)
            if value is None:
                continue

            row[col_index] = str(value)

            for j, (c, v) in enumerate(zip(self.colnames, row)):
                if c in ['da', 'mo', 'year']:
                    row[j] = '%i' % int(v)
                elif c in ['rad', 'w-dir']:
                    row[j] = '%.f' % float(v)
                else:
                    row[j] = '%.1f' % float(v)

            row = '{0:>3}{1:>3}{2:>5}{3:>6}{4:>6}{5:>5}{6:>7}'\
                  '{7:>6}{8:>6}{9:>5}{10:>5}{11:>6}{12:>6}\n'\
                  .format(*row)

            self.lines[self.data0line + i] = row

    @property
    def years(self):
        df = self.as_dataframe()
        years = [int(v) for v in sorted(set(df['year']))]
        return years

    def make_storm_file(self, dst_fn):
        header_template = """\
{num_rain_events} # The number of rain events
0 # Breakpoint data? (0 for no, 1 for yes)
#  id     day  month  year  Rain   Dur    Tp     Ip
#                           (mm)   (h)
"""
        storms = []
        df = self.as_dataframe()
        for i, row in df.iterrows():
            if row.prcp > 0:
                storms.append([int(row.da), int(row.mo), int(row.year), row.prcp, row.dur, row.tp, row.ip])

        with open(dst_fn, 'w') as fp:
            fp.write(header_template.format(num_rain_events=len(storms)))

            for i, (da, mo, year, prcp, dur, tp, ip) in enumerate(storms):
                fp.write('{0:<8}{1:<6}{2:<6}{3:<6}{4:<7}{5:<7}{6:<7}{7:<7}\n'
                         .format(i+1, da, mo, year, prcp, dur, tp, ip))

    def as_dataframe(self, calc_peak_intensities=False):
        colnames = self.colnames
        dtypes = self.dtypes
        d = {}
        for name in colnames:
            d[name] = []

        if calc_peak_intensities:
            d['10-min Peak Rainfall Intensity (mm/hour)'] = []
            d['30-min Peak Rainfall Intensity (mm/hour)'] = []
            d['60-min Peak Rainfall Intensity (mm/hour)'] = []

        for i, L in enumerate(self.lines[self.data0line:]):
            row = [v.strip() for v in L.split()]
            if L.strip() == '':
                break

            assert len(row) == len(self.colnames), (len(row), len(self.colnames))

            for dtype, name, v in zip(dtypes, colnames, row):
                d[name].append(dtype(v))

            if calc_peak_intensities:
                max_time = [10, 30, 60]
                intensities = cli2pat(prcp=d['prcp'][-1], dur=d['dur'][-1], tp=d['tp'][-1], ip=d['ip'][-1], max_time=max_time)
                d['10-min Peak Rainfall Intensity (mm/hour)'].append(intensities[0])
                d['30-min Peak Rainfall Intensity (mm/hour)'].append(intensities[1])
                d['60-min Peak Rainfall Intensity (mm/hour)'].append(intensities[2])

        return pd.DataFrame(data=d)

    def header_ppts(self):
        """

        :return: daily precipitation in daily inches
        """
        ppts = []
        for ppt in self.lines[12].split():
            try:
                ppts.append(float(ppt))
            except ValueError:
                ppts.append(float('nan'))

        assert len(ppts) == 12
        ppts = np.array(ppts)
        ppts *= 0.0393701
        ppts /= days_in_mo
        return ppts

    def count_wetdays(self):
        df = self.as_dataframe()
        nyears = len(set(df.year))

        df['wet'] = df.prcp > 0.0
        tbl = pd.pivot_table(df, values='wet', index=['mo'], aggfunc=np.sum)
        return tbl.wet/float(nyears)

    def calc_monthlies(self):
        df = self.as_dataframe()
        nyears = len(set(df.year))

        prcps = np.zeros((12,))
        tmaxs = np.zeros((12,))
        tmins = np.zeros((12,))
        nwds = np.zeros((12,))

        for i, row in df.iterrows():
            indx = int(row.mo) - 1
            prcps[indx] += row.prcp
            nwds[indx] += (0.0, 1.0)[row.prcp > 0.0]
            tmaxs[indx] += row.tmax
            tmins[indx] += row.tmin

        prcps /= nyears
        prcps *= 0.0393701  # convert to inches/month

        tmaxs /= nyears * days_in_mo
        tmaxs = c_to_f(tmaxs)

        tmins /= nyears * days_in_mo
        tmins = c_to_f(tmins)

        nwds /= nyears

        return {
            "ppts": [float(v) for v in prcps],
            "tmaxs": [float(v) for v in tmaxs],
            "tmins": [float(v) for v in tmins],
            "nwds": [float(v) for v in nwds]
        }

    def calc_intensity(self):
        ppts = sorted(self.as_dataframe().prcp)
        n = len(ppts)
        return {
            "99": float(ppts[int(round(0.99 * n))]),
            "95": float(ppts[int(round(0.95 * n))]),
            "90": float(ppts[int(round(0.9 * n))]),
            "pct_wet": len(np.where(np.array(ppts) > 0.0)[0]) / n
        }

    def write(self, fn):
        with open(fn, 'w') as fp:
            fp.write(''.join(self.lines))

    @property
    def contents(self):
        return ''.join(self.lines)


class Station:
    def __init__(self, par_fn):
        with open(par_fn) as fp:
            lines = fp.readlines()

        assert 'MEAN P' in lines[3]
        assert 'S DEV P' in lines[4]
        assert 'TMAX' in lines[8]
        assert 'TMIN' in lines[9]
        assert 'P(W/W)' in lines[6]
        assert 'P(W/D)' in lines[7]

        self.ppts = np.array([float(lines[3][-73:][i * 6:i * 6 + 6]) for i in range(12)])
        self.pstds = np.array([float(lines[4][-73:][i * 6:i * 6 + 6]) for i in range(12)])
        self.pwws = np.array([float(lines[6][-73:][i * 6:i * 6 + 6]) for i in range(12)])
        self.pwds = np.array([float(lines[7][-73:][i * 6:i * 6 + 6]) for i in range(12)])
        self.tmaxs = np.array([float(lines[8][-73:][i * 6:i * 6 + 6]) for i in range(12)])
        self.tmins = np.array([float(lines[9][-73:][i * 6:i * 6 + 6]) for i in range(12)])

        assert len(self.ppts) == 12
        assert len(self.pstds) == 12
        assert len(self.pwws) == 12
        assert len(self.pwds) == 12
        assert len(self.tmaxs) == 12
        assert len(self.tmins) == 12

        mdays = np.array([31, 28.25, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])
        self.nwds = mdays * (self.pwds / (1.0 - self.pwws + self.pwds))

        self.lines = lines

    @property
    def monthly_ppts(self):
        return self.ppts * self.nwds

    def localize(self, lng, lat,
                 p_mean='prism',
                 p_std='daymet',
                 p_skew='daymet',
                 p_ww='daymet',
                 p_wd='daymet',
                 tmax='prism',
                 tmin='prism',
                 dewpoint='prism',
                 solrad='daymet'):

        """
        This could is deprecated and the localization provided by
        wepppy.climates.prism.prism_mod
        """
        new = deepcopy(self)

        if p_mean == 'prism':
            ppts = get_prism_monthly_ppt(lng, lat, units='daily inch')
            ppts /= self.nwds
            new.lines[3] = ' MEAN P  ' + _row_formatter(ppts) + '\r\n'

        elif p_mean == 'daymet':
            ppts = get_daymet_prcp_mean(lng, lat, units='daily inch')
            ppts /= self.nwds
            new.lines[3] = ' MEAN P  ' + _row_formatter(ppts) + '\r\n'

        if p_std == 'daymet':
            p_stds = get_daymet_prcp_std(lng, lat, units='inch')
            new.lines[4] = ' S DEV P ' + _row_formatter(p_stds) + '\r\n'

        if p_skew == 'daymet':
            p_skew = get_daymet_prcp_skew(lng, lat, units='inch')
            new.lines[5] = ' SKEW P  ' + _row_formatter(p_skew) + '\r\n'

        if p_ww == 'daymet':
            p_wws = get_daymet_prcp_pww(lng, lat)
            p_wws = [clamp(v, 0.01, 0.99) for v in p_wws]
            new.lines[6] = ' P(W/W)  ' + _row_formatter(p_wws) + '\r\n'
        elif isfloat(p_ww):
            p_wws = self.pwws * float(p_ww)
            p_wws = [clamp(v, 0.01, 0.99) for v in p_wws]
            new.lines[6] = ' P(W/W)  ' + _row_formatter(p_wws) + '\r\n'

        if p_wd == 'daymet':
            p_wds = get_daymet_prcp_pwd(lng, lat)
            p_wds = [clamp(v, 0.01, 0.99) for v in p_wds]
            new.lines[7] = ' P(W/D)  ' + _row_formatter(p_wds) + '\r\n'
        elif isfloat(p_wd):
            p_wds = self.pwds * float(p_wd)
            p_wds = [clamp(v, 0.01, 0.99) for v in p_wds]
            new.lines[7] = ' P(W/D)  ' + _row_formatter(p_wds) + '\r\n'

        if tmax == 'prism':
            tmaxs = get_prism_monthly_tmax(lng, lat, units='f')
            new.lines[8] = ' TMAX AV ' + _row_formatter(tmaxs) + '\r\n'

        if tmin == 'prism':
            tmins = get_prism_monthly_tmin(lng, lat, units='f')
            new.lines[9] = ' TMIN AV ' + _row_formatter(tmins) + '\r\n'

        if solrad == 'daymet':
            slrds = get_daymet_srld_mean(lng, lat)
            new.lines[12] = ' SOL.RAD ' + _row_formatter(slrds) + '\r\n'

        if dewpoint == 'prism':
            tdmeans = get_prism_monthly_tdmean(lng, lat, units='f')
            new.lines[15] = ' DEW PT  ' + _row_formatter(tdmeans) + '\r\n'

        return new

    def write(self, fn):
        with open(fn, 'w') as fp:
            fp.write(''.join(self.lines))


class StationMeta:
    def __init__(self, state, desc, par, latitude, longitude, years, _type,
                 elevation, tp5, tp6, _distance=None):
        self.state = state
        self.par = par
        self.latitude = latitude
        self.longitude = longitude
        self.years = years
        self.type = _type
        self.elevation = elevation
        self.tp5 = tp5
        self.tp6 = tp6
        self.distance = None
        self.lat_distance = None
        self.rank = None

        self.id = par.replace('.par', '')
        #assert len(self.id) == 6

        self.desc = desc.split(str(self.id))[0].strip()

        self.parpath = _join(_stations_dir, par)
        assert _exists(self.parpath)

    def get_station(self):
        return Station(self.parpath)

    def calculate_lat_distance(self, loc_lat):
        self.lat_distance = abs(self.latitude - loc_lat)

    def calculate_distance(self, location):
        self.distance = haversine(location, (self.longitude, self.latitude))

    def as_dict(self, include_monthlies=False):

        d = {
            "state": self.state,
            "desc": self.desc,
            "par": self.par,
            "latitude": self.latitude,
            "longitude": self.longitude,
            "years": self.years,
            "type": self.type,
            "elevation": self.elevation,
            "tp5": self.tp5,
            "tp6": self.tp6,
            "distance_to_query_location": self.distance,
            "rank_based_on_query_location": self.rank,
            "id": self.id
        }

        if include_monthlies:
            station = self.get_station()
            d["monthlies"] = {
                "ppts": list(station.ppts),
                "nwds": list(station.nwds),
                "tmaxs": list(station.tmaxs),
                "tmins": list(station.tmins)
            }
            d['sum_ppt'] = np.sum(v * d for v, d in zip(station.ppts, station.nwds))
            d['ave_monthly_tmax'] = np.mean(station.tmaxs)
            d['ave_monthly_tmin'] = np.mean(station.tmins)

        return d

    def __repr__(self):
        return "%s(%r)" % (self.__class__, self.__dict__)


class CligenStationsManager:
    def __init__(self, version=None):

        # connect to sqlite3 db
        global _db, _stations_dir

        if '2015' in str(version):
            _db = _join(_thisdir, '2015_stations.db')
            _stations_dir = _join(_thisdir, '2015_par_files')

        if 'au' in str(version):
            _db = _join(_thisdir, 'au_stations.db')
            _stations_dir = _join(_thisdir, 'au_par_files')

        conn = sqlite3.connect(_db)
        c = conn.cursor()

        # load station meta data
        self.stations = []
        c.execute("SELECT * FROM stations")
        for row in c:
            self.stations.append(StationMeta(*row))

    def order_by_distance_to_location(self, location):
        """
        location in longitude, latitude
        """
        for station in self.stations:
            station.calculate_distance(location)

        self.stations = \
            sorted(self.stations, key=lambda s: s.distance)

    def get_closest_station(self, location):
        self.order_by_distance_to_location(location)
        return self.stations[0]

    def get_closest_stations(self, location, num_stations):
        self.order_by_distance_to_location(location)
        return self.stations[:num_stations]

    def order_by_lat_distance_to_location(self, location):
        """
        location in longitude, latitude
        """
        for station in self.stations:
            station.calculate_lat_distance(location[1])

        self.stations = \
            sorted(self.stations, key=lambda s: s.lat_distance)

    def get_closest_stations_by_lat(self, location, num_stations):
        self.order_by_lat_distance_to_location(location)
        return self.stations[:num_stations]

    def get_station_fromid(self, _id):
        for station in self.stations:
            if str(_id) in str(station.par):
                return station
        return None

    def get_station_heuristic_search(self, location, pool=10):
        return self.get_stations_heuristic_search(location, pool=pool)[0]

    def get_stations_heuristic_search(self, location, pool=10):

        stations = self.get_closest_stations(location, pool)

        lat_ranks = [(i, abs(s.latitude - location[1]))
                     for i, s in enumerate(stations)]
        lat_ranks = sorted(lat_ranks, key=lambda x: x[1])

        elev = elevationquery(*location)
        stations_elevs = np.array([elevationquery(s.longitude, s.latitude)
                                   for s in stations])
        stations_elevs -= elev
        stations_elevs = np.abs(stations_elevs)
        elev_ranks = [(i, err) for i, err in enumerate(stations_elevs)]
        elev_ranks = sorted(elev_ranks, key=lambda x: x[1])

        ppts = get_prism_monthly_ppt(*location, units='inch')

        ppt_ranks = np.array([math.sqrt(np.sum((s.get_station().monthly_ppts - ppts)**2.0))
                              for s in stations])
        ppt_ranks = [(i, err) for i, err in enumerate(ppt_ranks)]
        ppt_ranks = sorted(ppt_ranks, key=lambda x: x[1])

        s_ranks = list(range(pool))
        weights = [1, 1, 3]
        for ranks, w in zip([lat_ranks, elev_ranks, ppt_ranks],
                            weights):

            for score, (i, err) in enumerate(ranks):
                s_ranks[i] += score * w

        s_ranks = [(i, err) for i, err in enumerate(s_ranks)]
        s_ranks = sorted(s_ranks, key=lambda x: x[1])

        _stations = []
        for i, rank in s_ranks:
            _stations.append(stations[i])
            _stations[-1].rank = rank

        return _stations

    def get_stations_eu_heuristic_search(self, location, elev, pool=40):

        stations = self.get_closest_stations_by_lat(location, pool)

        lat_ranks = [(i, abs(s.latitude - location[1]))
                     for i, s in enumerate(stations)]
        lat_ranks = sorted(lat_ranks, key=lambda x: x[1])

        stations_elevs = np.array([elevationquery(s.longitude, s.latitude)
                                   for s in stations])
        stations_elevs -= elev
        stations_elevs = np.abs(stations_elevs)
        elev_ranks = [(i, err) for i, err in enumerate(stations_elevs)]
        elev_ranks = sorted(elev_ranks, key=lambda x: x[1])

        ppts = get_eobs_monthly_ppt(*location, units='inch')
        ppt_ranks = np.array([math.sqrt(np.sum((s.get_station().monthly_ppts - ppts)**2.0))
                              for s in stations])
        ppt_ranks = [(i, err) for i, err in enumerate(ppt_ranks)]
        ppt_ranks = sorted(ppt_ranks, key=lambda x: x[1])

        txs = get_eobs_monthly_tmax(*location, units='f')
        tx_ranks = np.array([math.sqrt(np.sum((s.get_station().tmaxs - txs)**2.0))
                              for s in stations])
        tx_ranks = [(i, err) for i, err in enumerate(tx_ranks)]
        tx_ranks = sorted(tx_ranks, key=lambda x: x[1])

        tns = get_eobs_monthly_tmin(*location, units='f')
        tn_ranks = np.array([math.sqrt(np.sum((s.get_station().tmins - tns)**2.0))
                              for s in stations])
        tn_ranks = [(i, err) for i, err in enumerate(tn_ranks)]
        tn_ranks = sorted(tn_ranks, key=lambda x: x[1])

        s_ranks = list(range(pool))
        weights = [1, 1, 3, 1.5, 1.5]
        for ranks, w in zip([lat_ranks, elev_ranks, ppt_ranks, tx_ranks, tn_ranks],
                            weights):

            for score, (i, err) in enumerate(ranks):
                s_ranks[i] += score * w

        s_ranks = [(i, err) for i, err in enumerate(s_ranks)]
        s_ranks = sorted(s_ranks, key=lambda x: x[1])

        _stations = []
        for i, rank in s_ranks:
            _stations.append(stations[i])
            _stations[-1].rank = rank

        return _stations

    def get_stations_au_heuristic_search(self, location, elev, pool=None):
        stations = self.stations
        pool = len(stations)

        norm_lat = abs(location[1])

        lat_ranks = [(i, abs(s.latitude - norm_lat))
                     for i, s in enumerate(stations)]
        lat_ranks = sorted(lat_ranks, key=lambda x: x[1])

        stations_elevs = np.array([elevationquery(s.longitude, s.latitude)
                                   for s in stations])
        stations_elevs -= elev
        stations_elevs = np.abs(stations_elevs)
        elev_ranks = [(i, err) for i, err in enumerate(stations_elevs)]
        elev_ranks = sorted(elev_ranks, key=lambda x: x[1])

        ppts = get_agdc_monthly_ppt(*location, units='inch')
        ppt_ranks = np.array([math.sqrt(np.sum((s.get_station().monthly_ppts - ppts)**2.0))
                              for s in stations])
        ppt_ranks = [(i, err) for i, err in enumerate(ppt_ranks)]
        ppt_ranks = sorted(ppt_ranks, key=lambda x: x[1])

        txs = get_agdc_monthly_tmax(*location, units='f')
        tx_ranks = np.array([math.sqrt(np.sum((s.get_station().tmaxs - txs)**2.0))
                              for s in stations])
        tx_ranks = [(i, err) for i, err in enumerate(tx_ranks)]
        tx_ranks = sorted(tx_ranks, key=lambda x: x[1])

        tns = get_agdc_monthly_tmin(*location, units='f')
        tn_ranks = np.array([math.sqrt(np.sum((s.get_station().tmins - tns)**2.0))
                              for s in stations])
        tn_ranks = [(i, err) for i, err in enumerate(tn_ranks)]
        tn_ranks = sorted(tn_ranks, key=lambda x: x[1])

        s_ranks = list(range(pool))
        weights = [1, 1, 3, 1.5, 1.5]
        for ranks, w in zip([lat_ranks, elev_ranks, ppt_ranks, tx_ranks, tn_ranks],
                            weights):

            for score, (i, err) in enumerate(ranks):
                s_ranks[i] += score * w

        s_ranks = [(i, err) for i, err in enumerate(s_ranks)]
        s_ranks = sorted(s_ranks, key=lambda x: x[1])

        _stations = []
        for i, rank in s_ranks:
            _stations.append(stations[i])
            _stations[-1].rank = rank
            _stations[-1].calculate_distance(location)
            _stations[-1].calculate_lat_distance(location[1])
        return _stations


class Cligen:
    def __init__(self, station, wd='./', cliver="5.3"):
        assert _exists(wd), 'Working dir does not exist'
        self.wd = wd

        assert isinstance(station, StationMeta), "station is not a StationMeta object"
        self.station = station

        self.cliver = cliver

        self.cligen52 = _join(_thisdir, "bin", "cligen52")
        self.cligen43 = _join(_thisdir, "bin", "cligen43")

        assert _exists(self.cligen52), "Cannot find cligen52 executable"
        assert _exists(self.cligen52), "Cannot find cligen43 executable"

    def run_multiple_year(self, years, cli_fname='wepp.cli',
                          localization=None, verbose=False):

        if verbose:
            print("running multiple year")

        assert cli_fname.endswith('.cli')

        station_meta = self.station

        if localization is None:
            # no prism adjustment is specified
            # just copy the par into the working directory
            par_fn = _join(self.wd, station_meta.par)
            shutil.copyfile(station_meta.parpath, par_fn)
        else:
            # adjust based on lng, lat
            lng, lat = localization
            assert lng >= -125.0208333
            assert lng <= -66.4791667
            assert lat >= 24.0625000
            assert lat <= 49.9375000

            station = station_meta.get_station()
            new_station = station.localize(lng, lat)

            par_fn = '%s.%s.par' % (station_meta.par[:-4], cli_fname[:-4])
            par_fn = _join(self.wd, par_fn)
            new_station.write(par_fn)

        assert _exists(par_fn)
        _, par = os.path.split(par_fn)

        _make_clinp(self.wd, self.cliver, years, cli_fname, par)

        if self.cliver == "5.2":
            cmd = [self.cligen52, "-i%s" % par]
        else:
            cmd = [self.cligen43]

        # change to working directory
        cli_dir = self.wd

        # delete cli file if it exists
        if _exists(_join(cli_dir, cli_fname)):
            os.remove(_join(cli_dir, cli_fname))

        _clinp = open(_join(cli_dir, "clinp.txt"))
        _log = open(_join(cli_dir, "cligen_{}.log".format(cli_fname[:-4])), "w")
        p = subprocess.Popen(cmd, stdin=_clinp, stdout=_log, stderr=_log, cwd=cli_dir)
        p.wait()
        _clinp.close()
        _log.close()

        assert _exists(cli_fname)

    def run_observed(self, prn_fn, cli_fn='wepp.cli',
                     verbose=False):

        if verbose:
            print("running observed")

        if self.cliver not in ['5.2', '5.3']:
            raise NotImplementedError('Cligen version must be greater than 5')

        if self.cliver == '5.2':
            if IS_WINDOWS:
                raise NotImplementedError('Cligen52.exe is not available on Windows')
            else:
                cligen_bin = _join(_bin_dir, 'cligen52')
        else:
            if IS_WINDOWS:
                cligen_bin = _join(_bin_dir, 'cligen532.exe')
            else:
                cligen_bin = _join(_bin_dir, 'cligen532')

        assert _exists(cligen_bin)

        assert cli_fn.endswith('.cli')

        station_meta = self.station

        # no prism adjustment is specified
        # just copy the par into the working directory
        par_fn = _join(self.wd, station_meta.par)

        if not _exists(par_fn):
            shutil.copyfile(station_meta.parpath, par_fn)

        assert _exists(par_fn)
        _, par = os.path.split(par_fn)

        # change to working directory
        cli_dir = self.wd

        # delete cli file if it exists
        if _exists(_join(cli_dir, cli_fn)):
            os.remove(_join(cli_dir, cli_fn))

        cmd = [cligen_bin,
               "-i%s" % par,
               "-O%s" % prn_fn,
               "-o%s" % cli_fn,
               "-t6", "-I2"]

        if verbose:
            print(cmd)

        # run cligen
        _log = open(_join(cli_dir, "cligen_{}.log".format(_split(cli_fn)[-1][:-4])), "w")
        p = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=_log, stderr=_log, cwd=cli_dir)
        p.wait()
        _log.close()

        assert _exists(_join(cli_dir, cli_fn))


def par_mod(par: int, years: int, lng: float, lat: float, wd: str, monthly_dataset='prism',
            nwds_method='', randseed=None, cliver=None, suffix='', logger=None, version='2015'):
    """

    :param par:
    :param years:
    :param lng:
    :param lat:
    :param wd:
    :param nwds_method: '' or 'daymet' (daymet is experimental)
    :param randseed:
    :param cliver:
    :param suffix:
    :param logger:
    :return:
    """
    days_in_mo = np.array([31, 28.25, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31])

    # determine which version of cligen to use
    if cliver is None:
        cliver = '5.3'

    # change to the working directory
    assert _exists(wd)

    try:
        curdir = os.path.abspath(os.curdir)
    except FileNotFoundError:
        curdir = '../'

    os.chdir(wd)
    fp_log = open("cligen.log", "w")

    stationManager = CligenStationsManager(version=version)
    stationMeta = stationManager.get_station_fromid(par)

    if stationMeta is None:
        raise Exception('Cannot find station')

    station = stationMeta.get_station()
    par_monthlies = station.ppts * station.nwds

    if logger is not None:
        logger.log('  prism_mod:fetching climates...')

    if monthly_dataset.lower() == 'prism':
        prism_ppts = get_prism_monthly_ppt(lng, lat, units='inch')
        prism_tmaxs = get_prism_monthly_tmax(lng, lat, units='f')
        prism_tmins = get_prism_monthly_tmin(lng, lat, units='f')
        #        p_stds = get_daymet_prcp_std(lng, lat, units='inch')
        #        p_skew = get_daymet_prcp_skew(lng, lat, units='inch')
    elif monthly_dataset.lower() == 'eobs':
        prism_ppts = get_eobs_monthly_ppt(lng, lat, units='inch')
        prism_tmaxs = get_eobs_monthly_tmax(lng, lat, units='f')
        prism_tmins = get_eobs_monthly_tmin(lng, lat, units='f')
    elif monthly_dataset.lower() == 'agdc':
        prism_ppts = get_agdc_monthly_ppt(lng, lat, units='inch')
        prism_tmaxs = get_agdc_monthly_tmax(lng, lat, units='f')
        prism_tmins = get_agdc_monthly_tmin(lng, lat, units='f')
    else:
        raise Exception

    fp_log.write('monthly_dataset = {}\n'.format(monthly_dataset))
    fp_log.write('prism_ppts (in) = {}\n'.format(prism_ppts))
    fp_log.write('prism_tmaxs (F) = {}\n'.format(prism_tmaxs))
    fp_log.write('prism_tmins (F) = {}\n'.format(prism_tmins))

    # calculate number of wet days
    if nwds_method.lower() == 'daymet':
        assert monthly_dataset == 'prism'
        p_wws = get_daymet_prcp_pww(lng, lat)
        p_wds = get_daymet_prcp_pwd(lng, lat)
        nwds = days_in_mo * (p_wds / (1.0 - p_wws + p_wds))

    else:
        station_nwds = days_in_mo * (station.pwds / (1.0 - station.pwws + station.pwds))
        delta = prism_ppts / par_monthlies
        nwds = [float(v)for v in station_nwds]

        # clamp between 50% and 200% of original value
        # and between 0.1 days and the number of days in the month
        for i, (d, nwd, days) in enumerate(zip(delta, nwds, days_in_mo)):

            if d > 1.0:
                nwd *= 1.0 + (d - 1.0) / 2.0
            else:
                nwd *= 1.0 - (1.0 - d) / 2.0

            if nwd < station_nwds[i] / 2.0:
                nwd = station_nwds[i] / 2.0
            if nwd < 0.1:
                nwd = 0.1
            if nwd > station_nwds[i] * 2.0:
                nwd = station_nwds[i] * 2.0
            if nwd > days - 0.25:
                nwd = days - 0.25

            nwds[i] = nwd

        pw = nwds / days_in_mo

        assert np.all(pw >= 0.0)
        assert np.all(pw <= 1.0), pw

        ratio = station.pwds / station.pwws
        p_wws = 1.0 / (1.0 - ratio + ratio / pw)
        p_wds = ((p_wws - 1.0) * pw) / (pw - 1.0)

    if logger is not None:
        logger.log_done()

    if randseed is None:
        randseed = 12345
    randseed = str(randseed)

    daily_ppts = prism_ppts / nwds  # in inches / day

    fp_log.write('daily_ppts (in) = {}\n'.format(daily_ppts))
    fp_log.write('nwds = {}\n'.format(nwds))

    # build par file
    par_fn = '{}{}.par'.format(par, suffix)

    if _exists(par_fn):
        os.remove(par_fn)

    # p_stds = station.pstds * x[3]

    s2 = deepcopy(station)
    s2.lines[3] = ' MEAN P  ' + _row_formatter(daily_ppts) + '\r\n'
    #        s2.lines[4] = ' S DEV P ' + _row_formatter(pstds) + '\r\n'
    s2.lines[6] = ' P(W/W)  ' + _row_formatter(p_wws) + '\r\n'
    s2.lines[7] = ' P(W/D)  ' + _row_formatter(p_wds) + '\r\n'
    s2.lines[8] = ' TMAX AV ' + _row_formatter(prism_tmaxs) + '\r\n'
    s2.lines[9] = ' TMIN AV ' + _row_formatter(prism_tmins) + '\r\n'

    s2.write(par_fn)

    # run cligen
    cli_fn = '{}{}.cli'.format(par, suffix)

    if _exists(cli_fn):
        os.remove(cli_fn)

    # create cligen input file
    clinp_fn = _make_clinp(wd, cliver, years, cli_fn, par_fn)

    # build cmd
    if cliver == "4.3":
        if IS_WINDOWS:
            raise NotImplementedError('Cligen43.exe is not available on Windows')
        else:
            cmd = [_join(_bin_dir, 'cligen43')]
    elif cliver == "5.2":
        if IS_WINDOWS:
            raise NotImplementedError('Cligen52.exe is not available on Windows')
        else:
            cmd = [_join(_bin_dir, 'cligen52'), "-i%s" % par_fn]
    else:
        if IS_WINDOWS:
            cmd = [_join(_bin_dir, 'cligen532.exe'), "-i%s" % par_fn]
        else:
            cmd = [_join(_bin_dir, 'cligen532'), "-i%s" % par_fn]

    if randseed is not None:
        cmd.append('-r%s' % randseed)

    # run cligen
    _clinp = open(clinp_fn)

    if IS_WINDOWS:
        process = Popen(cmd, stdin=_clinp, stdout=PIPE, stderr=PIPE)
    else:
        process = Popen(cmd, stdin=_clinp, stdout=PIPE, stderr=PIPE, preexec_fn=os.setsid)

    output = process.stdout.read()
    output += process.stderr.read()

    fp_log.write(str(output))

    assert _exists(cli_fn), (cli_fn, cmd)

    cli = ClimateFile(cli_fn)

    sim_ppts = cli.header_ppts() * days_in_mo
    if np.any(np.isnan(sim_ppts)):
        raise Exception('Cligen failed to produce precipitation')

    sim_nwds = cli.count_wetdays()

    if logger is not None:
        logger.log('Note: CLIGEN uses English Units.\n\n')

        logger.log('Station : %s\n' % _rowfmt(par_monthlies))
        logger.log('%s   : %s\n' % (monthly_dataset, _rowfmt(prism_ppts)))
        logger.log('Cligen  : %s\n' % _rowfmt(sim_ppts))

        logger.log('Monthly number wet days\n')
        logger.log('Station : %s\n' % _rowfmt(station.nwds))
        logger.log('Target  : %s\n' % _rowfmt(nwds))
        logger.log('Cligen  : %s\n' % _rowfmt(sim_nwds))

        logger.log('p(w|w) and p(w|d)\n')
        logger.log('Station p(w|w) : %s\n' % _rowfmt(station.pwws))
        logger.log('Cligen p(w|w)  : %s\n' % _rowfmt(p_wws))
        logger.log('Station p(w|d) : %s\n' % _rowfmt(station.pwds))
        logger.log('Cligen p(w|d)  : %s\n' % _rowfmt(p_wds))

        logger.log('Daily P for day precipitation occurs\n')
        logger.log('Station : %s\n' % _rowfmt(station.ppts))
        logger.log('Target  : %s\n' % _rowfmt(daily_ppts))

        logger.log('%s TMAX (F): %s\n' % (monthly_dataset, _rowfmt(prism_tmaxs)))
        logger.log('%s TMIN (F) : %s\n' % (monthly_dataset, _rowfmt(prism_tmins)))

    os.chdir(curdir)

    return cli.calc_monthlies()


if __name__ == "__main__":

    import sys
    from pprint import pprint

    print(cli2pat(prcp=43.2, dur=23.58, tp=0.001, ip=4.12))
    print(cli2pat(prcp=43.2, dur=23.58, tp=0.01, ip=4.12))
    print(cli2pat(prcp=43.2, dur=23.58, tp=0.1, ip=4.12))

    cli = ClimateFile('test.cli')
    pprint(cli.as_dataframe(calc_peak_intensities=True))


    sys.exit()
    stationManager = CligenStationsManager(version=2015)

    stationMeta = stationManager.get_closest_station((-117, 46))

    print(stationMeta)

    def print_tbl(max_times, prcps):
        print('dur  intensity')
        for m, p in zip(max_times, prcps):
            print(m, p)
