from os.path import exists as _exists

import numpy as np

from wepppy.all_your_base import try_parse, parse_units


class ObservedTimeseries:
    def __init__(self, fname):

        assert _exists(fname)

        with open(fname) as fp:
            lines = fp.readlines()

        hdr = lines[0].split(',')

        lines = np.array([[try_parse(v) for v in L.split(',')] for L in lines[1:]])

        d = {}
        for i, colname in enumerate(hdr):
            d[colname] = lines[:, i]

        units = [parse_units(colname) for colname in hdr]

        self.hdr = hdr
        self.data = d
        self.units = units


def validate(Qm, Qo):
    assert Qm.shape == Qo.shape
    assert len(Qo.shape) == 1


def nse(Qm, Qo):
    validate(Qm, Qo)

    return 1.0 - np.sum((Qm - Qo) ** 2.0) / \
                 np.sum((Qo - np.mean(Qo)) ** 2.0)


def r_square(Qm, Qo):
    validate(Qm, Qo)

    slope, intercept, r_value, p_value, std_err = stats.linregress(Qm, Qo)
    return r_value ** 2.0


def dv(Qm, Qo):
    validate(Qm, Qo)

    return np.mean((Qo - Qm) / Qo * 100.0)


def mse(Qm, Qo):
    validate(Qm, Qo)

    n = Qo.shape[1]
    return np.mean((Qo - Qm) ** 2.0)



if __name__ == "__main__":
    obs = ObservedTimeseries('tests/blackwood_observed.csv')
