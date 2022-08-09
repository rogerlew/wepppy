from glob import glob
import csv

from wepppy.wepp.soils.utils import YamlSoil

def parse_sol_name(fn):
    _fn = fn[1:]
    
    road_surface = 'n'
    if _fn.startswith('p'):
        road_surface = 'p'
        _fn = _fn[1:]

    elif _fn.startswith('g'):
        road_surface = 'g'
        _fn = _fn[1:]

    soil_texture = None
    if _fn.startswith('clay'):
        soil_texture = 'clay'
    elif _fn.startswith('sand'):
        soil_texture = 'sand' 
    elif _fn.startswith('silt'):
        soil_texture = 'silt' 
    elif _fn.startswith('loam'):
        soil_texture = 'loam' 

    assert soil_texture is not None
    _fn = _fn[4:-4]

    tauc = _fn

    return dict(road_surface=road_surface, soil_texture=soil_texture, tauc=tauc)

if __name__ == "__main__":
    sol_fns = glob('*.sol')

    fp = None
    for sol_fn in sol_fns:
        print(sol_fn)

        yaml_soil = YamlSoil(sol_fn)

        for ofe in yaml_soil.obj['ofes']:
            horizons = ofe.pop('horizons')

            d = parse_sol_name(sol_fn)
            d.update(ofe)
            d.update(horizons[0])

            if fp is None:
                fp = open('wrbat_soil_parameters.csv', 'w')
                wtr = csv.DictWriter(fp, fieldnames=list(d.keys()))
                wtr.writeheader()

            wtr.writerow(d)

    fp.close()


