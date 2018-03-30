import pandas as pd

from wepppy.wepp.out import LossReport


class Ebe(object):
    def __init__(self, fn):

        # read the loss report
        with open(fn) as fp:
            lines = fp.readlines()

        # strip trailing and leading white space
        lines = [L.strip() for L in lines]

        lines = [L for L in lines if L != '']

        # find the average annual
        i0 = 0
        for i0, L in enumerate(lines):
            if '---------' in L:
                break

        # restrict lines to just the average annual
        # values
        lines = lines[i0+1:]

        header = ['da', 'mo', 'year',
                  'Precipitation Depth (mm)',
                  'Runoff Volume (m^3)',
                  'Peak Runoff (m^3/s)',
                  'Sediment Yield (kg)',
                  'Soluble Reactive P (kg)',
                  'Particulate P (kg)',
                  'Total P (kg)']

        units = [int, int, int, float, float, float, float, float, float, float]

        data = [[u(v) for v, u in zip(L.split(), units)] for L in lines]
        data = list(map(list, zip(*data)))

        if data == []:
            raise Exception('{} contains no data'.format(fn))

        df = pd.DataFrame()
        for L, colname in zip(data, header):
            df[colname] = L

        self.df = df
        self.years = int(max(df['year']))
        self.header = header
        self.units_d = {
          'Precipitation Depth': 'mm',
          'Runoff Volume': 'm^3',
          'Peak Runoff': 'm^3/s',
          'Runoff': 'mm',
          'Sediment Yield': 'kg',
          'Soluble Reactive P': 'kg',
          'Particulate P': 'kg',
          'Total P': 'kg'
        }


if __name__ == "__main__":
    from pprint import  pprint

    loss_rtp = LossReport('/home/weppdev/PycharmProjects/wepppy/wepppy/wepp/out/test/data/ww2output.txt')
    ebe_rpt = Ebe('/home/weppdev/PycharmProjects/wepppy/wepppy/wepp/out/test/data/ww2events.txt')
    pprint(ebe_rpt.years)
    pprint(ebe_rpt.df)

#    report = EbeReport('/home/weppdev/PycharmProjects/wepppy/wepppy/validation/blackwood_MultPRISM/wepp/output/ebe_pw0.txt')