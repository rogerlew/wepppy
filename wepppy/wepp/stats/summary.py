# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

from os.path import join as _join
from os.path import exists as _exists
from glob import glob
from collections import OrderedDict

from wepppy.all_your_base import parse_units, parse_name, RowData

from wepppy.wepp.out import Loss
from wepppy.wepp.stats.report_base import ReportBase


class HillSummary(ReportBase):
    def __init__(self, loss: Loss):
        self.data = loss.hill_tbl

        self._hdr = (
            'WeppID',
            'TopazID',
            'Landuse',
            'Soil',
            'Length (m)',
            'Hillslope Area (ha)',
            'Runoff (mm)',
            'Subrunoff (mm)',
            'Baseflow Volume (m^3)',
            'Soil Loss Density (kg/ha)',
            'Sediment Deposition Density (kg/ha)',
            'Sediment Yield Density (kg/ha)',
            'Solub. React. P Density (kg/ha)',
            'Particulate P Density (kg/ha)',
            'Total P Density (kg/ha)'
        )

    @property
    def header(self):
        return [colname.replace(' Density', '') for colname in self._hdr]

    def __iter__(self):
        data = self.data
        for i in range(len(data)):
            yield RowData(OrderedDict([(colname.replace(' Density', ''),
                                        data[i][parse_name(colname)]) for colname in self._hdr]))


class ChannelSummary(ReportBase):
    def __init__(self, loss: Loss):
        self.data = loss.chn_tbl

        self._hdr = (
            'WeppID',
            'TopazID',
            'Length (m)',
            'Area (ha)',
            'Discharge Volume (m^3)',
            'Sediment Yield (tonne)',
            'Soil Loss (kg)',
            'Upland Charge (m^3)',
            'Subsuface Flow Volume (m^3)',
            'Solub. React. P Density (kg/ha)',
            'Particulate P Density (kg/ha)',
            'Total P Density (kg/ha)'
        )

    @property
    def header(self):
        return [colname.replace(' Density', '') for colname in self._hdr]

    def __iter__(self):
        data = self.data
        for i in range(len(data)):
            yield RowData(OrderedDict([(colname.replace(' Density', ''),
                                        data[i][parse_name(colname)]) for colname in self._hdr]))


class OutletSummary(ReportBase):
    def __init__(self, loss: Loss):
        data = loss.out_tbl
        data = dict([(d['key'], d) for d in data])
        self.data = data

    def __iter__(self):
        key = 'Total contributing area to outlet'
        area = self.data[key]['v']
        units = self.data[key]['units']
        yield key, area, units, None, None

        key = 'Avg. Ann. Precipitation volume in contributing area'
        v = self.data[key]['v']
        units = self.data[key]['units']
        v_norm = 1000.0 * v / (area * 10000.0)
        units_norm = 'mm/yr'
        yield 'Precipitation', v, units, v_norm, units_norm

        key = 'Avg. Ann. irrigation volume in contributing area'
        v = self.data[key]['v']
        units = self.data[key]['units']
        v_norm = 1000.0 * v / (area * 10000.0)
        units_norm = 'mm/yr'
        yield 'Irrigation', v, units, v_norm, units_norm

        key = 'Avg. Ann. water discharge from outlet'
        v = self.data[key]['v']
        units = self.data[key]['units']
        v_norm = 1000.0 * v / (area * 10000.0)
        units_norm = 'mm/yr'
        yield 'Water discharge', v, units, v_norm, units_norm

        key = 'Avg. Ann. total hillslope soil loss'
        v = self.data[key]['v']
        units = self.data[key]['units']
        v_norm = 1000.0 * v / area
        units_norm = 'kg/ha/yr'
        yield 'Total hillslope soil loss', v, units, v_norm, units_norm

        key = 'Avg. Ann. total channel soil loss'
        v = self.data[key]['v']
        units = self.data[key]['units']
        v_norm = 1000.0 * v / area
        units_norm = 'kg/ha/yr'
        yield 'Total channel soil loss', v, units, v_norm, units_norm

        key = 'Avg. Ann. sediment discharge from outlet'
        v = self.data[key]['v']
        units = self.data[key]['units']
        v_norm = 1000.0 * v / area
        units_norm = 'kg/ha/yr'
        yield 'Sediment discharge', v, units, v_norm, units_norm

        key = 'Sediment Delivery Ratio for Watershed'
        v = self.data[key]['v']
        yield 'Sediment delivery ratio for watershed', v, None, None, None

        key = 'Avg. Ann. Phosphorus discharge from outlet'
        v = self.data[key]['v']
        units = self.data[key]['units']
        v_norm = v / area
        units_norm = 'kg/ha/yr'
        yield 'Phosphorus discharge', v, units, v_norm, units_norm


if __name__ == "__main__":

    loss = Loss('/geodata/weppcloud_runs/88d80fb4-41b5-4fb7-a9aa-5e2de0892c4f/wepp/output/loss_pw0.txt',
                '/geodata/weppcloud_runs/88d80fb4-41b5-4fb7-a9aa-5e2de0892c4f/')

    hill_rpt = HillSummary(loss)

    for row in hill_rpt:
        for k, v in row:
            print(k, v)

    chn_rpt = ChannelSummary(loss)

    for row in chn_rpt:
        for k, v in row:
            print(k, v)

    out_rpt = OutletSummary(loss)

    for name, value, units, v_normed, units_normed in out_rpt:
        print(name, value, units, v_normed, units_normed)