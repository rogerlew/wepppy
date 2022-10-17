from os.path import exists as _exists

from wepppy.wepp.out.loss import _parse_tbl


class HillLoss(object):
    def __init__(self, fn):
        assert _exists(fn)

        with open(fn) as fp:
            lines = fp.readlines()

        annuals = 'annual' in lines[0].lower()

        indx0 = []
        for i, L in enumerate(lines):
            if 'Sediment particle information leaving profile' in L:
                indx0.append(i)

        class_data = None
        if len(indx0) > 0:
            indx0 = indx0[-1]
            _lines = lines[indx0:]

            assert _lines[6].strip().startswith('1')
            assert _lines[7].strip().startswith('2')
            assert _lines[8].strip().startswith('3')
            assert _lines[9].strip().startswith('4')
            assert _lines[10].strip().startswith('5')

            class_data = _parse_tbl(_lines[6:11],
                                    ['Class', 'Diameter', 'Specific Gravity',
                                     'Pct Sand', 'Pct Silt', 'Pct Clay', 'Pct OM',
                                     'Detached Sediment Fraction',
                                     'Fraction In Flow Exiting'])

        annuals_d = None
        if annuals:
            indx0 = None
            for i, L in enumerate(lines):
                if 'annual averages' in L:
                    indx0 = i + 3
                    break

            if indx0:
               annuals_d = {
                   'n_storms': int(lines[indx0-8][:10]),
                   'total_precip': float(lines[indx0-8][46:58]),
                   'n_storm_q_events': int(lines[indx0-7][:10]),
                   'storm_q': float(lines[indx0-7][46:58]),
                   'n_melt_q_events': int(lines[indx0-6][:10]),
                   'melt_q': float(lines[indx0-5][46:58]),
                   'years': int(lines[indx0][48:60]),
                   'annual_mean_precip' : float(lines[indx0+1][48:60]),
                   'annual_runoff_storm' : float(lines[indx0+2][48:60]),
                   'annual_runoff_melt' : float(lines[indx0+4][48:60]),
               }
                   
        self.annuals = annuals
        self.annuals_d = annuals_d
        self.class_data = class_data

    def fraction_under(self, particle_size=0.016):
        """

        :param particle_size: in mm
        :return: fraction (0-1) of flow exiting hillslope less than particle size.
        """
        if self.class_data is None:
            return 0.0

        class_data = [(c['Diameter'], c['Fraction In Flow Exiting']) for c in self.class_data]

        class_data.sort(key=lambda x: x[0])

        if particle_size >= class_data[-1][0]:
            return 1.0

        i = 0
        for diam, frac in class_data:
            if particle_size <= diam:
                break
            i += 1

        if i == 0:
            x0 = 0.0
        else:
            x0 = class_data[i-1][0]
        xend, frac = class_data[i]

        partial_frac = (particle_size-x0)/(xend-x0) * frac

        if i > 0:
            for j in range(i):
                partial_frac += class_data[j][1]

        return partial_frac


if __name__ == "__main__":
    from pprint import pprint
#    hill_loss = HillLoss('/home/weppdev/PycharmProjects/wepppy/wepppy/scripts/RRED_RattleSnake_Burned/wepp/output/H1.loss.dat')
    hill_loss = HillLoss('/workdir/wepppy/wepppy/fswepppy/wr/test/wd/test.loss')
    print(hill_loss.annuals)
    print(hill_loss.fraction_under(particle_size=0.016))
    print(hill_loss.fraction_under(particle_size=0.0))
    print(hill_loss.fraction_under(particle_size=1.0))
    pprint(hill_loss.annuals_d)
