import logging
import os
import hashlib
import re
from contextlib import contextmanager
from datetime import datetime, timezone
from pathlib import Path
import uuid

from flask import (
    Blueprint,
    jsonify,
    request,
    abort,
    render_template,
    redirect,
)
from flask_security import current_user

from cmarkgfm import github_flavored_markdown_to_html as markdown_to_html  # pip install cmarkgfm
# https://github.com/sindresorhus/github-markdown-css for styling
from jinja2.sandbox import SandboxedEnvironment
from jinja2 import nodes
from werkzeug.exceptions import HTTPException
from wepppy.weppcloud.utils.helpers import (
    authorize,
    authorize_and_handle_with_exception_factory,
    exception_factory,
    get_wd,
    url_for_run,
)
from wepppy.nodb.core import Ron
from wepppy.nodb.base import _iter_nodb_subclasses
from wepppy.rq.submission_recovery import checkpoint_run_lifecycle

from .._run_context import RunContext, load_run_context


import redis
from wepppy.config.redis_settings import (
    RedisDB,
    redis_connection_kwargs,
    redis_host,
)

redis_readme_client = None
REDIS_HOST = redis_host()
REDIS_README_DB = int(RedisDB.README)
_LOCK_TTL_SECONDS = 1800  # 30 minutes to keep session locks fresh
_CLIENT_STATE_TTL_SECONDS = 3600
_STALE_CLIENT_TTL_SECONDS = 600
_MUTATION_LOCK_TTL_SECONDS = 60

try:
    pool_kwargs = redis_connection_kwargs(
        RedisDB.README,
        decode_responses=True,
        extra={"max_connections": 50},
    )
    redis_readme_pool = redis.ConnectionPool(**pool_kwargs)
    redis_readme_client = redis.StrictRedis(connection_pool=redis_readme_pool)
    redis_readme_client.ping()
except (redis.exceptions.RedisError, OSError, ValueError) as e:
    redis_readme_client = None


readme_bp = Blueprint('readme', __name__, template_folder='templates')

_BASE_DIR = Path(__file__).resolve().parent

README_FILENAME = "README.md"
README_MAX_BYTES = 1_048_576
README_REQUEST_MAX_BYTES = README_MAX_BYTES + 4_096
MAX_SAVE_REVISION = 9_007_199_254_740_991
_CLIENT_UUID_RE = re.compile(r"^[0-9a-f]{32}$")
DEFAULT_TEMPLATE = _BASE_DIR / "templates" / "default.md.j2"


_SAFE_MARKDOWN_ENV = SandboxedEnvironment(autoescape=False)
_SAFE_TEMPLATE_NODE_TYPES = (
    nodes.Template,
    nodes.Output,
    nodes.TemplateData,
    nodes.Name,
    nodes.Getattr,
    nodes.Getitem,
    nodes.Const,
)
logger = logging.getLogger(__name__)


def _readme_path(wd):
    root = Path(wd).resolve()
    path = root / README_FILENAME
    if path.is_symlink():
        abort(400, description="README target must not be a symbolic link")
    try:
        path.resolve(strict=False).relative_to(root)
    except ValueError:
        abort(400, description="README target escapes the active run root")
    return path


def _collect_nodb_context(wd):
    context = {}
    for cls in _iter_nodb_subclasses():
        getter = getattr(cls, "getInstance", None)
        if getter is None:
            continue
        try:
            instance = getter(wd)
        except (FileNotFoundError, OSError, TypeError, ValueError):
            continue
        try:
            context[cls.__name__] = instance.stub
        except (AttributeError, TypeError, ValueError):
            continue
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


def _safe_markdown_context(context: dict) -> dict:
    ron = context.get("ron")
    run_record = context.get("run_record")
    safe_context = {
        "runid": context.get("runid"),
        "config": context.get("config"),
        "pup_relpath": context.get("pup_relpath"),
        "created_display": getattr(run_record, "date_created", None) or "unknown",
        "ron_name_display": getattr(ron, "name", None) or "Not set",
        "ron_scenario_display": getattr(ron, "scenario", None) or "Not set",
        "ron": {
            "name": getattr(ron, "name", None),
            "scenario": getattr(ron, "scenario", None),
            "mods": list(getattr(ron, "mods", None) or []),
            "public": getattr(ron, "public", None),
            "readonly": getattr(ron, "readonly", None),
        },
        "run_record": {
            "date_created": getattr(run_record, "date_created", None),
        },
        "created": getattr(run_record, "date_created", None),
    }

    nodb_context = context.get("nodb")
    if isinstance(nodb_context, dict):
        safe_context["nodb"] = nodb_context
    return safe_context


