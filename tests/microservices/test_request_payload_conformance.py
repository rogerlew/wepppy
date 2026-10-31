"""Real HTTP decoding in both adapters; no project or queue is involved."""
import io
import pytest
from fastapi import FastAPI, APIRouter, Request
from fastapi.testclient import TestClient
from flask import Flask, request
from flask_wtf.csrf import CSRFProtect, generate_csrf

from wepppy.microservices.rq_engine.payloads import PayloadRoute, parse_request_payload
from wepppy.weppcloud.routes._common import LoggedBlueprint, parse_request_payload as flask_parse
from wepppy.weppcloud.request import PayloadRequest

pytestmark = pytest.mark.microservice


@pytest.fixture(params=['rq', 'flask'])
def client(request):
    flags = {'clean', 'clean_hillslopes'}
    if request.param == 'rq':
        app = FastAPI()
        router = APIRouter(route_class=PayloadRoute)
        @router.post('/probe')
        async def probe(req: Request):
            return await parse_request_payload(req, boolean_fields=flags)
        app.include_router(router)
        with TestClient(app) as http:
            yield lambda body, media: http.post('/probe', content=body, headers={'Content-Type': media} if media else {})
    else:
        app = Flask(__name__)
        app.request_class = PayloadRequest
        bp = LoggedBlueprint('probe', __name__)
        @bp.post('/probe')
        def probe():
            return flask_parse(__import__('flask').request, boolean_fields=flags)
        app.register_blueprint(bp)
        with app.test_client() as http:
            yield lambda body, media: http.post('/probe', input_stream=io.BytesIO(body), content_length=len(body), content_type=media or None)


def response_json(response):
    return response.json() if callable(response.json) else response.json


@pytest.mark.parametrize('body', [b'{', b'[]', b'null', b'false', b'2', b'"text"', b' ', b'\xff', b'{"n":NaN}', b'{"n":Infinity}'])
def test_invalid_json_is_never_absence(client, body):
    response = client(body, 'application/json')
    assert response.status_code == 400
    assert response_json(response) == {'error': {'code': 'invalid_request', 'message': 'Invalid request payload.'}}


@pytest.mark.parametrize('body,media,expected', [
    (b'', '', {}), (b'', 'application/json', {}), (b'{}', 'application/json', {}),
    (b'{}', '', {}), (b'{"clean":false}', 'Application/JSON; charset=utf-8', {'clean': False}),
    (b'{"clean":0}', 'application/vnd.test+json', {'clean': False}),
    (b'clean=off', 'application/x-www-form-urlencoded', {'clean': False}),
    (b'clean=yes&clean=1', 'application/x-www-form-urlencoded', {'clean': True}),
    (b'', 'application/x-www-form-urlencoded', {}),
    (b'{"clean":null}', 'application/json', {'clean': None}),
    (b'{"clean":""}', 'application/json', {'clean': ''}),
])
def test_valid_defaults_forms_false_and_sentinels(client, body, media, expected):
    response = client(body, media)
    assert response.status_code == 200
    assert response_json(response) == expected


@pytest.mark.parametrize('value', ['"invalid"', '2', '-1', '[]', '[false]', '[false,true]', '{}'])
def test_scalar_flags_reject_supplied_invalid_values(client, value):
    response = client(('{"clean":'+value+'}').encode(), 'application/json')
    assert response.status_code == 400
    assert response_json(response)['error']['code'] == 'invalid_request'


@pytest.mark.parametrize('body,media', [
    (b'clean=on&clean=off','application/x-www-form-urlencoded'),
    (b'name=%FF','application/x-www-form-urlencoded'),
    (b'{"clean":false,"clean_hillslopes":true}','application/json'),
    (b'{}','text/plain'), (b'not json',''),
    (b'','multipart/form-data; boundary=a'),
    (b'--a\r\nContent-Disposition: form-data; name="clean"\r\n\r\nfalse','multipart/form-data; boundary=a'),
    (b'--a--\r\n','multipart/form-data'),
])
def test_ambiguous_or_malformed_transport(client, body, media):
    response=client(body,media)
    assert response.status_code == 400
    assert response_json(response)['error']['code'] == 'invalid_request'


