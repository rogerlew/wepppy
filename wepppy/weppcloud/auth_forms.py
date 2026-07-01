"""Custom Flask-Security forms for WEPPcloud authentication."""

from __future__ import annotations

from flask_security import LoginForm, RegisterForm
from wtforms import StringField
from wtforms.validators import DataRequired as Required, ValidationError

from wepppy.weppcloud.utils.cap_verify import CapVerificationError, verify_cap_token


CAPTCHA_REQUIRED_MESSAGE = "Complete CAPTCHA verification before continuing."


def _reject_url_like_name(form, field):
    value = field.data or ""
    if ":" in value or "/" in value:
        raise ValidationError(
            f"{field.label.text} cannot contain ':' or '/' characters."
        )


class CapTokenFormMixin:
    """Require a verified Cap.js token on public local auth forms."""

    def validate_cap_token(self, field):
        token = (field.data or "").strip()
        if not token:
            raise ValidationError(CAPTCHA_REQUIRED_MESSAGE)

        try:
            verification = verify_cap_token(token)
        except CapVerificationError as exc:
            raise ValidationError(CAPTCHA_REQUIRED_MESSAGE) from exc

        if not verification.get("success"):
            raise ValidationError(CAPTCHA_REQUIRED_MESSAGE)


class ExtendedLoginForm(CapTokenFormMixin, LoginForm):
    """WEPPcloud login form with Cap.js verification."""

    cap_token = StringField("CAPTCHA Token")


class ExtendedRegisterForm(CapTokenFormMixin, RegisterForm):
    """WEPPcloud registration form with name validation and Cap.js verification."""

    cap_token = StringField("CAPTCHA Token")
    first_name = StringField("First Name", [Required(), _reject_url_like_name])
    last_name = StringField("Last Name", [Required(), _reject_url_like_name])
