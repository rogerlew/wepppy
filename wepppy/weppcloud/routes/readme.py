import os
from datetime import datetime
from os.path import join as _join
from pathlib import Path

from flask import (
    Blueprint,
    jsonify,
    request,
    abort,
    render_template_string,
    render_template,
    redirect,
    url_for,
)
from flask_security import current_user

from cmarkgfm import github_flavored_markdown_to_html as markdown_to_html  # pip install cmarkgfm
# https://github.com/sindresorhus/github-markdown-css for styling
from wepppy.weppcloud.utils.helpers import get_wd, exception_factory
from wepppy.nodb import Ron
from wepppy.nodb.base import _iter_nodb_subclasses

readme_bp = Blueprint("readme", __name__)

_thisdir = os.path.dirname(os.path.abspath(__file__))

README_FILENAME = "README.md"
DEFAULT_TEMPLATE = _join(_thisdir, "../templates/readme/default.md.j2")


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


def _template_context(runid, config):
    from wepppy.weppcloud.app import Run  # local import to avoid circular

    wd = get_wd(runid)
    ron = Ron.getInstance(wd)
    run_rec = Run.query.filter_by(runid=runid).first()
    context = {
        "user": current_user,
        "runid": runid,
        "config": config,
        "ron": ron,
        "run_record": run_rec,
        "created": run_rec.date_created if run_rec else None,
        "nodb": _collect_nodb_context(wd),
    }
    return context


def ensure_readme(runid, config):
    wd = get_wd(runid)
    path = _readme_path(wd)
    if os.path.exists(path):
        return path

#    context = _template_context(runid, config)
    with open(DEFAULT_TEMPLATE, "r", encoding="utf-8") as f:
        template_source = f.read()
    markdown = template_source.replace('{runid}', runid).replace('{config}', config)
    Path(path).write_text(markdown, encoding="utf-8")
    return path


def _render_markdown(markdown_source, context):
    rendered_markdown = render_template_string(markdown_source, **context)
    return markdown_to_html(rendered_markdown)


def _load_markdown(runid, config):
    path = ensure_readme(runid, config)
    return Path(path).read_text(encoding="utf-8")


def _write_markdown(runid, config, markdown_text):
    path = _readme_path(get_wd(runid))
    Path(path).write_text(markdown_text, encoding="utf-8")


def _authorize(runid, config, require_owner=False):
    from wepppy.weppcloud.app import get_run_owners

    wd = get_wd(runid)
    owners = get_run_owners(runid)
    should_abort = True

    if not require_owner and Ron.getInstance(wd).public:
        should_abort = False

    if current_user in owners:
        should_abort = False

    if current_user.has_role("Admin"):
        should_abort = False

    if not owners:
        should_abort = False

    if should_abort:
        abort(403)


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
        _authorize(runid, config, require_owner=True)
        context = _template_context(runid, config)
        ron = context.get("ron")
        if getattr(ron, "readonly", False):
            return redirect(url_for("readme.readme_render", runid=runid, config=config))
        markdown = _load_markdown(runid, config)
        html = _render_markdown(markdown, context)
        return render_template(
            "readme/editor.html", initial_markdown=markdown, initial_html=html, **context
        )
    except:
        return exception_factory("Could not load README editor")

@readme_bp.route("/runs/<string:runid>/<config>/readme/raw")
def readme_raw(runid, config):
    try:
        _authorize(runid, config, require_owner=True)
        markdown = _load_markdown(runid, config)
        return jsonify({"markdown": markdown})
    except:
        return exception_factory("Could not load README raw")

@readme_bp.route("/runs/<string:runid>/<config>/readme/save", methods=["POST"])
def readme_save(runid, config):
    try:
        _authorize(runid, config, require_owner=True)
        data = request.get_json() or {}
        markdown = data.get("markdown", "")
        if not isinstance(markdown, str):
            abort(400)
        _write_markdown(runid, config, markdown)
        return jsonify({"Success": True})
    except:
        return exception_factory("Could not save README")


@readme_bp.route("/runs/<string:runid>/<config>/readme/preview", methods=["POST"])
def readme_preview(runid, config):
    try:
        _authorize(runid, config, require_owner=True)
        data = request.get_json() or {}
        markdown = data.get("markdown", "")
        if not isinstance(markdown, str):
            abort(400)
        context = _template_context(runid, config)
        html = _render_markdown(markdown, context)
        return jsonify({"html": html})
    except:
        return exception_factory("Could not render README preview")


@readme_bp.route("/runs/<string:runid>/<config>/README")
def readme_render(runid, config):
    try:
        _authorize(runid, config)
        markdown = _load_markdown(runid, config)
        context = _template_context(runid, config)
        html = _render_markdown(markdown, context)
        return render_template(
            "readme/view.html",
            readme_html=html,
            generated=datetime.now(),
            can_edit=_can_edit(runid),
            **context
        )
    except:
        return exception_factory("Could not load README viewer")
