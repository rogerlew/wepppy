# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

import numpy as np
from pandas import DataFrame, Series
from wepppy.all_your_base.stats import weibull_series
from .row_data import parse_name, parse_units, RowData

from wepppy.wepp.out import Loss, Ebe

from copy import deepcopy

class ReturnPeriods:
    def __init__(self, ebe: Ebe = None, loss: Loss = None, 
                 cli_df: DataFrame = None, 
                 recurrence=(2, 5, 10, 20, 25),
                 exclude_yr_indxs=None,
                 method='cta', gringorten_correction=False):
        """
        Args:
            ebe (Ebe): The event by event  report.
            loss (Loss): The WEPP loss report.
            cli_df (DataFrame): The climate data.
            recurrence (tuple): The recurrence intervals in years.
            exclude_yr_indxs (list): A list of year indexes to exclude from the analysis.
            method (str): The method used to calculate the return periods. Options are 'cta' (default) complete time series analysis or 'am' or annual maxima.
            gringorten_correction (bool): If True, applies the Gringorten correction to the Weibull formula.
        """

        if ebe is None or loss is None or cli_df is None:
            return

        self.has_phosphorus = loss.has_phosphorus

        df = deepcopy(ebe.df)

        df['10-min Peak Rainfall Intensity'] = cli_df['10-min Peak Rainfall Intensity (mm/hour)']
        df['30-min Peak Rainfall Intensity'] = cli_df['30-min Peak Rainfall Intensity (mm/hour)']

        _years = sorted(set(df['year']))
        _y0 = _years[0]
        if exclude_yr_indxs is not None:
            __years = []

            for indx, _yr in enumerate(sorted(set(df['year']))):
                if indx not in exclude_yr_indxs:
                    __years.append(_yr)
            _years = __years

            df = df[df['year'].isin(_years)]

        header = list(df.keys())
        header.remove('da')
        header.remove('mo')
        header.remove('year')

        self.header = header
        self.method = method
        self.gringorten_correction = gringorten_correction
        self.y0 = _y0
        self.years = years = len(_years)
        self.wsarea = wsarea = loss.wsarea
        self.recurrence = recurrence = sorted(recurrence)
        self.exclude_yr_indxs = exclude_yr_indxs

        rec = weibull_series(recurrence, years, 
                             method=method, gringorten_correction=gringorten_correction)

        days_in_year = len(df) / years

        results = {}
        for colname in header:

            if method == 'cta':
                df2 = df.sort_values(by=colname, ascending=False)
            else:
                df2 = df.groupby('year').max().sort_values(by=colname, ascending=False)

            colname = parse_name(colname)
            if colname == 'Runoff Volume':
                colname = 'Runoff'
            elif colname == 'Peak Runoff':
                colname = 'Peak Discharge'

            results[colname] = {}

            for retperiod, indx in rec.items():
                _row = dict(df2.iloc[indx])

                row = {}
                for k, v in _row.items():
                    cname = k.split('(')[0].strip()

                    if cname == 'Runoff Volume':
                        cname = 'Runoff'

                    if cname == 'Peak Runoff':
                        cname = 'Peak Discharge'

                    row[cname] = v

                row['Runoff'] = round(row['Runoff'] / (wsarea * 10000.0) * 1000.0, 2)
                row['weibull_rank'] = indx + 1
                row['weibull_T'] = ((len(df) + 1) / (indx + 1)) / days_in_year # T = (n + 1)  / m, where m is the rank and n is the number of observations
                row['Sediment Yield'] /= 1000.0

                results[colname][retperiod] = row

        self.return_periods = results
        self.num_events = df.shape[0]
        self.intervals = sorted(rec.keys())
        self.units_d = ebe.units_d
        self.units_d['10-min Peak Rainfall Intensity'] = 'mm/hour'
        self.units_d['30-min Peak Rainfall Intensity'] = 'mm/hour'
        self.units_d['Peak Discharge'] = 'm^3/s'
        self.units_d['Sediment Yield'] = 'tonne'

    def to_dict(self):
        return {
            'has_phosphorus': self.has_phosphorus,
            'header': self.header,
            'method': self.method,
            'gringorten_correction': self.gringorten_correction,
            'y0': self.y0,
            'years': self.years,
            'wsarea': self.wsarea,
            'recurrence': self.recurrence,
            'return_periods': self.return_periods,
            'num_events': self.num_events,
            'intervals': self.intervals,
            'units_d': self.units_d,
            'exclude_yr_indxs': self.exclude_yr_indxs
        }

    @classmethod
    def from_dict(cls, data):
        rp = cls()

        rp.has_phosphorus = data['has_phosphorus']
        rp.header = data['header']
        rp.method = data['method']
        rp.gringorten_correction = data['gringorten_correction']
        rp.y0 = data['y0']
        rp.years = data['years']
        rp.wsarea = data['wsarea']
        rp.recurrence = data['recurrence']
        rp.num_events = data['num_events']
        rp.intervals = data['intervals']
        rp.units_d = data['units_d']
        rp.exclude_yr_indxs = data.get('exclude_yr_indxs', None)

        ret_periods = data['return_periods']
        rp.return_periods = {}
        for measure in ret_periods:
            rp.return_periods[measure] = {}
            for rec, row in ret_periods[measure].items():
                rp.return_periods[measure][int(rec)] = row

        return rp

if __name__ == "__main__":
    from pprint import  pprint

    loss_rpt = Loss('/home/weppdev/PycharmProjects/wepppy/wepppy/wepp/out/test/data/ww2output.txt')
    ebe_rpt = Ebe('/home/weppdev/PycharmProjects/wepppy/wepppy/wepp/out/test/data/ww2events.txt')

    ret_rpt = ReturnPeriods(ebe_rpt, loss_rpt)

    print(ret_rpt.return_periods)
    print(ret_rpt.intervals)
