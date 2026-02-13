import os
import redis

from urllib.parse import urlparse

from wepppy.config.secrets import get_secret

REDIS_URL = os.environ.get('REDIS_URL', '')
REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
REDIS_PORT = int(os.environ.get('REDIS_PORT', '6379'))
REDIS_PASSWORD = get_secret("REDIS_PASSWORD") or ""


class StatusMessenger:
    """
    This class is used to publish messages to a redis channel.
    """
    _client = None
    _redis_config = {}

    @classmethod
    def _build_config(cls):
        if REDIS_URL:
            parsed = urlparse(REDIS_URL)
            if parsed.scheme and parsed.hostname:
                config = {
                    'host': parsed.hostname,
                    'port': parsed.port or REDIS_PORT,
                    'db': int(parsed.path.lstrip('/') or '2'),
                    'decode_responses': True,
                }
                if parsed.password:
                    config['password'] = parsed.password
                elif REDIS_PASSWORD:
                    config['password'] = REDIS_PASSWORD
                return config
        config = {
            'host': REDIS_HOST,
            'port': REDIS_PORT,
            'db': 2,
            'decode_responses': True,
        }
        if REDIS_PASSWORD:
            config['password'] = REDIS_PASSWORD
        return config

    @classmethod
    def _get_client(cls):
        # Lazy initialization of the redis client
        if cls._client is None:
            if not cls._redis_config:
                cls._redis_config = cls._build_config()
            cls._client = redis.Redis(**cls._redis_config)
        return cls._client

    @classmethod
    def publish(cls, channel, message):
        """
        Publish a message to a redis channel.
        """
        # Use the lazy-initialized client for publishing messages
        return cls._get_client().publish(channel, message)
