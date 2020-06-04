import os
from os.path import exists as _exists
import shutil

from wepppy.soils.ssurgo import SurgoSoilCollection, StatsgoSpatial

statsgo_mukeys = [403924]
surgo_c = SurgoSoilCollection(statsgo_mukeys, use_statsgo=True)
surgo_c.makeWeppSoils()

surgo_c.writeWeppSoils('soils', write_logs=True, version='2006.2')