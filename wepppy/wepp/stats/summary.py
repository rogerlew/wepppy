# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

import csv
from os.path import split as _split
from os.path import join as _join
from os.path import exists as _exists
from glob import glob
from collections import OrderedDict

from wepppy.all_your_base import parse_units, parse_name, RowData, flatten

from wepppy.wepp.out import Loss
from wepppy.wepp.stats.report_base import ReportBase


class HillSummary(ReportBase):
    def __init__(self, loss: Loss, class_fractions=False, fraction_under=None):
        self.loss_fn = loss.fn
        self.data = loss.hill_tbl
        self.has_phosphorus = loss.has_phosphorus
        self.class_fractions = class_fractions
        self.fraction_under = fraction_under

        self._hdr = [
            'WeppID',
            'TopazID',
            'Landuse',
            'Soil',
            'Length (m)',
            'Hillslope Area (ha)',
            'Runoff (mm)',
            'Subrunoff (mm)',
            'Baseflow (mm)',
            'Soil Loss Density (kg/ha)',
            'Sediment Deposition Density (kg/ha)',
            'Sediment Yield Density (kg/ha)'
        ]

        if self.has_phosphorus:
            self._hdr.extend([
                'Solub. React. P Density (kg/ha,3)',
                'Particulate P Density (kg/ha,3)',
                'Total P Density (kg/ha,3)'
            ])

        if self.class_fractions:
            self._hdr.extend([
                'Particle Class 1 Fraction',
                'Particle Class 2 Fraction',
                'Particle Class 3 Fraction',
                'Particle Class 4 Fraction',
                'Particle Class 5 Fraction'
            ])

        if self.fraction_under:
            self._hdr.extend([
                'Particle Fraction Under %0.3f mm' % self.fraction_under,
                'Sediment Yield of Particles Under %0.3f mm (kg/ha)' % self.fraction_under,
            ])

    @property
    def header(self):
        return [colname.replace(' Density', '').replace('Subrunoff', 'Lateral Flow') for colname in self._hdr]

    def __iter__(self):

        data = self.data
        for i in range(len(data)):
            _data = [(colname.replace(' Density', '').replace('Subrunoff', 'Lateral Flow'),
                      data[i][parse_name(colname)]) for colname in self._hdr[:12]]

            if self.has_phosphorus:
                _data.extend([(colname.replace(' Density', ''),
                               data[i][parse_name(colname)]) for colname in self._hdr[12:15]])

            if self.class_fractions or self.fraction_under:
                wepp_id = data[i]['WeppID']
                hill_loss_fn = _join(_split(self.loss_fn)[0], 'H%i.loss.dat' % int(wepp_id))
                assert _exists(hill_loss_fn)

                from wepppy.wepp.out import HillLoss
                hill_loss = HillLoss(hill_loss_fn)

                if self.class_fractions:
                    _data.append(('Particle Class 1 Fraction', hill_loss.class_data[0]['Fraction In Flow Exiting']))
                    _data.append(('Particle Class 2 Fraction', hill_loss.class_data[1]['Fraction In Flow Exiting']))
                    _data.append(('Particle Class 3 Fraction', hill_loss.class_data[2]['Fraction In Flow Exiting']))
                    _data.append(('Particle Class 4 Fraction', hill_loss.class_data[3]['Fraction In Flow Exiting']))
                    _data.append(('Particle Class 5 Fraction', hill_loss.class_data[4]['Fraction In Flow Exiting']))

                if self.fraction_under:
                    frac = hill_loss.fraction_under(self.fraction_under)
                    sed_yield = data[i]['Sediment Yield Density']
                    _data.append(('Particle Fraction Under %0.3f mm' % self.fraction_under, frac))
                    _data.append(('Sediment Yield of Particles Under %0.3f mm (kg/ha)' % self.fraction_under,
                                  frac * sed_yield))

            yield RowData(OrderedDict(_data))