@pytest.mark.parametrize("json_only", [False, True])
def test_flask_csrf_early_form_read_retains_parse_failure(json_only):
    app=Flask(__name__)
    app.secret_key='test-only'
    app.request_class=PayloadRequest
    CSRFProtect(app)
    bp=LoggedBlueprint('csrf_probe', __name__)
    effects=[]
    @bp.get('/token')
    def token():
        return {'token': generate_csrf()}
    @bp.post('/probe')
    def probe():
        from wepppy.weppcloud.routes._common import parse_json_payload
        payload=(parse_json_payload if json_only else flask_parse)(request)
        effects.append(payload)
        return payload
    app.register_blueprint(bp)
    with app.test_client() as client:
        token=client.get('/token').json['token']
        response=client.post('/probe',data=b'--broken',content_type='multipart/form-data; boundary=a',headers={'X-CSRFToken':token})
        assert response.status_code == 400
        assert response.json['error']['code']=='invalid_request'
        assert effects==[]
        assert client.post('/probe',json={},headers={'X-CSRFToken':token}).status_code==200
        assert effects==[{}]


def test_rq_chunked_request_without_content_length_rejects_malformed():
    from wepppy.microservices.rq_engine import rhem_routes
    app = FastAPI()
    router=APIRouter(route_class=PayloadRoute)
    @router.post('/probe')
    async def probe(req: Request):
        assert 'content-length' not in req.headers
        return await parse_request_payload(req)
    app.include_router(router)
    with TestClient(app) as client:
        response=client.post('/probe',content=iter([b'{']),headers={'Content-Type':'application/json'})
        assert response.status_code==400
        assert client.post('/probe',content=iter([b'{}']),headers={'Content-Type':'application/json'}).json()=={}


@pytest.mark.parametrize('failure', ['disconnect', 'cancel', 'operational'])
def test_rq_multipart_transport_failures_close_spools(monkeypatch, failure):
    import asyncio
    import starlette.formparsers as parsers
    from starlette.requests import Request, ClientDisconnect
    from wepppy.microservices.rq_engine.payloads import request_payload
    handles = []
    factory = parsers.SpooledTemporaryFile
    def spool(*args, **kwargs):
        handle = factory(*args, **kwargs); handles.append(handle); return handle
    monkeypatch.setattr(parsers, 'SpooledTemporaryFile', spool)
    sent = False
    exception = {'disconnect': ClientDisconnect, 'cancel': asyncio.CancelledError, 'operational': OSError}[failure]
    async def receive():
        nonlocal sent
        if sent:
            raise exception()
        sent = True
        return {'type':'http.request', 'more_body':True,
                'body':b'--a\r\nContent-Disposition: form-data; name="file"; filename="x"\r\n\r\nx'}
    req = Request({'type':'http','method':'POST','headers':[(b'content-type',b'multipart/form-data; boundary=a')]}, receive)
    with pytest.raises(exception):
        asyncio.run(request_payload(req))
    assert handles and all(handle.closed for handle in handles)


def test_flask_form_size_error_closes_partial_upload():
    from werkzeug.exceptions import RequestEntityTooLarge
    from wepppy.weppcloud.request import StrictFormDataParser
    handles = []
    def spool(*args, **kwargs):
        handle = io.BytesIO(); handles.append(handle); return handle
    body = (b'--a\r\nContent-Disposition: form-data; name="file"; filename="x"\r\n\r\nx\r\n'
            b'--a\r\nContent-Disposition: form-data; name="second"\r\n\r\nx\r\n--a--\r\n')
    parser = StrictFormDataParser(stream_factory=spool, max_form_parts=1)
    with pytest.raises(RequestEntityTooLarge):
        parser.parse(io.BytesIO(body), 'multipart/form-data', len(body), {'boundary':'a'})
    assert handles and all(handle.closed for handle in handles)


@pytest.mark.parametrize('declared_length', [4, None])
def test_flask_url_form_limit_precedes_encoding_buffer(declared_length):
    from werkzeug.exceptions import RequestEntityTooLarge
    from wepppy.weppcloud.request import StrictFormDataParser
    reads = []
    class ObservedStream(io.BytesIO):
        def read(self, size=-1):
            reads.append(size)
            assert size >= 0
            return super().read(size)
    with pytest.raises(RequestEntityTooLarge):
        StrictFormDataParser(max_form_memory_size=2).parse(
            ObservedStream(b'a=12'), 'application/x-www-form-urlencoded', declared_length, {})
    assert reads == ([] if declared_length else [3])
