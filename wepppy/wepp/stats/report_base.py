# Copyright (c) 2016-2018, University of Idaho
# All rights reserved.
#
# Roger Lew (rogerlew@gmail.com)
#
# The project described was supported by NSF award number IIA-1301792
# from the NSF Idaho EPSCoR Program and by the National Science Foundation.

import csv

import pandas as pd

from wepppy.wepp.stats.row_data import parse_name, parse_units


class ReportBase(object):
    header = []

    @property
    def hdr(self):
        for colname in self.header:
            yield parse_name(colname)

    @property
    def units(self):
        for colname in self.header:
            yield parse_units(colname)

    @property
    def hdr_units_zip(self):
        for colname in self.header:
            yield parse_name(colname), parse_units(colname)

    def write(self, fp, write_header=True, run_descriptors=None):

        wtr = csv.writer(fp)

        if write_header:
            hdr = []

            for cname, units in zip(self.hdr, self.units):
                hdr.append(cname)
                if units is not None:
                    units = units.split(',')[0]
                    hdr[-1] += ' (%s)' % units

            if run_descriptors is not None:
                hdr = [cname for cname, desc in run_descriptors] + hdr

            wtr.writerow(hdr)

        for row in self:
            data = [value for value, units in row]
            if run_descriptors is not None:
                data = [desc for cname, desc in run_descriptors] + data
            wtr.writerow(data)

    def to_dataframe(self, fp=None, write_header=True, run_descriptors=None, **to_parquet_kwargs):
        """
        Write the report to a Parquet file or buffer.

        Parameters
        ----------
        fp : str or file-like
            Path to output file (e.g. 'report.parquet') or a buffer.
        write_header : bool, optional
            If False, skips prepending descriptor columns.
        run_descriptors : list of (name, value), optional
            Any leading columns to prepend (same semantics as write()).
        **to_parquet_kwargs
            Passed through to pandas.DataFrame.to_parquet().
        """
        # build the display column names
        base_cols = list(self.header)  # e.g. ['Area', 'Sediment Yield', …]
        units    = list(self.units)   # e.g. ['ha', 'kg/ha', …]
        cols_with_units = []
        for name, unit in zip(base_cols, units):
            if unit:
                short = unit.split(',')[0]
                cols_with_units.append(f"{name} ({short})")
            else:
                cols_with_units.append(name)

        # if run_descriptors supplied, extract their names
        if write_header and run_descriptors:
            desc_names = [c for c, _ in run_descriptors]
            cols_full = desc_names + cols_with_units
        else:
            cols_full = cols_with_units

        # collect all rows into a list of dicts
        records = []
        for row in self:
            vals = [value for value, _ in row]
            if write_header and run_descriptors:
                desc_vals = [v for _, v in run_descriptors]
                vals = desc_vals + vals
            records.append(dict(zip(cols_full, vals)))

        # build DataFrame and write
        df = pd.DataFrame(records, columns=cols_full)

        if fp is not None:
            df.to_parquet(fp, **to_parquet_kwargs)

        return df