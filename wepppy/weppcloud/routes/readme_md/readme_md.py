import os
from datetime import datetime, timezone
from pathlib import Path
import uuid

from flask import (
    Blueprint,
    jsonify,
    request,
    abort,
    render_template_string,
    render_template,
    redirect,
)
from flask_security import current_user

from cmarkgfm import github_flavored_markdown_to_html as markdown_to_html  # pip install cmarkgfm
# https://github.com/sindresorhus/github-markdown-css for styling
from wepppy.weppcloud.utils.helpers import exception_factory, authorize, get_wd, url_for_run
from wepppy.nodb.core import Ron
from wepppy.nodb.base import _iter_nodb_subclasses

from .._run_context import RunContext, load_run_context


import redis

redis_readme_client = None
REDIS_HOST = os.environ.get('REDIS_HOST', 'localhost')
REDIS_README_DB = 14
_LOCK_TTL_SECONDS = 1800  # 30 minutes to keep session locks fresh
_CLIENT_STATE_TTL_SECONDS = 3600
_STALE_CLIENT_TTL_SECONDS = 600

try:
    redis_readme_pool = redis.ConnectionPool(
        host=REDIS_HOST, port=6379, db=REDIS_README_DB,
        decode_responses=True, max_connections=50
    )
    redis_readme_client = redis.StrictRedis(connection_pool=redis_readme_pool)
    redis_readme_client.ping()
except Exception as e:
    redis_readme_client = None


readme_bp = Blueprint('readme', __name__, template_folder='templates')

_BASE_DIR = Path(__file__).resolve().parent

README_FILENAME = "README.md"
DEFAULT_TEMPLATE = _BASE_DIR / "templates" / "default.md.j2"


def _readme_path(wd):
    return os.path.join(wd, README_FILENAME)


def _collect_nodb_context(wd):
    context = {}
    for cls in _iter_nodb_subclasses():
        getter = getattr(cls, "getInstance", None)
        if getter is None:
            continue
        try:
            instance = getter(wd)
        except Exception:
            continue
        try:
            context[cls.__name__] = instance.stub
        except Exception:
            pass
    return context


def _template_context(ctx: RunContext):
    from wepppy.weppcloud.app import Run  # local import to avoid circular

    wd = str(ctx.active_root)
    ron = Ron.getInstance(wd)
    run_rec = Run.query.filter_by(runid=ctx.runid).first()
    context = {
        "user": current_user,
        "runid": ctx.runid,
        "config": ctx.config,
        "ron": ron,
        "run_record": run_rec,
        "created": run_rec.date_created if run_rec else None,
    }
    if ctx.pup_relpath:
        context["pup_relpath"] = ctx.pup_relpath
    context["nodb"] = _collect_nodb_context(wd)
    return context


def _ensure_readme(wd, runid, config):
    path = _readme_path(wd)
    if os.path.exists(path):
        return path

    template_source = DEFAULT_TEMPLATE.read_text(encoding="utf-8")
    markdown = template_source.replace('{runid}', runid).replace('{config}', config)
    Path(path).write_text(markdown, encoding="utf-8")
    return path


def ensure_readme_on_create(runid, config):
    wd = get_wd(runid)
    return _ensure_readme(wd, runid, config)


def ensure_readme(ctx: RunContext):
    wd = str(ctx.active_root)
    return _ensure_readme(wd, ctx.runid, ctx.config)


def _render_markdown(markdown_source, context):
    rendered_markdown = render_template_string(markdown_source, **context)
    return markdown_to_html(rendered_markdown)


def _load_markdown(ctx: RunContext):
    path = ensure_readme(ctx)
    return Path(path).read_text(encoding="utf-8")


def _write_markdown(ctx: RunContext, markdown_text: str):
    path = _readme_path(str(ctx.active_root))
    Path(path).write_text(markdown_text, encoding="utf-8")


def _editor_lock_key(runid, config):
    return f"readme:lock:{runid}:{config}"


def _editor_client_key(runid, config, client_uuid):
    return f"readme:client:{runid}:{config}:{client_uuid}"


def _utc_iso_now():
    return datetime.now(timezone.utc).isoformat()


def _record_editor_session(runid, config, client_uuid, ron):
    global redis_readme_client
    if redis_readme_client is None:
        return
    
    lock_key = _editor_lock_key(runid, config)
    client_key = _editor_client_key(runid, config, client_uuid)
    now = _utc_iso_now()
    try:
        previous_uuid = redis_readme_client.get(lock_key)
        pipe = redis_readme_client.pipeline()
        pipe.set(lock_key, client_uuid, ex=_LOCK_TTL_SECONDS)
        pipe.hset(client_key, mapping={
            "runid": runid,
            "config": config,
            "uuid": client_uuid,
            "status": "active",
            "ron_name": getattr(ron, "name", ""),
            "ron_scenario": getattr(ron, "scenario", ""),
            "updated_at": now,
            "created_at": now,
        })
        pipe.expire(client_key, _CLIENT_STATE_TTL_SECONDS)
        if previous_uuid and previous_uuid != client_uuid:
            prev_key = _editor_client_key(runid, config, previous_uuid)
            pipe.hset(prev_key, mapping={
                "status": "stale",
                "stale_at": now,
            })
            pipe.expire(prev_key, _STALE_CLIENT_TTL_SECONDS)
        pipe.execute()
    except redis.RedisError:
        pass


