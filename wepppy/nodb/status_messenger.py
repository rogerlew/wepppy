import redis

class StatusMessenger:
    _client = None
    _redis_config = {
        'host': 'localhost',
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

