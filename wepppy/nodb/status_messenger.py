import os
from os.path import join as _join
import redis

from dotenv import load_dotenv
_thisdir = os.path.dirname(__file__)
load_dotenv(_join(_thisdir, '.env'))
REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')

class StatusMessenger:
    _client = None
    _redis_config = {
        'host': REDIS_HOST,
        'port': 6379,
        'db': 2,
        'decode_responses': True,
    }

    @classmethod
    def _get_client(cls):
        # Lazy initialization of the redis client
        if cls._client is None:
            cls._client = redis.Redis(**cls._redis_config)
        return cls._client

    @classmethod
    def publish(cls, channel, message):
        # Use the lazy-initialized client for publishing messages
        return cls._get_client().publish(channel, message)

