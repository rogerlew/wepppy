from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from flask import Flask, render_template
from markupsafe import Markup
from werkzeug.datastructures import MultiDict
from wtforms import BooleanField, Form, PasswordField, StringField, SubmitField

from wepppy.weppcloud import auth_forms
from wepppy.weppcloud.routes._security import ui as security_ui


pytestmark = pytest.mark.unit

TEMPLATE_ROOT = Path(__file__).resolve().parents[2] / "wepppy" / "weppcloud" / "templates"


class _RenderableForm(Form):
    cap_token = StringField("CAPTCHA Token")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.form_errors = []

    def hidden_tag(self):
        return Markup('<input id="csrf_token" name="csrf_token" type="hidden" value="csrf-token">')


class _RenderableLoginForm(_RenderableForm):
    email = StringField("Email")
    username = StringField("Username")
    password = PasswordField("Password")
    remember = BooleanField("Remember")
    submit = SubmitField("Sign in")


class _RenderableRegisterForm(_RenderableForm):
    first_name = StringField("First name")
    last_name = StringField("Last name")
    email = StringField("Email")
    password = PasswordField("Password")
    password_confirm = PasswordField("Confirm password")
    submit = SubmitField("Create account")


class _CaptchaOnlyForm(auth_forms.CapTokenFormMixin, Form):
    cap_token = StringField("CAPTCHA Token")


@pytest.fixture()
def auth_template_app(monkeypatch: pytest.MonkeyPatch) -> Flask:
    app = Flask(__name__, template_folder=str(TEMPLATE_ROOT))
    app.config.update(
        CAP_BASE_URL="/cap/",
        CAP_ASSET_BASE_URL="/cap/assets/",
        CAP_SITE_KEY="/test-site-key/",
    )
    monkeypatch.setattr(security_ui, "url_for_security", lambda endpoint: f"/{endpoint}")
    app.context_processor(security_ui.inject_auth_context)
    app.jinja_env.globals.update(
        static_url=lambda filename: f"/static/{filename}",
        csrf_token=lambda: "csrf-token",
        site_prefix="",
        controllers_gl_expected_build_id="",
        current_user=SimpleNamespace(is_authenticated=False),
        security=SimpleNamespace(confirmable=True, recoverable=True, changeable=True),
        url_for=lambda endpoint, **values: f"/mock/{endpoint}",
        url_for_security=lambda endpoint: f"/{endpoint}",
    )
    return app


def test_login_template_renders_cap_contract(auth_template_app: Flask) -> None:
    with auth_template_app.test_request_context("/login?next=/runs/example"):
        rendered = render_template(
            "security/login_user.html",
            login_user_form=_RenderableLoginForm(),
            identity_attributes=["email"],
            enabled_oauth_providers={
                "github": SimpleNamespace(name="GitHub"),
            },
            enable_local_login=True,
            cap_base_url="/cap",
            cap_asset_base_url="/cap/assets",
            cap_site_key="test-site-key",
        )

    assert 'form action="/login?next=/runs/example"' in rendered
    assert 'href="/mock/security_oauth.oauth_login"' in rendered
    assert 'id="cap-auth-login"' in rendered
    assert 'name="cap_token"' in rendered
    assert "data-cap-token" in rendered
    assert 'data-cap-api-endpoint="/cap/test-site-key/"' in rendered
    assert 'window.CAP_CUSTOM_WASM_URL = "/cap/assets/cap_wasm.js";' in rendered
    assert 'src="/cap/assets/widget.js"' in rendered
    assert 'src="/cap/assets/floating.js"' in rendered


