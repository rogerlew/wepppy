import os
from os.path import exists as _exists
import shutil

from wepppy.soils.ssurgo import SurgoSoilCollection, StatsgoSpatial

statsgo_mukeys = [403924]

print('building collection')
surgo_c = SurgoSoilCollection(statsgo_mukeys)  #, use_statsgo=True)

print('make WEPP soils')
surgo_c.makeWeppSoils()

print('write WEPP soils')
surgo_c.writeWeppSoils('soils', write_logs=True, version='2006.2')

print(surgo_c.invalidSoils.keys())
