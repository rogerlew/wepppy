# https://github.com/Iglesys347/redis-log-handler/
# https://raw.githubusercontent.com/Iglesys347/redis-log-handler/refs/heads/main/rlh/handlers.py
# this is MIT Licensed code

"""
This module contains handlers that can be used to forward logs from python logging module
to a Redis database.
"""

import logging
import pickle
import json

import redis

DEFAULT_FIELDS = [
    "msg",          # the log message
    "levelname",    # the log level
    "created"       # the log timestamp
]


class RedisLogHandler(logging.Handler):
    """Default class for Redis log handlers.

    Attributes
    ----------
    redis : redis.Redis
        The Redis client.
    batch_size : int
        The batch size, if this value is > 1, logs will be processed by batches.
    log_buffer : list
        The list containing the batched logs.

    Methods
    -------
    emit(record: logging.LogRecord)
        This method is intended to be implemented by subclasses and so raises a NotImplementedError.
    """

    def __init__(self, redis_client: redis.Redis = None, batch_size: int = 1,
                 check_conn: bool = True,  **redis_args) -> None:
        """Init RedisLogHandler

        Parameters
        ----------
        redis_client : redis.Redis, optional
            The Redis client to forward logs to, by default None.
        batch_size : int, optional
            The batch size, if > 1 logs will be processed by batches, by default 1.
        check_conn : bool, optional
            Wether to check of not if the Redis is available with a ping, by default True.

        Raises
        ------
        TypeError
            Raised if one of the aditional argument passed to Redis is invalid.
        ConnectionError
            Raised if the Redis DB is unavailable.
        """
        super().__init__()

        if redis_client is not None:
            self.redis = redis_client
        else:
            try:
                self.redis = redis.Redis(**redis_args)
            except TypeError as err:
                raise TypeError(
                    "One of the argument passed to Redis is not valid") from err

        if check_conn:
            # trying to ping Redis DB
            try:
                self.redis.ping()
            except redis.exceptions.ConnectionError as err:
                raise ConnectionError("Unable to ping Redis DB") from err

        self.batch_size = batch_size
        self.log_buffer = []

    def emit(self, record: logging.LogRecord) -> None:
        raise NotImplementedError(
            "emit must be implemented by RedisLogHandler subclasses")

    def _buffer_emit(self):
        raise NotImplementedError(
            "_buffer_emit must be implemented by RedisLogHandler subclasses")

    def _check_buff_and_emit(self):
        if len(self.log_buffer) >= self.batch_size:
            self._buffer_emit()

    def close(self):
        """Make sure to add all remaining logs in buffer to Redis before object is destroyed."""
        if self.log_buffer:
            self._buffer_emit()
        super().close()


class RedisStreamLogHandler(RedisLogHandler):
    """Handler used to forward logs to a Redis stream.

    Attributes
    ----------
    redis : redis.Redis
        The Redis client.
    batch_size : int
        The batch size, if this value is > 1, logs will be processed by batches.
    log_buffer : list
        The list containing the batched logs.
    stream_name : str
        The name of the Redis stream.
    fields : list(str)
        The list of logs fields to forward.
    as_pkl : bool
        If true, the logs are written as pickle format in the stream.
    as_json : bool
        If true, the logs are written as JSON in the stream.

    Methods
    -------
    emit(record: logging.LogRecord)
        Forward log to the Redis stream.

    Notes
    -----
    Redis streams: https://redis.io/docs/data-types/streams/
    """

    def __init__(self, redis_client: redis.Redis = None, batch_size: int = 1,
                 check_conn: bool = True, stream_name: str = "logs",
                 maxlen: int = None, approximate: bool = True, 
                 fields: list = None, as_pkl: bool = False, as_json: bool = False,
                 **redis_args) -> None:
        """Init RedisStreamLogHandler

        Parameters
        ----------
        redis_client : redis.Redis, optional
            The Redis client to forward logs to, by default None.
        batch_size : int, optional
            The batch size, if > 1 logs will be processed by batches, by default 1.
        check_conn : bool, optional
            Wether to check of not if the Redis is available with a ping, by default True.
        stream_name : str, optional
            The name of the Redis stream where the logs are stored, by default "logs".
        maxlen : int, optional
            The maximum lenght of the Redis stream, if 0 no limit applied, by default 0.
        approximate : bool, optional
            If True, the Redis size won't be exactly equals to `maxlen`, but will be at least
            `maxlen`, by default True.
        fields : list, optional
            The list of logs fields to save, by default None.
        as_pkl : bool, optional
            Wether to save the log as its pickle format or not, by default False.
        as_json : bool, optional
            Wether to save the log as JSON format or not, by default False.

        Notes
        -----
        More info about Redis caped stream: https://redis.io/docs/data-types/streams-tutorial/#capped-streams
        """
        super().__init__(redis_client, batch_size, check_conn, **redis_args)

        self.stream_name = stream_name
        self.maxlen = maxlen
        self.approximate = approximate
        self.as_pkl = as_pkl
        self.as_json = as_json

        self.fields = fields if fields is not None else DEFAULT_FIELDS

    def emit(self, record: logging.LogRecord):
        """Write the log record in the Redis stream.

        Every time a log is emitted, an entry is inserted in the stream.
        This entry is a dict whose format depends on the handler
        attributes.
        
        If `as_pkl` is set to true, the records are saved as
        their pickle format with the key "pkl". If `as_json` is set to true,
        the records are saved as their JSON representation with the key "json".
        Otherwise we use the different fields as keys and their associated value
        in the record as the value.

        If `batch_size=n`, the logs are emited by batches of size `n`.

        Parameters
        ----------
        record : logging.LogRecord
            The log record to emit.
        """
        stream_entry = _make_entry(record, self.fields, self.as_pkl, self.as_json)
        self.log_buffer.append(stream_entry)
        self._check_buff_and_emit()

    def _buffer_emit(self):
        """Emits the logs batched in log buffer."""
        pipe = self.redis.pipeline()
        for log in self.log_buffer:
            pipe.xadd(self.stream_name, log, maxlen=self.maxlen, approximate=self.approximate)
        pipe.execute()
        self.log_buffer = []