def test_login_template_skips_cap_when_local_login_disabled(auth_template_app: Flask) -> None:
    with auth_template_app.test_request_context("/login"):
        rendered = render_template(
            "security/login_user.html",
            login_user_form=_RenderableLoginForm(),
            identity_attributes=["email"],
            enabled_oauth_providers={
                "github": SimpleNamespace(name="GitHub"),
            },
            enable_local_login=False,
            cap_base_url="/cap",
            cap_asset_base_url="/cap/assets",
            cap_site_key="test-site-key",
        )

    assert 'href="/mock/security_oauth.oauth_login"' in rendered
    assert 'name="cap_token"' not in rendered
    assert "cap-widget" not in rendered
    assert 'src="/cap/assets/widget.js"' not in rendered


def test_register_template_renders_cap_contract(auth_template_app: Flask) -> None:
    with auth_template_app.test_request_context("/register"):
        rendered = render_template(
            "security/register_user.html",
            register_user_form=_RenderableRegisterForm(),
            cap_base_url="/cap",
            cap_asset_base_url="/cap/assets",
            cap_site_key="test-site-key",
        )

    assert 'form action="/register"' in rendered
    assert 'id="cap-auth-register"' in rendered
    assert 'name="cap_token"' in rendered
    assert "data-cap-token" in rendered
    assert 'data-cap-api-endpoint="/cap/test-site-key/"' in rendered
    assert 'window.CAP_CUSTOM_WASM_URL = "/cap/assets/cap_wasm.js";' in rendered
    assert 'src="/cap/assets/widget.js"' in rendered
    assert 'src="/cap/assets/floating.js"' in rendered


def test_register_template_uses_cap_context_from_app_config(auth_template_app: Flask) -> None:
    with auth_template_app.test_request_context("/register"):
        rendered = render_template(
            "security/register_user.html",
            register_user_form=_RenderableRegisterForm(),
        )

    assert 'data-cap-api-endpoint="/cap/test-site-key/"' in rendered
    assert 'data-cap-api-endpoint="/cap//"' not in rendered
    assert 'window.CAP_CUSTOM_WASM_URL = "/cap/assets/cap_wasm.js";' in rendered


def test_cap_token_form_mixin_rejects_missing_token(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []
    monkeypatch.setattr(auth_forms, "verify_cap_token", lambda token: calls.append(token))

    form = _CaptchaOnlyForm(formdata=MultiDict({"cap_token": ""}))

    assert not form.validate()
    assert calls == []
    assert form.cap_token.errors == [auth_forms.CAPTCHA_REQUIRED_MESSAGE]


def test_cap_token_form_mixin_rejects_failed_verification(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(auth_forms, "verify_cap_token", lambda token: {"success": False})

    form = _CaptchaOnlyForm(formdata=MultiDict({"cap_token": "bad-token"}))

    assert not form.validate()
    assert form.cap_token.errors == [auth_forms.CAPTCHA_REQUIRED_MESSAGE]


def test_cap_token_form_mixin_rejects_verification_error(monkeypatch: pytest.MonkeyPatch) -> None:
    def _raise(_token: str) -> dict[str, bool]:
        raise auth_forms.CapVerificationError("siteverify failed")

    monkeypatch.setattr(auth_forms, "verify_cap_token", _raise)

    form = _CaptchaOnlyForm(formdata=MultiDict({"cap_token": "bad-token"}))

    assert not form.validate()
    assert form.cap_token.errors == [auth_forms.CAPTCHA_REQUIRED_MESSAGE]


def test_cap_token_form_mixin_accepts_successful_verification(monkeypatch: pytest.MonkeyPatch) -> None:
    calls = []

    def _verify(token: str) -> dict[str, bool]:
        calls.append(token)
        return {"success": True}

    monkeypatch.setattr(auth_forms, "verify_cap_token", _verify)

    form = _CaptchaOnlyForm(formdata=MultiDict({"cap_token": "good-token"}))

    assert form.validate()
    assert calls == ["good-token"]
    assert form.cap_token.errors == []


def test_extended_security_forms_include_cap_validation() -> None:
    assert issubclass(auth_forms.ExtendedLoginForm, auth_forms.CapTokenFormMixin)
    assert issubclass(auth_forms.ExtendedRegisterForm, auth_forms.CapTokenFormMixin)
