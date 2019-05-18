import csv
from os.path import join as _join

from collections import OrderedDict

from wepppy.wepp.out import TotalWatSed
from wepppy.wepp.out.loss import _parse_tbl

from wepppy.all_your_base import RowData, try_parse


class SedimentDelivery(object):
    def __init__(self, wd):
        from wepppy.nodb import Wepp
        wepp = Wepp.getInstance(wd)

        loss_pw0 = _join(wepp.output_dir, 'loss_pw0.txt')
        # read the loss report
        with open(loss_pw0) as fp:
            lines = fp.readlines()

        # strip trailing and leading white space
        lines = [L.strip() for L in lines]

        sed_discharge = None
        indx0 = []
        for i, L in enumerate(lines):
            if 'Avg. Ann. sediment discharge from outlet' in L:
                indx0.append(i)
        if len(indx0) > 0:

            sed_discharge = float(lines[indx0[-1]].split('=')[-1].split()[0])


        # Find class table
        indx0 = []
        for i, L in enumerate(lines):
            if 'sediment particle information leaving' in L.lower():
                indx0.append(i)

        if len(indx0) == 0:
            self.class_data = None
            return

        indx0 = indx0[-1]
        lines = lines[indx0:]

        assert lines[7].startswith('1')
        assert lines[8].startswith('2')
        assert lines[9].startswith('3')
        assert lines[10].startswith('4')
        assert lines[11].startswith('5')

        class_data = _parse_tbl(lines[7:12],
                                ['Class', 'Diameter', 'Specific Gravity',
                                 'Pct Sand', 'Pct Silt', 'Pct Clay', 'Pct OM',
                                 'Fraction In Flow Exiting'])

        class_fractions = [row['Fraction In Flow Exiting'] for row in class_data]

        assert lines[20].startswith('clay')
        assert lines[21].startswith('silt')
        assert lines[22].startswith('sand')
        assert lines[23].startswith('organic matter')

        particle_distribution = {}
        particle_distribution['clay'] = try_parse(lines[20].split()[-1])
        particle_distribution['silt'] = try_parse(lines[21].split()[-1])
        particle_distribution['sand'] = try_parse(lines[22].split()[-1])
        particle_distribution['organic matter'] = try_parse(lines[23].split()[-1])

        totwatsed_fn = _join(wepp.output_dir, 'totalwatsed.txt')
        totwatsed = TotalWatSed(totwatsed_fn, wepp.baseflow_opts,
                                phosOpts=wepp.phosphorus_opts)

        hill_class_fractions = totwatsed.class_fractions

        hill_particle_distribution = {}
        hill_particle_distribution['clay'] = [c['Pct Clay']/100.0 * f for c, f in zip(class_data, hill_class_fractions)]
        hill_particle_distribution['silt'] = [c['Pct Silt']/100.0 * f for c, f in zip(class_data, hill_class_fractions)]
        hill_particle_distribution['sand'] = [c['Pct Sand']/100.0 * f for c, f in zip(class_data, hill_class_fractions)]
        hill_particle_distribution['organic matter'] = [c['Pct OM']/100.0 * f for c, f in zip(class_data, hill_class_fractions)]

        for k in hill_particle_distribution:
            hill_particle_distribution[k] = sum(hill_particle_distribution[k])

        assert lines[26].startswith('Index of specific surface')
        assert lines[27].startswith('Enrichment ratio of specific surface')

        specific_surface_index = try_parse(lines[26].split('=')[-1].split()[0])
        enrichment_ratio_of_spec_surf = try_parse(lines[27].split('=')[-1].split()[0])
        
        self.class_data = class_data

        self.sed_discharge = sed_discharge
        self.class_fractions = class_fractions
        self.particle_distribution = particle_distribution

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