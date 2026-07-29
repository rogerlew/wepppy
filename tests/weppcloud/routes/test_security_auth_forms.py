from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from flask import Flask, render_template
from flask_security import RoleMixin, SQLAlchemyUserDatastore, Security, UserMixin
from flask_sqlalchemy import SQLAlchemy
from flask_wtf import CSRFProtect
from flask_wtf.csrf import generate_csrf
from markupsafe import Markup
from werkzeug.datastructures import MultiDict
from wtforms import BooleanField, Form, PasswordField, StringField, SubmitField

from wepppy.weppcloud.auth_forms import ExtendedLoginForm, ExtendedRegisterForm
from wepppy.weppcloud.routes._security import ui as security_ui

pytestmark = pytest.mark.routes

TEMPLATE_ROOT = Path(__file__).resolve().parents[3] / "wepppy" / "weppcloud" / "templates"


class _SecurityForm(Form):
    def __init__(self, *args: object, **kwargs: object) -> None:
        super().__init__(*args, **kwargs)
        self.form_errors: list[str] = []

    def hidden_tag(self) -> Markup:
        return Markup(
            '<input id="csrf_token" name="csrf_token" type="hidden" '
            'value="csrf-token">'
        )


class _EmailForm(_SecurityForm):
    email = StringField("Email")
    submit = SubmitField("Continue")


class _LoginForm(_SecurityForm):
    email = StringField("Email")
    username = StringField("Username")
    password = PasswordField("Password")
    remember = BooleanField("Remember")
    cap_token = StringField("CAPTCHA Token")
    submit = SubmitField("Sign in")


class _RegisterForm(_SecurityForm):
    first_name = StringField("First name")
    last_name = StringField("Last name")
    email = StringField("Email")
    password = PasswordField("Password")
    password_confirm = PasswordField("Confirm password")
    cap_token = StringField("CAPTCHA Token")
    submit = SubmitField("Create account")


class _ResetPasswordForm(_SecurityForm):
    password = PasswordField("Password")
    password_confirm = PasswordField("Confirm password")
    submit = SubmitField("Reset password")


class _ChangePasswordForm(_SecurityForm):
    password = PasswordField("Password")
    new_password = PasswordField("New password")
    new_password_confirm = PasswordField("Confirm new password")
    submit = SubmitField("Change password")


@pytest.fixture()
def security_template_app() -> Flask:
    app = Flask(__name__, template_folder=str(TEMPLATE_ROOT))
    app.config["SECRET_KEY"] = "security-form-test"
    app.jinja_env.globals.update(
        static_url=lambda filename: f"/static/{filename}",
        csrf_token=lambda: "csrf-token",
        site_prefix="",
        controllers_gl_expected_build_id="",
        current_user=SimpleNamespace(is_authenticated=False),
        security=SimpleNamespace(confirmable=True, recoverable=True, changeable=True),
        enable_local_login=True,
        url_for=lambda endpoint, **values: (
            f"/{endpoint}"
            + (f"?{next(iter(values))}={next(iter(values.values()))}" if values else "")
        ),
        url_for_security=lambda endpoint, **values: (
            f"/{endpoint}"
            + (f"/{values['token']}" if "token" in values else "")
        ),
    )
    return app


@pytest.fixture()
def security_route_app(monkeypatch: pytest.MonkeyPatch) -> Flask:
    app = Flask(__name__, template_folder=str(TEMPLATE_ROOT))
    app.config.update(
        SECRET_KEY="security-route-test",
        SQLALCHEMY_DATABASE_URI="sqlite://",
        SQLALCHEMY_TRACK_MODIFICATIONS=False,
        SECURITY_PASSWORD_SALT="security-route-salt",
        SECURITY_PASSWORD_HASH="bcrypt",
        SECURITY_REGISTERABLE=True,
        SECURITY_SEND_REGISTER_EMAIL=False,
        SECURITY_TRACKABLE=False,
        WTF_CSRF_ENABLED=True,
        CAP_BASE_URL="/cap",
        CAP_ASSET_BASE_URL="/cap/assets",
        CAP_SITE_KEY="test-site-key",
    )
    app.jinja_env.globals.update(
        static_url=lambda filename: f"/static/{filename}",
        site_prefix="",
        controllers_gl_expected_build_id="",
    )
    app.url_build_error_handlers.append(
        lambda _error, endpoint, _values: f"/mock/{endpoint}"
    )
    app.context_processor(security_ui.inject_auth_context)
    monkeypatch.setattr(security_ui, "url_for_security", lambda endpoint: f"/{endpoint}")

    db = SQLAlchemy(app)
    roles_users = db.Table(
        "roles_users",
        db.Column("user_id", db.Integer(), db.ForeignKey("user.id")),
        db.Column("role_id", db.Integer(), db.ForeignKey("role.id")),
    )

    class Role(db.Model, RoleMixin):
        id = db.Column(db.Integer(), primary_key=True)
        name = db.Column(db.String(80), unique=True)

    class User(db.Model, UserMixin):
        id = db.Column(db.Integer(), primary_key=True)
        email = db.Column(db.String(255), unique=True)
        password = db.Column(db.String(255))
        active = db.Column(db.Boolean(), default=True)
        fs_uniquifier = db.Column(db.String(64), unique=True, nullable=False)
        first_name = db.Column(db.String(255))
        last_name = db.Column(db.String(255))
        roles = db.relationship("Role", secondary=roles_users)

    CSRFProtect(app)
    datastore = SQLAlchemyUserDatastore(db, User, Role)
    Security(
        app,
        datastore,
        login_form=ExtendedLoginForm,
        register_form=ExtendedRegisterForm,
    )

    @app.get("/test-csrf")
    def test_csrf() -> str:
        return generate_csrf()

    with app.app_context():
        db.create_all()

    return app


