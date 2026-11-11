"""Opt-in disposable Redis endpoint; never use a shared Redis database."""
import pytest


def pytest_addoption(parser):
    parser.addoption('--f5-redis-socket', default=None, help='Unix socket of an explicitly disposable F5 Redis server')


@pytest.fixture
def f5_redis_socket(request):
    import redis
    path = request.config.getoption('--f5-redis-socket')
    if not path:
        pytest.skip('requires --f5-redis-socket disposable server')
    client = redis.StrictRedis(unix_socket_path=path)
    try:
        assert client.get('f5-disposable-server') == b'synthetic-only'
    finally:
        client.close()
    return path
