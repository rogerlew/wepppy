import sys
import os
from pprint import pprint

from os.path import join as _join
from os.path import exists as _exists

sys.path.append('/Users/roger/src/wepppy-neris-ash/')

from wepppy.all_your_base.dateutils import YearlessDate
from wepppy.nodb.mods.ash_transport import WhiteAshModel, BlackAshModel

from wepppy.climates.cligen import ClimateFile
from wepppy.wepp.out import Element, HillWat

_thisdir = os.path.dirname(__file__)
_data_dir = _join(_thisdir, 'data')


cli = ClimateFile('/Users/roger/runs/rlew-expressed-barometer/wepp/runs/p1.cli')
cli_df = cli.as_dataframe()

element = Element('/Users/roger/runs/rlew-expressed-barometer/wepp/output/H1.element.dat')
element_d = element.d

hill_wat = HillWat('/Users/roger/runs/rlew-expressed-barometer/wepp/output/H1.wat.dat')

fire_date = YearlessDate(8, 4)

black_ash = BlackAshModel()
pprint(black_ash.run_model(fire_date, element_d, cli_df, hill_wat, 'out', 'black', ini_ash_depth=5.0))

white_ash = WhiteAshModel()
white_ash.run_model(fire_date, element_d, cli_df, hill_wat, 'out', 'white', ini_ash_depth=5.0)