@pytest.mark.parametrize(
    ("template_name", "form_name", "form", "action", "field_contract"),
    [
        (
            "security/login_user.html",
            "login_user_form",
            _LoginForm(),
            "/login",
            (
                ("email", "username"),
                ("username", "username"),
                ("password", "current-password"),
                ("remember", None),
                ("cap_token", "off"),
            ),
        ),
        (
            "security/register_user.html",
            "register_user_form",
            _RegisterForm(),
            "/register",
            (
                ("first_name", "given-name"),
                ("last_name", "family-name"),
                ("email", "email"),
                ("password", "new-password"),
                ("password_confirm", "new-password"),
                ("cap_token", "off"),
            ),
        ),
        (
            "security/send_confirmation.html",
            "send_confirmation_form",
            _EmailForm(),
            "/send_confirmation",
            (("email", "email"),),
        ),
        (
            "security/forgot_password.html",
            "forgot_password_form",
            _EmailForm(),
            "/forgot_password",
            (("email", "email"),),
        ),
        (
            "security/reset_password.html",
            "reset_password_form",
            _ResetPasswordForm(),
            "/reset_password/reset-token",
            (("password", "new-password"), ("password_confirm", "new-password")),
        ),
        (
            "security/change_password.html",
            "change_password_form",
            _ChangePasswordForm(),
            "/change_password",
            (
                ("password", "current-password"),
                ("new_password", "new-password"),
                ("new_password_confirm", "new-password"),
            ),
        ),
        (
            "security/send_login.html",
            "send_login_form",
            _EmailForm(),
            "/login",
            (("email", "email"),),
        ),
    ],
)
def test_security_form_renders_action_csrf_fields_and_autocomplete(
    security_template_app: Flask,
    template_name: str,
    form_name: str,
    form: Form,
    action: str,
    field_contract: tuple[tuple[str, str | None], ...],
) -> None:
    context = {
        form_name: form,
        "reset_password_token": "reset-token",
        "identity_attributes": ["email", "username"],
        "enabled_oauth_providers": {},
        "cap_base_url": "/cap",
        "cap_asset_base_url": "/cap/assets",
        "cap_site_key": "test-site-key",
    }
    with security_template_app.test_request_context("/security-form"):
        rendered = render_template(template_name, **context)

    assert f'<form action="{action}" method="post" name="{form_name}"' in rendered
    assert 'name="csrf_token"' in rendered
    assert 'value="csrf-token"' in rendered
    for field_name, autocomplete in field_contract:
        assert f'name="{field_name}"' in rendered
        if autocomplete is not None:
            assert f'autocomplete="{autocomplete}"' in rendered
    assert 'type="submit"' in rendered


def test_security_form_escapes_values_field_errors_and_form_errors(
    security_template_app: Flask,
) -> None:
    hostile = '<img src=x onerror="window.pwned=true">'
    form = _EmailForm(formdata=MultiDict({"email": hostile}))
    form.email.errors = (hostile,)
    form.form_errors = [hostile]

    with security_template_app.test_request_context("/forgot"):
        rendered = render_template(
            "security/forgot_password.html",
            forgot_password_form=form,
        )

    assert hostile not in rendered
    assert "&lt;img src=x onerror=" in rendered
    assert "window.pwned=true" in rendered
    assert rendered.count("&lt;img") == 3


def test_welcome_and_goodbye_escape_identity_and_navigation(
    security_template_app: Flask,
) -> None:
    hostile = '<svg onload="window.pwned=true">'
    with security_template_app.test_request_context("/welcome"):
        welcome = render_template(
            "security/welcome.html",
            user=SimpleNamespace(first_name=hostile, email="user@example.test"),
        )
        goodbye = render_template(
            "security/goodbye.html",
            auth_login_url="/login?next=<script>alert(1)</script>",
        )

    assert hostile not in welcome
    assert "&lt;svg onload=" in welcome
    assert 'href="/user.runs"' in welcome
    assert 'href="/user.profile"' in welcome
    assert "<script>alert(1)</script>" not in goodbye
    assert "next=&lt;script&gt;alert(1)&lt;/script&gt;" in goodbye


@pytest.mark.parametrize(
    ("endpoint", "payload"),
    [
        ("/login", {"email": "nobody@example.test", "password": "wrong"}),
        (
            "/register",
            {
                "first_name": "Test",
                "last_name": "User",
                "email": "new@example.test",
                "password": "long-enough-password",
                "password_confirm": "long-enough-password",
            },
        ),
    ],
)
def test_real_security_routes_require_csrf_before_cap(
    security_route_app: Flask,
    endpoint: str,
    payload: dict[str, str],
) -> None:
    client = security_route_app.test_client()

    missing_csrf = client.post(endpoint, data=payload)
    assert missing_csrf.status_code == 400

    csrf_token = client.get("/test-csrf").get_data(as_text=True)
    missing_cap = client.post(endpoint, data={**payload, "csrf_token": csrf_token})
    assert missing_cap.status_code == 200
    assert "Complete CAPTCHA verification before continuing." in missing_cap.get_data(
        as_text=True
    )
