from os.path import exists as _exists
from os.path import join as _join
from glob import glob
import os
import logging
from datetime import datetime, timezone
from pathlib import Path

from typing import Optional, Type

from flask import url_for
from sqlalchemy.exc import SQLAlchemyError

from wepppy.nodb.core import Ron
from wepppy.nodb.unitizer import Unitizer
from wepppy.weppcloud.utils.assets import resolve_controllers_gl_build_id
from wepppy.weppcloud.utils.helpers import get_wd, url_for_run
from wepppy.all_your_base import isfloat

logger = logging.getLogger(__name__)

RunModel: Optional[Type] = None
UserModel: Optional[Type] = None

def _get_run_name(runid):
    try:
        ron = Ron.load_detached_from_runid(runid)
        return ron.name
    except (FileNotFoundError, OSError, ValueError) as exc:
        logger.debug("Run name unavailable for runid=%s: %s", runid, exc)
        return '-'
    except Exception:
        logger.exception("Unexpected error loading run name for runid=%s", runid)
        return '-'


def _run_exists(runid):
    wd = get_wd(runid)
    if not _exists(_join(wd, 'ron.nodb')):
        return False
    return True


def _get_run_owner(runid):
    try:
        if RunModel is None or UserModel is None:
            return '-'

        from sqlalchemy import String, cast, select
        from wepppy.weppcloud.app import db

        run_table = RunModel.__table__
        user_table = UserModel.__table__
        owner_join = cast(user_table.c.id, String) == run_table.c.owner_id
        stmt = (
            select(
                run_table.c.owner_id,
                user_table.c.email.label("owner_email"),
            )
            .select_from(run_table.outerjoin(user_table, owner_join))
            .where(run_table.c.runid == runid)
            .limit(1)
        )
        with db.engine.connect() as conn:
            row = conn.execute(stmt).first()

        if row is None:
            return '-'
        if row.owner_id is None:
            return 'anonymous'
        return row.owner_email or '-'
    except (ImportError, SQLAlchemyError, OSError, ValueError) as exc:
        logger.debug("Run owner unavailable for runid=%s: %s", runid, exc)
        return '-'
    except Exception:
        logger.exception("Unexpected error resolving run owner for runid=%s", runid)
        return '-'


def _get_last_modified(runid):
    try:
        from wepppy.nodb.base import redis_lock_client
    except Exception:
        redis_lock_client = None  # type: ignore

    last_ts = 0

    if redis_lock_client is not None:
        try:
            data = redis_lock_client.hgetall(runid) or {}
            raw_last = data.get('last_modified')
            if raw_last:
                last_ts = max(last_ts, int(round(float(raw_last))))
            for key, raw in data.items():
                if not key.startswith('timestamps:'):
                    continue
                try:
                    ts_val = int(round(float(raw)))
                    if ts_val > last_ts:
                        last_ts = ts_val
                except Exception:
                    continue
        except Exception:
            pass

    if last_ts == 0:
        wd = get_wd(runid)
        nodbs = glob(_join(wd, '*.nodb'))

        for fn in nodbs:
            statbuf = os.stat(fn)
            if statbuf.st_mtime > last_ts:
                last_ts = statbuf.st_mtime

    if last_ts == 0:
        return None

    rounded_ts = round(last_ts)
    return datetime.fromtimestamp(rounded_ts, tz=timezone.utc)

def _get_all_users():
    if UserModel is None:
        return []
    return UserModel.query.order_by(UserModel.last_login_at).all()

