from os.path import join as _join

from collections import OrderedDict

from wepppy.wepp.out import TotalWatSed
from wepppy.wepp.out.loss import _parse_tbl

from wepppy.all_your_base import RowData


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
        # Find class table
        indx0 = []
        for i, L in enumerate(lines):
            if 'Avg. Ann. sediment discharge from outlet' in L:
                sed_discharge = float(L.split()[-2])
            if 'Sediment Particle Information Leaving Channel' in L:
                indx0.append(i)

        assert len(indx0) > 0
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
        particle_distribution['clay'] = float(lines[20].split()[-1])
        particle_distribution['silt'] = float(lines[21].split()[-1])
        particle_distribution['sand'] = float(lines[22].split()[-1])
        particle_distribution['organic matter'] = float(lines[23].split()[-1])

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

        self.class_data = class_data

        self.sed_discharge = sed_discharge
        self.class_fractions = class_fractions
        self.particle_distribution = particle_distribution

        self.hill_sed_delivery = totwatsed.sed_delivery / totwatsed.num_years
        self.hill_class_fractions = hill_class_fractions
        self.hill_particle_distribution = hill_particle_distribution

    @property
    def class_info_report(self):
        return SedimentClassInfo(self.class_data)


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
    pc = SedimentDelivery('/geodata/weppcloud_runs/Watershed_11_General/')

    rpt = pc.class_info_report
    print(rpt.hdr)

    for rowdata in rpt:
        for colname, (value, units) in zip(rpt.hdr, rowdata):
            print(colname, value, units)
