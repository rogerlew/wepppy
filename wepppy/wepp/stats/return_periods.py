from collections import OrderedDict
import  numpy as np
from wepppy.all_your_base import parse_units, RowData

from wepppy.wepp.out import LossReport, Ebe


class ReturnPeriods:
    def __init__(self, ebe: Ebe, loss_rtp: LossReport, recurence=[2, 5, 10, 25]):

        df = ebe.df
        header = ebe.header
        years = ebe.years
        wsarea = loss_rtp.wsarea

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
                reccount = reccount + 1

            i += 1

        results = {}

        for col_name in [v for v in header if v not in ['da', 'mo', 'year']]:
            df2 = df.sort_values(by=col_name, ascending=False)

            col_name = col_name.split('(')[0].strip()
            results[col_name] = {}
            if col_name == 'Runoff Volume':
                results['Runoff'] = {}

            for retperiod, indx in rec.items():
                row = dict(df2.iloc[indx])
                row = dict((k.split('(')[0].strip(), float(v)) for k, v in row.items())

                row['Runoff'] = round(row['Runoff Volume'] / (wsarea * 10000.0) * 1000.0, 2)

                results[col_name][retperiod] = row

                if col_name == 'Runoff Volume':
                    results['Runoff'][retperiod] = row

        self.return_periods = results
        self.num_events = df.shape[0]
        self.wsarea = wsarea
        self.intervals = sorted(rec.keys())
        self.units_d = ebe.units_d


if __name__ == "__main__":
    from pprint import  pprint

    loss_rpt = LossReport('/home/weppdev/PycharmProjects/wepppy/wepppy/wepp/out/test/data/ww2output.txt')
    ebe_rpt = Ebe('/home/weppdev/PycharmProjects/wepppy/wepppy/wepp/out/test/data/ww2events.txt')

    ret_rpt = ReturnPeriods(ebe_rpt, loss_rpt)

    print(ret_rpt.return_periods)
    print(ret_rpt.intervals)
