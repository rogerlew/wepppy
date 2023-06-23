import os
from os.path import join as _join
from os.path import exists as _exists
from wepppy.nodb.mods import Ash

cfg_fn='/workdir/wepppy/wepppy/nodb/configs/disturbed9002.cfg'

def chmod_r(wd):
    os.system(f'chmod -R 777 {wd}')

if __name__ == '__main__':
    for run_id in (
            'srivas42-mountainous-misogyny',
            'srivas42-polymorphous-wok',
            'srivas42-domed-nuance',       # no ash
            'srivas42-perpendicular-gong', # no ash
            'srivas42-anxious-gannet',     # no ash
            'srivas42-coiling-grinding',
                   ):

        wd = _join('/geodata/weppcloud_runs', run_id)
        print(wd)
        chmod_r(wd)

        if _exists(_join(wd, 'ash.nodb')):
            os.remove(_join(wd, 'ash.nodb'))

        print('running ash')
        ash = Ash(wd, cfg_fn=cfg_fn)
        ash.run_ash()

