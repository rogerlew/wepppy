import os
import unittest
from tempfile import TemporaryDirectory

from wepppy.nodb.core import Ron
from wepppy.nodb.base import redis_lock_client


@unittest.skipIf(redis_lock_client is None, "Redis lock client is unavailable")
class RonLockedTests(unittest.TestCase):
    cfg_filename = 'disturbed9002.cfg'

    @classmethod
    def setUpClass(cls):
        cls._tempdir = TemporaryDirectory()
        cls.wd = cls._tempdir.name

        wepp_path = os.path.join(cls.wd, 'wepp.nodb')
        if os.path.exists(wepp_path):
            os.remove(wepp_path)

        cls.wepp = Ron(cls.wd, cls.cfg_filename)

    @classmethod
    def tearDownClass(cls):
        try:
            cls.wepp.unlock()
        except Exception:
            pass
        cls._tempdir.cleanup()

    def setUp(self):
        self.wepp = type(self).wepp
        try:
            self.wepp.unlock()
        except Exception:
            pass

    def tearDown(self):
        try:
            self.wepp.unlock()
        except Exception:
            pass

    def test_locked_context_sets_lock(self):
        with self.wepp.locked():
            self.assertTrue(self.wepp.islocked())

    def test_lock_released_after_context(self):
        with self.wepp.locked():
            pass
        self.assertFalse(self.wepp.islocked())

    def test_exception_releases_lock(self):
        with self.assertRaises(ValueError):
            with self.wepp.locked():
                float('dsd')
        self.assertFalse(self.wepp.islocked())


if __name__ == '__main__':
    unittest.main()
