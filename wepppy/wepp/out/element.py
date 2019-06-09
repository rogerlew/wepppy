import numpy as np
from pandas import Series

''' OFE DD MM YYYY  Precip   Runoff   EffInt PeakRO  EffDur Enrich    Keff   Sm  LeafArea  CanHgt  Cancov IntCov  RilCov  LivBio DeadBio  Ki    Kr     Tcrit RilWid   SedLeave
 na  na na  na     mm       mm     mm/h    mm/h      h    Ratio    mm/h   mm    Index    m       %       %       %     Kg/m^2  Kg/m^2  na    na      na     m       kg/m'''


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

        units = [int, int, int, int, float, float, float, float, float, float, float, float,
                 float, float, float, float, float, float, float, float, float, float, float, float]

        data = [[u(v) for v, u in zip(L.split(), units)] for L in lines]

        d = {}

        for row in data:
            da, mo, year = row[1], row[2], row[3]
            d[(year, mo, da)] = dict(zip(header, row))

        self.d = d

