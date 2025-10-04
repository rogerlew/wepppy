# parser for wepp chan.out files

import pandas as pd
import pyarrow as pa
import pyarrow.parquet as pq
import json
import os
from os.path import split as _split
from os.path import exists as _exists
from os.path import join as _join
from datetime import date, timedelta

from wepppy.topo.watershed_abstraction import WeppTopTranslator

""" 
 Channel Routing Output
   Muskingum-Cunge method

Peak Flow Time and Rate

  Year    Day   Elmt_ID Chan_ID  Time(s) Peak_Discharge(m^3/s)
     1      1     95     19         60.      8.02E-02
     1      1     98     22         60.      2.23E-02
     1      1    107     31        840.      2.71E-01
     1      2     95     19        240.      1.41E-01
     1      2     98     22       1080.      3.90E-02
     1      2    107     31       1020.      4.79E-01
     1      3     95     19        240.      1.91E-01
     1      3     98     22        780.      5.58E-02
     1      3    107     31        480.      6.72E-01
     1      4     95     19        240.      2.28E-01
     1      4     98     22        120.      5.66E-02
     1      4    107     31        420.      7.89E-01
     1      5     95     19         60.      2.23E-01
     1      5     98     22         60.      4.95E-02
     1      5    107     31         60.      7.85E-01
     1      6     95     19         60.      2.07E-01
     1      6     98     22         60.      4.18E-02
     1      6    107     31         60.      7.34E-01
     1      7     95     19         60.      1.72E-01
     1      7     98     22         60.      3.36E-02
     1      7    107     31         60.      6.18E-01
     1      8     95     19         60.      1.43E-01
     1      8     98     22         60.      2.74E-02
     1      8    107     31         60.      5.26E-01
     1      9     95     19         60.      1.20E-01
     1      9     98     22         60.      2.29E-02
     1      9    107     31         60.      4.49E-01
     1     10     95     19         60.      1.02E-01
     1     10     98     22         60.      1.95E-02
     1     10    107     31         60.      3.88E-01
     1     11     95     19         60.      8.69E-02
     1     11     98     22         60.      1.68E-02
     1     11    107     31         60.      3.39E-01
...
"""

def _get_lines(fn):
    with open(fn, 'r') as f:
        lines = f.readlines()

    lines = [L.strip() for L in lines]
    assert lines[0].startswith('Channel Routing Output'), f'"{lines[0]}"'
    assert lines[1].startswith('Muskingum-Cunge method'), f'"{lines[1]}"'
    assert lines[2] == '', f'"{lines[2]}"'
    assert lines[3].startswith('Peak Flow Time and Rate'), f'"{lines[3]}"'
    assert lines[4] == '', f'"{lines[4]}"'
    assert lines[5].startswith('Year    Day   Elmt_ID Chan_ID  Time(s) Peak_Discharge(m^3/s)'), f'"{lines[5]}"'

    return lines[7:]


