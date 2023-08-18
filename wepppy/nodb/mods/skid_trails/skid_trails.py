# non-standard

# wepppy

# wepppy submodules
from wepppy.nodb.mixins.log_mixin import LogMixin
from wepppy.nodb.base import NoDbBase

# standard library
import os
from os.path import join as _join
from os.path import exists as _exists

# non-standard
import jsonpickle

class skid_trailsNoDbLockedException(Exception):
    pass


class SkidTrails(NoDbBase, LogMixin):
    __name__ = 'skid_trails'

    def __init__(self, wd, cfg_fn):
        super(SkidTrails, self).__init__(wd, cfg_fn)

        self.lock()

        # noinspection PyBroadException
        try:
            skid_trails_dir = self.skid_trails_dir
            if not _exists(skid_trails_dir):
                os.mkdir(skid_trails_dir)

            self.clean()

            self.dump_and_unlock()

        except Exception:
            self.unlock('-f')
            raise

    @property
    def skid_trails_dir(self):
        return _join(self.wd, 'skid_trails')

    @property
    def runs_dir(self):
        return _join(self.wd, 'skid_trails', 'runs')

    @property
    def output_dir(self):
        return _join(self.wd, 'skid_trails', 'output')

    @property
    def status_log(self):
        return os.path.abspath(_join(self.runs_dir, 'status.log'))

    #
    # Required for NoDbBase Subclass
    #

    # noinspection PyPep8Naming
    @staticmethod
    def getInstance(wd):
        with open(_join(wd, 'skid_trails.nodb')) as fp:
            db = jsonpickle.decode(fp.read())
            assert isinstance(db, SkidTrails)

            if _exists(_join(wd, 'READONLY')):
                db.wd = os.path.abspath(wd)
                return db

            if os.path.abspath(wd) != os.path.abspath(db.wd):
                db.wd = wd
                db.lock()
                db.dump_and_unlock()

            return db

    @property
    def _nodb(self):
        return _join(self.wd, 'skid_trails.nodb')

    @property
    def _lock(self):
        return _join(self.wd, 'skid_trails.nodb.lock')
