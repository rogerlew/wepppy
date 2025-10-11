import csv
import math
from collections import OrderedDict
from os.path import join as _join
from typing import Dict

from wepppy.wepp.out import TotalWatSed2
from wepppy.wepp.out.loss import Loss

from .row_data import RowData


class SedimentDelivery(object):
    def __init__(self, wd):
        self.wd = wd

        from wepppy.nodb.core import Wepp
        wepp = Wepp.getInstance(wd)

        loss_pw0 = _join(wepp.output_dir, 'loss_pw0.txt')
        loss_report = Loss(loss_pw0, wepp.has_phosphorus, wepp.wd)

        class_data = loss_report.class_data
        if not class_data:
            self.class_data = None
            return

        def _safe_value(entry: Dict[str, object], key: str) -> float:
            value = entry.get(key)
            try:
                numeric = float(value)
            except (TypeError, ValueError):
                return 0.0
            return 0.0 if math.isnan(numeric) else numeric

        self.class_data = class_data
        self.class_fractions = [_safe_value(row, 'Fraction In Flow Exiting') for row in class_data]

        particle_distribution = {
            'clay': sum(_safe_value(row, 'Pct Clay') / 100.0 * _safe_value(row, 'Fraction In Flow Exiting') for row in class_data),
            'silt': sum(_safe_value(row, 'Pct Silt') / 100.0 * _safe_value(row, 'Fraction In Flow Exiting') for row in class_data),
            'sand': sum(_safe_value(row, 'Pct Sand') / 100.0 * _safe_value(row, 'Fraction In Flow Exiting') for row in class_data),
            'organic matter': sum(_safe_value(row, 'Pct OM') / 100.0 * _safe_value(row, 'Fraction In Flow Exiting') for row in class_data),
        }

        out_lookup = {row['key']: row['value'] for row in loss_report.out_tbl}
        sed_discharge = out_lookup.get('Avg. Ann. sediment discharge from outlet', 0.0)
        specific_surface_index = out_lookup.get('Index of specific surface', 0.0)
        enrichment_ratio_of_spec_surf = out_lookup.get('Enrichment ratio of specific surface', 0.0)

        totwatsed = TotalWatSed2(wd)
        hill_class_fractions = totwatsed.class_fractions

        hill_particle_distribution = {
            'clay': sum(_safe_value(row, 'Pct Clay') / 100.0 * frac for row, frac in zip(class_data, hill_class_fractions)),
            'silt': sum(_safe_value(row, 'Pct Silt') / 100.0 * frac for row, frac in zip(class_data, hill_class_fractions)),
            'sand': sum(_safe_value(row, 'Pct Sand') / 100.0 * frac for row, frac in zip(class_data, hill_class_fractions)),
            'organic matter': sum(_safe_value(row, 'Pct OM') / 100.0 * frac for row, frac in zip(class_data, hill_class_fractions)),
        }

        self.particle_distribution = particle_distribution
        self.sed_discharge = sed_discharge
        self.hill_sed_delivery = totwatsed.sed_delivery / totwatsed.num_years / 1000.0
        self.hill_class_fractions = hill_class_fractions
        self.hill_particle_distribution = hill_particle_distribution
        self.specific_surface_index = specific_surface_index  # m**2/g of total sediment
        self.enrichment_ratio_of_spec_surf = enrichment_ratio_of_spec_surf

    @property
    def class_info_report(self):
        return SedimentClassInfo(self.class_data)

    def write(self, fp, write_header=True, run_descriptors=None):

        hdr = ['Channel Class 1', 'Channel Class 2', 'Channel Class 3', 'Channel Class 4', 'Channel Class 5',
               'Channel Clay', 'Channel Silt', 'Channel Sand', 'Channel Organic Matter',
               'Hillslopes Class 1', 'Hillslopes Class 2', 'Hillslopes Class 3', 'Hillslopes Class 4',
               'Hillslopes Class 5',
               'Hillslopes Clay', 'Hillslopes Silt', 'Hillslopes Sand', 'Hillslopes Organic Matter',
               'Average Annual Sediment Discharge from Outlet (tonnes/yr)',
               'Average Annual Sediment Delivery from Hillslopes (tonnes/yr)',
               'Index of specific surface (m**2/g of total sediment)',
               'Enrichment ratio of specific surface']

        wtr = csv.writer(fp)

        if write_header:

            if run_descriptors is not None:
                hdr = [cname for cname, desc in run_descriptors] + hdr

            wtr.writerow(hdr)

        if self.class_data is None:
            row = [0 for colname in hdr]
        else:
            row = self.class_fractions + \
                  [self.particle_distribution['clay'],
                   self.particle_distribution['silt'],
                   self.particle_distribution['sand'],
                   self.particle_distribution['organic matter']] + \
                  self.hill_class_fractions + \
                  [self.hill_particle_distribution['clay'],
                   self.hill_particle_distribution['silt'],
                   self.hill_particle_distribution['sand'],
                   self.hill_particle_distribution['organic matter']] + \
                  [self.sed_discharge,
                   self.hill_sed_delivery,
                   self.specific_surface_index,
                   self.enrichment_ratio_of_spec_surf]

        if run_descriptors is not None:
            row = [desc for cname, desc in run_descriptors] + row

        wtr.writerow(row)


class SedimentClassInfo(object):
    def __init__(self, class_data):
        self.hdr = ['Class', 'Diameter (mm)', 'Specific Gravity',
                    '% Sand', '% Silt', '% Clay', '% OM']

        self.class_data = class_data

    def __iter__(self):
        for c in self.class_data:
            yield RowData(OrderedDict([(k, c[k]) for k in
                                       ['Class', 'Diameter', 'Specific Gravity',
                                        'Pct Sand', 'Pct Silt', 'Pct Clay', 'Pct OM']]))


if __name__ == "__main__":
    pc = SedimentDelivery('/geodata/weppcloud_runs/devvm4c5-6dec-464a-b520-00e668d993f2/')

    rpt = pc.class_info_report
    print(rpt.hdr)

    for rowdata in rpt:
        for colname, (value, units) in zip(rpt.hdr, rowdata):
            print(colname, value, units)

    print(pc.specific_surface_index)
    print(pc.enrichment_ratio_of_spec_surf)

    fp = open('/home/weppdev/sed.csv', 'w')
    pc.write(fp)
