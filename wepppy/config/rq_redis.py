"""Owned RQ config/connection adapter; module config contains no credentials.

Invoke RQ with --url '' --config wepppy.config.rq_redis
--connection-class wepppy.config.rq_redis.Connection. Empty --url suppresses
Click's RQ_REDIS_URL default; the canonical resolver still ingests that input.
"""

import sys
from wepppy.observability.safe_logging import install as install_safe_logging
from wepppy.observability.secret_profiles import worker_profile
install_safe_logging(worker_profile(tuple(arg for arg in sys.argv if arg in {'default', 'batch', 'fork-archive'})))
import redis
from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs


# Identity marker identifies only RQ config construction, not native callers.
REDIS_HOST = object()


class Connection(redis.Redis):
    """Preserve native options omitted by RQ 2.12 config field handling."""

    def __init__(self, *args, **kwargs):
        if kwargs.get("host") is REDIS_HOST:
            kwargs = redis_connection_kwargs(RedisDB.RQ)
        super().__init__(*args, **kwargs)
