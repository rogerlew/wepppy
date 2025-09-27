from contextlib import contextmanager
from os.path import exists as _exists
from os.path import join as _join
from time import time
import jsonpickle
import json
import os

from collections import Counter

"""
This is a ViewModel that deserializes the run statistics from a json file.
It is not a NoDbBase subclass, but it does implement similiar locking and dumping
functionality similar to NoDbBase subclasses.
"""

class RunStatistics(object):
    def __init__(self, wd):
        assert _exists(wd)
        self.wd = wd

        if _exists(self._nodb):
            raise Exception('NoDb has already been initialized')
        
        with self.locked():
            self._counter = Counter()

    def increment(self, cfg, num_hills=0, increment_project=True):
        num_hills = int(num_hills)
        assert int(num_hills) == int(float(num_hills))
        assert isinstance(cfg, str)

        with self.locked():
            self._counter['%s_hillruns' % cfg] += num_hills
            if increment_project:
                self._counter['%s_projects' % cfg] += 1

    def increment_hillruns(self, cfg, num_hills):
        num_hills = int(num_hills)
        assert int(num_hills) == int(float(num_hills))
        assert isinstance(cfg, str)

        with self.locked():
            self._counter['%s_hillruns' % cfg] += num_hills
            
    def increment_projects(self, cfg):
        assert isinstance(cfg, str)

        with self.locked():
            self._counter['%s_projects' % cfg] += 1

    @contextmanager
    def locked(self, validate_on_success=True):
        """
        A context manager to handle the lock -> modify -> dump/unlock pattern.

        Usage:
            with self.locked():
                # modify attributes here
                self.foo = 'bar'
        
        On successful exit from the 'with' block, it calls dump_and_unlock().
        If an exception occurs, it calls unlock() and re-raises the exception.
        """

        self.lock()
        try:
            yield
        except Exception:
            self.unlock()
            raise
        else:
            self.dump_and_unlock()

    def dump_and_unlock(self, validate=True):
        self.dump()
        self.unlock()

        if validate:
            nodb = type(self)

            # noinspection PyUnresolvedReferences
            nodb.getInstance(self.wd)

    @property
    def _lock(self):
        return _join(self.wd, 'run_statistics.nodb.lock')

    @property
    def _json(self):
        return _join(self.wd, 'run_statistics.json')

    @property
    def counter(self):
        d = dict(self._counter)
        num_hills = 0
        num_projs = 0

        for k, cnt in d.items():
            if 'hillruns' in k:
                num_hills += cnt
            else:
                num_projs += cnt

        d['total_hillruns'] = num_hills
        d['total_projects'] = num_projs

        return d

    def dump(self):
        if not self.islocked():
            raise Exception('cannot dump to unlocked db')

        js = jsonpickle.encode(self)
        # noinspection PyUnresolvedReferences
        with open(self._nodb, 'w') as fp:
            fp.write(js)

        with open(self._json, 'w') as fp:

            fp.write(json.dumps(self.counter))

        # validate

    def lock(self):
        if self.islocked():
            raise Exception('lock() called on an already locked nodb')

        with open(self._lock, 'w') as fp:
            fp.write(str(time()))

    def unlock(self, flag=None):
        if self.islocked():
            os.remove(self._lock)
        else:
            if flag != '-f':
                raise Exception('unlock() called on an already unlocked nodb')

    def islocked(self):
        return _exists(self._lock)

    def getInstance(wd):
        with open(_join(wd, 'run_statistics.nodb')) as fp:
            db = jsonpickle.decode(fp.read())

        if os.path.abspath(wd) != os.path.abspath(db.wd):
            if not db.islocked():
                db.lock()
                db.wd = wd
                db.dump_and_unlock()

        return db
    

if __name__ == "__main__":
    rs = RunStatistics.getInstance('/geodata/weppcloud_runs/')