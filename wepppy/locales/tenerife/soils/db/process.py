from glob import glob

from wepppy.wepp.soils.utils import WeppSoilUtil

sols = glob('*.template.sol')

for sol in sols:
#    print(sol)
    wsu = WeppSoilUtil(sol, compute_erodibilities=True, compute_conductivity=False)
    wsu7778 = wsu.to7778()
    wsu7778.write(sol.replace('.template.sol', '.sol'))
    

