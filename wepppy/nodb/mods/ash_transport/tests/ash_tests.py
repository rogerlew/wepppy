import sys
import math
import csv
import os
import shutil
import enum
from pprint import pprint

from os.path import join as _join
from os.path import exists as _exists

sys.path.append('/home/roger/wepppy')

from wepppy.all_your_base import YearlessDate, weibull_series
from wepppy.nodb.mods.ash_transport import WhiteAshModel, BlackAshModel, lookup_wind_threshold_white_ash_proportion

from wepppy.climates.cligen import ClimateFile
from wepppy.wepp.out import Element

_thisdir = os.path.dirname(__file__)
_data_dir = _join(_thisdir, 'data')


cli = ClimateFile(_join('data/climateRAW.cli'))
cli_df = cli.as_dataframe()

element = Element(_join('data/peakroRAW.txt'))
element_d = element.d

fire_date = YearlessDate(8, 4)

black_ash = BlackAshModel()
black_ash.ini_ash_depth_mm = 5.0
pprint(black_ash.run_model(fire_date, element_d, cli_df, 'out', 'black'))

white_ash = WhiteAshModel()
white_ash.ini_ash_depth_mm = 5.0
white_ash.run_model(fire_date, element_d, cli_df, 'out', 'white')