class ChanOut:
    def __init__(self, fn, wepp_top_translator: WeppTopTranslator = None):
        self.fn = fn

        if _exists(self.parquet_fn):
            self._load_parquet()
            return
        else:
            self._parse(fn, wepp_top_translator)
            self.to_parquet()

    @property
    def parquet_fn(self):
        return self.fn.replace('.out', '.parquet')

    def _parse(self, fn, wepp_top_translator):
        lines = _get_lines(fn)

        is_gregorian = int(lines[0].split()[0]) > 1900

        header = ['yr', 'jd', 'WeppID', 'ChanEnum', 'Time(s)', 'Peak_Discharge(m^3/s)', 'mo', 'da']
        units = [int,   int,  int,      int,        float,       float]
        n_header = len(header) - 2  # minus mo, da

        data = []
        for line in lines:
            values = line.split()
            n_values = len(values)
            assert n_values == n_header, f'Expected {n_header} values, got {n_values}: {line}'
            for i, (value, unit) in enumerate(zip(values, units)):
                if unit == int:
                    value = int(value)
                elif unit == float:
                    value = float(value)
                values[i] = value

            if is_gregorian:
                _date = date(values[0], 1, 1) + timedelta(days=values[1]-1)
            else:
                _date = date(2001, 1, 1) + timedelta(days=values[1]-1)

            values.append(_date.month)
            values.append(_date.day)
                
            data.append(values)

        df = pd.DataFrame(data, columns=header)

        if wepp_top_translator is not None:
            header.append('TopazID')
            df['TopazID'] = df['WeppID'].apply(wepp_top_translator.top)

        self.df = df

    def to_parquet(self):
        self.df.to_parquet(self.parquet_fn)

    def _load_parquet(self):
        self.df = pd.read_parquet(self.parquet_fn)

    def to_dss(self, fn: str):
        """
        Exports the peak flow data to a HEC-DSS file as an irregular time-series.
        Each channel (identified by TopazID or ChanEnum) is saved as a separate 
        record in the DSS file.

        Args:
            fn (str): The path to the output DSS file. The file will be created 
                      if it does not exist.
        """
        from datetime import datetime, timedelta
        from pydsstools.heclib.dss import HecDss
        from pydsstools.core import TimeSeriesContainer

        # Determine which column to use for the channel identifier.
        # Prioritize 'TopazID' as it is the channel ID.
        if 'TopazID' in self.df.columns:
            id_col = 'TopazID'
        else:
            id_col = 'ChanEnum'

        # Group the DataFrame by each unique channel identifier
        grouped_by_channel = self.df.groupby(id_col)

        # Open the DSS file once to write all records
        with HecDss.Open(fn) as fid:
            # Iterate over each channel's data
            for chn_id, group_df in grouped_by_channel:
                
                # Make a copy to safely add a new column
                df = group_df.copy()

                # Create a 'datetime' column by combining year, julian day, and time in seconds
                df['datetime'] = df.apply(
                    lambda row: datetime(int(row['yr']), 1, 1) +
                                timedelta(days=int(row['jd']) - 1, seconds=int(row['Time(s)'])),
                    axis=1
                )

                # Prepare the values and corresponding timestamps for the DSS record
                values = df['Peak_Discharge(m^3/s)'].to_list()
                times = df['datetime'].to_list()

                # Configure the TimeSeriesContainer for irregular time-series data
                tsc = TimeSeriesContainer()
                
                # DSS Pathname Parts: /A/B/C/D/E/F/
                # A: Project -> WEPP
                # B: Version -> CHAN-OUT
                # C: Parameter -> PEAK-FLOW
                # D: Time Window -> IR-YEAR (Irregular Yearly)
                # E: Interval -> Blank for irregular data
                # F: Location -> Channel ID
                tsc.pathname = f"/WEPP/CHAN-OUT/PEAK-FLOW//IR-YEAR/{chn_id}/"
                
                tsc.times = times
                tsc.values = values
                tsc.numberValues = len(values)
                tsc.units = "M3/S"  # Cubic Meters per Second
                tsc.type = "INST"   # Instantaneous values
                tsc.interval = -1   # An interval <= 0 signifies irregular time-series

                # Write the time-series record to the DSS file
                fid.put_ts(tsc)


def chanout_dss_export(wd, status_channel=None):
    """
    Exports 
    """
    from wepppy.nodb.status_messenger import StatusMessenger
    from wepppy.nodb.core import Watershed

    watershed = Watershed.getInstance(wd)
    translator = watershed.translator_factory()
    dss_export_dir = _join(wd, 'export/dss')

    chan_out = _join(wd, 'wepp/output/chan.out')
    if not _exists(chan_out):
        raise FileNotFoundError(f'chan.out not found: {chan_out}')
    
    chan_dss = _join(dss_export_dir, 'chan.dss')

    if _exists(chan_dss):
        if status_channel is not None:
            StatusMessenger.publish(status_channel, 'cleaning export/dss/chan.dss\n')
        os.remove(chan_dss)

    if status_channel is not None:
        StatusMessenger.publish(status_channel, 'chanout_dss_export()...\n')

    if not _exists(dss_export_dir):
        os.makedirs(dss_export_dir, exist_ok=True)

    chan = ChanOut(chan_out, wepp_top_translator=translator)
    chan.to_dss(chan_dss)


if __name__ == "__main__":
    import os
    from time import time
    from os.path import exists as _exists

    from wepppy.nodb.core import Watershed

    translator = Watershed.getInstanceFromRunID('rlew-confirmed-complementarity/').translator_factory()

    chan_out = '/wc1/runs/rl/rlew-confirmed-complementarity/wepp/output/chan.out'
    chan_parquet = chan_out.replace('.out', '.parquet')
    times = []
    for i in range(10):
        if _exists(chan_parquet):
            os.remove(chan_parquet)

        t0 = time()
        chan = ChanOut(chan_out, wepp_top_translator=translator)
        elapsed = time() - t0
        times.append(elapsed)

    print(f'Average time to read and convert chan.out: {sum(times) / len(times):.3f} seconds')

    times = []
    for i in range(10):
        t0 = time()
        chan2 = ChanOut(chan_out, wepp_top_translator=translator)
        elapsed = time() - t0
        times.append(elapsed)

    print(f'Average time to read chan.out from parquet: {sum(times) / len(times):.3f} seconds')

    chan_dss = chan_out.replace('.out', '.dss')
    chan2.to_dss(chan_dss)
