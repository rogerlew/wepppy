"""Stateless exception diagnostics. See docs/schemas/safe-traceback-contract.md.

Only immutable source metadata may be retained. Secret values and derived
variants are private to one call; no framework or application imports belong here.
"""
from __future__ import annotations

from dataclasses import dataclass, field
import json
from importlib.machinery import PathFinder
import base64
import binascii
import os
import re
import sys
import traceback
from uuid import uuid4
from urllib.parse import quote, quote_plus, unquote, urlsplit, parse_qsl

REDACTED = '[REDACTED]'
UNAVAILABLE = 'Diagnostic unavailable (sanitization failed).'
MAX_SOURCE = 64 * 1024
MAX_TEXT = 1024 * 1024
MAX_VALUES = 256


class _GeneratedErrorId(str):
    """Provenance marker; never construct from caller-controlled identifiers."""


def new_error_id() -> str:
    return _GeneratedErrorId(uuid4().hex)


def unavailable(error_id=None) -> str:
    if isinstance(error_id, _GeneratedErrorId):
        return f'{UNAVAILABLE} [error_id={error_id}]'
    return UNAVAILABLE


@dataclass(frozen=True)
class SecretSourceSpec:
    setting: str | None
    file_setting: str | None = None
    required: bool = False
    decoder: str = 'raw'
    path: str | None = None
    fallback_for: tuple[str, ...] = ()
    package_file: tuple[str, str] | None = None


@dataclass(frozen=True)
class SecretSourceProfile:
    name: str
    sources: tuple[SecretSourceSpec, ...] = ()


@dataclass(frozen=True)
class _Snapshot:
    variants: tuple[str, ...] = field(repr=False)


_PERCENT = re.compile(r'%[0-9a-fA-F]{2}')
_PEM_START = re.compile(r'-----BEGIN ([A-Z ]{0,32}PRIVATE KEY)-----')
_PEM = re.compile(r'-----BEGIN (?:[A-Z ]*PRIVATE KEY)-----.*?-----END (?:[A-Z ]*PRIVATE KEY)-----', re.S)
_URI = re.compile(r'(?i)(?<![a-z0-9+.-])([a-z][a-z0-9+.-]{0,31}://)[^\s/<>\"\']*@')
_JWT = re.compile(r'(?<![\w-])([A-Za-z0-9_-]+)\.([A-Za-z0-9_-]+)\.([A-Za-z0-9_-]*)(?![\w-])')
_BEARER = re.compile(r'(?i)\b(Bearer|Basic)\s+[A-Za-z0-9._~+/=%-]+')
_QUOTED = r'''(?:"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|[^\s,;}\]]+)'''
_ASSIGN = re.compile(r'''(?i)(?<![\w-])(["']?[\w-]+["']?\s*[:=]\s*)''')
_VALUE = re.compile(_QUOTED)

_SENSITIVE = re.compile(r'(?i)password|passwd|secret|token|api[_-]?key|credential')

_HEADER = re.compile(
    r'''(?im)(["']?\b(?:authorization|proxy-authorization|cookie|set-cookie)["']?\s*[:=]\s*)'''
    + r'''(?:"(?:\\.|[^"\\])*"|'(?:\\.|[^'\\])*'|[^\r\n]+)'''
)


def _decode(value: str, decoder: str) -> tuple[str, ...]:
    if len(value) > MAX_SOURCE:
        raise ValueError('source limit')
    if decoder == 'redis':
        value = value.rstrip('\n')
        if value != value.strip():
            raise ValueError('invalid Redis framing')
    else:
        value = value.strip()
    if not value:
        raise ValueError('empty source')
    if decoder == 'comma':
        values = (value, *(item.strip() for item in value.split(',') if item.strip()))
    elif decoder in ('url', 'database-url'):
        if not re.match(r'^[\w+.-]+://', value):
            raise ValueError('invalid credential URL')
        if decoder == 'database-url':
            # SQLAlchemy accepts unescaped slash in password; RFC urlsplit does
            # not. Match its userinfo grammar without importing the framework.
            match = re.match(r'^[\w+]+://(?:([^:/]*)(?::([^@]*))?@)?', value)
            if match is None:
                raise ValueError('invalid database URL')
            parts = match.groups()
            if '@' in value.split('?', 1)[0] and parts[0] is None:
                raise ValueError('unsupported database userinfo')
        else:
            parsed = urlsplit(value)
            parts = (parsed.username, parsed.password)
            if '@' in value and parsed.username is None:
                raise ValueError('invalid URL userinfo')
        values = tuple(unquote(part) for part in parts if part)
        query = value.split('?', 1)[1] if '?' in value else ''
        values += tuple(item for key, item in parse_qsl(query, max_num_fields=256)
                        if re.search(r'(?i)password|passwd|secret|token|api[_-]?key', key) and item)
    elif decoder == 'pem':
        if not _PEM.fullmatch(value):
            raise ValueError('invalid private key')
        lines = tuple(line.strip() for line in value.splitlines() if line and not line.startswith('-----'))
        values = (value, ''.join(lines), *lines)
    elif decoder in ('raw', 'redis'):
        values = (value,)
    else:
        raise ValueError('unknown decoder')
    if len(values) > MAX_VALUES:
        raise ValueError('source constituent limit')
    return values