def _ensure_readme(wd, runid, config):
    path = _readme_path(wd)
    if os.path.exists(path):
        return path

    template_source = DEFAULT_TEMPLATE.read_text(encoding="utf-8")
    _atomic_write_markdown(path, template_source)
    return path


def ensure_readme_on_create(runid, config):
    wd = get_wd(runid)
    return _ensure_readme(wd, runid, config)


def ensure_readme(ctx: RunContext):
    wd = str(ctx.active_root)
    return _ensure_readme(wd, ctx.runid, ctx.config)


def _render_markdown(markdown_source, context):
    _validate_markdown_size(markdown_source)
    safe_context = _safe_markdown_context(context)
    try:
        parsed = _SAFE_MARKDOWN_ENV.parse(markdown_source)
        if any(
            not isinstance(node, _SAFE_TEMPLATE_NODE_TYPES)
            for node in parsed.find_all(nodes.Node)
        ):
            raise ValueError(
                "README templates support variable interpolation only"
            )
        chunks = []
        rendered_bytes = 0
        template = _SAFE_MARKDOWN_ENV.from_string(markdown_source)
        for chunk in template.generate(safe_context):
            rendered_bytes += len(chunk.encode("utf-8"))
            if rendered_bytes > README_MAX_BYTES:
                abort(413, description="Rendered README exceeds the 1 MiB size limit")
            chunks.append(chunk)
        rendered_markdown = "".join(chunks)
    except HTTPException:
        raise
    except Exception as exc:
        logger.warning("README template render failed: %s", exc)
        rendered_markdown = "**ERROR**: README template failed to render."
    html = markdown_to_html(rendered_markdown)
    if len(html.encode("utf-8")) > README_MAX_BYTES:
        abort(413, description="Rendered README HTML exceeds the 1 MiB size limit")
    return html


def _load_markdown(ctx: RunContext):
    path = _readme_path(str(ctx.active_root))
    if not path.exists():
        template_source = DEFAULT_TEMPLATE.read_text(encoding="utf-8")
        _validate_markdown_size(template_source)
        return template_source
    if path.stat().st_size > README_MAX_BYTES:
        abort(413, description="README exceeds the 1 MiB size limit")
    markdown = path.read_text(encoding="utf-8")
    _validate_markdown_size(markdown)
    return markdown


def _write_markdown(ctx: RunContext, markdown_text: str):
    _validate_markdown_size(markdown_text)
    path = _readme_path(str(ctx.active_root))
    _atomic_write_markdown(path, markdown_text)


def _atomic_write_markdown(path: Path, markdown_text: str) -> None:
    tmp_path = path.with_name(f".{README_FILENAME}.{uuid.uuid4().hex}.tmp")
    try:
        with tmp_path.open("x", encoding="utf-8") as handle:
            handle.write(markdown_text)
            handle.flush()
            os.fsync(handle.fileno())
        os.replace(tmp_path, path)
    finally:
        try:
            tmp_path.unlink()
        except FileNotFoundError:
            pass


def _validate_markdown_size(markdown_text: str) -> None:
    if len(markdown_text.encode("utf-8")) > README_MAX_BYTES:
        abort(413, description="README exceeds the 1 MiB size limit")


def _validate_client_uuid(client_uuid) -> str:
    if not isinstance(client_uuid, str) or not _CLIENT_UUID_RE.fullmatch(client_uuid):
        abort(400, description="README editor UUID is invalid")
    return client_uuid


def _require_json_request_envelope() -> None:
    content_length = request.content_length
    if content_length is None and request.is_json:
        abort(411, description="README mutation requires a bounded request body")
    if (
        content_length is not None
        and content_length > README_REQUEST_MAX_BYTES
    ):
        abort(413, description="README request exceeds the allowed size")


def _editor_scope(ctx: RunContext) -> str:
    return hashlib.sha256(str(ctx.active_root.resolve()).encode("utf-8")).hexdigest()


def _owner_runid(runid: str) -> str:
    parts = runid.split(";;")
    if len(parts) >= 3 and parts[-2] in {"omni", "omni-contrast"}:
        return ";;".join(parts[:-2])
    return runid


def _editor_identity(runid: str, ctx: RunContext) -> tuple[str, str]:
    return _owner_runid(runid), _editor_scope(ctx)


def _editor_lock_key(runid, config, scope):
    return f"readme:lock:{scope}"


def _editor_client_key(runid, config, scope, client_uuid):
    return f"readme:client:{scope}:{client_uuid}"


def _editor_mutation_key(runid, config, scope):
    return f"readme:mutation:{scope}"


