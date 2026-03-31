from __future__ import annotations

import re
from html import unescape as html_unescape

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")
_NON_SLUG_CHARS_RE = re.compile(r"[^\w\- ]+", re.UNICODE)
_MULTI_DASH_RE = re.compile(r"-{2,}")


def usersum_anchor_slug(value: str) -> str:
    """Return a stable anchor slug used by Usersum heading links."""
    text = html_unescape(value.strip())
    if not text:
        return ""
    text = _HTML_TAG_RE.sub("", text)
    text = _WHITESPACE_RE.sub(" ", text)
    text = text.strip().lower()
    text = _NON_SLUG_CHARS_RE.sub("", text)
    text = _WHITESPACE_RE.sub("-", text)
    text = _MULTI_DASH_RE.sub("-", text)
    return text.strip("-")


def usersum_anchor_from_section(section: str | None) -> str | None:
    """Normalize user-supplied section text/id to an anchor fragment id."""
    if section is None:
        return None
    token = section.strip()
    if not token:
        return None
    if token.startswith("#"):
        token = token[1:]
    slug = usersum_anchor_slug(token)
    return slug or None
