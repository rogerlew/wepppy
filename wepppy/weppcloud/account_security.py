"""Mailbox proof and email-first local signup; CILogon contacts never identify users."""
from datetime import datetime, timezone
import secrets
from smtplib import SMTPException

from flask import Blueprint, abort, current_app, flash, jsonify, redirect, render_template, request, url_for
from flask_security import current_user
from flask_security.forms import ResetPasswordForm
from flask_security.utils import get_within_delta, hash_password, send_mail
from flask_wtf import FlaskForm
from itsdangerous import BadSignature, SignatureExpired
from sqlalchemy import func, inspect
from sqlalchemy.exc import IntegrityError
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Email, Length
from werkzeug.datastructures import MultiDict

from .auth_forms import CapTokenFormMixin, _reject_url_like_name

account_security_bp = Blueprint("account_security", __name__)
_GENERIC_SENT = "If this address can receive account instructions, an email has been sent."


class SignupForm(CapTokenFormMixin, FlaskForm):
    first_name = StringField("First name", [DataRequired(), Length(max=255), _reject_url_like_name])
    last_name = StringField("Last name", [DataRequired(), Length(max=255), _reject_url_like_name])
    email = StringField("Email", [DataRequired(), Email(), Length(max=255)])
    cap_token = StringField("CAPTCHA Token")
    submit = SubmitField("Send verification email")


class EmailRequestForm(FlaskForm):
    email = StringField("Email", [DataRequired(), Email(), Length(max=255)])
    submit = SubmitField("Send verification email")


class VerifyForm(FlaskForm):
    submit = SubmitField("Verify email")


def normalize_email(value):
    return value.strip().lower() if isinstance(value, str) else None


def account_email(user):
    return user.contact_email if user.account_kind == "cilogon" else user.email


def mailbox_verified(user):
    address = normalize_email(account_email(user))
    return bool(address and user.mailbox_verified_at and user.mailbox_verified_email == address)


def _datastore():
    return current_app.extensions["security"].datastore


def _form(cls):
    # Flask-WTF handles ordinary HTML form and header CSRF; JSON follows the same validators.
    if request.is_json:
        payload = request.get_json()
        if not isinstance(payload, dict):
            abort(400)
        return cls(MultiDict(payload))
    return cls()


def _response(message, status=200):
    if request.is_json:
        return jsonify(message=message), status
    flash(message, "info" if status < 400 else "error")
    return redirect(url_for("security.login"))


def _shared_by_email(address):
    model = _datastore().user_model
    matches = model.query.filter(model.account_kind == "shared", func.lower(func.trim(model.email)) == address).limit(2).all()
    return matches[0] if len(matches) == 1 else None


def _send_instructions(user, purpose):
    """Reserve a single account-scoped send before contacting the mail transport."""
    datastore = _datastore()
    user = datastore.user_model.query.filter_by(id=user.id).with_for_update().populate_existing().one()
    address = normalize_email(account_email(user))
    if not user.active or not address or (purpose == "setup" and user.account_kind != "shared"):
        datastore.db.session.rollback()
        return "unavailable"
    now = datetime.now(timezone.utc)
    last = user.verification_sent_at
    if last and (now - last.replace(tzinfo=timezone.utc)).total_seconds() < current_app.config["ACCOUNT_EMAIL_RESEND_SECONDS"]:
        datastore.db.session.rollback()
        return "cooldown"
    nonce = secrets.token_urlsafe(32)
    user.verification_nonce = nonce
    user.verification_sent_at = now
    token = current_app.extensions["security"].confirm_serializer.dumps(
        ["weppcloud-mailbox-v1", user.id, user.fs_uniquifier, address, purpose, nonce]
    )
    datastore.commit()
    link = url_for("account_security.complete", token=token, _external=True)
    try:
        if purpose == "reset":
            from flask_security.recoverable import send_reset_password_instructions
            send_reset_password_instructions(user)
        else:
            send_mail("Verify your WEPPcloud email", address, "account_verification", user=user,
                      verification_link=link, setup_password=purpose == "setup")
    except (SMTPException, OSError):
        # Mail is an external boundary. Keep the send reservation to bound retries.
        current_app.logger.warning("Account verification mail delivery failed")
        return "failed"
    return "sent"


def register():
    if current_user.is_authenticated:
        return redirect(url_for("user.profile"))
    form = _form(SignupForm)
    if form.validate_on_submit():
        datastore = _datastore()
        address = normalize_email(form.email.data)
        user = _shared_by_email(address)
        if user is None:
            try:
                user = datastore.create_user(email=address, password=None, active=True,
                    first_name=form.first_name.data, last_name=form.last_name.data,
                    account_kind="shared", local_credential_state="pending")
                datastore.commit()
            except IntegrityError:
                datastore.db.session.rollback()
                # Duplicate and concurrent registration have the same public outcome.
                user = _shared_by_email(address)
        if user is not None:
            purpose = "setup" if user.local_credential_state in {"none", "pending"} else "verify"
            _send_instructions(user, purpose)
        return _response(_GENERIC_SENT)
    if request.is_json:
        return jsonify(errors=form.errors), 400 if request.method == "POST" else 200
    return render_template("security/register_user.html", register_user_form=form)


