import os
from os.path import join as _join
from os.path import split as _split
from os.path import exists as _exists

from glob import glob
from pprint import pprint

from wepppy.all_your_base import haversine

_thisdir = os.path.dirname(__file__)
_data_dir = os.path.abspath(_join(_thisdir, 'build'))


class LivnehDataManager(object):
    def __init__(self):
        cli_fns = glob(_join(_data_dir, '*.cli'))

        d = {}
        for fn in cli_fns:
            head, tail = _split(fn)
            lat, lng = tail.replace('data_', '').replace('.cli', '').split('_')
            lat = float(lat)
            lng = float(lng)

            d[(lng, lat)] = tail

        self.d = d

    def closest_cli(self, lng, lat):
        d = self.d

        cli_fn = None
        distance = 1e38

        for loc in d:
            dist = haversine(loc, (lng, lat))
            if dist < distance:
                cli_fn = d[loc]
                distance = dist

        assert cli_fn is not None

        return _join(_data_dir, cli_fn)

    @property
    def par_path(self):
        par_path = glob(_join(_data_dir, '*.par'))
        assert len(par_path) == 1
        return par_path[0]


if __name__ == "__main__":
    dm = LivnehDataManager()
    print(dm.closest_cli(-122.75, 45.5))