@contextmanager
def _editor_mutation_guard(runid, config, scope):
    if redis_readme_client is None:
        abort(503, description="README editor coordination is unavailable")
    key = _editor_mutation_key(runid, config, scope)
    owner = uuid.uuid4().hex
    try:
        acquired = redis_readme_client.set(
            key, owner, nx=True, ex=_MUTATION_LOCK_TTL_SECONDS
        )
    except redis.RedisError:
        abort(503, description="README editor coordination is unavailable")
    if not acquired:
        abort(409, description="Another README mutation is in progress")
    try:
        yield
    finally:
        try:
            redis_readme_client.eval(
                "if redis.call('get', KEYS[1]) == ARGV[1] then "
                "return redis.call('del', KEYS[1]) else return 0 end",
                1,
                key,
                owner,
            )
        except redis.RedisError:
            logger.warning(
                "README mutation lock release failed runid=%s config=%s scope=%s",
                runid,
                config,
                scope,
                exc_info=True,
            )


def _utc_iso_now():
    return datetime.now(timezone.utc).isoformat()


def _record_editor_session(runid, config, scope, client_uuid, ron):
    global redis_readme_client
    try:
        with _editor_mutation_guard(runid, config, scope):
            lock_key = _editor_lock_key(runid, config, scope)
            client_key = _editor_client_key(runid, config, scope, client_uuid)
            now = _utc_iso_now()
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
                "last_revision": "0",
                "updated_at": now,
                "created_at": now,
            })
            pipe.expire(client_key, _CLIENT_STATE_TTL_SECONDS)
            if previous_uuid and previous_uuid != client_uuid:
                prev_key = _editor_client_key(runid, config, scope, previous_uuid)
                pipe.hset(prev_key, mapping={
                    "status": "stale",
                    "stale_at": now,
                })
                pipe.expire(prev_key, _STALE_CLIENT_TTL_SECONDS)
            pipe.execute()
    except HTTPException:
        raise
    except redis.RedisError:
        abort(503, description="README editor coordination is unavailable")


def _refresh_editor_session(runid, config, scope, client_uuid, ron, revision):
    lock_key = _editor_lock_key(runid, config, scope)
    client_key = _editor_client_key(runid, config, scope, client_uuid)
    now = _utc_iso_now()
    pipe = redis_readme_client.pipeline()
    pipe.set(lock_key, client_uuid, xx=True, ex=_LOCK_TTL_SECONDS)
    pipe.hset(client_key, mapping={
            "status": "active",
            "ron_name": getattr(ron, "name", ""),
            "ron_scenario": getattr(ron, "scenario", ""),
            "last_revision": str(revision),
            "updated_at": now,
    })
    pipe.expire(client_key, _CLIENT_STATE_TTL_SECONDS)
    pipe.execute()


def _get_editor_state(runid, config, scope, client_uuid):
    if redis_readme_client is None:
        abort(503, description="README editor coordination is unavailable")
    client_key = _editor_client_key(runid, config, scope, client_uuid)
    try:
        state = redis_readme_client.hgetall(client_key)
    except redis.RedisError:
        abort(503, description="README editor coordination is unavailable")
    return state or {}


def _invalidate_editor_session(runid, config, scope, client_uuid):
    if redis_readme_client is None or not client_uuid:
        return
    client_key = _editor_client_key(runid, config, scope, client_uuid)
    now = _utc_iso_now()
    try:
        redis_readme_client.hset(client_key, mapping={
            "status": "invalidated",
            "invalidated_at": now,
        })
        redis_readme_client.expire(client_key, _STALE_CLIENT_TTL_SECONDS)
    except redis.RedisError:
        abort(503, description="README editor coordination is unavailable")


def _session_has_lock(runid, config, scope, client_uuid):
    if redis_readme_client is None:
        abort(503, description="README editor coordination is unavailable")
    if not client_uuid:
        return False
    lock_key = _editor_lock_key(runid, config, scope)
    try:
        current_uuid = redis_readme_client.get(lock_key)
    except redis.RedisError:
        abort(503, description="README editor coordination is unavailable")
    if current_uuid is None:
        return False
    return current_uuid == client_uuid

def _can_edit(runid):
    from wepppy.weppcloud.app import get_run_owners

    owners = get_run_owners(_owner_runid(runid))
    if current_user.has_role("Admin"):
        return True
    if current_user in owners:
        return True
    return False


def _require_editor_access(runid: str, ctx: RunContext):
    if not _can_edit(runid):
        abort(403)
    ron = Ron.getInstance(str(ctx.active_root))
    if getattr(ron, "readonly", False):
        abort(409, description="README editing is disabled for readonly projects")
    return ron


@readme_bp.route("/runs/<string:runid>/<config>/readme-editor")
def readme_editor(runid, config):
    try:
        authorize(runid, config)
        ctx = load_run_context(runid, config)
        if not _can_edit(runid):
            abort(403)
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
        identity_runid, scope = _editor_identity(runid, ctx)
        _record_editor_session(identity_runid, config, scope, client_uuid, ron)
        return render_template(
            "readme_editor.htm",
            initial_markdown=markdown,
            initial_html=html,
            editor_client_uuid=client_uuid,
            **context,
        )
    except HTTPException:
        raise
    except Exception:
        logger.exception("Could not load README editor runid=%s config=%s", runid, config)
        return exception_factory("Could not load README editor")

