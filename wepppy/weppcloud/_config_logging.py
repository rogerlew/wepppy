
import logging

class HealthFilter(logging.Filter):
    def filter(self, record):
        msg = record.getMessage()
        return not ("OPTIONS /health" in msg or "Closing connection" in msg)
    
_loggers = ["gunicorn.error", "gunicorn.access", "weppcloud.security", "weppcloud.app"]

def config_logging(level=logging.INFO):
    # make sure the health filter is applied to all relevant loggers
    filter_type = HealthFilter
    for logger_name in _loggers:
        logger = logging.getLogger(logger_name)
        if not logger:
            continue
        if not any(isinstance(f, filter_type) for f in logger.filters):
            logger.addFilter(filter_type())
        logger.setLevel(level)