class RedisPubSubLogHandler(RedisLogHandler):
    """Handler used to publish logs to a Redis pub/sub channel.

    Attributes
    ----------
    redis : redis.Redis
        The Redis client.
    batch_size : int
        The batch size, if this value is > 1, logs will be processed by batches.
    log_buffer : list
        The list containing the batched logs.
    channel_name : str
        The name of the Redis pub/sub channel.
    fields : list(str)
        The list of logs fields to forward.
    as_pkl : bool
        If true, the logs are written as pickle format in the message.

    Methods
    -------
    emit(record: logging.LogRecord)
        Publish log to the Redis pub/sub channel.

    Notes
    -----
    Redis pub/sub: https://redis.io/docs/manual/pubsub/
    """

    def __init__(self, redis_client: redis.Redis = None, batch_size: int = 1,
                 check_conn: bool = True, channel_name: str = "logs",
                 fields: list = None, as_pkl: bool = False, **redis_args) -> None:
        """Init RedisPubSubLogHandler

        Parameters
        ----------
        redis_client : redis.Redis, optional
            The Redis client to forward logs to, by default None.
        batch_size : int, optional
            The batch size, if > 1 logs will be processed by batches, by default 1.
        check_conn : bool, optional
            Wether to check of not if the Redis is available with a ping, by default True.
        channel_name : str, optional
            The name of the Redis pub/sub channel where the logs are pushed, by default "logs".
        fields : list, optional
            The list of logs fields to save, by default None.
        as_pkl : bool, optional
            Wether to save the log as its pickle format or not, by default False.
        """
        super().__init__(redis_client, batch_size, check_conn, **redis_args)

        self.channel_name = channel_name
        self.as_pkl = as_pkl

        self.fields = fields if fields is not None else DEFAULT_FIELDS

    def emit(self, record: logging.LogRecord):
        """Publish the log record in the Redis pub/sub channel.

        Every time a log is emitted, an entry is published on the channel.
        This entry is encoded as JSON whose format depends on the handler
        attributes. If `as_pkl` is set to true, the records are saved as
        their pickle format with the key "pkl". Otherwise we use the
        different fields as keys and their associated value in the record
        as the value (default fields are used if not specified).

        Parameters
        ----------
        record : logging.LogRecord
            The log record to emit.
        """
        log_entry = _make_entry(record, self.fields, self.as_pkl,
                                raw_pkl=True)
        if self.as_pkl:
            self.log_buffer.append(log_entry)
        else:
            self.log_buffer.append(json.dumps(log_entry))
        self._check_buff_and_emit()

    def _buffer_emit(self):
        """Emits the logs batched in log buffer."""
        pipe = self.redis.pipeline()
        for log in self.log_buffer:
            pipe.publish(self.channel_name, log)
        pipe.execute()
        self.log_buffer = []


def _make_fields(record, fields):
    """Return the fields dict for the log record.

    If all the specified fields are invalid, use the default fields.
    """
    field_dict = {field: getattr(record, field)
                  for field in fields if hasattr(record, field)}

    if field_dict == {}:
        return {field: getattr(record, field)
                for field in DEFAULT_FIELDS if hasattr(record, field)}

    if "msg" in field_dict:
        field_dict["msg"] = record.getMessage()

    return field_dict


def _make_entry(record, fields, as_pkl, as_json=False, raw_pkl=False):
    """Format the log entry."""
    if as_pkl:
        if raw_pkl:
            return pickle.dumps(record)
        return {"pkl": pickle.dumps(record)}
    if as_json:
        return {"json": json.dumps(_make_fields(record, fields))}
    return _make_fields(record, fields)