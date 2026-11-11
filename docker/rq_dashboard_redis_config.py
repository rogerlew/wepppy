"""RQ dashboard file-backed credential config; mounted into the existing image."""
from pathlib import Path


class _Password(str):
    # Redis encodes str values with .encode(), preserving the original bytes.
    # Flask config diagnostics use repr; explicit string formatting is safe too.
    def __repr__(self):
        return '<redacted>'

    __str__ = __repr__

    def __format__(self, spec):
        return format("<redacted>", spec)


try:
    _value = Path('/run/secrets/redis_password').read_bytes().decode('utf-8').rstrip('\n')
except (OSError, UnicodeError):
    raise RuntimeError('Redis password file unavailable') from None
if not _value or _value != _value.strip() or any(c in _value for c in '\x00\r\n'):
    raise RuntimeError('Redis password file empty or invalid')
RQ_DASHBOARD_REDIS_URL = 'redis://redis:6379/9'
RQ_DASHBOARD_REDIS_PASSWORD = _Password(_value)
del _value
