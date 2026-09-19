"""Bounded Forest validation client; run inside the existing weppcloud container."""
import argparse
from datetime import datetime, timezone
import json

import requests
from wepppy.weppcloud.utils.auth_tokens import issue_token

SOURCE = 'equestrian-bonheur'
TARGET = 'cover-defaults-validation-20260919'
CONFIG = 'canada-wbt-mofe'
BASE = 'https://wc.bearhive.duckdns.org/rq-engine/api'


def main():
    parser = argparse.ArgumentParser(__doc__)
    parser.add_argument('operation', choices=['discover', 'discover-target', 'fork', 'job', 'modify', 'run', 'archive', 'restore'])
    parser.add_argument('--job')
    parser.add_argument('--archive')
    args = parser.parse_args()
    token = issue_token('cover-defaults-validation', scopes=['rq:read', 'rq:status', 'rq:enqueue'],
                        runs=[SOURCE, TARGET], audience='rq-engine', expires_in=900,
                        extra_claims={'token_class': 'service'})['token']
    session = requests.Session()
    session.headers['Authorization'] = 'Bearer ' + token
    def call(method, path, body=None):
        response = session.request(method, BASE + path, json=body, timeout=300)
        print(json.dumps({'at': datetime.now(timezone.utc).isoformat(), 'method': method,
                          'path': path, 'status': response.status_code, 'body': response.json()}))
        response.raise_for_status()
    source = f'/runs/{SOURCE}/{CONFIG}'
    target = f'/runs/{TARGET}/{CONFIG}'
    if args.operation == 'discover':
        for path in ['/configs', '/endpoints', '/endpoints/rq_engine_create/schema',
                     source + '/pipeline', source + '/readiness',
                     source + '/endpoints?include_operation_docs=true']:
            call('GET', path)
    elif args.operation == 'discover-target':
        for suffix in ('/pipeline', '/readiness', '/endpoints?include_operation_docs=true', '/outputs'):
            call('GET', target + suffix)
    elif args.operation == 'fork':
        call('POST', source + '/fork', {'target_runid': TARGET, 'undisturbify': False,
             'skip_wepp_runs_output': True, 'skip_omni_scenarios_contrasts': True})
    elif args.operation == 'job':
        assert args.job
        call('GET', '/jobinfo/' + args.job)
    elif args.operation == 'modify':
        call('POST', target + '/modify-landuse', {'topaz_ids': [101], 'landuse': '406'})
    elif args.operation == 'run':
        call('POST', target + '/run-wepp', {})  # Intentionally omit kslast.
    elif args.operation == 'archive':
        call('POST', target + '/archive', {})
    elif args.operation == 'restore':
        assert args.archive and args.archive.startswith(TARGET + '.') and '/' not in args.archive
        call('POST', target + '/restore-archive', {'archive_name': args.archive})


if __name__ == '__main__':
    main()
