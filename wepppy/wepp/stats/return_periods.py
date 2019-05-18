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
    def __init__(self, ebe: Ebe, loss: Loss, cli_df: DataFrame, recurrence=[2, 5, 10, 20, 25]):
        self.has_phosphorus = loss.has_phosphorus

        df = ebe.df

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

        df['10-min Peak Rainfall Intensity'] = Series(_pk10, index=df.index)
        df['30-min Peak Rainfall Intensity'] = Series(_pk30, index=df.index)

        header = list(df.keys())
        header.remove('da')
        header.remove('mo')
        header.remove('year')

        self.header = header
        self.years = years = ebe.years
        self.wsarea = wsarea = loss.wsarea
        self.recurrence = recurrence = sorted(recurrence)

        recurrence = sorted(recurrence)

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

        while i < len(recurrence) and rankind >= 2.5:
            retperiod = recurrence[i]
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
            print('"%s"' % colname)
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

                    if cname == 'Peak Runoff':
                        cname = 'Peak Discharge'

                    row[cname] = v

                print(row.keys())
                row['Runoff'] = round(row['Runoff Volume'] / (wsarea * 10000.0) * 1000.0, 2)
                results[colname][retperiod] = row

        print(results)
        self.return_periods = results
        self.num_events = df.shape[0]
        self.intervals = sorted(rec.keys())
        self.units_d = ebe.units_d
        self.units_d['Peak Discharge'] = 'm^3/s'
        self.units_d['10-min Peak Rainfall Intensity'] = 'mm/hour'
        self.units_d['30-min Peak Rainfall Intensity'] = 'mm/hour'


if __name__ == "__main__":
    from pprint import  pprint

    loss_rpt = Loss('/home/weppdev/PycharmProjects/wepppy/wepppy/wepp/out/test/data/ww2output.txt')
    ebe_rpt = Ebe('/home/weppdev/PycharmProjects/wepppy/wepppy/wepp/out/test/data/ww2events.txt')

    ret_rpt = ReturnPeriods(ebe_rpt, loss_rpt)

    print(ret_rpt.return_periods)
    print(ret_rpt.intervals)
