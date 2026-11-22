from __future__ import annotations

import re
from html import escape as html_escape, unescape as html_unescape

_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")
_NON_SLUG_CHARS_RE = re.compile(r"[^\w\- ]+", re.UNICODE)
_MULTI_DASH_RE = re.compile(r"-{2,}")

_HEADING_RE = re.compile(
    r"<h(?P<level>[1-6])(?P<attrs>[^>]*)>(?P<body>.*?)</h\1>",
    re.IGNORECASE | re.DOTALL,
)
_HEADING_ID_ATTR_RE = re.compile(r'\bid\s*=\s*(["\'])(?P<id>.*?)\1', re.IGNORECASE | re.DOTALL)


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


def add_heading_anchors(content_html: str) -> str:
    slug_counts: dict[str, int] = {}

    def _reserve_slug(slug: str) -> str:
        count = slug_counts.get(slug, 0)
        if count == 0:
            slug_counts[slug] = 1
            return slug
        while True:
            candidate = f"{slug}-{count}"
            count += 1
            if candidate not in slug_counts:
                slug_counts[slug] = count
                slug_counts[candidate] = 1
                return candidate

    def _replace(match: re.Match[str]) -> str:
        level = match.group("level")
        attrs = match.group("attrs") or ""
        body = match.group("body")
        existing_id_match = _HEADING_ID_ATTR_RE.search(attrs)
        if existing_id_match is not None:
            existing_id = existing_id_match.group("id").strip()
            if existing_id:
                slug_counts.setdefault(existing_id, 1)
            return match.group(0)
        base_slug = usersum_anchor_slug(body) or "section"
        anchor_id = _reserve_slug(base_slug)
        escaped_anchor_id = html_escape(anchor_id, quote=True)
        return f'<h{level}{attrs} id="{escaped_anchor_id}">{body}</h{level}>'

    return _HEADING_RE.sub(_replace, content_html)
