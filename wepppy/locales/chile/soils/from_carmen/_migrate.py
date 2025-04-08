from os.path import split as _split
from os.path import join as _join

from glob import glob
from wepppy.wepp.soils.utils import WeppSoilUtil

for sol_fn in glob('*.sol'):
    print(sol_fn)

    wsu = WeppSoilUtil(sol_fn, compute_erodibilities=True, compute_conductivity=True)
    wsu7778 = wsu.to7778()

    wsu7778.write(_join('..', _split(sol_fn)[-1]))
    