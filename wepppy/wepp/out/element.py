import numpy as np
from pandas import Series

''' OFE DD MM YYYY  Precip   Runoff   EffInt PeakRO  EffDur Enrich    Keff   Sm  LeafArea  CanHgt  Cancov IntCov  RilCov  LivBio DeadBio  Ki    Kr     Tcrit RilWid   SedLeave
 na  na na  na     mm       mm     mm/h    mm/h      h    Ratio    mm/h   mm    Index    m       %       %       %     Kg/m^2  Kg/m^2  na    na      na     m       kg/m'''


def _float(x):
    try:
        return float(x)
    except ValueError:
        return None


class Element(object):
    def __init__(self, fn):

        with open(fn) as fp:
            lines = fp.readlines()

        # strip trailing and leading white space
        lines = [L.strip() for L in lines]
        lines = [L for L in lines if L != '']
        lines = lines[2:]

        header = ['ofe', 'da', 'mo', 'year',
                  'Precip', 'Runoff', 'EffInt', 'PeakRO', 'EffDur', 'Enrich',
                  'Keff', 'Sm', 'LeafArea', 'CanHgt', 'Cancov', 'IntCov', 'RilCov',
                  'LivBio', 'DeadBio', 'Ki', 'Kr', 'Tcrit', 'RilWid', 'SedLeave']

        units = [int, int, int, int, _float, _float, _float, _float, _float, _float, _float, _float,
                 _float, _float, _float, _float, _float, _float, _float, _float, _float, _float, _float, _float]

        data = []
        for i, L in enumerate(lines):
            data.append([u(v) for v, u in zip(L.split(), units)])

            # replace ****** values with previous day
            for j, v in enumerate(data[-1]):
                if v is None:
                    data[-1][j] = data[-2][j]

        d = {}

        for row in data:
            da, mo, year = row[1], row[2], row[3]
            d[(year, mo, da)] = dict(zip(header, row))

        self.d = d

