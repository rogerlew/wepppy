"""Read a fresh operation credential for each submission; no module-level cache."""
import base64
import json
import os
import re
from pathlib import Path


def load_weppcloud_token() -> str:
    path = os.environ.get("WEPPCLOUD_TOKEN_FILE")
    if path is None:
        token = os.environ.get("WEPPCLOUD_TOKEN")
        if not token:
            raise ValueError("WEPPCLOUD_TOKEN is not configured")
        return token
    if not path.strip():
        raise ValueError("WEPPCLOUD_TOKEN_FILE is empty")
    try:
        with Path(path).open(encoding="utf-8") as stream:
            raw = stream.read(16385)
    except (OSError, UnicodeError):
        raise ValueError("WEPPCLOUD_TOKEN_FILE cannot be read") from None
    token = raw.strip()
    try:
        parts = token.split(".")
        if len(raw) > 16384 or len(parts) != 3 or not all(re.fullmatch(r"[A-Za-z0-9_-]+", p) for p in parts):
            raise ValueError
        decoded = [base64.b64decode(p + "=" * (-len(p) % 4), altchars=b"-_", validate=True) for p in parts]
        if not all(isinstance(json.loads(p), dict) for p in decoded[:2]):
            raise ValueError
    except (ValueError, UnicodeError):
        raise ValueError("WEPPCLOUD_TOKEN_FILE contains an invalid credential") from None
    return token
