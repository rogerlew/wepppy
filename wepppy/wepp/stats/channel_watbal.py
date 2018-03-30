from collections import OrderedDict
import  numpy as np
from wepppy.all_your_base import parse_units, RowData

class ChanWatbal:
    def __init__(self, chnwb):

        self.header = ['Year', 'P (mm)', 'RM (mm)',
                       'Ep (mm)', 'Es (mm)', 'Er (mm)', 'Dp (mm)',
                       'Total-Soil Water (mm)', 'frozwt (mm)', 'Snow-Water (mm)',
                       'Tile (mm)', 'Irr (mm)', 'Q (mm)', 'latqcc (mm)']

        data = OrderedDict()

        for colname in self.header:
            data[colname] = []

        _data = chnwb.data
        area_w = _data['Area Weights']

        weighted_vars = ['RM (mm)', 'Ep (mm)', 'Es (mm)', 'Er (mm)', 'Dp (mm)',
                         'Total-Soil Water (mm)', 'frozwt (mm)',
                         'Snow-Water (mm)', 'Tile (mm)', 'Irr (mm)']

        last_ofe_vars = ['Q (mm)', 'latqcc (mm)']

        years = sorted(set(_data['Y'].flatten()))
        for year in years:
            indx = np.where(year == _data['Y'])[0]

            data['Year'].append(year)
            data['P (mm)'].append(np.sum(_data['P (mm)'][indx, :], axis=1))

            for k in weighted_vars:
                data[k].append(np.sum(_data[k][indx, :] * area_w, axis=1))

            for k in last_ofe_vars:
                data[k].append(_data[k][indx[-1], :])

        self.data = data

    @property
    def hdr(self):
        for colname in self.header:
            yield colname.split()[0]

    @property
    def units(self):
        for colname in self.header:
            yield parse_units(colname)

    def __iter__(self):
        data = self.data
        for i in range(len(data['Year'])):
            yield RowData(OrderedDict([(colname, np.sum(data[colname][i])) for colname in self.header]))
