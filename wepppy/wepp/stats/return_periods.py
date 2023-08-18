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
    def __init__(self, ebe: Ebe = None, loss: Loss = None, cli_df: DataFrame = None, recurrence=(2, 5, 10, 20, 25)):
        if ebe is None or loss is None or cli_df is None:
            return

        self.has_phosphorus = loss.has_phosphorus

        df = deepcopy(ebe.df)
        print(df.info())

        pk_intensity_dict = {}

        # annoyingly the ebe has enumerated years and not gregorian years
        # so we have to add the keys with enumerated years FML
        y0 = np.min(cli_df['year'])
        yend = np.max(cli_df['year']) + 0.5
        _years = np.arange(y0, yend, dtype=np.int32)

        years_map = dict(zip(_years, range(1, len(_years) + 1)))

        for i, d in cli_df.iterrows():
            key = int(d['da']), int(d['mo']), years_map[int(d['year'])]
            pk_intensity_dict[key] = d

        _pk10 =[]
        _pk30 = []
        for i, d in df.iterrows():
            key = int(d['da']), int(d['mo']), int(d['year'])
            _pk10.append(pk_intensity_dict[key]['10-min Peak Rainfall Intensity (mm/hour)'])
            _pk30.append(pk_intensity_dict[key]['30-min Peak Rainfall Intensity (mm/hour)'])

        # Breakpoint climates don't have peak intensities

        if _pk10[0] >= 0:
            df['10-min Peak Rainfall Intensity'] = Series(_pk10, index=df.index)

        if _pk30[0] >= 0:
            df['30-min Peak Rainfall Intensity'] = Series(_pk30, index=df.index)

        df['Sediment Yield (tonne)'] = df['Sediment Yield (kg)'] / 1000.0
        del df['Sediment Yield (kg)']

        header = list(df.keys())
        header.remove('da')
        header.remove('mo')
        header.remove('year')

        self.header = header
        self.y0 = y0
        self.years = years = ebe.years
        self.wsarea = wsarea = loss.wsarea
        self.recurrence = recurrence = sorted(recurrence)

        rec = weibull_series(recurrence, years)

        results = {}
        for colname in header:

            df2 = df.sort_values(by=colname, ascending=False)

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
            'y0': self.y0,
            'years': self.years,
            'wsarea': self.wsarea,
            'recurrence': self.recurrence,
            'return_periods': self.return_periods,
            'num_events': self.num_events,
            'intervals': self.intervals,
            'units_d': self.units_d
        }

    @classmethod
    def from_dict(cls, data):
        rp = cls()

        rp.has_phosphorus = data['has_phosphorus']
        rp.header = data['header']
        rp.y0 = data['y0']
        rp.years = data['years']
        rp.wsarea = data['wsarea']
        rp.recurrence = data['recurrence']
        rp.num_events = data['num_events']
        rp.intervals = data['intervals']
        rp.units_d = data['units_d']

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
