"""Redis-backed status publisher used by NoDb logging handlers."""

from __future__ import annotations

from wepppy.observability.safe_logging import safe_record_message, current_profile
from wepppy.observability.secret_profiles import WORKER

import logging
import sys
from wepppy.observability.safe_traceback import safe_text
from typing import Optional
from .stream_messages import sanitize_progress

import redis
from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs

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

        if sys.exception() is not None:
            message = safe_text(message, source_profile=current_profile(WORKER))
        return cls._get_client().publish(channel, sanitize_progress(message))

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

        msg = safe_record_message(record, current_profile(WORKER))
        StatusMessenger.publish(self.channel, msg)
