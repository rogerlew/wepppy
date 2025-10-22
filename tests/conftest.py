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

    class _Connection:
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

    def _from_url(url, *args, **kwargs):
        connection_class = kwargs.pop("connection_class", None)
        kwargs.setdefault("url", url)
        client = _Redis(*args, **kwargs)
        if connection_class is not None:
            client.connection_class = connection_class
        return client

    exceptions_module = types.ModuleType("redis.exceptions")
    exceptions_module.RedisError = _RedisError
    exceptions_module.ConnectionError = _RedisError
    exceptions_module.TimeoutError = _RedisError
    exceptions_module.WatchError = _RedisError
    exceptions_module.ResponseError = _RedisError

    client_module = types.ModuleType("redis.client")

    class _Pipeline:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = kwargs

        def __enter__(self):
            return self

        def __exit__(self, exc_type, exc, tb):
            return False

        def watch(self, *args, **kwargs):
            return None

        def multi(self):
            return None

        def execute(self):
            return []

        def unwatch(self):
            return None

        def sadd(self, *args, **kwargs):
            return 1

        def smembers(self, *args, **kwargs):
            return set()

        def expire(self, *args, **kwargs):
            return True

        def get(self, *args, **kwargs):
            return None

        def set(self, *args, **kwargs):
            return True

        def delete(self, *args, **kwargs):
            return 0

    client_module.Pipeline = _Pipeline

    redis_stub.StrictRedis = _StrictRedis
    redis_stub.Redis = _Redis
    redis_stub.ConnectionPool = _ConnectionPool
    redis_stub.Connection = _Connection
    redis_stub.from_url = _from_url
    redis_stub.exceptions = exceptions_module
    redis_stub.RedisError = _RedisError
    redis_stub.ConnectionError = _RedisError
    redis_stub.TimeoutError = _RedisError
    redis_stub.WatchError = _RedisError
    redis_stub.Pipeline = _Pipeline

    sys.modules["redis.exceptions"] = exceptions_module
    sys.modules["redis.client"] = client_module

    sys.modules['redis'] = redis_stub


_install_redis_stub()