def _snapshot(profile: SecretSourceProfile) -> _Snapshot:
    values: set[str] = set()
    for spec in profile.sources:
        if any(os.getenv(name) for name in spec.fallback_for):
            continue  # explicit consumer precedence, expressed as metadata
        path = spec.path or ((os.getenv(spec.file_setting) or '').strip() if spec.file_setting else '')
        if spec.package_file:
            package, relative = spec.package_file
            package_spec = PathFinder.find_spec(package)
            if package_spec is None:
                if spec.required:
                    raise ValueError('missing source package')
                continue
            locations = package_spec.submodule_search_locations
            if not locations or len(locations) != 1:
                raise ValueError('ambiguous source package')
            path = os.path.join(locations[0], relative)
        if path:
            try:
                with open(path, 'rb') as stream:
                    raw_bytes = stream.read(MAX_SOURCE + 1)
            except FileNotFoundError:
                # The optional Discord consumer disables itself when its file is absent.
                if spec.package_file and not spec.required:
                    continue
                raise
            if len(raw_bytes) > MAX_SOURCE:
                raise ValueError('source byte limit')
            raw = raw_bytes.decode('utf-8')
        else:
            raw = os.getenv(spec.setting) if spec.setting else None
            if not raw or not raw.strip():
                if spec.required:
                    raise ValueError('missing required source')
                continue
        decoder = 'raw' if spec.decoder == 'redis' and not path else spec.decoder
        values.update(_decode(raw, decoder))
        if len(values) > MAX_VALUES:
            raise ValueError('snapshot constituent limit')
    variants: set[str] = set()
    for value in values:
        variants.add(value)
        variants.update((json.dumps(value, ensure_ascii=True)[1:-1],
                         json.dumps(value, ensure_ascii=False)[1:-1],
                         repr(value)[1:-1]))
        for encoded in (quote(value, safe=''), quote_plus(value, safe='')):
            variants.add(encoded)
            variants.add(re.sub(r'%[0-9A-F]{2}', lambda m: m[0].lower(), encoded))
    variants.discard('')
    return _Snapshot(tuple(sorted(variants, key=len, reverse=True)))


def _redact_assignments(text: str) -> str:
    parts = []
    offset = 0
    for label in _ASSIGN.finditer(text):
        if label.start() < offset or not _SENSITIVE.search(label[1]):
            continue
        value = _VALUE.match(text, label.end())
        if value is None:
            continue
        parts.extend((text[offset:label.end()], REDACTED))
        offset = value.end()
    parts.append(text[offset:])
    return ''.join(parts)


def _redact_pem(text: str) -> str:
    parts = []
    offset = 0
    while match := _PEM_START.search(text, offset):
        parts.extend((text[offset:match.start()], REDACTED))
        footer = '-----END ' + match[1] + '-----'
        end = text.find(footer, match.end())
        if end < 0:
            return ''.join(parts)  # unterminated credential: discard the remainder
        offset = end + len(footer)
    parts.append(text[offset:])
    return ''.join(parts)


def _redact_jwt(match: re.Match) -> str:
    header = match[1]
    if len(header) > MAX_SOURCE:
        return REDACTED
    try:
        decoded = base64.b64decode(header + '=' * (-len(header) % 4), altchars=b'-_', validate=True)
        document = json.loads(decoded)
    except (ValueError, UnicodeError, binascii.Error):
        return match[0]
    return REDACTED if isinstance(document, dict) and 'alg' in document else match[0]


def sanitize_text(text: str, snapshot: _Snapshot) -> str:
    """Internal rendering primitive; callers use safe_text/render_exception."""
    if not isinstance(text, str) or len(text) > MAX_TEXT:
        raise ValueError('diagnostic limit')
    # Percent escapes are case-insensitive independently (including mixed case).
    # Only the static token regex is cached; never compile secret-derived regexes.
    normalized = _PERCENT.sub(lambda m: m[0].upper(), text)
    for value in snapshot.variants:
        needle = _PERCENT.sub(lambda m: m[0].upper(), value)
        start = 0
        parts = []
        while True:
            index = normalized.find(needle, start)
            if index < 0:
                break
            parts.extend((text[start:index], REDACTED))
            start = index + len(needle)
        if parts:
            parts.append(text[start:])
            text = ''.join(parts)
            normalized = normalized.replace(needle, REDACTED)
    text = _redact_pem(text)
    text = _URI.sub(lambda m: m[1] + REDACTED + '@', text)
    text = _JWT.sub(_redact_jwt, text)
    text = _HEADER.sub(lambda m: m[1] + REDACTED, text)
    text = _BEARER.sub(lambda m: m[1] + ' ' + REDACTED, text)
    text = _redact_assignments(text)
    if len(text) > MAX_TEXT:
        raise ValueError('diagnostic output limit')
    return text


