import pandas as pd

from wepppy.wepp.out import LossReport


class EbeReport(object):
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
        self.return_periods = None
        self.num_events = None
        self.wsarea = None
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
        

    def run_return_periods(self, loss_rtp: LossReport, recurence=[2, 5, 10, 25]):

        df = self.df
        header = self.header
        years = self.years
        wsarea = loss_rtp.wsarea

        recurence = sorted(recurence)

        # Note that return period of the events are estimated by applying
        # Weibull formula on annual maxima series.
        #    T = (N + 1)/m
        #
        # where T is the return period, N is the number of simulation years,
        # and m is the rank of the annual maxima event.

        rec = {}
        i = 0
        rankind = self.years
        orgind = years + 1
        reccount = 0

        while i < len(recurence) and rankind >= 2.5:
            retperiod = recurence[i]
            rankind = float(years + 1) / retperiod
            intind = int(rankind) - 1
    
            if intind < orgind:
                rec[retperiod] = intind
                orgind = intind
                reccount = reccount + 1
            
            i += 1

        results = {}

        for col_name in [v for v in header if v not in ['da', 'mo', 'year']]:
            df2 = df.sort_values(by=col_name, ascending=False)

            col_name = col_name.split('(')[0].strip()
            results[col_name] = {}
            if col_name == 'Runoff Volume':
                results['Runoff'] = {}

            for retperiod, indx in rec.items():
                row = dict(df2.iloc[indx])
                row = dict((k.split('(')[0].strip(), float(v)) for k, v in row.items())

                row['Runoff'] = round(row['Runoff Volume'] / (wsarea * 10000.0) * 1000.0, 2)

                results[col_name][retperiod] = row

                if col_name == 'Runoff Volume':
                    results['Runoff'][retperiod] = row

        self.return_periods = results
        self.num_events = df.shape[0]
        self.wsarea = wsarea


if __name__ == "__main__":
    from pprint import  pprint

    loss_rtp = LossReport('/home/weppdev/PycharmProjects/wepppy/wepppy/wepp/out/test/data/ww2output.txt')
    ebe_rpt = EbeReport('/home/weppdev/PycharmProjects/wepppy/wepppy/wepp/out/test/data/ww2events.txt')
    ebe_rpt.run_return_periods(loss_rtp)
    pprint(ebe_rpt.years)
    pprint(ebe_rpt.num_events)
    pprint(ebe_rpt.return_periods)
    pprint(ebe_rpt.wsarea)

#    report = EbeReport('/home/weppdev/PycharmProjects/wepppy/wepppy/validation/blackwood_MultPRISM/wepp/output/ebe_pw0.txt')