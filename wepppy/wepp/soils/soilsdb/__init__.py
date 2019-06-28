import os
from os.path import join as _join
from os.path import exists as _exists
from glob import glob

from wepppy.wepp.soils.utils import YamlSoil


_thisdir = os.path.dirname(__file__)
_data_dir = _join(_thisdir, 'data')


def load_db():
    sols = glob(_join(_data_dir, '*/*.sol'))
    # sols.extend(glob(_join(_data_dir, '*/*/*.sol')))
    sols = [os.path.relpath(sol, _data_dir) for sol in sols]
    return sols


def get_soil(sol):
    path = _join(os.path.abspath(_data_dir), sol)
    assert _exists(path)
    return path


def read_disturbed_wepp_soil_fire_pars(simple_texture, fire_severity):
    fn = None
    if simple_texture == 'silt loam':
        if fire_severity == 'high':
            fn = _join(_data_dir, 'Forest', 'High sev fire-silt loam.sol')
        else:
            fn = _join(_data_dir, 'Forest', 'Low sev fire-silt loam.sol')
    elif simple_texture == 'loam':
        if fire_severity == 'high':
            fn = _join(_data_dir, 'Forest', 'High sev fire-loam.sol')
        else:
            fn = _join(_data_dir, 'Forest', 'Low sev fire-loam.sol')
    elif simple_texture == 'sand loam':
        if fire_severity == 'high':
            fn = _join(_data_dir, 'Forest', 'High sev fire-sandy loam.sol')
        else:
            fn = _join(_data_dir, 'Forest', 'Low sev fire-sandy loam.sol')
    elif simple_texture == 'clay loam':
        if fire_severity == 'high':
            fn = _join(_data_dir, 'Forest', 'High sev fire-clay loam.sol')
        else:
            fn = _join(_data_dir, 'Forest', 'Low sev fire-clay loam.sol')

    assert fn is not None
    assert _exists(fn)

    yaml_soil = YamlSoil(fn)

    return yaml_soil.obj['ofes'][0]


if __name__ == "__main__":
    print(load_db())