def _structure(value, snapshot: _Snapshot, budget: list[int], depth: int = 0):
    budget[0] -= 1
    if budget[0] < 0 or depth > 64:
        raise ValueError('structured diagnostic limit')
    if isinstance(value, str):
        result = sanitize_text(value, snapshot)
        budget[1] -= max(len(value), len(result))
        if budget[1] < 0:
            raise ValueError('aggregate diagnostic limit')
        return result
    if value is None or type(value) in (bool, int, float):
        return value
    if type(value) in (list, tuple):
        return type(value)(_structure(item, snapshot, budget, depth + 1) for item in value)
    if type(value) is dict:
        result = {}
        for key, item in value.items():
            safe_key = _structure(key, snapshot, budget, depth + 1)
            if safe_key in result:
                raise ValueError('sanitized key collision')
            if isinstance(key, str) and re.search(r'(?i)password|passwd|secret|token|api[_-]?key|authorization|cookie', key):
                result[safe_key] = REDACTED
            else:
                result[safe_key] = _structure(item, snapshot, budget, depth + 1)
        return result
    if isinstance(value, BaseException):
        return _structure(str(value), snapshot, budget, depth + 1)
    raise TypeError('unsupported diagnostic object')


def safe_text(value, *, source_profile: SecretSourceProfile) -> str:
    """Render an exception-derived message, failing closed at this output boundary."""
    try:
        return sanitize_text(str(value), _snapshot(source_profile))
    except Exception:  # broad-except: output boundary must never return raw diagnostic data
        return UNAVAILABLE


def safe_structure(value, *, source_profile: SecretSourceProfile):
    """Sanitize JSON-shaped diagnostic content, never the outer API envelope."""
    try:
        return _structure(value, _snapshot(source_profile), [1024, MAX_TEXT])
    except Exception:  # broad-except: serialization boundary discards unsafe diagnostic content
        return UNAVAILABLE


def _exception_text(exc: BaseException) -> str:
    # Bound the graph before TracebackException walks causes/contexts/groups.
    pending = [exc]
    seen: set[int] = set()
    while pending:
        current = pending.pop()
        if id(current) in seen:
            continue
        seen.add(id(current))
        if len(seen) > MAX_VALUES:
            raise ValueError('exception graph limit')
        pending.extend(item for item in (current.__cause__, current.__context__) if item is not None)
        if isinstance(current, BaseExceptionGroup):
            pending.extend(current.exceptions)
    formatted = traceback.TracebackException.from_exception(
        exc, limit=100, capture_locals=False, max_group_width=15, max_group_depth=10,
    )
    parts = []
    size = 0
    for part in formatted.format():
        size += len(part)
        if size > MAX_TEXT:
            raise ValueError('traceback limit')
        parts.append(part)
    return ''.join(parts)


def render_exception(exc: BaseException, *, source_profile: SecretSourceProfile, error_id: str | None = None) -> str:
    """Render frames/chains/notes/groups with no locals and one temporary snapshot.

    Fail-closed output retains only identifiers generated by new_error_id; a
    caller-provided string has no trusted provenance.
    """
    try:
        snapshot = _snapshot(source_profile)
        return sanitize_text(_exception_text(exc), snapshot)
    except Exception:  # broad-except: traceback output boundary fails closed, including broken __str__
        return unavailable(error_id)


def render_current_exception(*, source_profile: SecretSourceProfile, error_id: str | None = None) -> str:
    exc = sys.exception()
    if exc is None:
        return 'NoneType: None\n'
    return render_exception(exc, source_profile=source_profile, error_id=error_id)


def render_stack(*, source_profile: SecretSourceProfile) -> str:
    try:
        return sanitize_text(''.join(traceback.format_stack(limit=100)[:-1]), _snapshot(source_profile))
    except Exception:  # broad-except: stack output is an exceptional diagnostic boundary
        return UNAVAILABLE


def safe_diagnostics(*, source_profile: SecretSourceProfile, **fields):
    """Sanitize a set of named diagnostic fields with a single snapshot.

    The field names are adapter-owned schema keys. On failure retain their
    presence; discard the entire content rather than any raw partial result.
    """
    try:
        snapshot = _snapshot(source_profile)
        budget = [1024, MAX_TEXT]
        return {key: _structure(value, snapshot, budget) for key, value in fields.items()}
    except Exception:  # broad-except: preserve adapter-owned schema, discard failed diagnostic content
        return {key: None if value is None else ([] if isinstance(value, list) else ({} if isinstance(value, dict) else UNAVAILABLE))
                for key, value in fields.items()}
