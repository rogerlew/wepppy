from glob import glob
import csv
import os

from os.path import split as _split

from wepppy.wepp.soils.utils import WeppSoilUtil

def parse_og_sol_name(fn):
    _fn = fn[1:]
    
    road_surface = 'RoadSurface.Natural'
    if _fn.startswith('p'):
        road_surface = 'RoadSurface.Paved'
        _fn = _fn[1:]

    elif _fn.startswith('g'):
        road_surface = 'RoadSurface.Gravel'
        _fn = _fn[1:]

    soil_texture = None
    if 'clay' in _fn:
        soil_texture = 'SoilTexture.Clay'
    elif 'sand' in fn:
        soil_texture = 'SoilTexture.Sand' 
    elif 'silt' in fn:
        soil_texture = 'SoilTexture.Silt' 
    elif 'loam' in fn:
        soil_texture = 'SoilTexture.Loam' 

    assert soil_texture is not None
    _fn = _fn[4:-4]

    tauc = _fn

    return road_surface, soil_texture, tauc

if __name__ == "__main__":
    os.chdir('../')
    sol_fns = glob('og/*.sol')

    for sol_fn in sol_fns:
       head, tail = _split(sol_fn)

       wsu = WeppSoilUtil(sol_fn)
       new = wsu.to7778()

       road_surface, soil_texture, tauc = parse_og_sol_name(tail)
       new_fn = f'3_{road_surface}_{soil_texture}_{tauc}.sol'
       new.write(new_fn)


