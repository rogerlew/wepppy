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


if __name__ == "__main__":
    obs = ObservedTimeseries('tests/blackwood_observed.csv')
