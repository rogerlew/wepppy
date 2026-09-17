"""Retained development-canary HTTP utility; secrets never enter evidence."""
from datetime import datetime, timezone
import json
from pathlib import Path
import requests

ARTIFACTS = Path(__file__).parent
AUTH_FILE = Path('/tmp/wepppy-freshness-runtime-auth.json')


def session():
    auth = json.loads(AUTH_FILE.read_text())
    client = requests.Session()
    client.headers['Authorization'] = 'Bearer ' + auth['token']
    client.cookies.update(auth['cookies'])
    return auth['host'], client


def request(label, method, path, *, payload=None, allow_mutation=False):
    host, client = session()
    if method != 'GET' and not allow_mutation:
        raise ValueError('Mutation requires explicit disposable-scope invocation')
    if method != 'GET' and '/runs/qa-freshness-' not in path:
        raise ValueError('Mutation outside disposable freshness run')
    response = client.request(method, host + path, json=payload, timeout=120)
    try:
        body = response.json()
    except requests.JSONDecodeError:
        body = {'text': response.text[:4000]}
    record = {'utc': datetime.now(timezone.utc).isoformat(), 'method': method,
              'path': path, 'request': payload, 'status': response.status_code,
              'body': body}
    destination = ARTIFACTS / ('runtime_' + label + '.json')
    if destination.exists():
        raise FileExistsError(destination)
    destination.write_text(json.dumps(record, indent=2) + '\n')
    print(label, response.status_code, flush=True)
    response.raise_for_status()
    return body


if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('label')
    parser.add_argument('path')
    parser.add_argument('--payload')
    args = parser.parse_args()
    request(args.label, 'POST' if args.payload else 'GET', args.path,
            payload=json.loads(args.payload) if args.payload else None,
            allow_mutation=bool(args.payload))
