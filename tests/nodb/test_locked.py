import json
import os
import unittest
from tempfile import TemporaryDirectory
from time import sleep

from wepppy.nodb.core import Ron
from wepppy.nodb.base import clear_locks, redis_lock_client


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

    def test_distributed_lock_records_token(self):
        with self.wepp.locked():
            payload = redis_lock_client.get(self.wepp._distributed_lock_key)
            self.assertIsNotNone(payload)
            data = json.loads(payload)
            self.assertIn('token', data)
            self.assertTrue(data['token'])
            self.assertIn('owner', data)
        self.assertIsNone(redis_lock_client.get(self.wepp._distributed_lock_key))

    def test_lock_expiration_resets_flag(self):
        try:
            self.wepp.lock(ttl=2)
            lock_key = self.wepp._distributed_lock_key
            self.assertIsNotNone(redis_lock_client.get(lock_key))
            sleep(3)
            self.assertFalse(self.wepp.islocked())
            self.assertIsNone(redis_lock_client.get(lock_key))
            flag_value = redis_lock_client.hget(self.wepp.runid, self.wepp._file_lock_key)
            self.assertEqual('false', flag_value)
        finally:
            try:
                self.wepp.unlock(flag='-f')
            except Exception:
                pass

    def test_clear_locks_releases_distributed_lock(self):
        try:
            self.wepp.lock()
            lock_key = self.wepp._distributed_lock_key
            self.assertIsNotNone(redis_lock_client.get(lock_key))
            cleared = clear_locks(self.wepp.runid)
            self.assertIn(self.wepp._file_lock_key, cleared)
            self.assertFalse(self.wepp.islocked())
            self.assertIsNone(redis_lock_client.get(lock_key))
        finally:
            try:
                self.wepp.unlock(flag='-f')
            except Exception:
                pass


if __name__ == '__main__':
    unittest.main()
