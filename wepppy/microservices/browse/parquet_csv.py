"""On-demand CSV downloads: one native backend, fixed policy, owned response lifetime."""
from __future__ import annotations

import asyncio
import base64
import binascii
import logging
import json
import hashlib
import math
from pathlib import Path
import time
from urllib.parse import quote

from starlette.responses import JSONResponse, Response

from wepppy.microservices.parquet_csv import Converter, ConversionError, Limits
from wepppy.microservices.parquet_csv.provenance import strict_json
from wepppy.microservices.parquet_csv.runner import _finish_despite_cancellation, _owned_thread
from wepppy.microservices.parquet_filters import ParquetFilterError, validate_filter_tree
from wepppy.observability.correlation import generate_correlation_id
from .errors import request_id

LOGGER = logging.getLogger(__name__)
CONVERTER = Converter(Path('/usr/local/bin/parquet_csv_cli'),
                      Path('/opt/parquet-csv/provenance.json'),
                      Path('/tmp/wepppy-parquet-csv'), Limits())
SERVING_SECONDS = 600
STATUS = {
    'busy': 503, 'validation_error': 422, 'no_rows_matched_filter': 422,
    'parquet_filter_row_limit_exceeded': 413, 'resource_limit': 413,
    'input_too_large': 413, 'input_rejected': 422, 'source_rejected': 422,
    'source_changed': 409, 'timeout': 504, 'staging_timeout': 504,
    'provenance_invalid': 503, 'spawn_failed': 503,
    'arguments': 500, 'io_error': 500, 'protocol_error': 500,
    'diagnostic_overflow': 500, 'child_failed': 500, 'output_invalid': 500,
    'cleanup_failed': 500,
}
FILTER_CODES = {'validation_error', 'no_rows_matched_filter', 'parquet_filter_row_limit_exceeded'}


def parse_filter(raw: str | None) -> dict | None:
    if not raw or not raw.strip():
        return None
    if len(raw) > 87384:
        raise ParquetFilterError('Parquet filter payload is too large.', node_path='pqf')
    try:
        value = raw.strip().encode('ascii')
        decoded = base64.b64decode(value + b'=' * (-len(value) % 4), altchars=b'-_', validate=True)
        if len(decoded) > 65536:
            raise ValueError('payload size')
        parsed = strict_json(decoded)
        # Validate Unicode scalar values before shared errors can echo bad keys.
        json.dumps(parsed, ensure_ascii=False).encode("utf-8")
        node = validate_filter_tree(parsed)
    except (ValueError, UnicodeError, binascii.Error) as exc:
        if isinstance(exc, ParquetFilterError):
            raise
        raise ParquetFilterError('Invalid parquet filter payload.', node_path='pqf') from exc

    def normalize(item):
        if item['kind'] == 'group':
            for child in item['children']:
                normalize(child)
        else:
            try:
                number = float(item['value'])
            except ValueError:
                number = None
            item['number'] = number if number is not None and math.isfinite(number) else None
    normalize(node)
    return node


class CSVResponse(Response):
    """Hold the completed artifact through ASGI send, including every failure path."""

    def __init__(self, artifact, filename: str, reference: str):
        self.artifact = artifact
        self.reference = reference
        super().__init__(content=b'', media_type='text/csv', headers={
            'Content-Length': str(artifact.bytes),
            'Content-Disposition': "attachment; filename*=UTF-8''" + quote(filename, safe=''),
            'X-Request-Id': reference,
        })

    async def __call__(self, scope, receive, send):
        digest = hashlib.sha256()
        served_bytes = 0
        async def stream():
            nonlocal served_bytes
            # This response intentionally ignores Range and conditional headers.
            with self.artifact.path.open('rb') as source:
                await send({'type': 'http.response.start', 'status': 200, 'headers': self.raw_headers})
                if scope.get('method') != 'HEAD':
                    while chunk := await _owned_thread(source.read, 64 * 1024):
                        digest.update(chunk)
                        served_bytes += len(chunk)
                        await send({'type': 'http.response.body', 'body': chunk, 'more_body': True})
                if scope.get('method') != 'HEAD' and served_bytes != self.artifact.bytes:
                    raise ConversionError('output_invalid')
                await send({'type': 'http.response.body', 'body': b'', 'more_body': False})

        async def disconnected():
            while True:
                if (await receive())['type'] == 'http.disconnect':
                    return

        tasks = [asyncio.create_task(stream()), asyncio.create_task(disconnected())]
        outcome = 'cancelled'
        try:
            done, _ = await asyncio.wait(tasks, timeout=SERVING_SECONDS,
                                         return_when=asyncio.FIRST_COMPLETED)
            if not done:
                outcome = 'serving_timeout'
                raise TimeoutError('CSV serving deadline')
            if tasks[0] in done:
                outcome = 'send_failed'
                tasks[0].result()
                outcome = 'served'
            else:
                outcome = 'disconnected'
        finally:
            async def finalize():
                for task in tasks:
                    if not task.done():
                        task.cancel()
                await asyncio.gather(*tasks, return_exceptions=True)
                await _owned_thread(self.artifact.cleanup)
            try:
                await _finish_despite_cancellation(asyncio.create_task(finalize()))
            except ConversionError as exc:
                outcome = 'cleanup_failed'
                LOGGER.error('parquet_csv request_id=%s outcome=%s during=response_cleanup retained_capacity=true',
                             self.reference, exc.code)
                raise
            finally:
                LOGGER.info('parquet_csv request_id=%s outcome=%s rows=%s input_bytes=%s output_bytes=%s input_sha256=%s output_sha256=%s conversion_seconds=%s peak_rss_kib=%s cpu_seconds=%s',
                            self.reference, outcome, self.artifact.rows, self.artifact.input_bytes, self.artifact.bytes,
                            self.artifact.input_sha256, digest.hexdigest() if outcome == 'served' and served_bytes == self.artifact.bytes else None,
                            self.artifact.wall_seconds, self.artifact.peak_rss_kib, self.artifact.cpu_seconds)



