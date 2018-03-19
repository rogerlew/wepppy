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

        header = ['da', 'mo', 'year', 'prcp_depth(mm)', 'runoff_vol(m^3)', 'peak_runoff(m^3/s)', 'sediment_yld(kg)',
                  'solub_react_p(kg)', 'particulate_p(kg)', 'total_p(kg)']

        units = [int, int, int, float, float, float, float, float, float, float]

        data = [[u(v) for v, u in zip(L.split(), units)] for L in lines]
        data = list(map(list, zip(*data)))

        df = pd.DataFrame()
        for L, colname in zip(data, header):
            df[colname] = L

        self.df = df
        self.years = int(max(df['year']))
        self.header = header

    def return_periods(self, loss_rtp: LossReport, recurence=[2, 5, 10, 25]):

        df = self.df
        header = self.header
        years = self.years
        wsarea = loss_rtp.wsarea
        print(wsarea)

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
            results[col_name] = {}

            for retperiod, indx in rec.items():
                row = dict(df2.iloc[indx])
                row = dict((k, float(v)) for k, v in row.items())
                results[col_name][retperiod] = row

        return results

if __name__ == "__main__":
    from pprint import  pprint

    loss_rtp = LossReport('/home/weppdev/PycharmProjects/wepppy/wepppy/wepp/out/test/data/ww2output.txt')
    ebe_rpt = EbeReport('/home/weppdev/PycharmProjects/wepppy/wepppy/wepp/out/test/data/ww2events.txt')
    print(ebe_rpt.years)
    results = ebe_rpt.return_periods(loss_rtp)
    pprint(results)

#    report = EbeReport('/home/weppdev/PycharmProjects/wepppy/wepppy/validation/blackwood_MultPRISM/wepp/output/ebe_pw0.txt')