"""Redact confirmed free-text disclosures before status publication.

Go's outbound guard independently handles structured failures and direct Redis
publishers. Detailed exception reports remain on the authorized job-info path.
"""
from __future__ import annotations

import re

_PATH = re.compile(r'''(?:[A-Za-z]:[\\/]|\\\\|/)[^\s"'<>\]\[{},;()]+''')
_CREDENTIAL = re.compile(r'(?i)bearer[. ]+[A-Za-z0-9_.~+/-]+')
_JWT = re.compile(r'[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}')
_SECRET = re.compile(r'''(?i)(password|secret|token|api[_-]?key|authorization)["']?\s*[:=]\s*(?:"[^"]*"|'[^']*'|[^\s,;}]+)''')
_SETTER = re.compile(r'([A-Za-z0-9_]+\.[A-Za-z0-9_]+) -> .*', re.DOTALL)
_OPTIONS = re.compile(r'(?i)(job options:).*', re.DOTALL)


def sanitize_progress(message: str) -> str:
    # Preserve structured parser contracts for the typed service sanitizer.
    if 'EXCEPTION_JSON' in message or 'DIAGNOSTICS_V1:' in message:
        return message
    if 'EXCEPTION' in message:
        message = message.split('EXCEPTION', 1)[0] + 'EXCEPTION Operation failed. Inspect the authorized job report for details.'
    if 'Traceback (most recent call last)' in message or 'File "' in message:
        return 'Operation failed. Inspect the authorized job report for details.'
    message = _CREDENTIAL.sub('[credential]', message)
    message = _JWT.sub('[credential]', message)
    message = _SECRET.sub(r'\1=[redacted]', message)
    message = _PATH.sub('[path]', message)
    message = _SETTER.sub(r'\1 -> [redacted]', message)
    return _OPTIONS.sub(r'\1 [redacted]', message)
