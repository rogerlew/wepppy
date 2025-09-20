import os
from os.path import join as _join
import redis
import logging

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


class StatusMessengerHandler(logging.Handler):
    """
    A logging handler that publishes log records to a Redis channel
    using the StatusMessenger class.
    """
    def __init__(self, channel: str):
        """
        Initializes the handler.

        Args:
            channel (str): The Redis channel to publish messages to.
        """
        super().__init__()
        if not isinstance(channel, str) or not channel:
            raise ValueError("A valid channel name is required.")
        self.channel = channel

    def emit(self, record: logging.LogRecord):
        """
        Formats the record and publishes it to the specified Redis channel.

        Args:
            record (logging.LogRecord): The log record to be processed.
        """
        # Get the formatted log message from the record
        msg = record.getMessage()
        
        # Use the existing StatusMessenger to publish the message
        StatusMessenger.publish(self.channel, msg)