# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.
import numpy as np
from pandas import DataFrame, Series
from wepppy.all_your_base.stats import weibull_series
from .row_data import parse_name, parse_units, RowData

from wepppy.wepp.out import Loss, Ebe, TotalWatSed2

from copy import deepcopy

class ReturnPeriods:
    def __init__(self, ebe: Ebe = None, loss: Loss = None,
                 cli_df: DataFrame = None, 
                 recurrence=(2, 5, 10, 20, 25),
                 exclude_yr_indxs=None,
                 method='cta', gringorten_correction=False, 
                 totwatsed2: TotalWatSed2 = None):
        """
        Args:
            ebe (Ebe): The event by event  report.
            loss (Loss): The WEPP loss report.
            cli_df (DataFrame): The climate data.
            recurrence (tuple): The recurrence intervals in years.
            exclude_yr_indxs (list): A list of year indexes to exclude from the analysis.
            method (str): The method used to calculate the return periods. Options are 'cta' (default) complete time series analysis or 'am' or annual maxima.
            gringorten_correction (bool): If True, applies the Gringorten correction to the Weibull formula.
            totwatsed2 (pandas.DataFrame or None): if not None provides Hill SedDel and Hill Streamflow
        """

        if ebe is None or loss is None or cli_df is None:
            return

        self.has_phosphorus = loss.has_phosphorus

        df = deepcopy(ebe.df)

        df['10-min Peak Rainfall Intensity'] = cli_df['10-min Peak Rainfall Intensity (mm/hour)']
        if '15-min Peak Rainfall Intensity (mm/hour)' in cli_df:
            df['15-min Peak Rainfall Intensity'] = cli_df['15-min Peak Rainfall Intensity (mm/hour)']
        df['30-min Peak Rainfall Intensity'] = cli_df['30-min Peak Rainfall Intensity (mm/hour)']
        df['Storm Duration'] = cli_df['dur']

        if totwatsed2 is not None:
            wsarea_m2 = totwatsed2.wsarea
            df['Hill Sed Del'] = totwatsed2.d['Sed Del (kg)'] / 1000.0  # tonne
            df['Hill Streamflow'] = totwatsed2.d['Streamflow (mm)']

        _years = sorted(set(df['year']))
        _y0 = _years[0]
        if exclude_yr_indxs is not None:
            __years = []

            for indx, _yr in enumerate(sorted(set(df['year']))):
                if indx not in exclude_yr_indxs:
                    __years.append(_yr)
            _years = __years

            df = df[df['year'].isin(_years)]

        header = list(df.keys())
        header.remove('da')
        header.remove('mo')
        header.remove('year')

        self.header = header
        self.method = method
        self.gringorten_correction = gringorten_correction
        self.y0 = _y0
        self.years = years = len(_years)
        self.wsarea = wsarea = loss.wsarea
        self.recurrence = recurrence = sorted(recurrence)
        self.exclude_yr_indxs = exclude_yr_indxs

        rec = weibull_series(recurrence, years, 
                             method=method, gringorten_correction=gringorten_correction)

        days_in_year = len(df) / years

        results = {}
        for colname in header:

            if method == 'cta':
                df2 = df.sort_values(by=colname, ascending=False)
            else:
                df2 = df.groupby('year').max().sort_values(by=colname, ascending=False)

            colname = parse_name(colname)
            if colname == 'Runoff Volume':
                colname = 'Runoff'
            elif colname == 'Peak Runoff':
                colname = 'Peak Discharge'

            results[colname] = {}

            for retperiod, indx in rec.items():
                _row = dict(df2.iloc[indx])

                row = {}
                for k, v in _row.items():
                    cname = k.split('(')[0].strip()

                    if cname == 'Runoff Volume':
                        cname = 'Runoff'

                    if cname == 'Peak Runoff':
                        cname = 'Peak Discharge'

                    row[cname] = v

                row['Runoff'] = round(row['Runoff'] / (wsarea * 10000.0) * 1000.0, 2)
                row['weibull_rank'] = indx + 1
                row['weibull_T'] = ((len(df) + 1) / (indx + 1)) / days_in_year  # T = (n + 1)  / m, where m is the rank and n is the number of observations
                row['Sediment Yield'] /= 1000.0

                results[colname][retperiod] = row

        self.return_periods = results
        self.num_events = df.shape[0]
        self.intervals = sorted(rec.keys())
        self.units_d = ebe.units_d
        self.units_d['10-min Peak Rainfall Intensity'] = 'mm/hour'
        if '15-min Peak Rainfall Intensity (mm/hour)' in cli_df:
            self.units_d['15-min Peak Rainfall Intensity'] = 'mm/hour'
        self.units_d['30-min Peak Rainfall Intensity'] = 'mm/hour'
        self.units_d['Peak Discharge'] = 'm^3/s'
        self.units_d['Sediment Yield'] = 'tonne'
        self.units_d['Storm Duration'] = 'hours'
        self.units_d['Hill Sed Del'] = 'tonne'
        self.units_d['Hill Streamflow'] = 'mm'

    def to_dict(self):
        return {
            'has_phosphorus': self.has_phosphorus,
            'header': self.header,
            'method': self.method,
            'gringorten_correction': self.gringorten_correction,
            'y0': self.y0,
            'years': self.years,
            'wsarea': self.wsarea,
            'recurrence': self.recurrence,
            'return_periods': self.return_periods,
            'num_events': self.num_events,
            'intervals': self.intervals,
            'units_d': self.units_d,
            'exclude_yr_indxs': self.exclude_yr_indxs
        }

    def export_tsv_summary(self, summary_path, extraneous=False):
        """
        Export the return periods summary to a TSV file.

        Args:
            summary_path (str): Path to save the TSV file.
        """

        if extraneous:
            self._export_tsv_summary_extraneous(summary_path)
        else:
            self._export_tsv_summary_simple(summary_path)

    def _export_tsv_summary_simple(self, summary_path):
        """
        Export the return periods summary to a TSV file.

        Args:
            summary_path (str): Path to save the TSV file.
        """
        with open(summary_path, 'w', encoding='utf-8') as f:
            # Write simulation summary
            f.write("WEPPcloud Return Period Analysis\n")
            f.write(f"Years in Simulation\t{self.years}\n")
            f.write(f"Events in Simulation\t{self.num_events}\n")
            if self.exclude_yr_indxs:
                f.write(f"Excluded Year Indexes\t{', '.join(map(str, self.exclude_yr_indxs))}\n")
                
            if self.gringorten_correction:
                f.write(f"Using Gringorten Correction for Weibull fomula\n")

            f.write("\n")

            # Define measures to include
            measures = [
                'Precipitation Depth',
                'Runoff',
                'Peak Discharge',
                '10-min Peak Rainfall Intensity',
                '15-min Peak Rainfall Intensity',
                '30-min Peak Rainfall Intensity',
                'Sediment Yield'
            ]
            if self.has_phosphorus:
                measures.extend(['Soluble Reactive P', 'Particulate P', 'Total P'])

            # Write tables for each measure
            for key in measures:
                if key in self.return_periods:
                    # Write table header
                    f.write(f"{key}\n")
                    header = ["Recurrence Interval (years)", "Date (mm/dd/yyyy)", f"{key} ({self.units_d.get(key, '')})"]
                    f.write("\t".join(header) + "\n")
                    
                    # Write table rows
                    for rec_interval in sorted(self.intervals, reverse=True):
                        data = self.return_periods[key][rec_interval]
                        date = f"{int(data['mo']):02d}/{int(data['da']):02d}/{int(data['year'] + self.y0 - 1):04d}"
                        value = f"{data[key]:.2f}"
                        row = [str(rec_interval), date, value]
                        f.write("\t".join(row) + "\n")
                    f.write("\n")

    def _export_tsv_summary_extraneous(self, summary_path):
        """
        Export the return periods summary with extraneous variables to a TSV file.

        Args:
            summary_path (str): Path to save the TSV file.
        """
        with open(summary_path, 'w', encoding='utf-8') as f:
            # Write simulation summary
            f.write("WEPPcloud Return Period Analysis\n")
            f.write(f"Years in Simulation\t{self.years}\n")
            f.write(f"Events in Simulation\t{self.num_events}\n")
            if self.exclude_yr_indxs:
                f.write(f"Excluded Year Indexes\t{', '.join(map(str, self.exclude_yr_indxs))}\n")
            else:
                f.write("Excluded Year Indexes\tNone\n")
            f.write("\n")

            # Define measures to include
            measures = [
                'Precipitation Depth',
                'Runoff',
                'Peak Discharge',
                '10-min Peak Rainfall Intensity',
                '15-min Peak Rainfall Intensity',
                '30-min Peak Rainfall Intensity',
                'Sediment Yield'
            ]
            if self.has_phosphorus:
                measures.extend(['Soluble Reactive P', 'Particulate P', 'Total P'])

            # Write tables for each measure
            for miar in measures:
                if miar in self.return_periods:
                    # Write table header
                    f.write(f"{miar}\n")
                    headers = [
                        "Recurrence Interval (years)",
                        "Date (mm/dd/yyyy)",
                        f"Precipitation Depth ({self.units_d.get('Precipitation Depth', 'mm')})",
                        f"Runoff ({self.units_d.get('Runoff', '')})",
                        f"Peak Discharge ({self.units_d.get('Peak Discharge', '')})"
                    ]
                    if '10-min Peak Rainfall Intensity' in self.return_periods:
                        headers.append(f"10-min Peak Rainfall Intensity ({self.units_d.get('10-min Peak Rainfall Intensity', '')})")
                    if '15-min Peak Rainfall Intensity' in self.return_periods:
                        headers.append(f"15-min Peak Rainfall Intensity ({self.units_d.get('15-min Peak Rainfall Intensity', '')})")
                    if '30-min Peak Rainfall Intensity' in self.return_periods:
                        headers.append(f"30-min Peak Rainfall Intensity ({self.units_d.get('30-min Peak Rainfall Intensity', '')})")
                    if 'Storm Duration' in self.return_periods:
                        headers.append(f"Storm Duration ({self.units_d.get('Storm Duration', '')})")
                    headers.append(f"Sediment Yield ({self.units_d.get('Sediment Yield', '')})")
                    if self.has_phosphorus:
                        headers.extend([
                            f"Soluble Reactive P ({self.units_d.get('Soluble Reactive P', '')})",
                            f"Particulate P ({self.units_d.get('Particulate P', '')})",
                            f"Total P ({self.units_d.get('Total P', '')})"
                        ])
                    headers.extend(["Rank", "Weibull T"])
                    f.write("\t".join(headers) + "\n")

                    # Write table rows
                    for rec_interval in sorted(self.intervals, reverse=True):
                        data = self.return_periods[miar][rec_interval]
                        date = f"{int(data['mo']):02d}/{int(data['da']):02d}/{int(data['year'] + self.y0 - 1):04d}"
                        row = [
                            str(rec_interval),
                            date,
                            f"{data.get('Precipitation Depth', 0):.2f}",
                            f"{data.get('Runoff', 0):.2f}",
                            f"{data.get('Peak Discharge', 0):.2f}"
                        ]
                        if '10-min Peak Rainfall Intensity' in self.return_periods:
                            row.append(f"{data.get('10-min Peak Rainfall Intensity', 0):.2f}")
                        if '15-min Peak Rainfall Intensity' in self.return_periods:
                            row.append(f"{data.get('15-min Peak Rainfall Intensity', 0):.2f}")
                        if '30-min Peak Rainfall Intensity' in self.return_periods:
                            row.append(f"{data.get('30-min Peak Rainfall Intensity', 0):.2f}")
                        if 'Storm Duration' in self.return_periods:
                            row.append(f"{data.get('Storm Duration', 0):.2f}")
                        row.append(f"{data.get('Sediment Yield', 0):.2f}")
                        if self.has_phosphorus:
                            row.extend([
                                f"{data.get('Soluble Reactive P', 0):.2f}",
                                f"{data.get('Particulate P', 0):.2f}",
                                f"{data.get('Total P', 0):.2f}"
                            ])
                        row.extend([
                            str(data.get('weibull_rank', '')),
                            f"{data.get('weibull_T', 0):.2f}"
                        ])
                        f.write("\t".join(row) + "\n")
                    f.write("\n")

    @classmethod
    def from_dict(cls, data):
        rp = cls()

        rp.has_phosphorus = data['has_phosphorus']
        rp.header = data['header']
        rp.method = data['method']
        rp.gringorten_correction = data['gringorten_correction']
        rp.y0 = data['y0']
        rp.years = data['years']
        rp.wsarea = data['wsarea']
        rp.recurrence = data['recurrence']
        rp.num_events = data['num_events']
        rp.intervals = data['intervals']
        rp.units_d = data['units_d']
        rp.exclude_yr_indxs = data.get('exclude_yr_indxs', None)

        ret_periods = data['return_periods']
        rp.return_periods = {}
        for measure in ret_periods:
            rp.return_periods[measure] = {}
            for rec, row in ret_periods[measure].items():
                rp.return_periods[measure][int(rec)] = row

        return rp

if __name__ == "__main__":
    from pprint import  pprint

    loss_rpt = Loss('/home/weppdev/PycharmProjects/wepppy/wepppy/wepp/out/test/data/ww2output.txt')
    ebe_rpt = Ebe('/home/weppdev/PycharmProjects/wepppy/wepppy/wepp/out/test/data/ww2events.txt')

    ret_rpt = ReturnPeriods(ebe_rpt, loss_rpt)

    print(ret_rpt.return_periods)
    print(ret_rpt.intervals)
