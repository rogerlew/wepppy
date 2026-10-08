"""Bounded PRISM requests with retained response evidence."""
from datetime import datetime, timezone
import hashlib
import json
import math
from pathlib import PurePosixPath
import re
import time

import requests

from ._bulk_protocol import (
    DOWNLOAD_ROOT, RELEASE_ROOT, RPC_URL, VARIABLES,
    PrismError, PrismProtocolError, parse_release,
)


def write_json(path, value):
    path.write_text(json.dumps(value, indent=2, sort_keys=True, allow_nan=False) + '\n')


def now():
    return datetime.now(timezone.utc).isoformat()


class BulkTransport:
    def __init__(self, session=None, *, poll_seconds=5.0, job_timeout=600.0):
        if any(not math.isfinite(v) or v <= 0 for v in (poll_seconds, job_timeout)):
            raise ValueError('Polling interval and job timeout must be positive')
        self.session = session if session is not None else requests.Session()
        self.poll_seconds = poll_seconds
        self.job_timeout = job_timeout

    def request(self, method, url, artifact, *, data=None, limit=2_000_000):
        started = time.monotonic()
        try:
            with self.session.request(method, url, data=data, timeout=(10, 60),
                                      # Provider keep-alive expires at the five-second
                                      # polling boundary; do not reuse that socket.
                                      headers={'Connection': 'close'},
                                      allow_redirects=False, stream=True) as response:
                response.raise_for_status()
                if response.status_code != 200:
                    raise PrismProtocolError(f'Unexpected HTTP {response.status_code}')
                chunks, length = [], 0
                for chunk in response.iter_content(65536):
                    length += len(chunk)
                    if length > limit:
                        raise PrismProtocolError(f'PRISM response exceeds {limit} bytes')
                    chunks.append(chunk)
                raw = b''.join(chunks)
                write_json(artifact, dict(url=url, request=data, status=response.status_code,
                    retrieved_utc=now(), seconds=time.monotonic()-started,
                    headers=dict(response.headers), bytes=length,
                    sha256=hashlib.sha256(raw).hexdigest(),
                    body=raw.decode('utf-8', errors='replace') if limit == 2_000_000 else None))
                return raw
        except requests.RequestException as exc:
            raise PrismError(f'PRISM HTTP request failed for {url}: {exc}') from exc

    def manifests(self, start, end, attempt, label):
        result = {}
        for variable in VARIABLES:
            url = f'{RELEASE_ROOT}/{variable}/{start:%Y%m%d}/{end:%Y%m%d}?json=true'
            raw = self.request('GET', url, attempt / f'{label}-{variable}.json')
            result[variable] = parse_release(raw, variable, start, end)
        write_json(attempt / f'{label}.json', result)
        return result

    def extract(self, cells, start, end, attempt):
        params = dict(call='pp/daily_timeseries_mp', proc='gridserv', spares='800m',
            interp='0', stats=' '.join(VARIABLES), units='si', range='daily',
            start=f'{start:%Y%m%d}', end=f'{end:%Y%m%d}',
            lons='|'.join(f'{c.center[0]:.10f}' for c in cells),
            lats='|'.join(f'{c.center[1]:.10f}' for c in cells),
            names='|'.join(c.id for c in cells))
        write_json(attempt / 'request.json', params)
        started = time.monotonic()
        raw = self.request('POST', RPC_URL, attempt / 'submit.json', data=params)
        ticket = None
        for poll in range(121):
            try:
                response = json.loads(raw)
            except (ValueError, UnicodeError) as exc:
                raise PrismProtocolError('Non-JSON PRISM job response') from exc
            if not isinstance(response, dict) or response.get('errors'):
                raise PrismProtocolError(f'PRISM job failed: {response}')
            if 'result' in response:
                result = response['result']
                relative = result.get('csv') if isinstance(result, dict) else None
                if (not isinstance(relative, str) or not re.fullmatch(r'[A-Za-z0-9_./-]+\.csv', relative)
                        or relative.startswith('/') or '..' in PurePosixPath(relative).parts):
                    raise PrismProtocolError('Invalid PRISM download path')
                if time.monotonic()-started > self.job_timeout:
                    raise TimeoutError('PRISM job deadline exceeded')
                return self.request('GET', DOWNLOAD_ROOT + relative, attempt / 'download.json', limit=64_000_000)
            ticket = response.get('gricket', ticket)
            if not isinstance(ticket, str) or not ticket or 'delay' not in response:
                raise PrismProtocolError('Missing PRISM job ticket/status')
            remaining = self.job_timeout - (time.monotonic()-started)
            if remaining <= 0 or poll == 120:
                raise TimeoutError(f'PRISM bulk job timed out; ticket retained: {ticket}')
            time.sleep(min(self.poll_seconds, remaining))
            raw = self.request('POST', RPC_URL, attempt / f'poll-{poll}.json',
                               data=dict(call='pp/checkup', proc='gridserv', gricket=ticket))
        raise AssertionError('Unreachable polling state')
