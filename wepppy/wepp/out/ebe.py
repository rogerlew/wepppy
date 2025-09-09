# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

from os.path import split as _split

from datetime import datetime

import json
import pandas as pd

import pyarrow as pa
import pyarrow.parquet as pq

from wepppy.wepp.out import Loss
from wepppy.topo.watershed_abstraction import WeppTopTranslator


def _get_lines(fn):
    # read the loss report
    with open(fn) as fp:
        lines = fp.readlines()

    # strip trailing and leading white space
    lines = [L.strip() for L in lines]

    lines = [L for L in lines if L != '']

    i0 = 0
    for i0, L in enumerate(lines):
        if L.startswith('---'):
            break

    return lines[i0 + 1:]


class HillslopeEbe(object):
    def __init__(self, fn):
        self.fn = fn

        if _exists(self.parquet_fn):
            self._load_parquet()
        else:
            self._parse()
            self.to_parquet()


    def _parse(self):
        fn = self.fn
        lines = _get_lines(fn)

        header = ['da', 'mo', 'year',
                  'Precipitation Depth (mm)', 
                  'Runoff Depth (mm)',
                  'IR-det (kg/m^2)', 
                  'Av-det (kg/m^2)', 
                  'Mx-det (kg/m^2)',
                  'Point0 (m)',
                  'Av-dep (kg/m^2)', 
                  'Max-dep (kg/m^2)',
                  'Point1 (m)', 
                  'Sed.Del (kg/m^2)', 
                  'ER (kg/m^2)']

        units = [int, int, int, float, float, float, float, float, float, float, float, float, float, float]

        data = [[u(v) for v, u in zip(L.split(), units)] for L in lines]

        if data == []:
            raise Exception('{} contains no data'.format(fn))

        df = pd.DataFrame()
        for L, colname in zip(data, header):
            df[colname] = L

        wepp_id = _split(fn)[-1].split('.')[0]

        assert wepp_id.startswith('H')
        self.wepp_id = wepp_id[1:]
        self.df = df
        self.header = header

    @property
    def parquet_fn(self):
        return self.fn.replace('.dat', '.parquet')

    def to_parquet(self):
        # Convert the pandas DataFrame to an arrow Table
        table = pa.Table.from_pandas(self.df)

        metadata = {'wepp_id': self.wepp_id}
        metadata_bytes = {bytes(k, 'utf-8'): bytes(json.dumps(v), 'utf-8') for k, v in metadata.items()}
        table = table.replace_schema_metadata(metadata_bytes)

        # Write the table to a Parquet file
        pq.write_table(table, self.parquet_fn)

    def _load_parquet(self):
        table = pq.read_table(self.parquet_fn)
        self.df = table.to_pandas()
        self.wepp_id = table.schema.metadata[b'wepp_id'].decode('utf-8')
        self.header = list(self.df.columns)


class Ebe(object):
    def __init__(self, fn, wepp_top_translator: WeppTopTranslator = None):
        self.fn = fn

        if _exists(self.parquet_fn):
            self._load_parquet()
        else:
            self._parse(wepp_top_translator)
            self.to_parquet()

    def _parse(self, wepp_top_translator):
        lines = _get_lines(self.fn)

        header = ['da', 'mo', 'year',
                  'Precipitation Depth (mm)',
                  'Runoff Volume (m^3)',
                  'Peak Runoff (m^3/s)',
                  'Sediment Yield (kg)',
                  'Soluble Reactive P (kg)',
                  'Particulate P (kg)',
                  'Total P (kg)',
                  'WeppID']

        units = [int, int, int, float, float, float, float, float, float, float, int]

        data = [[u(v) for v, u in zip(L.split(), units)] for L in lines]
        data = list(map(list, zip(*data)))

        if data == []:
            raise Exception('{} contains no data'.format(self.fn))

        df = pd.DataFrame()
        for L, colname in zip(data, header):
            df[colname] = L

        df['Sed. Del (kg)'] = df['Sediment Yield (kg)']

        if wepp_top_translator is not None and 'WeppID' in df.columns:
            header.append('TopazID')
            df['TopazID'] = df['WeppID'].apply(wepp_top_translator.top)

        self.df = df
        self.years = len(set(df['year']))
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

    @property
    def parquet_fn(self):
        return self.fn.replace('.txt', '.parquet')

    def to_parquet(self):
        self.df.to_parquet(self.parquet_fn)

    def _load_parquet(self):
        self.df = pd.read_parquet(self.parquet_fn)
        self.years = len(set(self.df['year']))
        self.header = list(self.df.columns)
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
    import os
    from time import time
    from os.path import exists as _exists

    from wepppy.nodb import Watershed

    translator = Watershed.getInstanceFromRunID('rlew-confirmed-complementarity/').translator_factory()

    ebe_fn = '/wc1/runs/rl/rlew-confirmed-complementarity/wepp/output/ebe_pw0.txt'
    ebe_parquet = ebe_fn.replace('.txt', '.parquet')
    times = []
    for i in range(10):
        if _exists(ebe_parquet):
            os.remove(ebe_parquet)

        t0 = time()
        ebe = Ebe(ebe_fn, wepp_top_translator=translator)
        elapsed = time() - t0
        times.append(elapsed)

    print(f'Average time to read and convert EBE: {sum(times) / len(times):.3f} seconds')


    times = []
    for i in range(10):

        t0 = time()
        ebe2 = Ebe(ebe_fn, wepp_top_translator=translator)
        elapsed = time() - t0
        times.append(elapsed)

    print(f'Average time to read EBE from parquet: {sum(times) / len(times):.3f} seconds')

    print(ebe.years, ebe2.years)
    print(ebe.header, ebe2.header)
    