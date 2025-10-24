"""Redis-backed status publisher used by NoDb logging handlers."""

from __future__ import annotations

import logging
import os
from os.path import join as _join
from typing import Optional

import redis
from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs

from dotenv import load_dotenv
_thisdir = os.path.dirname(__file__)
load_dotenv(_join(_thisdir, '.env'))

class StatusMessenger:
    """Thin wrapper around Redis pub/sub for status messages."""

    _client: Optional[redis.Redis] = None
    _redis_config = redis_connection_kwargs(
        RedisDB.STATUS,
        decode_responses=True,
    )

    @classmethod
    def _get_client(cls) -> redis.Redis:
        """Return the shared Redis client, initializing it on first use."""

        if cls._client is None:
            cls._client = redis.Redis(**cls._redis_config)
        return cls._client

    @classmethod
    def publish(cls, channel: str, message: str) -> int:
        """Publish ``message`` to ``channel`` via Redis pub/sub."""

        return cls._get_client().publish(channel, message)

    @classmethod
    def publish_command(cls, runid: str, message: str) -> int:
        """Publish a command message scoped to ``runid``."""

        if not runid:
            raise ValueError("runid is required to publish command messages.")
        channel = f'{runid}:command'
        return cls.publish(channel, message)


class StatusMessengerHandler(logging.Handler):
    """Logging handler that forwards records to Redis via StatusMessenger."""

    def __init__(self, channel: str):
        super().__init__()
        if not isinstance(channel, str) or not channel:
            raise ValueError("A valid channel name is required.")
        self.channel = channel

    def emit(self, record: logging.LogRecord) -> None:
        """Format ``record`` and publish the message to the configured channel."""

        msg = record.getMessage()
        StatusMessenger.publish(self.channel, msg)
