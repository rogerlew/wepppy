# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

from collections import OrderedDict
import  numpy as np
from pandas import DataFrame, Series
from wepppy.all_your_base import parse_units, RowData, parse_name

from wepppy.wepp.out import Loss, Ebe


class ReturnPeriods:
    def __init__(self, ebe: Ebe, loss: Loss, cli_df: DataFrame, recurence=[2, 5, 10, 20, 25]):
        self.has_phosphorus = loss.has_phosphorus

        df = ebe.df

        pk_intensity_dict = {}
        for i, d in cli_df.iterrows():
            pk_intensity_dict[d['da'], d['mo'], d['year']] = d

        _pk10 =[]
        _pk30 = []
        for i, d in df.iterrows():
            _pk10.append(pk_intensity_dict[d['da'], d['mo'], d['year']]['10-min Peak Intensity (mm/hour)'])
            _pk30.append(pk_intensity_dict[d['da'], d['mo'], d['year']]['30-min Peak Intensity (mm/hour)'])

        df['10-min Peak Intensity'] = Series(_pk10, index=df.index)
        df['30-min Peak Intensity'] = Series(_pk30, index=df.index)

        header = list(df.keys())
        header.remove('da')
        header.remove('mo')
        header.remove('year')

        self.header = header
        self.years = years = ebe.years
        self.wsarea = wsarea = loss.wsarea
        self.recurence = recurence = sorted(recurence)

        recurence = sorted(recurence)

        # Note that return period of the events are estimated by applying
        # Weibull formula on annual maxima series.
        #    T = (N + 1)/m
        #
        # where T is the return period, N is the number of simulation years,
        # and m is the rank of the annual maxima event.

        rec = {}
        i = 0
        rankind = ebe.years
        orgind = years + 1
        reccount = 0

        while i < len(recurence) and rankind >= 2.5:
            retperiod = recurence[i]
            rankind = float(years + 1) / retperiod
            intind = int(rankind) - 1

            if intind < orgind:
                rec[retperiod] = intind
                orgind = intind
                reccount += 1

            i += 1

        results = {}

        for colname in header:

            df2 = df.sort_values(by=colname, ascending=False)

            colname = parse_name(colname)
            results[colname] = {}
            if colname == 'Runoff Volume':
                results['Runoff'] = {}

            for retperiod, indx in rec.items():
                row = dict(df2.iloc[indx])
                row = dict((k.split('(')[0].strip(), float(v)) for k, v in row.items())

                row['Runoff'] = round(row['Runoff Volume'] / (wsarea * 10000.0) * 1000.0, 2)

                results[colname][retperiod] = row

                if colname == 'Runoff Volume':
                    results['Runoff'][retperiod] = row

        self.return_periods = results
        self.num_events = df.shape[0]
        self.intervals = sorted(rec.keys())
        self.units_d = ebe.units_d
        self.units_d['10-min Peak Intensity'] = 'mm/hour'
        self.units_d['30-min Peak Intensity'] = 'mm/hour'


if __name__ == "__main__":
    from pprint import  pprint

    loss_rpt = Loss('/home/weppdev/PycharmProjects/wepppy/wepppy/wepp/out/test/data/ww2output.txt')
    ebe_rpt = Ebe('/home/weppdev/PycharmProjects/wepppy/wepppy/wepp/out/test/data/ww2events.txt')

    ret_rpt = ReturnPeriods(ebe_rpt, loss_rpt)

    print(ret_rpt.return_periods)
    print(ret_rpt.intervals)
