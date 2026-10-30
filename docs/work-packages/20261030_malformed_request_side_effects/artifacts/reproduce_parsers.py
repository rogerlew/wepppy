"""Read-only baseline probe: actual HTTP decoding, no project/queue access."""
import importlib.util
import json
from pathlib import Path
from fastapi import FastAPI, Request
from fastapi.testclient import TestClient
from flask import Flask, request

root = Path('/workdir/wepppy')
spec = importlib.util.spec_from_file_location('probe_payloads', root / 'wepppy/microservices/rq_engine/payloads.py')
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
from wepppy.weppcloud.routes._common import parse_request_payload as flask_parse

api = FastAPI()
@api.post('/probe')
async def probe(req: Request):
    return await module.parse_request_payload(req, boolean_fields={'clean'})
app = Flask(__name__)
@app.post('/probe')
def probe_flask():
    return flask_parse(request, boolean_fields={'clean'})

cases = [('{', 'application/json'), ('[]', 'application/json'), ('null', 'application/json'), ('   ', 'application/json'), ('', 'application/json'), ('{}', 'application/json'), ('{"clean":"not-a-boolean"}', 'application/json'), ('{"clean":2}', 'application/json'), ('{"clean":false}', 'application/json'), ('clean=off', 'application/x-www-form-urlencoded')]
with TestClient(api) as client, app.test_client() as fc:
    for body, media in cases:
        a = client.post('/probe', content=body, headers={'Content-Type': media})
        f = fc.post('/probe', data=body, content_type=media)
        print(json.dumps({'body':body,'media':media,'rq_status':a.status_code,'rq_payload':a.json(),'flask_status':f.status_code,'flask_payload':f.get_json()}))
