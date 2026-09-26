"""Exercise actual streaming multipart admission, including hostile framing."""
import asyncio

import pytest
from starlette.requests import Request
import starlette.formparsers as formparsers

from wepppy.microservices.rq_engine.single_input_uploads import input_payload
from wepppy.wepp.single_input import MAX_SOURCE_BYTES, SingleInputError

pytestmark = pytest.mark.unit


def multipart(parts, boundary='source-test', finished=True):
    result = b''
    for field, filename, data in parts:
        disposition = f'Content-Disposition: form-data; name="{field}"'
        if filename is not None:
            disposition += f'; filename="{filename}"'
        result += f'--{boundary}\r\n{disposition}\r\n\r\n'.encode() + data + b'\r\n'
    if finished:
        result += f'--{boundary}--\r\n'.encode()
    return result


def request_for(body, *, boundary='source-test'):
    offset = 0
    async def receive():
        nonlocal offset
        chunk = body[offset:offset + 8192]
        offset += len(chunk)
        return {'type': 'http.request', 'body': chunk, 'more_body': offset < len(body)}
    return Request({'type': 'http', 'method': 'POST', 'headers': [
        (b'content-type', f'multipart/form-data; boundary={boundary}'.encode()),
        (b'content-length', b'1'),  # must count streamed bytes, not trust this
    ]}, receive)


def test_valid_upload_boolean_normalization_and_cleanup(monkeypatch):
    handles = []
    original = formparsers.SpooledTemporaryFile
    def spool(*args, **kwargs):
        handle = original(*args, **kwargs); handles.append(handle); return handle
    monkeypatch.setattr(formparsers, 'SpooledTemporaryFile', spool)
    body = multipart([('input_upload_single_soil', 'Soil.SOL', b'7778\n'), ('clear', None, b'on')])
    async def run():
        async with input_payload(request_for(body), 'soils', boolean_fields={'clear'}) as (payload, form):
            assert payload['clear'] is True
            assert await form['input_upload_single_soil'].read() == b'7778\n'
    asyncio.run(run())
    assert handles and all(handle.closed for handle in handles)


@pytest.mark.parametrize('parts,finished,status', [
    ([('input_upload_single_soil', 'a.sol', b'x' * (MAX_SOURCE_BYTES + 1))], True, 413),
    ([('input_upload_single_soil', 'a.sol', b'x'), ('input_upload_single_soil', 'b.sol', b'x')], True, 400),
    ([('unexpected', 'a.sol', b'x')], True, 400),
    ([('input_upload_single_soil', 'a.sol', b'x')], False, 400),
    ([('field', None, b'x' * 16385)], True, 413),
    ([(f'field{i}', None, b'x') for i in range(65)], True, 400),
])
def test_invalid_stream_is_bounded_and_closes_spools(monkeypatch, parts, finished, status):
    handles = []
    original = formparsers.SpooledTemporaryFile
    def spool(*args, **kwargs):
        handle = original(*args, **kwargs); handles.append(handle); return handle
    monkeypatch.setattr(formparsers, 'SpooledTemporaryFile', spool)
    async def run():
        async with input_payload(request_for(multipart(parts, finished=finished)), 'soils'):
            pytest.fail('malformed request admitted')
    with pytest.raises(SingleInputError) as error:
        asyncio.run(run())
    assert error.value.status_code == status
    assert all(handle.closed for handle in handles)


def test_file_fields_require_multipart():
    body = b'{"input_upload_single_soil": "fake.sol"}'
    async def receive():
        return {'type': 'http.request', 'body': body, 'more_body': False}
    request = Request({'type': 'http', 'method': 'POST', 'headers': [(b'content-type', b'application/json')]}, receive)
    async def run():
        async with input_payload(request, 'soils'):
            pytest.fail('scalar file admitted')
    with pytest.raises(SingleInputError, match='multipart'):
        asyncio.run(run())