def _refresh_editor_session(runid, config, client_uuid, ron):
    if redis_readme_client is None:
        return
    lock_key = _editor_lock_key(runid, config)
    client_key = _editor_client_key(runid, config, client_uuid)
    now = _utc_iso_now()
    try:
        pipe = redis_readme_client.pipeline()
        pipe.set(lock_key, client_uuid, ex=_LOCK_TTL_SECONDS)
        pipe.hset(client_key, mapping={
            "status": "active",
            "ron_name": getattr(ron, "name", ""),
            "ron_scenario": getattr(ron, "scenario", ""),
            "updated_at": now,
        })
        pipe.expire(client_key, _CLIENT_STATE_TTL_SECONDS)
        pipe.execute()
    except redis.RedisError:
        pass


def _get_editor_state(runid, config, client_uuid):
    if redis_readme_client is None:
        return {}
    client_key = _editor_client_key(runid, config, client_uuid)
    try:
        state = redis_readme_client.hgetall(client_key)
    except redis.RedisError:
        return {}
    return state or {}


def _invalidate_editor_session(runid, config, client_uuid):
    if redis_readme_client is None or not client_uuid:
        return
    client_key = _editor_client_key(runid, config, client_uuid)
    now = _utc_iso_now()
    try:
        redis_readme_client.hset(client_key, mapping={
            "status": "invalidated",
            "invalidated_at": now,
        })
        redis_readme_client.expire(client_key, _STALE_CLIENT_TTL_SECONDS)
    except redis.RedisError:
        pass


def _session_has_lock(runid, config, client_uuid):
    if redis_readme_client is None:
        return True
    if not client_uuid:
        return False
    lock_key = _editor_lock_key(runid, config)
    try:
        current_uuid = redis_readme_client.get(lock_key)
    except redis.RedisError:
        return True
    if current_uuid is None:
        return False
    return current_uuid == client_uuid

def _can_edit(runid):
    from wepppy.weppcloud.app import get_run_owners

    owners = get_run_owners(runid)
    if current_user.has_role("Admin"):
        return True
    if current_user in owners:
        return True
    return False


@readme_bp.route("/runs/<string:runid>/<config>/readme-editor")
def readme_editor(runid, config):
    try:
        authorize(runid, config)
        ctx = load_run_context(runid, config)
        context = _template_context(ctx)
        ron = context.get("ron")
        if getattr(ron, "readonly", False):
            target_args = {"runid": runid, "config": config}
            if ctx.pup_relpath:
                target_args["pup"] = ctx.pup_relpath
            return redirect(url_for_run("readme.readme_render", **target_args))
        markdown = _load_markdown(ctx)
        html = _render_markdown(markdown, context)
        client_uuid = uuid.uuid4().hex
        _record_editor_session(runid, config, client_uuid, ron)
        return render_template(
            "readme_editor.htm",
            initial_markdown=markdown,
            initial_html=html,
            editor_client_uuid=client_uuid,
            **context,
        )
    except:
        return exception_factory("Could not load README editor")

@readme_bp.route("/runs/<string:runid>/<config>/readme/raw")
def readme_raw(runid, config):
    try:
        authorize(runid, config)
        ctx = load_run_context(runid, config)
        markdown = _load_markdown(ctx)
        return jsonify({"markdown": markdown})
    except:
        return exception_factory("Could not load README raw")

@readme_bp.route("/runs/<string:runid>/<config>/readme/save", methods=["POST"])
def readme_save(runid, config):
    try:
        authorize(runid, config)
        ctx = load_run_context(runid, config)
        data = request.get_json() or {}
        markdown = data.get("markdown", "")
        client_uuid = data.get("uuid")
        if not isinstance(markdown, str):
            abort(400)
        lock_ok = _session_has_lock(runid, config, client_uuid)
        if not lock_ok:
            reason = "lock_mismatch"
            if not client_uuid:
                reason = "missing_uuid"
            _invalidate_editor_session(runid, config, client_uuid)
            return jsonify({"Success": False, "invalidated": True, "reason": reason})
        _write_markdown(ctx, markdown)
        ron = Ron.getInstance(str(ctx.active_root))
        previous_state = _get_editor_state(runid, config, client_uuid) if client_uuid else {}
        previous_name = (previous_state.get("ron_name") or "") if previous_state else ""
        previous_scenario = (previous_state.get("ron_scenario") or "") if previous_state else ""
        current_name = getattr(ron, "name", "")
        current_scenario = getattr(ron, "scenario", "")
        ron_update = {}
        if previous_name != current_name:
            ron_update["name"] = current_name
        if previous_scenario != current_scenario:
            ron_update["scenario"] = current_scenario
        if client_uuid:
            _refresh_editor_session(runid, config, client_uuid, ron)
        response = {"Success": True}
        if ron_update:
            response["ronUpdate"] = ron_update
        return jsonify(response)
    except:
        return exception_factory("Could not save README")


@readme_bp.route("/runs/<string:runid>/<config>/readme/preview", methods=["POST"])
def readme_preview(runid, config):
    try:
        authorize(runid, config)
        ctx = load_run_context(runid, config)
        data = request.get_json() or {}
        markdown = data.get("markdown", "")
        if not isinstance(markdown, str):
            abort(400)
        context = _template_context(ctx)
        html = _render_markdown(markdown, context)
        return jsonify({"html": html})
    except:
        return exception_factory("Could not render README preview")


@readme_bp.route("/runs/<string:runid>/<config>/README")
def readme_render(runid, config):
    try:
        authorize(runid, config)
        ctx = load_run_context(runid, config)
        markdown = _load_markdown(ctx)
        context = _template_context(ctx)
        html = _render_markdown(markdown, context)
        return render_template(
            "readme_view.htm",
            readme_html=html,
            generated=datetime.now(),
            can_edit=_can_edit(runid),
            **context
        )
    except:
        return exception_factory("Could not load README viewer")
