import importlib.util
import logging
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
MODULE_PATH = REPO_ROOT / "wepppy" / "weppcloud" / "_config_logging.py"

config_logging_spec = importlib.util.spec_from_file_location(
    "wepppy.weppcloud._config_logging", MODULE_PATH
)
config_logging_module = importlib.util.module_from_spec(config_logging_spec)
assert config_logging_spec and config_logging_spec.loader
config_logging_spec.loader.exec_module(config_logging_module)

HealthFilter = config_logging_module.HealthFilter
config_logging = config_logging_module.config_logging


def _make_record(message: str) -> logging.LogRecord:
    return logging.LogRecord(
        name="test",
        level=logging.INFO,
        pathname=__file__,
        lineno=1,
        msg=message,
        args=(),
        exc_info=None,
    )


def test_health_filter_blocks_health_messages():
    health_filter = HealthFilter()
    assert not health_filter.filter(_make_record("OPTIONS /health ping"))
    assert not health_filter.filter(_make_record("Closing connection due to timeout"))
    assert health_filter.filter(_make_record("GET /status HTTP/1.1"))


def test_config_logging_applies_filter_and_level():
    logger_names = [
        "gunicorn.error",
        "gunicorn.access",
        "weppcloud.security",
        "weppcloud.app",
    ]
    backups = {}
    try:
        for name in logger_names:
            logger = logging.getLogger(name)
            backups[name] = (logger.level, list(logger.filters))
            logger.filters.clear()
            logger.setLevel(logging.NOTSET)

        config_logging(level=logging.WARNING)

        for name in logger_names:
            logger = logging.getLogger(name)
            assert any(isinstance(f, HealthFilter) for f in logger.filters)
            assert logger.level == logging.WARNING

        filter_counts = {
            name: sum(
                isinstance(f, HealthFilter) for f in logging.getLogger(name).filters
            )
            for name in logger_names
        }

        config_logging(level=logging.ERROR)

        for name in logger_names:
            logger = logging.getLogger(name)
            assert (
                sum(isinstance(f, HealthFilter) for f in logger.filters)
                == filter_counts[name]
            )
            assert logger.level == logging.ERROR
    finally:
        for name, (level, filters) in backups.items():
            logger = logging.getLogger(name)
            logger.setLevel(level)
            logger.filters[:] = filters
