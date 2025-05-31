from os.path import join as _join
from os.path import exists as _exists
from datetime import datetime, timedelta
from glob import glob
from collections import OrderedDict
import numpy as np
import os
import pandas as pd
from deprecated import deprecated

def _float(x):
    try:
        return float(x)
    except ValueError:
        return None

class HillSoil:
    def __init__(self, fname):
        assert _exists(fname), f"File not found: {fname}"

        self.fname = fname

        # Read datafile
        with open(self.fname) as f:
            lines = [L.strip() for L in f.readlines()]

        if 'daily output' not in lines[0]:
            raise NotImplementedError(
                f"Expected 'daily output' in the first line of {fname}, but found: {lines[0]}"
            )
        
        # Define headers, units, and types
        header = ['OFE', 'Day', 'Y', 'Poros', 'Keff', 'Suct', 'FC', 'WP', 'Rough', 'Ki', 'Kr', 'Tauc', 'Saturation', 'TSW']
        units = ['', '', '', '%', 'mm/hr', 'mm', 'mm/mm', 'mm/mm', 'mm', 'adjsmt', 'adjsmt', 'adjsmt', 'frac', 'mm']
        _types = [int, int, int, try_parse_float, try_parse_float, try_parse_float, try_parse_float, 
                  try_parse_float, try_parse_float, try_parse_float, try_parse_float, try_parse_float, 
                  try_parse_float, try_parse_float]

        # Initialize empty DataFrame
        df = pd.DataFrame(columns=header)
        
        # Parse data lines (skip header and separator lines)
        data_rows = []
        for L in lines[3:]:  # Skip first 3 lines (title, separator, units)
            if L and not L.startswith('----'):  # Ignore empty or separator lines
                values = L.split()
                if len(values) == len(header):
                    # Convert values to appropriate types
                    row = {key: _type(v) for key, v, _type in zip(header, values, _types)}
                    data_rows.append(row)
        
        # Populate DataFrame
        if data_rows:
            df = pd.DataFrame(data_rows, columns=header)
        
        self.df = df
