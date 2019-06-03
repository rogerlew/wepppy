from os.path import join as _join
from os.path import exists as _exists

_euhydrogrids_dir = '/geodata/eu/eusoilhydrogrids'

from wepppy.all_your_base import RasterDatasetInterpolator


class SoilHydroGrids:
    def __init__(self):
        self.datasets = ['THS', 'KS', 'WP', 'FC']
        self.depths = ['sl1', 'sl2', 'sl3', 'sl4', 'sl5', 'sl6', 'sl7']

        for depth in self.depths:
            for dataset in self.datasets:
                fn = self.get_fn(dataset, depth)
                assert _exists(fn), fn

    def query(self, lng, lat, dataset):

        d = {}
        for code, depth in zip(self.depths, [0, 5, 15, 30, 60, 100, 200]):
            rdi = RasterDatasetInterpolator(self.get_fn(dataset, code))
            d[code] = (depth, rdi.get_location_info(lng, lat, method='near'))

        return d

    @staticmethod
    def get_fn(dataset, depth):
        return _join(_euhydrogrids_dir, '{dataset}_{depth}/{dataset}_{depth}.tif'
                     .format(dataset=dataset, depth=depth))
