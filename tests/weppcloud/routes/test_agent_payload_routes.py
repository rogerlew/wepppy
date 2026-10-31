"""Agent payload validation before token/spawn/publish boundaries."""
from types import SimpleNamespace
import pytest
from flask import Flask
from flask_login import LoginManager
from wepppy.weppcloud.routes import agent as routes
from wepppy.weppcloud.utils import helpers

pytestmark = pytest.mark.routes


@pytest.mark.parametrize('endpoint', ['agent/chat', 'agent/chat/session'])
@pytest.mark.parametrize('ttl', [-1, 'bad', ' ', [], {}, [1], -0.5])
def test_invalid_ttl_has_no_external_effect_and_valid_followup(monkeypatch, endpoint, ttl):
    app = Flask(__name__)
    app.config.update(TESTING=True, SECRET_KEY='test')
    app.config[routes.AGENT_JWT_SECRET_KEY] = 'test'
    app.register_blueprint(routes.agent_bp)
    login = LoginManager(app)
    login.request_loader(lambda req: SimpleNamespace(is_authenticated=True, get_id=lambda: '1'))
    monkeypatch.setattr(helpers, 'authorize', lambda *a, **k: None)
    effects = []
    monkeypatch.setattr(routes, 'generate_agent_token', lambda **k: effects.append('token') or 'token')
    monkeypatch.setattr(routes, 'spawn_wojak_session', SimpleNamespace(delay=lambda *a: effects.append('spawn') or SimpleNamespace(id='test')))
    monkeypatch.setattr(routes, '_publish', lambda *a: effects.append('publish'))
    monkeypatch.setattr(routes, '_update_last_activity', lambda session, ttl: effects.append(('ttl', ttl)))
    with app.test_client() as client:
        url = '/runs/test/cfg/' + endpoint
        response = client.post(url, json={'message':'hello', 'ttl_seconds':ttl})
        assert response.status_code == 400
        assert response.json['error']['code'] == 'invalid_request'
        assert effects == []
        response = client.post(url, json={'message':'hello', 'ttl_seconds':0})
        assert response.status_code in (200, 202)
        assert ('ttl', 1800) in effects
