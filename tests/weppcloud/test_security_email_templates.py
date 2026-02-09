from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest
from flask import Flask, render_template

pytestmark = pytest.mark.unit


def test_security_email_templates_render() -> None:
    template_root = Path(__file__).resolve().parents[2] / "wepppy" / "weppcloud" / "templates"
    app = Flask(__name__, template_folder=str(template_root))
    app.jinja_env.globals["url_for_security"] = (
        lambda endpoint, _external=True: f"https://wepp.cloud/weppcloud/{endpoint}"
    )

    context = {
        "user": SimpleNamespace(email="user@example.com", username="existing_user"),
        "security": SimpleNamespace(confirmable=True, recoverable=True),
        "confirmation_link": "https://wepp.cloud/weppcloud/confirm/demo-token",
        "confirmation_token": "demo-token",
        "reset_link": "https://wepp.cloud/weppcloud/reset/demo-token",
        "reset_token": "demo-token",
        "recovery_link": "https://wepp.cloud/weppcloud/forgot",
        "email": "new-user@example.com",
        "username": "existing_user",
    }

    templates = [
        "security/email/change_notice.html",
        "security/email/change_notice.txt",
        "security/email/confirmation_instructions.html",
        "security/email/confirmation_instructions.txt",
        "security/email/reset_instructions.html",
        "security/email/reset_instructions.txt",
        "security/email/reset_notice.html",
        "security/email/reset_notice.txt",
        "security/email/welcome.html",
        "security/email/welcome.txt",
        "security/email/welcome_existing.html",
        "security/email/welcome_existing.txt",
        "security/email/welcome_existing_username.html",
        "security/email/welcome_existing_username.txt",
    ]

    with app.app_context():
        for template_name in templates:
            rendered = render_template(template_name, **context)
            assert rendered.strip()
