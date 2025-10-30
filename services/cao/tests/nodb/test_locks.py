import os
import tempfile

import pytest


class _RedisStub:
    def __init__(self):
        self.store = {}
        self.hashes = {}

    # Key-value operations
    def set(self, key, value, nx=False, ex=None):  # ex is ignored by stub
        if nx and key in self.store:
            return False
        self.store[key] = value
        return True

    def get(self, key):
        return self.store.get(key)

    def delete(self, key):
        self.store.pop(key, None)

    # Hash operations
    def hset(self, name, key, value):
        bucket = self.hashes.setdefault(name, {})
        bucket[key] = value
        return 1

    def hget(self, name, key):
        return self.hashes.get(name, {}).get(key)


@pytest.mark.unit
def test_unlock_after_lock_clears_lock(monkeypatch):
    # Install Redis stub onto the nodb base module
    monkeypatch.setattr("wepppy.nodb.base.redis_lock_client", _RedisStub(), raising=False)

    # Import here after monkeypatch to ensure any lookups use the stub
    from wepppy.nodb.core import Ron
    from wepppy.nodb.base import redis_lock_client

    # Create isolated working directory for the controller
    with tempfile.TemporaryDirectory() as wd:
        # Sanity: directory exists for NoDbBase constructor
        assert os.path.isdir(wd)

        wepp = Ron(wd, "disturbed9002.cfg")

        # Acquire lock
        wepp.lock()
        assert wepp.islocked() is True

        # Ensure the distributed lock key is present
        lock_key = wepp._distributed_lock_key
        assert redis_lock_client.get(lock_key) is not None

        # Release lock
        wepp.unlock()

        # Lock is fully cleared
        assert wepp.islocked() is False
        assert redis_lock_client.get(lock_key) is None
        assert redis_lock_client.hget(wepp.runid, wepp._file_lock_key) == "false"

