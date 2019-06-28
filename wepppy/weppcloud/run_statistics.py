from os.path import exists as _exists
from os.path import join as _join
from time import time
import jsonpickle
import json
import os

from collections import Counter


class RunStatistics(object):
    def __init__(self, wd):
        assert _exists(wd)
        self.wd = wd

        self.lock()
        self._counter = Counter()

        if _exists(self._nodb):
            raise Exception('NoDb has already been initialized')

        self.dump_and_unlock()

    def increment(self, cfg, num_hills=0, increment_project=True):
        num_hills = int(num_hills)
        assert int(num_hills) == int(float(num_hills))
        assert isinstance(cfg, str)

        self.lock()
        try:
            self._counter['%s_hillruns' % cfg] += num_hills
            if increment_project:
                self._counter['%s_projects' % cfg] += 1

            self.dump_and_unlock()
        except:
            self.unlock()

    def increment_hillruns(self, cfg, num_hills):
        num_hills = int(num_hills)
        assert int(num_hills) == int(float(num_hills))
        assert isinstance(cfg, str)

        self.lock()
        try:
            self._counter['%s_hillruns' % cfg] += num_hills
            self.dump_and_unlock()
        except:
            self.unlock()

    def increment_projects(self, cfg):
        assert isinstance(cfg, str)

        self.lock()
        try:
            self._counter['%s_projects' % cfg] += 1
            self.dump_and_unlock()
        except:
            self.unlock()

    def dump_and_unlock(self, validate=True):
        self.dump()
        self.unlock()

        if validate:
            nodb = type(self)

            # noinspection PyUnresolvedReferences
            nodb.getInstance(self.wd)

    @property
    def _nodb(self):
        return _join(self.wd, 'run_statistics.nodb')

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
                db.wd = wd
                db.lock()
                db.dump_and_unlock()

            return db


if __name__ == "__main__":
    rs = RunStatistics.getInstance('/geodata/weppcloud_runs/')