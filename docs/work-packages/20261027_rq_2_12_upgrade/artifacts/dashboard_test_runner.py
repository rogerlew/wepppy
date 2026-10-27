import unittest
import redis
from tests.test_basic import BasicTestCase

socket = '/tmp/rq212-redis/redis.sock'
assert redis.Redis(unix_socket_path=socket, db=0).get('batch-boundary-test-server') == b'disposable'

class SocketCase(BasicTestCase):
    def get_redis_client(self):
        if self.redis_client is None:
            self.redis_client = redis.Redis(unix_socket_path=socket, db=5)
        return self.redis_client

    def setUp(self):
        super().setUp()
        self.app.config['RQ_DASHBOARD_REDIS_URL'] = ['unix://' + socket + '?db=5']

suite = unittest.TestSuite(SocketCase(name) for name in (
    'test_job_info_preserves_dependency_ids',
    'test_empty_started_registry_removes_missing_job_execution',
))
result = unittest.TextTestRunner(verbosity=2).run(suite)
raise SystemExit(not result.wasSuccessful())