def send_confirmation():
    form = _form(EmailRequestForm)
    if form.validate_on_submit():
        user = _shared_by_email(normalize_email(form.email.data))
        if user:
            purpose = "setup" if user.local_credential_state in {"none", "pending"} else "verify"
            _send_instructions(user, purpose)
        return _response(_GENERIC_SENT)
    if request.is_json:
        return jsonify(errors=form.errors), 400 if request.method == "POST" else 200
    return render_template("security/send_confirmation.html", send_confirmation_form=form)


def forgot_password():
    form = _form(EmailRequestForm)
    if form.validate_on_submit():
        user = _shared_by_email(normalize_email(form.email.data))
        if user:
            purpose = "setup" if user.local_credential_state in {"none", "pending"} else "reset"
            _send_instructions(user, purpose)
        return _response(_GENERIC_SENT)
    if request.is_json:
        return jsonify(errors=form.errors), 400 if request.method == "POST" else 200
    return render_template("security/forgot_password.html", forgot_password_form=form)


@account_security_bp.post("/account/email/send")
def send():
    if not current_user.is_authenticated:
        abort(401)
    purpose = request.form.get("purpose", "verify")
    if purpose not in {"verify", "setup"}:
        abort(400)
    if purpose == "setup" and (current_user.account_kind != "shared" or current_user.local_credential_state not in {"none", "pending"}):
        abort(400)
    if purpose == "verify" and mailbox_verified(current_user):
        flash("Your email is already verified.", "info")
    else:
        result = _send_instructions(current_user, purpose)
        messages = {"sent": "Verification email sent. Check your inbox and spam folder.",
                    "cooldown": "Please wait a minute before requesting another email.",
                    "failed": "We could not send the email. Please try again in a minute.",
                    "unavailable": "There is no email address available to verify."}
        flash(messages[result], "info" if result in {"sent", "cooldown"} else "error")
    return redirect(url_for("user.profile"))


def _read_token(token):
    try:
        data = current_app.extensions["security"].confirm_serializer.loads(
            token, max_age=get_within_delta("CONFIRM_EMAIL_WITHIN").total_seconds())
    except (BadSignature, SignatureExpired):
        return None
    if not isinstance(data, list) or len(data) != 6 or data[0] != "weppcloud-mailbox-v1":
        return None
    _, user_id, identity, address, purpose, nonce = data
    if type(user_id) is not int or purpose not in {"verify", "setup"} or not all(isinstance(v, str) for v in (identity, address, nonce)):
        return None
    user = _datastore().user_model.query.filter_by(id=user_id).first()
    if not user or not user.active or user.fs_uniquifier != identity or user.verification_nonce != nonce:
        return None
    if normalize_email(account_email(user)) != address:
        return None
    if purpose == "setup" and (user.account_kind != "shared" or user.local_credential_state not in {"none", "pending"}):
        return None
    return user, data


@account_security_bp.route("/account/email/confirm/<token>", methods=["GET", "POST"])
def complete(token):
    verified = _read_token(token)
    if verified is None:
        return _response("This email link is invalid or expired. Request another verification email.", 400)
    user, data = verified
    if current_user.is_authenticated and current_user.id != user.id:
        return _response("This link is for a different account. Sign out before continuing.", 403)
    purpose = data[4]
    form = _form(ResetPasswordForm if purpose == "setup" else VerifyForm)
    form.user = user
    if form.validate_on_submit():
        values = {"mailbox_verified_email": data[3], "mailbox_verified_at": datetime.now(timezone.utc),
                  "verification_nonce": None}
        if purpose == "setup":
            values.update(password=hash_password(form.password.data), local_credential_state="enabled",
                          confirmed_at=datetime.now(timezone.utc).replace(tzinfo=None), fs_uniquifier=secrets.token_hex(32))
        model = _datastore().user_model
        # Compare-and-swap consumption protects against concurrent redemption, including SQLite tests.
        query = model.query.filter_by(id=user.id, fs_uniquifier=data[2], verification_nonce=data[5], active=True)
        field = model.contact_email if user.account_kind == "cilogon" else model.email
        query = query.filter(func.lower(func.trim(field)) == data[3])
        if purpose == "setup":
            query = query.filter(model.account_kind == "shared", model.local_credential_state.in_(["none", "pending"]))
        changed = query.update(values, synchronize_session=False)
        if changed != 1:
            _datastore().db.session.rollback()
            return _response("This link has already been used or replaced. Request another email.", 400)
        _datastore().commit()
        if purpose == "setup":
            from flask_security.utils import logout_user
            logout_user()
            return _response("Your email is verified and your password is set. You can now sign in.")
        flash("Your email is verified.", "success")
        return redirect(url_for("user.profile") if current_user.is_authenticated else url_for("security.login"))
    if request.is_json:
        return jsonify(errors=form.errors), 400 if request.method == "POST" else 200
    return render_template("security/verify_account.html", form=form, setup_password=purpose == "setup")


