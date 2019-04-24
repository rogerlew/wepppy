import os
from os.path import join as _join
from os.path import exists as _exists
from glob import glob


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


if __name__ == "__main__":
    print(load_db())
