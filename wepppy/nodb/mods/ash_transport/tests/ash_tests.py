import sys
import os
from pprint import pprint

from os.path import join as _join
from os.path import exists as _exists

sys.path.append("/home/roger/wepppy")

from wepppy.all_your_base.dateutils import YearlessDate
from wepppy.nodb.mods.ash_transport.neris_ash_model import WhiteAshModel, BlackAshModel

from wepppy.climates.cligen import ClimateFile
from wepppy.wepp.out import Element, HillWat

_thisdir = os.path.dirname(__file__)
_data_dir = _join(_thisdir, "data")


cli = ClimateFile("/wc1/runs/ri/rigid-self-education/wepp/runs/p32.cli")
cli_df = cli.as_dataframe()

element = Element("/wc1/runs/ri/rigid-self-education/wepp/output/H32.element.dat")
element_d = element.d

hill_wat = HillWat("/wc1/runs/ri/rigid-self-education/wepp/output/H32.wat.dat")

fire_date = YearlessDate(8, 4)

black_ash = BlackAshModel()
black_ash.ini_ash_depth_mm = 5.0
pprint(
    black_ash.run_model(
        fire_date=fire_date,
        element_d=element_d,
        cli_df=cli_df,
        hill_wat=hill_wat,
        out_dir="out",
        prefix="black",
        ini_ash_depth=5.0,
        run_wind_transport=False,
    )
)
white_ash = WhiteAshModel()
white_ash.ini_ash_depth_mm = 5.0
pprint(
    white_ash.run_model(
        fire_date=fire_date,
        element_d=element_d,
        cli_df=cli_df,
        hill_wat=hill_wat,
        out_dir="out",
        prefix="white",
        ini_ash_depth=5.0,
        run_wind_transport=False,
    )
)
