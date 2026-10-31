"""Verify the reviewed report and navigation through the local Caddy host route."""
from pathlib import Path
import hashlib
import json
import subprocess
import urllib.request


def main():
    root = Path('/workdir/wepppy')
    public = root / 'wepppy/weppcloud/static/reports/wepp/release-notes/wepp_261029'
    host = subprocess.check_output(['docker', 'exec', 'wepppy-caddy', 'printenv',
                                    'CADDY_SITE_HOST'], text=True).strip()
    assert host
    prefix = '/weppcloud/static/reports/wepp/release-notes/wepp_261029/'
    targets = {
        'pdf': (prefix + 'wepp_261029_release-notes-r2.pdf', 'application/pdf'),
        'manifest': (prefix + 'publication-manifest-r2.json', 'application/json'),
        'model': ('/weppcloud/usersum/view/weppcloud/wepp-model.md', 'text/html'),
    }
    receipt = {}
    for key, (path, expected_type) in targets.items():
        request = urllib.request.Request('http://127.0.0.1:8080' + path,
                    headers={'Host': host, 'X-Forwarded-Proto': 'https'})
        with urllib.request.urlopen(request, timeout=30) as response:
            body = response.read()
            assert response.status == 200 and expected_type in response.headers['Content-Type']
            if key != 'model':
                assert body == (public / path.rsplit('/', 1)[1]).read_bytes()
            else:
                assert b'wepp_261029_release-notes-r2.pdf' in body
                assert b'wepp_261029_release-notes-r1.pdf' in body
                assert b'187%' in body
            receipt[key] = dict(status=response.status, content_type=response.headers['Content-Type'],
                                size=len(body), sha256=hashlib.sha256(body).hexdigest())
    manifest = json.loads((public / 'publication-manifest-r2.json').read_text())
    assert receipt['pdf']['sha256'] == manifest['pdf_sha256']
    receipt['environment'] = 'Local development Caddy host route with forwarded HTTPS; no production deployment'
    out = root / 'docs/work-packages/20261030_wepp_261029_rerelease/artifacts/report-download-check.json'
    out.write_text(json.dumps(receipt, indent=2) + '\n')
    print(json.dumps(receipt, indent=2))


if __name__ == '__main__':
    main()
