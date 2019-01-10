# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

from math import log
from collections import OrderedDict
import numpy as np

from wepppy.all_your_base import RowData
from wepppy.wepp.out import Loss, Ebe
from .report_base import ReportBase


class FrqFlood(ReportBase):
    def __init__(self, ebe: Ebe, loss: Loss, recurence=[2, 5, 10, 20, 25]):

        df = ebe.df
        header = list(df.keys())
        header.remove('da')
        header.remove('mo')
        header.remove('year')

        self.years = years = ebe.years
        self.wsarea = wsarea = loss.wsarea
        self.recurence = recurence = sorted(recurence)

        # Event of return period T is estimated by applying Chow's frequency factor method and Gumbel's distribution
        # with on the annual maxima series following Patra (2000). X_T is the estimated value of the event of return
        # period T
        #
        # K_factor = -(0.45005 + 0.7797 ln(ln(T/(T - 1)))
        # X_T = mean + standard_deviation * K_factor
        #    where,
        #    T is the return period
        #
        # Watershed event by event output are used and frequency analysis on precipitation, runoff, peak runoff, and
        # sediment yield are conducted separately.

        d = {}
        for colname in header + ['year']:
            d[colname] = []

        for y in sorted(set(df['year'])):
            indx = np.where(np.array(df['year']) == y)
            i0, iend = indx[0][0], indx[0][-1]

            for colname in header:
                d[colname].append(np.max(df[colname][i0:iend]))

        recs = {}
        for colname in header + ['Runoff (mm)', 'Recurence']:
            recs[colname] = []

        means = {}
        for colname in header:
            means[colname] = float(np.mean(d[colname]))

        stds = {}
        for colname in header:
            stds[colname] = float(np.std(d[colname]))

        for T in [y for y in recurence if y < years]:

            # Frequency factor based on Gumble Distribution
            kfactor = -1.0 * (0.45005 + 0.7797 * log(log(T / (T - 1.0))))

            # Chow's frequency factor method (1951)
            for colname in header:
                recs[colname].append(means[colname] + stds[colname] * kfactor)

            recs['Runoff (mm)'].append(round(recs['Runoff Volume (m^3)'][-1] / (wsarea * 10000.0) * 1000.0, 2))
            recs['Recurence'].append(T)

        self.header = ['Recurence'] + header
        self.recs = recs
        self.means = means
        self.stds = stds
        self.num_events = df.shape[0]
        self.units_d = ebe.units_d

    def __iter__(self):
        recs = self.recs
        means = self.means
        stds = self.stds
        recurence, years, header = self.recurence, self.years, self.header
        header.remove('Recurence')
        for i, T in enumerate([y for y in recurence if y < years]):
            yield RowData(OrderedDict([('Recurence', T)] +
                                      [(colname, recs[colname][i]) for colname in header]))

        yield RowData(OrderedDict([('Recurence', 'Mean')] +
                                  [(colname, means[colname]) for colname in header]))

        yield RowData(OrderedDict([('Recurence', 'StdDev')] +
                                  [(colname, stds[colname]) for colname in header]))


if __name__ == "__main__":
    from pprint import pprint

    loss = Loss('/home/weppdev/PycharmProjects/wepppy/wepppy/wepp/out/test/data2/ww2output.txt')
    ebe = Ebe('/home/weppdev/PycharmProjects/wepppy/wepppy/wepp/out/test/data2/ww2events.txt')

    frq_rpt = FrqFlood(ebe, loss)

    for row in frq_rpt:
        for (k, v) in row:
            print(k, v)



