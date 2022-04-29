from glob import glob
from os.path import split as _split

with open('salvage-north_star_2m.cfg.template') as fp:
    _template = fp.read()

fns = glob('/geodata/salvage_logging/north_star/NorthStar_DEM_2m,*.tif')
for fn in fns:
    if '.mask' in fn:
        continue
    fn0, fn1 = _split(fn)
    cond = fn1.replace('NorthStar_DEM_', '').replace('.tif', '')
    print(fn, cond)
    with open(f'salvage-north_star_{cond}.cfg', 'w') as pf:
        pf.write(_template.format(cond=cond))
        
    
