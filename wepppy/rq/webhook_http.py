"""Pinned HTTPS delivery in a killable process. Never log a destination or body.

The subprocess boundary enforces the *total* DNS/TCP/TLS/header deadline. Socket
read timeouts alone cannot bound a resolver or a receiver trickling bytes.
"""
from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime
import ipaddress
import json
import re
import socket
import ssl
import subprocess
import sys
from urllib.parse import quote, urlsplit, urlunsplit

from . import webhook_policy as policy


class InvalidDestination(ValueError):
    """Public error deliberately excludes the rejected URL."""


@dataclass(frozen=True)
class Destination:
    url: str
    host: str
    target: str


def destination(value: object) -> Destination:
    if not isinstance(value, str) or not value:
        raise InvalidDestination('Expected a nonempty HTTPS callback URL within the size limit.')
    try:
        if len(value.encode('utf-8')) > policy.URL_BYTES:
            raise InvalidDestination('Callback URL exceeds the size limit.')
    except UnicodeError:
        raise InvalidDestination('Invalid callback URL syntax.') from None
    if any(ord(c) <= 32 or ord(c) == 127 for c in value) or '\\' in value:
        raise InvalidDestination('Invalid callback URL syntax.')
    try:
        parts = urlsplit(value)
        if parts.scheme != 'https' or not parts.hostname or parts.username is not None or parts.password is not None:
            raise ValueError
        if parts.fragment or '#' in value or parts.port not in (None, 443):
            raise ValueError
        host = parts.hostname.encode('idna').decode('ascii').lower()
        if len(host) > 253 or not all(re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', label) for label in host.split('.')):
            raise ValueError
        try:
            ipaddress.ip_address(host)
        except ValueError:
            pass
        else:
            raise ValueError
        try:
            socket.inet_aton(host)
        except OSError:
            pass
        else:
            raise ValueError
        # Reject numeric/legacy inet_aton names, trailing dots and percent authority.
        if '%' in parts.netloc or ':' in host or host.replace('.', '').isdigit():
            raise ValueError
        path = quote(parts.path or '/', safe="/%:@!$&'()*+,;=-._~")
        query = quote(parts.query, safe="/%?:@!$&'()*+,;=-._~")
        target = path + ('?' + query if query else '')
        normalized = urlunsplit(('https', host, path, query, ''))
        if len(normalized.encode()) > policy.URL_BYTES:
            raise ValueError
        return Destination(normalized, host, target)
    except (ValueError, UnicodeError):
        raise InvalidDestination('Invalid callback URL syntax.') from None


def public_address(value: str) -> bool:
    try:
        address = ipaddress.ip_address(value)
    except ValueError:
        return False
    if not address.is_global or address.is_multicast or address.is_reserved or address.is_unspecified:
        return False
    if isinstance(address, ipaddress.IPv6Address):
        if address.is_site_local or address in ipaddress.ip_network('3fff::/20'):
            return False
        if address.ipv4_mapped or address.sixtofour or address.teredo:
            return False
        # Translation prefixes can hide private IPv4 destinations.
        if address in ipaddress.ip_network('64:ff9b::/96') or address in ipaddress.ip_network('64:ff9b:1::/48'):
            return False
    return True


def retry_after(value: str | None, now: datetime | None = None) -> int | None:
    if value is None:
        return None
    try:
        if value.isascii() and value.isdigit():
            seconds = int(value[:12])
        else:
            date = parsedate_to_datetime(value)
            if date.tzinfo is None:
                return None
            seconds = int((date - (now or datetime.now(timezone.utc))).total_seconds())
        return max(0, min(seconds, policy.RETRY_AFTER_MAX))
    except (ValueError, TypeError, OverflowError):
        return None


def _exchange(target: Destination, body: bytes, event_id: str, seconds: float) -> dict:
    answers = socket.getaddrinfo(target.host, 443, type=socket.SOCK_STREAM)
    if not answers or any(not public_address(answer[4][0]) for answer in answers):
        return {'error': 'unsafe_destination', 'transient': False}
    family, kind, protocol, _, address = answers[0]
    context = ssl.create_default_context()
    with socket.socket(family, kind, protocol) as raw:
        raw.settimeout(seconds)
        raw.connect(address)
        with context.wrap_socket(raw, server_hostname=target.host) as stream:
            if ipaddress.ip_address(stream.getpeername()[0]) != ipaddress.ip_address(address[0]):
                return {'error': 'unsafe_destination', 'transient': False}
            request = (f'POST {target.target} HTTP/1.1\r\nHost: {target.host}\r\n'
                       f'Content-Type: application/json\r\nWebhook-Id: {event_id}\r\n'
                       f'Content-Length: {len(body)}\r\nConnection: close\r\n\r\n').encode('ascii')
            stream.sendall(request + body)
            return _read_response(stream)


def _read_response(stream) -> dict:
    total = 0
    while True:
        headers = bytearray()
        # Do not consume receiver bodies, even when headers/body share a packet.
        while not headers.endswith(b'\r\n\r\n'):
            if total >= policy.HEADER_BYTES:
                return {'error': 'response_headers', 'transient': False}
            chunk = stream.recv(1)
            if not chunk:
                return {'error': 'connection', 'transient': True}
            headers.extend(chunk)
            total += 1
        lines = headers.decode('iso-8859-1').split('\r\n')
        status_line = re.fullmatch(r'HTTP/1\.[01] ([1-5][0-9]{2})(?: [^\r\n]*)?', lines[0])
        if status_line is None:
            return {'error': 'response_headers', 'transient': False}
        status = int(status_line.group(1))
        if 100 <= status < 200 and status != 101:
            continue  # Informational blocks share the same total header/deadline budget.
        delay = None
        for line in lines[1:]:
            name, separator, value = line.partition(':')
            if separator and name.lower() == 'retry-after':
                delay = retry_after(value.strip())
        return {'status': status, 'transient': status in policy.RETRY_STATUSES, 'retry_after': delay}


def _child(payload: dict) -> dict:
    try:
        return _exchange(destination(payload['url']), payload['body'].encode('utf-8'), payload['event_id'], payload['seconds'])
    except InvalidDestination:
        return {'error': 'unsafe_destination', 'transient': False}
    except ssl.SSLError:
        return {'error': 'tls', 'transient': False}
    except socket.gaierror as exc:
        return {'error': 'dns', 'transient': exc.errno == socket.EAI_AGAIN}
    except (TimeoutError, OSError):
        return {'error': 'connection', 'transient': True}


def deliver(url: str, body: str, event_id: str, *, seconds: float = policy.ATTEMPT_SECONDS) -> dict:
    """Return only bounded safe audit fields; caller persists attempt-start first."""
    destination(url)
    if len(body.encode('utf-8')) > policy.EVENT_BYTES or not re.fullmatch(r'[A-Za-z0-9-]{1,64}', event_id):
        raise ValueError('Invalid webhook event envelope.')
    if seconds <= 0:
        return {'error': 'timeout', 'transient': True}
    seconds = min(seconds, policy.ATTEMPT_SECONDS)
    payload = json.dumps({'url': url, 'body': body, 'event_id': event_id, 'seconds': seconds})
    try:
        completed = subprocess.run([sys.executable, '-m', 'wepppy.rq.webhook_http'], input=payload,
                                   text=True, capture_output=True, timeout=seconds, check=False)
    except subprocess.TimeoutExpired:
        return {'error': 'timeout', 'transient': True}
    if completed.returncode != 0:
        return {'error': 'sender', 'transient': False}
    try:
        return json.loads(completed.stdout)
    except (ValueError, TypeError):
        return {'error': 'sender', 'transient': False}


if __name__ == '__main__':
    # Boundary: all unexpected child errors are collapsed, never print raw URL,
    # traceback, TLS diagnostic, response headers or inherited credentials.
    try:
        result = _child(json.loads(sys.stdin.read(policy.URL_BYTES + policy.EVENT_BYTES + 4096)))
    except Exception:
        result = {'error': 'sender', 'transient': False}
    sys.stdout.write(json.dumps(result))