@readme_bp.route("/runs/<string:runid>/<config>/readme/raw")
def readme_raw(runid, config):
    try:
        authorize(runid, config)
        ctx = load_run_context(runid, config)
        markdown = _load_markdown(ctx)
        client_uuid = request.headers.get("X-Readme-Client", "").strip()
        if client_uuid:
            client_uuid = _validate_client_uuid(client_uuid)
        identity_runid, scope = _editor_identity(runid, ctx)
        locked_out = bool(
            client_uuid
            and not _session_has_lock(
                identity_runid, config, scope, client_uuid
            )
        )
        return jsonify({"markdown": markdown, "locked_out": locked_out})
    except HTTPException:
        raise
    except Exception:
        logger.exception("Could not load README raw runid=%s config=%s", runid, config)
        return exception_factory("Could not load README raw")

@readme_bp.route("/runs/<string:runid>/<config>/readme/save", methods=["POST"])
@authorize_and_handle_with_exception_factory
def readme_save(runid, config):
    try:
        authorize(runid, config)
        ctx = load_run_context(runid, config)
        ron = _require_editor_access(runid, ctx)
        _require_json_request_envelope()
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            abort(400, description="README save body must be a JSON object")
        markdown = data.get("markdown", "")
        client_uuid = _validate_client_uuid(data.get("uuid"))
        revision = data.get("revision")
        if not isinstance(markdown, str):
            abort(400)
        _validate_markdown_size(markdown)
        if (
            not isinstance(revision, int)
            or isinstance(revision, bool)
            or revision < 1
            or revision > MAX_SAVE_REVISION
        ):
            abort(400, description="README save revision is invalid")
        identity_runid, scope = _editor_identity(runid, ctx)
        checkpoint_run_lifecycle(runid)
        with _editor_mutation_guard(identity_runid, config, scope):
            lock_ok = _session_has_lock(
                identity_runid, config, scope, client_uuid
            )
            if not lock_ok:
                reason = "lock_mismatch"
                _invalidate_editor_session(
                    identity_runid, config, scope, client_uuid
                )
                return jsonify({
                    "error": {"message": "README editor lock mismatch", "code": reason},
                    "invalidated": True,
                    "reason": reason,
                }), 409
            previous_state = (
                _get_editor_state(identity_runid, config, scope, client_uuid)
                if client_uuid
                else {}
            )
            previous_revision = int(previous_state.get("last_revision") or 0)
            if revision <= previous_revision:
                return jsonify({
                    "error": {
                        "message": "README save revision is stale",
                        "code": "stale_revision",
                    },
                    "invalidated": False,
                    "reason": "stale_revision",
                }), 409
            _write_markdown(ctx, markdown)
            previous_name = (previous_state.get("ron_name") or "") if previous_state else ""
            previous_scenario = (previous_state.get("ron_scenario") or "") if previous_state else ""
            current_name = getattr(ron, "name", "")
            current_scenario = getattr(ron, "scenario", "")
            ron_update = {}
            if previous_name != current_name:
                ron_update["name"] = current_name
            if previous_scenario != current_scenario:
                ron_update["scenario"] = current_scenario
            _refresh_editor_session(
                identity_runid, config, scope, client_uuid, ron, revision
            )
        response = {}
        if ron_update:
            response["ronUpdate"] = ron_update
        return jsonify(response)
    except HTTPException:
        raise
    except Exception:
        logger.exception("Could not save README runid=%s config=%s", runid, config)
        return exception_factory("Could not save README")


@readme_bp.route("/runs/<string:runid>/<config>/readme/preview", methods=["POST"])
def readme_preview(runid, config):
    try:
        authorize(runid, config)
        ctx = load_run_context(runid, config)
        _require_editor_access(runid, ctx)
        _require_json_request_envelope()
        data = request.get_json(silent=True)
        if not isinstance(data, dict):
            abort(400, description="README preview body must be a JSON object")
        markdown = data.get("markdown", "")
        if not isinstance(markdown, str):
            abort(400)
        _validate_markdown_size(markdown)
        context = _template_context(ctx)
        html = _render_markdown(markdown, context)
        return jsonify({"html": html})
    except HTTPException:
        raise
    except Exception:
        logger.exception("Could not render README preview runid=%s config=%s", runid, config)
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
    except HTTPException:
        raise
    except Exception:
        logger.exception("Could not load README viewer runid=%s config=%s", runid, config)
        return exception_factory("Could not load README viewer")