def register_context_processors(app, get_all_runs, user_model, run_model):
    global RunModel, UserModel
    RunModel = run_model
    UserModel = user_model

    @app.context_processor
    def inject_site_prefix():
        return dict(site_prefix=app.config.get('SITE_PREFIX', ''))

    @app.context_processor
    def versioned_static_processor():
        version = app.config.get("ASSET_VERSION")

        def controllers_gl_expected_build_id() -> str | None:
            candidates = []
            sync_dir = os.getenv("STATIC_ASSET_SYNC_DIR")
            if sync_dir:
                candidates.append(os.path.join(sync_dir, "js", "controllers-gl.js"))
            if app.static_folder:
                candidates.append(os.path.join(app.static_folder, "js", "controllers-gl.js"))

            for candidate in candidates:
                value = resolve_controllers_gl_build_id(Path(candidate))
                if value:
                    return value
            return None

        def static_url(filename: str):
            params = {"filename": filename}
            if version:
                params["v"] = version
            return url_for("static", **params)

        return dict(
            asset_version=version,
            static_url=static_url,
            controllers_gl_expected_build_id=controllers_gl_expected_build_id(),
        )
        
    @app.context_processor
    def utility_processor():
        def format_mode(mode):
            return str(int(mode))
        return dict(format_mode=format_mode)

    @app.context_processor
    def units_processor():
        return Unitizer.context_processor_package()

    @app.context_processor
    def commafy_processor():
        def commafy(v):
            try:
                return "{:,}".format(int(v))
            except (TypeError, ValueError, OverflowError):
                return v
            except Exception:
                logger.exception("Unexpected error commafying value=%r", v)
                return v

        return dict(commafy=commafy)

    @app.context_processor
    def isfloat_processor():
        return dict(isfloat=isfloat)

    @app.context_processor
    def startswith_processor():
        return dict(startswith=lambda x, y: str(x).startswith(str(y)))

    @app.context_processor
    def hasattr_processor():
        return dict(hasattr=lambda item, attr: hasattr(item, attr))

    @app.context_processor
    def current_ron_processor():
        # get current runid from request path
        from flask import request
        from wepppy.nodb.core.ron import RonViewModel
        runid = None
        path_parts = request.path.split('/')

        try:
            _indx = path_parts.index('runs')
            runid = path_parts[_indx + 1]
            ron = RonViewModel.getInstanceFromRunID(runid)
            mods = list(getattr(ron, 'mods', []) or [])
            storm_event_analyzer_ready = False
            ttl_state = None
            try:
                from wepppy.weppcloud.utils.helpers import get_wd
                from wepppy.nodb.core import Wepp
                from wepppy.weppcloud.utils.run_ttl import read_ttl_state

                wd = get_wd(runid)
                wepp = Wepp.load_detached(wd)
                storm_event_analyzer_ready = bool(
                    wepp and wepp.storm_event_analyzer_ready
                )
                ttl_state = read_ttl_state(wd)
            except Exception:
                storm_event_analyzer_ready = False
                ttl_state = None

            return dict(
                current_ron=ron,
                current_mods=mods,
                storm_event_analyzer_ready=storm_event_analyzer_ready,
                current_ttl=ttl_state,
            )
        except Exception:
            return dict(
                current_ron=None,
                current_mods=[],
                storm_event_analyzer_ready=False,
                current_ttl=None,
            )

    @app.context_processor
    def security_processor():
        return dict(run_exists=_run_exists,
                    get_run_name=_get_run_name,
                    get_run_owner=_get_run_owner,
                    get_last_modified=_get_last_modified,
                    get_all_runs=get_all_runs,
                    get_all_users=_get_all_users,
                    url_for_run=url_for_run)

    @app.context_processor
    def oauth_provider_processor():
        providers = app.config.get("OAUTH_PROVIDERS", {}) or {}
        enabled = {
            name: data
            for name, data in providers.items()
            if data and data.get("enabled")
        }
        return dict(
            oauth_providers=providers,
            enabled_oauth_providers=enabled,
        )

    @app.context_processor
    def auth_feature_flags_processor():
        return dict(enable_local_login=app.config.get("ENABLE_LOCAL_LOGIN", True))

    @app.context_processor
    def csrf_token_processor():
        try:
            from flask_wtf.csrf import generate_csrf
        except Exception:
            return {}
        return dict(csrf_token=generate_csrf)

    @app.context_processor
    def pup_context_processor():
        from flask import g
        return dict(pup_relpath=getattr(g, 'pup_relpath', None))