class ChannelSummary(ReportBase):
    def __init__(self, loss: Loss):
        self.data = loss.chn_tbl
        self.has_phosphorus = loss.has_phosphorus

        self._hdr = [
            'WeppID',
            'WeppChnID',
            'TopazID',
            'Length (m)',
            'Area (ha)',
            'Contributing Area (ha)',
            'Discharge Volume (m^3)',
            'Sediment Yield (tonne)',
            'Soil Loss (kg)',
            'Upland Charge (m^3)',
            'Subsuface Flow Volume (m^3)']

        if self.has_phosphorus:
            self._hdr.extend([
                'Solub. React. P Density (kg/ha)',
                'Particulate P Density (kg/ha)',
                'Total P Density (kg/ha)'
            ])

    @property
    def header(self):
        return [colname.replace(' Density', '')
                       .replace('Area', 'Channel Area')
                       .replace(' Volume', '')
                       .replace('Subsuface', 'Lateral')
                       .replace('(m^3)', '(mm)')
                       .replace('(kg)', '(tonne)')
                       .replace('Soil Loss', 'Channel Erosion')
                       for colname in self._hdr]

    def __iter__(self):
        data = self.data
        for i in range(len(data)):
            _data = OrderedDict()

            for colname in self._hdr:
                cname = colname.replace(' Density', '') \
                              .replace('Area', 'Channel Area') \
                              .replace(' Volume', '') \
                              .replace('Subsuface', 'Subsurface') \
                              .replace('Soil Loss', 'Channel Erosion')

                if 'Discharge' in colname:
                    _data['Discharge (mm)'] = data[i]['Discharge Volume'] / data[i]['Contributing Area'] / 10000.0 * 1000.0
                elif 'Upland Charge' in colname:
                    _data['Upland Charge (mm)'] = data[i]['Upland Charge'] / data[i]['Contributing Area'] / 10000.0 * 1000.0
                elif 'Subsuface Flow' in colname:
                    _data['Lateral Flow (mm)'] = data[i]['Subsuface Flow Volume'] / data[i]['Contributing Area'] / 10000.0 * 1000.0
                elif 'Soil Loss' in colname:
                    _data['Soil Loss (tonne)'] = data[i]['Soil Loss'] / 1000.0
                else:
                    _data[cname] = data[i][parse_name(colname)]

            yield RowData(_data)


class OutletSummary(ReportBase):
    def __init__(self, loss: Loss, fraction_under=None):
        data = loss.out_tbl
        data = dict([(d['key'], d) for d in data])
        self.data = data
        self.has_phosphorus = loss.has_phosphorus
        self.fraction_under = fraction_under
        self.loss = loss

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

#        key = 'Avg. Ann. irrigation volume in contributing area'
#        v = self.data[key]['v']
#        units = self.data[key]['units']
#        v_norm = 1000.0 * v / (area * 10000.0)
#        units_norm = 'mm/yr'
#        yield 'Irrigation', v, units, v_norm, units_norm

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
        sed_del = v = self.data[key]['v']
        units = self.data[key]['units']
        v_norm = 1000.0 * v / area
        units_norm = 'kg/ha/yr'
        yield 'Sediment discharge', v, units, v_norm, units_norm

        key = 'Sediment Delivery Ratio for Watershed'
        v = self.data[key]['v']
        yield 'Sediment delivery ratio for watershed', v, None, None, None

        if self.has_phosphorus:
            key = 'Avg. Ann. Phosphorus discharge from outlet'
            v = self.data[key]['v']
            units = self.data[key]['units']
            v_norm = v / area
            units_norm = 'kg/ha/yr'
            yield 'Phosphorus discharge', v, units, v_norm, units_norm

        if self.fraction_under:
            key = 'Particle Fraction Under %0.3f mm' % self.fraction_under
            v = self.loss.outlet_fraction_under(self.fraction_under)
            yield key, v, None, None, None

            key = 'Sediment Yield of Particles Under %0.3f mm' % self.fraction_under
            units = 'tonne/yr'
            v *= sed_del
            v_norm = 1000.0 * v / area
            units_norm = 'kg/ha/yr'
            yield key, v, units, v_norm, units_norm

    def write(self, fp, write_header=True, run_descriptors=None):

        wtr = csv.writer(fp)

        _data = list(self.__iter__())

        hdr = []
        row = []
        for key, v, units, v_norm, units_norm in _data:
            hdr.append(key)
            if units is not None:
                hdr[-1] += ' (%s)' % units

            row.append(v)

            if v_norm is not None:
                hdr.append('%s per area' % key)
                if units_norm is not None:
                    hdr[-1] += ' (%s)' % units_norm

                row.append(v_norm)

        if write_header:

            if run_descriptors is not None:
                hdr = [cname for cname, desc in run_descriptors] + hdr

            wtr.writerow(hdr)

        if run_descriptors is not None:
            row = [desc for cname, desc in run_descriptors] + row

        wtr.writerow(row)


if __name__ == "__main__":

    loss = Loss('/geodata/weppcloud_runs/2aa3e70e-769b-4e1b-959c-54c8c7c4f2e6/wepp/output/loss_pw0.txt',
                has_phosphorus=False,
                wd='/geodata/weppcloud_runs/2aa3e70e-769b-4e1b-959c-54c8c7c4f2e6/')

    hill_rpt = HillSummary(loss)