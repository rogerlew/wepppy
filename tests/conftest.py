import sys
import types


def _install_redis_stub() -> None:
    if 'redis' in sys.modules:
        return

    redis_stub = types.ModuleType('redis')

    class _RedisError(Exception):
        """Fallback Redis error used by the stub."""

    class _ConnectionPool:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

    class _BaseRedis:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        def ping(self):
            raise _RedisError('Redis stub is not connected')

        def set(self, *args, **kwargs):
            return 1

        def get(self, key):
            return None

        def delete(self, key):
            return 0

        def hgetall(self, key):
            return {}

        def scan_iter(self, match=None):
            return []

        def publish(self, channel, message):
            return 0

    class _StrictRedis(_BaseRedis):
        pass

    class _Redis(_BaseRedis):
        pass

    redis_stub.StrictRedis = _StrictRedis
    redis_stub.Redis = _Redis
    redis_stub.ConnectionPool = _ConnectionPool
    redis_stub.exceptions = types.SimpleNamespace(RedisError=_RedisError)

    sys.modules['redis'] = redis_stub


_install_redis_stub()
