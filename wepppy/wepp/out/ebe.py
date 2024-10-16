# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

from datetime import datetime

import pandas as pd

from wepppy.wepp.out import Loss


def _get_lines(fn):
    # read the loss report
    with open(fn) as fp:
        lines = fp.readlines()

    # strip trailing and leading white space
    lines = [L.strip() for L in lines]

    lines = [L for L in lines if L != '']

    i0 = 0
    for i0, L in enumerate(lines):
        if L.startswith('---'):
            break

    return lines[i0 + 1:]


class HillslopeEbe(object):
    def __init__(self, fn):
        lines = _get_lines(fn)

        header = ['da', 'mo', 'year',
                  'Precp', 'Runoff',
                  'IR-det', 'Av-det', 'Mx-det',
                  'Point0', 'Av-dep', 'Max-dep',
                  'Point1', 'Sed.Del', 'ER']

        units = [int, int, int, float, float, float, float, float, float, float, float, float, float, float]

        data = [[u(v) for v, u in zip(L.split(), units)] for L in lines]

        d = {}

        for row in data:
            da, mo, year = row[0], row[1], row[2]
            d[(year, mo, da)] = dict(zip(header, row))

        self.d = d


class Ebe(object):
    def __init__(self, fn):
        lines = _get_lines(fn)

        header = ['da', 'mo', 'year',
                  'Precipitation Depth (mm)',
                  'Runoff Volume (m^3)',
                  'Peak Runoff (m^3/s)',
                  'Sediment Yield (kg)',
                  'Soluble Reactive P (kg)',
                  'Particulate P (kg)',
                  'Total P (kg)']

        units = [int, int, int, float, float, float, float, float, float, float]

        data = [[u(v) for v, u in zip(L.split(), units)] for L in lines]
        data = list(map(list, zip(*data)))

        if data == []:
            raise Exception('{} contains no data'.format(fn))

        df = pd.DataFrame()
        for L, colname in zip(data, header):
            df[colname] = L

        df['Sed. Del (kg)'] = df['Sediment Yield (kg)']

        self.df = df
        self.years = int(max(df['year']))
        self.header = header
        self.units_d = {
          'Precipitation Depth': 'mm',
          'Runoff Volume': 'm^3',
          'Peak Runoff': 'm^3/s',
          'Runoff': 'mm',
          'Sediment Yield': 'kg',
          'Soluble Reactive P': 'kg',
          'Particulate P': 'kg',
          'Total P': 'kg'
        }


if __name__ == "__main__":
    from pprint import  pprint

    loss_rtp = Loss('/home/weppdev/PycharmProjects/wepppy/wepppy/wepp/out/test/data/ww2output.txt')
    ebe_rpt = Ebe('/home/weppdev/PycharmProjects/wepppy/wepppy/wepp/out/test/data/ww2events.txt')
    pprint(ebe_rpt.years)
    pprint(ebe_rpt.df.keys())

#    report = EbeReport('/home/weppdev/PycharmProjects/wepppy/wepppy/validation/blackwood_MultPRISM/wepp/output/ebe_pw0.txt')