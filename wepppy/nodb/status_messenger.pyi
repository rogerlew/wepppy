from __future__ import annotations

import logging
from typing import Optional

import redis

class StatusMessenger:
    _client: Optional[redis.Redis]

    @classmethod
    def _get_client(cls) -> redis.Redis: ...

    @classmethod
    def publish(cls, channel: str, message: str) -> int: ...

    @classmethod
    def publish_command(cls, runid: str, message: str) -> int: ...


class StatusMessengerHandler(logging.Handler):
    channel: str

    def __init__(self, channel: str) -> None: ...

    def emit(self, record: logging.LogRecord) -> None: ...
