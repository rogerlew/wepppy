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

from copy import deepcopy

from wepppy.all_your_base import parse_units, parse_name, RowData, flatten, isfloat

from wepppy.wepp.out import Loss
from wepppy.wepp.stats.report_base import ReportBase

_hill_default_hdr = [
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

_hill_phos_hdr = [
    'Solub. React. P Density (kg/ha,3)',
    'Particulate P Density (kg/ha,3)',
    'Total P Density (kg/ha,3)'
]

_hill_ash_hdr = [
    'Wind Transport (kg/ha)',
    'Water Transport (kg/ha)',
    'Burnclass'
]

class HillSummary(ReportBase):
    def __init__(self, loss: Loss, class_fractions=False, fraction_under=None, subs_summary=None,
                 ash_out=None):
        self.loss_fn = loss.fn
        self.data = loss.hill_tbl
        self.has_phosphorus = loss.has_phosphorus
        self.class_fractions = class_fractions
        self.fraction_under = fraction_under
        self.subs_summary = subs_summary
        self.ash_out = ash_out

        self._hdr = deepcopy(_hill_default_hdr)

        if self.subs_summary:
            self._hdr.extend([
                'Width (m)',
                'Slope',
                'LanduseDesc',
                'SoilDesc'
            ])

        if self.has_phosphorus:
            self._hdr.extend(_hill_phos_hdr)

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

        if ash_out:
            self._hdr.extend(_hill_ash_hdr)

    @property
    def header(self):
        return [colname.replace(' Density', '').replace('Subrunoff', 'Lateral Flow') for colname in self._hdr]

    def __iter__(self):
        subs_summary = self.subs_summary
        ash_out = self.ash_out

        data = self.data
        for i in range(len(data)):
            _data = [(colname.replace(' Density', '').replace('Subrunoff', 'Lateral Flow'),
                      data[i][parse_name(colname)]) for colname in _hill_default_hdr]

            topaz_id = data[i]['TopazID']

            if subs_summary:
                sub_summary = subs_summary[topaz_id]
                _data.append(('Width (m)', sub_summary['watershed']['width']))
                _data.append(('Slope', sub_summary['watershed']['slope_scalar']))
                _data.append(('LanduseDesc', sub_summary['landuse']['desc']))
                _data.append(('SoilDesc', sub_summary['soil']['desc']))

            if self.has_phosphorus:
                _data.extend([(colname.replace(' Density', ''),
                               data[i][parse_name(colname)]) for colname in _hill_phos_hdr])

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

            if ash_out:
                _data.append(('Wind Transport (kg/ha)', ash_out[str(topaz_id)]['wind_transport (kg/ha)']))
                _data.append(('Water Transport (kg/ha)', ash_out[str(topaz_id)]['water_transport (kg/ha)']))
                _data.append(('Burnclass', ash_out[str(topaz_id)]['burnclass']))

            yield RowData(OrderedDict(_data))


_chn_default_hdr = [
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
    'Subsuface Flow Volume (m^3)'
]


_chn_summary_hdr = [
    'CellWidth',
    'Order',
    'Slope',
    'Landuse',
    'LanduseDesc',
    'Soil',
    'SoilDesc',
    'ChannelType'
]


_chn_phos_hdr = [
    'Solub. React. P Density (kg/ha)',
    'Particulate P Density (kg/ha)',
    'Total P Density (kg/ha)'
]


class ChannelSummary(ReportBase):
    def __init__(self, loss: Loss, chns_summary=None):
        self.data = loss.chn_tbl
        self.chns_summary = chns_summary
        self.has_phosphorus = loss.has_phosphorus

        self._hdr = deepcopy(_chn_default_hdr)

        if self.chns_summary:
            self._hdr.extend(_chn_summary_hdr)

        if self.has_phosphorus:
            self._hdr.extend(_chn_phos_hdr)

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
        chns_summary = self.chns_summary

        for i in range(len(data)):
            _data = OrderedDict()

            topaz_id = data[i]['TopazID']

            for colname in _chn_default_hdr:
                cname = colname.replace(' Density', '') \
                               .replace('Area', 'Channel Area') \
                               .replace(' Volume', '') \
                               .replace('Subsuface', 'Subsurface') \
                               .replace('Soil Loss', 'Channel Erosion')

                if 'Discharge' in colname:
                    if isfloat(data[i]['Discharge Volume']):
                        _data['Discharge (mm)'] = data[i]['Discharge Volume'] /\
                                                  data[i]['Contributing Area'] / 10000.0 * 1000.0
                    else:
                        _data['Discharge (mm)'] = float('nan')
                elif 'Upland Charge' in colname:
                    if isfloat(data[i]['Upland Charge']):
                        _data['Upland Charge (mm)'] = data[i]['Upland Charge'] /\
                                                      data[i]['Contributing Area'] / 10000.0 * 1000.0
                    else:
                        _data['Upland Charge (mm)'] = float('nan')
                elif 'Subsuface Flow' in colname:
                    if isfloat(data[i]['Subsuface Flow Volume']):
                        _data['Lateral Flow (mm)'] = data[i]['Subsuface Flow Volume'] /\
                                                     data[i]['Contributing Area'] / 10000.0 * 1000.0
                    else:
                        _data['Lateral Flow (mm)'] = float('nan')
                elif 'Soil Loss' in colname:
                    if isfloat(data[i]['Soil Loss']):
                        _data['Soil Loss (tonne)'] = data[i]['Soil Loss'] / 1000.0
                    else:
                        _data['Soil Loss (tonne)'] = float('nan')
                else:
                    _data[cname] = data[i][parse_name(colname)]

            if chns_summary:
                chn_summary = chns_summary[topaz_id]
                _data['CellWidth'] = chn_summary['watershed']['cell_width']
                _data['Order'] = chn_summary['watershed']['order']
                _data['Slope'] = chn_summary['watershed']['slope_scalar']
                _data['Landuse'] = chn_summary['landuse']['key']
                _data['LanduseDesc'] = chn_summary['landuse']['desc']
                _data['Soil'] = chn_summary['soil']['mukey']
                _data['SoilDesc'] = chn_summary['soil']['desc']
                _data['ChannelType'] = chn_summary['soil']['desc']

            if self.has_phosphorus:
                for colname in _chn_phos_hdr:
                    cname = colname.replace(' Density', '') \
                                   .replace('Area', 'Channel Area') \
                                   .replace(' Volume', '') \
                                   .replace('Subsuface', 'Subsurface') \
                                   .replace('Soil Loss', 'Channel Erosion')

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