async def _convert_connected(source, tree, request, reference):
    if request is None:
        return await CONVERTER.convert(source, tree)

    async def disconnected():
        while (await request.receive())['type'] != 'http.disconnect':
            pass

    conversion = asyncio.create_task(CONVERTER.convert(source, tree))
    watcher = asyncio.create_task(disconnected())
    transferred = False
    try:
        done, _ = await asyncio.wait([conversion, watcher], return_when=asyncio.FIRST_COMPLETED)
        if watcher in done:
            watcher.result()
            raise asyncio.CancelledError('CSV client disconnected')
        artifact = conversion.result()
        transferred = True
        return artifact
    finally:
        async def finalize():
            for task in (conversion, watcher):
                if not task.done():
                    task.cancel()
            await asyncio.gather(conversion, watcher, return_exceptions=True)
            if not transferred and not conversion.cancelled():
                failure = conversion.exception()
                if failure is None:
                    await _owned_thread(conversion.result().cleanup)
                else:
                    code = failure.code if isinstance(failure, ConversionError) else type(failure).__name__
                    LOGGER.error('parquet_csv request_id=%s outcome=%s during=request_cleanup retained_capacity=%s',
                                 reference, code, code == 'cleanup_failed')
        cleanup = asyncio.create_task(finalize())
        try:
            await asyncio.shield(cleanup)
        except asyncio.CancelledError:
            await _finish_despite_cancellation(cleanup)
            if transferred:
                await _finish_despite_cancellation(asyncio.create_task(_owned_thread(conversion.result().cleanup)))
            raise


async def csv_response(path: str, raw_filter: str | None, request=None) -> Response:
    reference = request_id(request) if request is not None else generate_correlation_id()
    started = time.monotonic()
    try:
        tree = parse_filter(raw_filter)
        # The route already authorizes containment (including supported shared roots).
        artifact = await _convert_connected(Path(path).resolve(strict=True), tree, request, reference)
    except asyncio.CancelledError:
        LOGGER.info('parquet_csv request_id=%s outcome=cancelled duration_seconds=%.3f', reference, time.monotonic()-started)
        raise
    except ParquetFilterError as exc:
        payload = exc.to_payload()
        payload['request_id'] = reference
        return JSONResponse(payload, status_code=exc.status_code, headers={'X-Request-Id': reference})
    except ConversionError as exc:
        code = exc.code if exc.code in STATUS else 'protocol_error'
        public_code = code if code in FILTER_CODES else 'parquet_csv_' + code
        message = {
            'busy': 'CSV conversion is busy. Retry shortly.',
            'no_rows_matched_filter': 'No rows matched the parquet filter.',
            'validation_error': 'Invalid parquet filter.',
            'parquet_filter_row_limit_exceeded': 'The parquet filter matched too many rows.',
        }.get(code, 'CSV conversion could not complete. The original Parquet file remains available.')
        LOGGER.warning('parquet_csv request_id=%s outcome=%s duration_seconds=%.3f input_sha256=%s input_bytes=%s output_sha256=None',
                       reference, code, time.monotonic()-started, exc.input_sha256, exc.input_bytes)
        headers = {'X-Request-Id': reference}
        if code == 'busy':
            headers['Retry-After'] = '1'
        return JSONResponse({'error': {'code': public_code, 'message': message, 'details': message},
                             'request_id': reference}, status_code=STATUS[code], headers=headers)
    try:
        return CSVResponse(artifact, Path(path).stem + '.csv', reference)
    except BaseException:  # broad-except: release artifact if response construction fails
        await _finish_despite_cancellation(asyncio.create_task(_owned_thread(artifact.cleanup)))
        raise
