import pandas as pd
from wepppy.all_your_base import isfloat


def try_parse(x):
    try:
        ff = float(x)
        fi = int(ff)
        if ff == fi:
            return fi
        return ff
    except ValueError:
        return float('nan')


class RhemOutput(object):
    def __init__(self, fn):
        with open(fn) as fp:
            lines = fp.readlines()

        cnames = lines[0].split()
        units = lines[1].split()

        data = []

        for line in lines[2:]:
            _line = line[:8], line[8:15], line[15:22], line[22:29], line[29:41], line[41:53], line[53:65], \
                    line[65:77], line[77:89], line[89:101], line[101:113], line[113:125]

            data.append([try_parse(v) for v in _line])

        df = pd.DataFrame(data, columns=cnames)
        df.sort_values(by=['Year', 'Month', 'Day'])

        self.df = df


class RhemSummary(object):
    def __init__(self, fn, area_ha=None):
        with open(fn) as fp:
            lines = fp.readlines()

        annuals = {}
        for i in range(2, 6):
            k, v = lines[i].split('=')
            measure = k.strip().replace('ton', 'tonne').replace('year', 'yr')\
                .replace('(', ' (').replace('  (', ' (')
            annuals[measure] = try_parse(v)

        periods = lines[10].split()[1:]
        return_freqs = {}
        for i in range(12, 16):
            line = lines[i].split()
            measure = ''.join(line[:-len(periods)]).replace('ton', 'tonne').replace('year', 'yr')\
                .replace('(', ' (').replace('  (', ' (')
            return_freqs[measure] = [try_parse(v) for v in line[-len(periods):]]

        if area_ha is not None:
            assert isfloat(area_ha)

            _annuals = {}
            for measure in annuals:
                if '/ha' in measure:
                    _annuals[measure.replace('/ha', '')] = annuals[measure] * area_ha
                if 'mm' in measure:
                    _annuals[measure.replace('mm', 'm^3')] = annuals[measure] * area_ha * 10
            annuals.update(_annuals)

            _return_freqs = {}
            for measure in return_freqs:
                if '/ha' in measure:
                    _return_freqs[measure.replace('/ha', '')] = [v * area_ha for v in return_freqs[measure]]
                if 'mm' in measure:
                    _return_freqs[measure.replace('mm', 'm^3')] = [v * area_ha * 10 for v in return_freqs[measure]]
            return_freqs.update(_return_freqs)

        self.area = area_ha
        self.annuals = annuals
        self.ret_freq_periods = periods
        self.return_freqs = return_freqs


if __name__ == "__main__":
    fn = '/geodata/weppcloud_runs/devvm7f5-db67-4491-8e26-ab37cbf5c55e/rhem/output/hill_22.out'
    RhemOutput(fn)

    fn2 = '/geodata/weppcloud_runs/devvm7f5-db67-4491-8e26-ab37cbf5c55e/rhem/output/hill_22.sum'
    summary = RhemSummary(fn2, 20)
    from pprint import pprint
    pprint(summary.annuals)
    pprint(summary.return_freqs)

