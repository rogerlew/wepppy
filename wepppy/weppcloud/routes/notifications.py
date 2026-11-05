"""Session-authenticated inbox; background work never runs on a request."""

from flask import Blueprint, current_app, render_template, request, url_for
from flask_security import current_user
from sqlalchemy.exc import SQLAlchemyError
from werkzeug.exceptions import BadRequest, UnsupportedMediaType

from wepppy.weppcloud.notifications import repository
from wepppy.weppcloud.utils.helpers import error_factory, success_factory

notifications_bp = Blueprint("notifications", __name__)


@notifications_bp.app_context_processor
def inbox_availability():
    # Bind-mounted templates can reach old workers before their routes reload.
    # Only processes that registered this blueprint advertise the inbox link.
    return {"notification_inbox_available": True}


def _engine():
    from wepppy.weppcloud.app import db
    return db.engine


@notifications_bp.before_request
def require_account():
    if not current_user.is_authenticated:
        if request.endpoint == "notifications.index":
            return current_app.login_manager.unauthorized()
        return error_factory("Sign in to view notifications.", status_code=401)
    return None


@notifications_bp.after_request
def private_response(response):
    response.headers["Cache-Control"] = "private, no-store"
    return response


@notifications_bp.errorhandler(SQLAlchemyError)
def database_unavailable(error):
    current_app.logger.error("Notification database unavailable", exc_info=error)
    if request.endpoint == "notifications.index":
        return render_template("notifications.htm", items=[], page=1, sort="unread_first",
                               has_next=False, error="Notifications are unavailable. Please try again."), 503
    return error_factory("Notifications are unavailable. Please try again.", status_code=503)


@notifications_bp.get("/notifications")
def index():
    raw_page = request.args.get("page", "1")
    sort = request.args.get("sort", "unread_first")
    if not raw_page.isascii() or not raw_page.isdecimal() or len(raw_page) > 10:
        return error_factory("Choose a valid notification page.", status_code=400)
    page = int(raw_page)
    if not 1 <= page <= 2147483647 or sort not in repository.SORTS:
        return error_factory("Choose a valid notification page and sort.", status_code=400)
    with _engine().connect() as connection:
        items, has_next = repository.list_notifications(connection, int(current_user.id), page, sort)
    for item in items:
        item["project_url"] = (url_for("run_0.runs0", runid=item["runid"], config=item["config"])
                               if item["runid"] and item["config"] else None)
    return render_template("notifications.htm", items=items, page=page, sort=sort,
                           has_next=has_next, error=None)


@notifications_bp.get("/api/notifications/unread-count")
def unread_count():
    with _engine().connect() as connection:
        count = repository.unread_count(connection, int(current_user.id))
    return success_factory({"unread_count": count})


@notifications_bp.post("/api/notifications/read-state")
def read_state():
    try:
        payload = request.get_json()
    except (BadRequest, UnsupportedMediaType):
        return error_factory("Send a valid notification selection as JSON.", status_code=400)
    if type(payload) is not dict:
        return error_factory("Send a notification selection as a JSON object.", status_code=400)
    try:
        result = repository.set_read_state(_engine(), int(current_user.id),
                                            payload.get("notification_ids"), payload.get("read"))
    except repository.SelectionNotFound:
        return error_factory("Notification selection is unavailable. Refresh the page and try again.", status_code=404)
    except ValueError as error:
        return error_factory(str(error), status_code=400)
    return success_factory(result)
