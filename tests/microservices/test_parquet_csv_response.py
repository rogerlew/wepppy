"""Native CSV HTTP ownership and strict request boundary tests."""
import asyncio
import base64
import json

import pyarrow as pa
import pyarrow.parquet as pq
import pytest

from wepppy.microservices.browse.parquet_csv import CSVResponse, parse_filter
from wepppy.microservices.parquet_filters import ParquetFilterError


def test_normalized_filter_has_bounded_headroom():
    node = {'kind': 'group', 'logic': 'AND', 'children': [
        {'kind': 'condition', 'field': 'x', 'operator': 'Contains', 'value': '😀' * 492}
        for _ in range(32)]}
    raw = json.dumps(node, ensure_ascii=False, separators=(',', ':')).encode()
    assert len(raw) <= 65536
    normalized = parse_filter(base64.urlsafe_b64encode(raw).decode())
    request = json.dumps({'version': 2, 'filter': normalized}, ensure_ascii=False, separators=(',', ':')).encode()
    assert 65536 < len(request) <= 131072


@pytest.mark.parametrize('raw', [b'{"kind":"condition","kind":"group"}', b'\xef\xbb\xbf{}', b'{"value":NaN}', b'[' * 1500])
def test_filter_rejects_non_strict_json(raw):
    with pytest.raises(ParquetFilterError):
        parse_filter(base64.urlsafe_b64encode(raw).decode())


@pytest.mark.parametrize('mode', ['disconnect', 'send_error', 'cancel', 'complete'])
def test_response_owns_artifact_until_terminal_send(tmp_path, native_csv_converter, mode):
    source = tmp_path / 'table.parquet'
    pq.write_table(pa.table({'v': [1, 2]}), source)
    async def exercise():
        artifact = await native_csv_converter.convert(source)
        response = CSVResponse(artifact, 'table.csv', 'test-reference')
        started = asyncio.Event()
        release = asyncio.Event()
        sent = []
        async def send(message):
            sent.append(message)
            if message['type'] == 'http.response.start':
                started.set()
                assert artifact.path.exists()
                if mode == 'send_error':
                    raise OSError('client send failure')
                if mode in ('disconnect', 'cancel'):
                    await release.wait()
        async def receive():
            await started.wait()
            if mode == 'disconnect':
                return {'type': 'http.disconnect'}
            await asyncio.Event().wait()
        task = asyncio.create_task(response({'type': 'http', 'method': 'GET'}, receive, send))
        if mode == 'cancel':
            await started.wait()
            task.cancel()
            with pytest.raises(asyncio.CancelledError):
                await task
        elif mode == 'send_error':
            with pytest.raises(OSError):
                await task
        else:
            await task
        assert not artifact.path.exists()
        with await native_csv_converter.convert(source):
            pass
        if mode == 'complete':
            assert b''.join(m.get('body', b'') for m in sent) == b'v\n1\n2\n'
    asyncio.run(exercise())


def test_lone_surrogate_filter_rejected_but_valid_pair_accepted():
    node = {'kind': 'condition', 'field': 'x', 'operator': 'Contains', 'value': '\ud800'}
    with pytest.raises(ParquetFilterError):
        parse_filter(base64.urlsafe_b64encode(json.dumps(node).encode()).decode())
    node['value'] = '😀'
    assert parse_filter(base64.urlsafe_b64encode(json.dumps(node).encode()).decode())['value'] == '😀'


def test_disconnect_cancels_conversion_and_logs_failed_cleanup(monkeypatch, caplog):
    from wepppy.microservices.browse import parquet_csv
    from wepppy.microservices.parquet_csv import ConversionError
    class Converter:
        async def convert(self, *args):
            try:
                await asyncio.Event().wait()
            except asyncio.CancelledError:
                raise ConversionError('cleanup_failed')
    class Request:
        async def receive(self):
            await asyncio.sleep(.01)
            return {'type': 'http.disconnect'}
    monkeypatch.setattr(parquet_csv, 'CONVERTER', Converter())
    with pytest.raises(asyncio.CancelledError):
        asyncio.run(parquet_csv._convert_connected(None, None, Request(), 'cleanup-correlation'))
    assert 'cleanup-correlation' in caplog.text
    assert 'cleanup_failed' in caplog.text
    assert 'retained_capacity=True' in caplog.text


def test_lone_surrogate_unknown_key_is_safe_validation_error():
    node = {'kind': 'condition', 'field': 'x', 'operator': 'Contains', 'value': 'v', '\ud800': 1}
    with pytest.raises(ParquetFilterError) as caught:
        parse_filter(base64.urlsafe_b64encode(json.dumps(node).encode()).decode())
    json.dumps(caught.value.to_payload(), ensure_ascii=False).encode('utf-8')
