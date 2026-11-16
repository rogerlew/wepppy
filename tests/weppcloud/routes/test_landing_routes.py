from __future__ import annotations

from types import SimpleNamespace

import pytest
from flask import Flask

import wepppy.weppcloud.routes.weppcloud_site as site_module

pytestmark = [pytest.mark.routes, pytest.mark.unit]


@pytest.fixture()
def landing_client(tmp_path, monkeypatch):
    app = Flask(__name__, static_folder=str(tmp_path))
    app.config['TESTING'] = True
    app.register_blueprint(site_module.weppcloud_site_bp)
    monkeypatch.setattr(site_module, '_load_or_refresh_run_locations', lambda: [])
    monkeypatch.setattr(site_module, 'current_user', SimpleNamespace(is_authenticated=False))
    export_root = tmp_path / site_module._LANDING_STATIC_DIRNAME
    export_root.mkdir()
    with app.test_client() as client:
        yield client, export_root


@pytest.mark.parametrize('route,theme', [
    ('/', 'light'), ('/landing/', 'light'),
    ('/landing/light/', 'light'), ('/landing/dark/', 'dark'),
])
def test_landing_serves_requested_theme_with_state(landing_client, route, theme):
    client, export_root = landing_client
    for name, variant in [('index-light.html', 'light'), ('index.html', 'dark')]:
        (export_root / name).write_text(f'<html><head></head><body>{variant}</body></html>')

    response = client.get(route)

    assert response.status_code == 200
    assert f'<body>{theme}</body>' in response.text
    assert 'window.__WEPP_STATE__ = {"user": {"is_authenticated": false' in response.text
    assert response.headers['Cache-Control'] == 'no-store, max-age=0'


@pytest.mark.parametrize('route,filename,other', [
    ('/', 'index-light.html', 'index.html'),
    ('/landing/', 'index-light.html', 'index.html'),
    ('/landing/light/', 'index-light.html', 'index.html'),
    ('/landing/dark/', 'index.html', 'index-light.html'),
])
@pytest.mark.parametrize('state', ['missing', 'unreadable', 'invalid_utf8'])
def test_unavailable_export_returns_logged_503_without_fallback(
    landing_client, route, filename, other, state, caplog,
):
    client, export_root = landing_client
    # Keep the other theme available: it must not substitute for this export.
    (export_root / other).write_text('<html><body>other theme</body></html>')
    if state == 'unreadable':
        # An actual read_text failure, including when tests execute as root.
        (export_root / filename).mkdir()
    elif state == 'invalid_utf8':
        (export_root / filename).write_bytes(b'\xff')

    response = client.get(route)

    assert response.status_code == 503
    assert response.text == 'Landing page temporarily unavailable.'
    assert response.mimetype == 'text/plain'
    assert response.headers['Cache-Control'] == 'no-store, max-age=0'
    assert str(export_root) not in response.text
    assert 'Landing HTML export unavailable' in caplog.text
    assert str(export_root / filename) in caplog.text