def _invalidate_changed_address(mapper, connection, user):
    """Address changes cannot retain old proof or grants, including legacy reset tokens."""
    state = inspect(user)
    if state.attrs.email.history.has_changes() or state.attrs.contact_email.history.has_changes():
        user.mailbox_verified_email = None
        user.mailbox_verified_at = None
        user.verification_nonce = None
        user.fs_uniquifier = secrets.token_hex(32)


def init_account_security(app, datastore):
    """Install owned registration/proof routes while preserving established legacy login."""
    from sqlalchemy import event
    from flask_security import password_reset, password_changed
    app.config.setdefault("ACCOUNT_EMAIL_RESEND_SECONDS", 60)
    app.register_blueprint(account_security_bp)
    app.view_functions["security.register"] = register
    app.view_functions["security.send_confirmation"] = send_confirmation
    app.view_functions["security.forgot_password"] = forgot_password
    if not event.contains(datastore.user_model, "before_update", _invalidate_changed_address):
        event.listen(datastore.user_model, "before_update", _invalidate_changed_address)

    @app.context_processor
    def verification_context():
        return {"account_mailbox_verified": mailbox_verified, "account_display_email": account_email}

    @app.before_request
    def protect_credentials():
        endpoint = request.endpoint
        if endpoint == "security.change_password" and current_user.is_authenticated:
            if current_user.account_kind != "shared" or current_user.local_credential_state in {"none", "pending"}:
                flash("Use the email verification card to set a local password.", "info")
                return redirect(url_for("user.profile"))
        if endpoint in {"security.reset_password", "security.confirm_email"}:
            # Existing issued framework links remain valid only for grandfathered/established local credentials.
            from flask_security.recoverable import reset_password_token_status
            from flask_security.confirmable import confirm_email_token_status
            check = reset_password_token_status if endpoint == "security.reset_password" else confirm_email_token_status
            expired, invalid, user = check((request.view_args or {}).get("token", ""))
            if user and not invalid and not expired and (user.account_kind != "shared" or user.local_credential_state in {"none", "pending"}):
                return _response("Request a verification email to set up local sign-in.", 400)

    def password_updated(sender, user, **kwargs):
        # The framework checked the existing credential or recovery token. Never fabricate mailbox proof.
        if user.account_kind == "shared" and user.local_credential_state == "legacy":
            user.local_credential_state = "enabled"

    password_reset.connect(password_updated, app, weak=False)
    password_changed.connect(password_updated, app, weak=False)


def resolve_federated_account(datastore, provider, subject, email, email_owned, profile, token):
    """Commit one identity binding, never infer CILogon identity from a contact email."""
    from email_validator import EmailNotValidError, validate_email
    from .routes._security.oauth import _extract_name_from_profile, _token_expiry_from_token
    from .utils.oauth import normalize_token_scopes
    if not isinstance(subject, str) or not subject or len(subject) > 255:
        raise ValueError("Invalid provider subject")
    email = normalize_email(email)
    if email:
        try:
            validate_email(email, check_deliverability=False)
        except EmailNotValidError:
            email = None
    model = datastore.user_model
    oauth_model = model.oauth_accounts.property.mapper.class_
    try:
        account = datastore.find_oauth_account(provider, subject)
        user = account.user if account else None
        expected_kind = "cilogon" if provider == "cilogon" else "shared"
        if user and user.account_kind != expected_kind:
            raise ValueError("Provider account class conflict")
        if user is None and provider != "cilogon":
            if not email or not email_owned:
                raise ValueError("A verified email address is required for the first sign-in")
            matches = model.query.filter(model.account_kind == "shared", func.lower(func.trim(model.email)) == email).limit(2).all()
            if len(matches) > 1:
                raise ValueError("More than one account matches this email; contact support")
            user = matches[0] if matches else None
        if user and not user.active:
            raise ValueError("Account is inactive; contact support")
        if user is None:
            first_name, last_name = _extract_name_from_profile(profile)
            user = datastore.create_user(email=None if provider == "cilogon" else email,
                contact_email=email if provider == "cilogon" else None,
                account_kind=expected_kind, local_credential_state="none", password=None,
                active=True, confirmed_at=datetime.now(timezone.utc).replace(tzinfo=None),
                first_name=first_name[:255] if isinstance(first_name, str) else None,
                last_name=last_name[:255] if isinstance(last_name, str) else None)
            datastore.db.session.flush()
        if account is None:
            account = oauth_model(user=user, provider=provider, provider_uid=subject)
            datastore.db.session.add(account)
        # Preserve token storage contract for existing shared providers; CILogon needs no offline tokens.
        account.email = email
        if provider != "cilogon":
            for key in ("access_token", "refresh_token", "token_type"):
                setattr(account, key, token.get(key))
            account.token_expiry = _token_expiry_from_token(token)
            account.scopes = normalize_token_scopes(token, current_app.config.get("OAUTH_PROVIDERS", {}).get(provider))
        datastore.commit()
        return user
    except (IntegrityError, ValueError):
        datastore.db.session.rollback()
        raise
