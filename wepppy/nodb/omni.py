import os

from os.path import exists as _exists
from os.path import join as _join
from os.path import split as _split
from os.path import isdir

import json
import shutil

# non-standard
import jsonpickle
import utm
import what3words

# wepppy
import requests


from .base import (
    NoDbBase,
    TriggerEvents
)

def _omni_clone(scenario, wd):
    omni_dir = _join(wd, 'omni', 'scenarios', scenario.replace(' ', '_'))

    if _exists(omni_dir):
        shutil.rmtree(omni_dir)

    os.makedirs(omni_dir)

    for fn in os.listdir(wd):
        if fn in ['climate', 'dem', 'watershed', 'climate.nodb', 'dem.nodb', 'watershed.nodb']:
            src = _join(wd, fn)
            dst = _join(omni_dir, fn)
            if not _exists(dst):
                os.symlink(src, dst)

        elif fn.endswith('.nodb'):
            src = _join(wd, fn)
            dst = _join(omni_dir, fn)
            if not _exists(dst):
                shutil.copy(src, dst)

            with open(dst, 'r') as f:
                d = json.load(f)

            d['wd'] = omni_dir

            with open(dst, 'w') as f:
                json.dump(d, f)
    

    for fn in os.listdir(wd):
        if fn == 'omni':
            continue

        src = _join(wd, fn)
        if os.path.isdir(src):
            dst = _join(omni_dir, fn)

            if not _exists(dst):
                try:
                    # Create directory structure without copying files
                    for root, dirs, _ in os.walk(src):
                        for dir_name in dirs:
                            src_dir = _join(root, dir_name)
                            rel_path = os.path.relpath(src_dir, src)
                            dst_dir = _join(dst, rel_path)
                            if not _exists(dst_dir):
                                os.makedirs(dst_dir, exist_ok=True)
                except PermissionError as e:
                    print(f"Permission denied creating directory: {e}")
                except OSError as e:
                    print(f"Error creating directory: {e}")

            if not _exists(dst):
                os.makedirs(dst, exist_ok=True)

    return omni_dir


def _build_scenario(scenario, wd):
    from wepppy.nodb import Landuse, Soils, Wepp
    from wepppy.nodb.mods import Disturbed

    assert scenario in ['uniform low', 'uniform high', 'uniform moderate', 'uniform high', 'thinning']
    new_wd = _omni_clone(scenario, wd)


    if scenario == 'uniform low':
        value = 1
    elif scenario == 'uniform moderate':
        value = 2
    elif scenario == 'uniform high':
        value = 3

    disturbed = Disturbed.getInstance(new_wd)
    sbs_fn = disturbed.build_uniform_sbs(int(value))
    res = disturbed.validate(sbs_fn)

    landuse = Landuse.getInstance(new_wd)
    landuse.build()

    soils = Soils.getInstance(new_wd)
    soils.build()

    wepp = Wepp.getInstance(new_wd)
    wepp.prep_hillslopes()
    wepp.run_hillslopes()

    wepp.prep_watershed()
    wepp.run_watershed()







class Omni(NoDbBase):
    """
    Manager that keeps track of project details
    and coordinates access of NoDb instances.
    """
    __name__ = 'Omni'

    __exclude__ = ('_w3w', 
                   '_locales', 
                   '_enable_landuse_change',
                   '_dem_db',
                   '_boundary')

    def __init__(self, wd, cfg_fn='0.cfg'):
        super(Omni, self).__init__(wd, cfg_fn)

        self.lock()

        # noinspection PyBroadException
        try:
            
            if not _exists(self.omni_dir):
                os.makedirs(self.omni_dir)

            self._scenarios = self.config_get_list('omni', 'scenarios')

        except Exception:
            self.unlock('-f')
            raise

    @property
    def scenarios(self):
        return self._scenarios
    
    @scenarios.setter
    def scenarios(self, value):
        self._scenarios = value

    @property
    def omni_dir(self):
        return _join(self.wd, 'omni')

    #
    # Required for NoDbBase Subclass
    #

    # noinspection PyPep8Naming
    @staticmethod
    def getInstance(wd='.', allow_nonexistent=False, ignore_lock=False):
        filepath = _join(wd, 'Omni.nodb')

        if not _exists(filepath):
            if allow_nonexistent:
                return None
            else:
                raise FileNotFoundError(f"'{filepath}' not found!")

        with open(filepath) as fp:
            db = jsonpickle.decode(fp.read())
            assert isinstance(db, Omni), db

        if _exists(_join(wd, 'READONLY')) or ignore_lock:
            db.wd = os.path.abspath(wd)
            return db

        if os.path.abspath(wd) != os.path.abspath(db.wd):
            db.wd = wd
            db.lock()
            db.dump_and_unlock()

        return db

    @staticmethod
    def getInstanceFromRunID(runid, allow_nonexistent=False, ignore_lock=False):
        from wepppy.weppcloud.utils.helpers import get_wd
        return Omni.getInstance(
            get_wd(runid, allow_nonexistent=allow_nonexistent, ignore_lock=ignore_lock))

    @property
    def _nodb(self):
        return _join(self.wd, 'Omni.nodb')

    @property
    def _lock(self):
        return _join(self.wd, 'Omni.nodb.lock')

    def _omni_builder(self):
        for scenario in self.scenarios:
            _build_scenario(scenario, self.runid)


if __name__ == '__main__':
     _build_scenario('uniform low', '/geodata/weppcloud_runs/rlew-discretionary-pulsar/')