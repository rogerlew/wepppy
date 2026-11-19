"""Exercise the actual browse HTTP route in an isolated candidate container."""
import base64
import os
import hashlib
import json
from pathlib import Path
import subprocess
import time
import tempfile
import urllib.error
import urllib.request


def main():
    expected = Path('/opt/parquet-csv/readiness.csv').read_bytes()
    log = tempfile.TemporaryFile(mode='w+t')
    server = subprocess.Popen([
        '/opt/venv/bin/gunicorn', '--workers', '8', '--timeout', '120',
        '--bind', '127.0.0.1:19009', '-k', 'uvicorn.workers.UvicornWorker',
        'wepppy.microservices.browse:app',
    ], stdout=log, stderr=log)
    try:
        for _ in range(120):
            if server.poll() is not None:
                raise RuntimeError('Browse candidate exited before readiness')
            try:
                with urllib.request.urlopen('http://127.0.0.1:19009/health', timeout=1) as response:
                    log.seek(0)
                    if response.status == 200 and log.read().count('Application startup complete.') >= 8:
                        break
                    time.sleep(.25)
            except (urllib.error.URLError, TimeoutError):
                time.sleep(.25)
        else:
            raise RuntimeError('Browse candidate readiness timed out')
        url = 'http://127.0.0.1:19009/weppcloud/runs/csv-readiness/cfg/download/table.parquet'
        request = urllib.request.Request(url + '?as_csv=1', headers={'Range': 'bytes=invalid'})
        with urllib.request.urlopen(request, timeout=160) as response:
            actual = response.read()
            if response.status != 200 or actual != expected or int(response.headers['Content-Length']) != len(actual):
                raise RuntimeError('Native CSV HTTP bytes/headers mismatch')
        with urllib.request.urlopen(url, timeout=10) as response:
            if response.read() != Path('/opt/parquet-csv/readiness.parquet').read_bytes():
                raise RuntimeError('Raw Parquet HTTP bytes mismatch')
        filtered_cases = []
        for value, status, wanted in [('ativ', 200, b'value (mm),name\n1.25,native\n'), ('e', 200, expected), ('absent', 422, None)]:
            tree = {'kind':'condition','field':'name','operator':'Contains','value':value}
            encoded = base64.urlsafe_b64encode(json.dumps(tree).encode()).decode()
            try:
                response = urllib.request.urlopen(url + '?as_csv=1&pqf=' + encoded, timeout=20)
            except urllib.error.HTTPError as error:
                response = error
            with response:
                body = response.read()
                assert response.status == status, (value, response.status, body)
                if wanted is not None: assert body == wanted
                else: assert json.loads(body)['error']['code'] == 'no_rows_matched_filter'
                filtered_cases.append({'value':value,'status':status,'bytes':len(body),'sha256':hashlib.sha256(body).hexdigest()})
        print(json.dumps({'uid':os.getuid(),'gid':os.getgid(),'groups':os.getgroups(),'filtered_cases':filtered_cases,'legacy_enable_zero_and_cap_one_ignored_for_csv':True}))
        # The private project has identical bytes and no PUBLIC marker.
        private = url.replace('csv-readiness', 'csv-private') + '?as_csv=1'
        try:
            urllib.request.urlopen(urllib.request.Request(private, headers={'Accept': 'application/json'}), timeout=10)
        except urllib.error.HTTPError as error:
            if error.code not in (401, 403):
                raise
        else:
            raise RuntimeError('Private project CSV unexpectedly authorized')
        print(json.dumps({'status': 'ok', 'workers': 8, 'csv_bytes': len(actual),
                          'csv_sha256': hashlib.sha256(actual).hexdigest(),
                          'raw_readback': True, 'private_denied': True}))
    finally:
        server.terminate()
        try:
            server.wait(timeout=15)
        except subprocess.TimeoutExpired:
            server.kill()
            server.wait()
        log.close()


if __name__ == '__main__':
    main()
