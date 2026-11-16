"""Check actual Flask routes with real export reads and controlled unavailable files."""
import json
from pathlib import Path
from tempfile import TemporaryDirectory
from unittest.mock import patch
from wepppy.weppcloud.app import app

receipts = []
with app.test_client() as client:
    for route in ['/', '/landing/', '/landing/light/', '/landing/dark/']:
        response = client.get(route)
        assert response.status_code == 200
        assert 'window.__WEPP_STATE__' in response.text
        receipts.append({'route': route, 'state': 'exported', 'status': response.status_code})
    with TemporaryDirectory() as tmp:
        path = Path(tmp) / 'unavailable.html'
        for state in ['missing', 'unreadable', 'invalid_utf8']:
            if state == 'unreadable':
                path.mkdir()
            elif state == 'invalid_utf8':
                path.rmdir()
                path.write_bytes(b'\xff')
            with patch('wepppy.weppcloud.routes.weppcloud_site._resolve_landing_static_asset', return_value=path):
                for route in ['/', '/landing/', '/landing/light/', '/landing/dark/']:
                    response = client.get(route)
                    assert response.status_code == 503
                    assert response.text == 'Landing page temporarily unavailable.'
                    assert tmp not in response.text
                    receipts.append({'route': route, 'state': state, 'status': response.status_code})
print(json.dumps(receipts, indent=2))
