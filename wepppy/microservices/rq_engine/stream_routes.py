"""Cookie-only, least-privileged browser stream credential bridge."""
from __future__ import annotations

import json
import logging
import stat
import zipfile
import os
import re
import time
import uuid
from pathlib import Path

import redis
from fastapi import APIRouter, Request
from fastapi.responses import JSONResponse
from rq.job import Job
from rq.exceptions import NoSuchJobError

from wepppy.config.secrets import SecretConfigurationError
from wepppy.config.redis_settings import RedisDB, redis_connection_kwargs
from wepppy.nodb.core import Ron
from wepppy.weppcloud.utils import auth_tokens
from . import session_routes as sessions
from .auth import AuthError, _check_session_revocation
from .feature_access import require_workflow_access
from .openapi import agent_route_responses, rq_operation_id
from .payloads import PayloadRoute
from .responses import error_response

logger = logging.getLogger(__name__)
router = APIRouter(route_class=PayloadRoute)
TTL_SECONDS = 300
IDENTIFIER = re.compile(r"^[A-Za-z0-9_.;-]+$")
CONFIG = re.compile(r"^[a-z0-9_-]+$")
# Atomic marker extension and SID fence check; never shorten existing RQ authority.
_MARKER_SCRIPT = """
if redis.call('EXISTS', KEYS[2]) == 1 then return 0 end
local ttl = redis.call('TTL', KEYS[1])
if ttl == -2 or (ttl >= 0 and ttl < tonumber(ARGV[1])) then
  redis.call('SETEX', KEYS[1], ARGV[1], '1')
end
return 1
"""


def _config(value: str) -> str:
    value = value.strip().lower().removesuffix('.cfg')
    if not CONFIG.fullmatch(value):
        raise AuthError("Invalid configuration", status_code=400, code="validation_error")
    return value


def _resolve_config(runid: str, requested: str) -> str:
    wd = Path(sessions.get_wd(runid, prefer_active=False))
    if not wd.is_dir() or not (wd / 'ron.nodb').is_file():
        raise AuthError("Run not found", status_code=404, code="not_found")
    ron = Ron.load_detached(str(wd))
    actual = _config(ron.config_stem)
    if requested not in {'cfg', actual}:
        raise AuthError("Run not found", status_code=404, code="not_found")
    return actual


def _restore_identity(runid: str) -> tuple[str, bool] | None:
    """Read identity from the exact active restore input, never extract/hydrate it."""
    authority_runid = sessions._authorization_runid(runid)
    bound_runid = None
    archive_name = None
    for candidate in dict.fromkeys([runid, authority_runid]):
        with redis.Redis(**redis_connection_kwargs(RedisDB.LOCK)) as conn:
            job_id = conn.hget(candidate, 'archive:job_id')
        if not job_id:
            continue
        if isinstance(job_id, bytes):
            job_id = job_id.decode('utf-8')
        with redis.Redis(**redis_connection_kwargs(RedisDB.RQ)) as conn:
            try:
                job = Job.fetch(job_id, connection=conn)
            except NoSuchJobError:
                continue
            if (job.func_name != 'wepppy.rq.project_rq.restore_archive_rq'
                    or job.origin != 'fork-archive' or job.get_status(refresh=True) != 'started'):
                continue
            if len(job.args) != 2 or job.args[0] != candidate:
                raise AuthError('Restore identity unavailable', status_code=503, code='service_unavailable')
            bound_runid, archive_name = candidate, job.args[1]
            break
    if bound_runid is None:
        return None
    from .fork_archive_routes import _resolve_run_archive_path
    wd = sessions.get_wd(bound_runid, prefer_active=False, read_only=True)
    ron_member = 'ron.nodb'
    if bound_runid != runid:
        # The bound parent archive is authoritative even while a legacy child
        # tree is absent and filesystem discovery would select another run root.
        kind, leaf = runid.split(';;')[-2:]
        if kind not in {'omni', 'omni-contrast'} or leaf in {'', '.', '..'}:
            raise AuthError('Restore identity unavailable', status_code=503, code='service_unavailable')
        category = 'scenarios' if kind == 'omni' else 'contrasts'
        ron_member = f'_pups/omni/{category}/{leaf}/ron.nodb'
    archive = _resolve_run_archive_path(wd, archive_name)
    with zipfile.ZipFile(archive) as source:
        names = source.namelist()
        if names.count(ron_member) != 1 or names.count('PUBLIC') > 1:
            raise AuthError('Restore identity unavailable', status_code=503, code='service_unavailable')
        info = source.getinfo(ron_member)
        if info.file_size > 1024 * 1024 or stat.S_ISLNK(info.external_attr >> 16):
            raise AuthError('Restore identity unavailable', status_code=503, code='service_unavailable')
        data = json.loads(source.read(info))
        state = data.get('py/state', data) if isinstance(data, dict) else None
        if not isinstance(state, dict) or not isinstance(state.get('_config'), str):
            raise AuthError('Restore identity unavailable', status_code=503, code='service_unavailable')
        if 'PUBLIC' in names and stat.S_ISLNK(source.getinfo('PUBLIC').external_attr >> 16):
            raise AuthError('Restore identity unavailable', status_code=503, code='service_unavailable')
        return _config(state['_config'].split('.cfg', 1)[0]), ('PUBLIC' in names and bound_runid == authority_runid)


def _has_session_cookie(request: Request) -> bool:
    names = {sessions._session_cookie_name()}
    if sessions._session_cookie_migration_enabled():
        names.update({sessions._primary_session_cookie_name(), sessions._legacy_session_cookie_name()})
    # Presence (including empty/invalid values) must never become public fallback.
    return any(part.strip().split('=', 1)[0] in names
               for raw in sessions._raw_cookie_headers(request)
               for part in raw.decode('latin-1').split(';'))


def _run_sync_config(job_id: str, runid: str, requested: str, roles: list[str]) -> str:
    if not {'admin', 'root'}.intersection(role.lower() for role in roles):
        raise AuthError("Run sync inspection requires administrator access", status_code=403, code="forbidden")
    with redis.Redis(**redis_connection_kwargs(RedisDB.RQ)) as conn:
        try:
            job = Job.fetch(job_id, connection=conn)
        except NoSuchJobError as exc:
            raise AuthError("Job not found", status_code=404, code="not_found") from exc
        if (job.func_name != 'wepppy.rq.run_sync_rq.run_sync_rq' or job.origin != 'default'
                or len(job.args) != 5 or job.args[0] != runid):
            raise AuthError("Job not authorized", status_code=403, code="forbidden")
        actual = _config(job.args[4] or 'cfg')
        if requested != actual:
            raise AuthError("Job not authorized", status_code=403, code="forbidden")
        return actual


def _store_marker(runid: str, sid: str) -> None:
    with redis.Redis(**redis_connection_kwargs(RedisDB.SESSION)) as conn:
        if conn.eval(_MARKER_SCRIPT, 2, f'auth:session:run:{runid}:{sid}',
                     f'auth:session:revoked:{sid}', TTL_SECONDS) != 1:
            raise AuthError("Session expired or invalid", status_code=401, code="unauthorized")


@router.post(
    '/runs/{runid}/{config}/stream-token',
    summary='Issue a short-lived status or preflight credential',
    tags=['rq-engine', 'session'], operation_id=rq_operation_id('issue_stream_token'),
    responses=agent_route_responses(success_code=200, success_description='Stream credential issued.'),
)
async def issue_stream_token(runid: str, config: str, request: Request) -> JSONResponse:
    try:
        if 'authorization' in request.headers:
            raise AuthError("Use the browser session bridge", status_code=400, code="validation_error")
        if not sessions._is_same_origin_cookie_request(request):
            raise AuthError("Cross-origin request blocked", status_code=403, code="forbidden")
        if (not IDENTIFIER.fullmatch(runid) or len(runid) > 255
                or any(part in {'', '.', '..'} for part in runid.split(';;'))):
            raise AuthError("Invalid run identifier", status_code=400, code="validation_error")
        requested = _config(config)
        payload = await sessions._parse_optional_json_payload(request)
        service = payload.get('service')
        job_id = payload.get('job_id')
        if (not isinstance(service, str) or service not in {'status', 'preflight'} or set(payload) - {'service', 'job_id'}
                or ('job_id' in payload and (service != 'status' or not isinstance(job_id, str)
                    or not re.fullmatch(r'[A-Za-z0-9_-]{1,128}', job_id)))):
            raise AuthError("Invalid stream request", status_code=400, code="validation_error")
        user_id, roles = None, []
        if _has_session_cookie(request):
            sid, session_payload = sessions._resolve_session_from_cookie(request)
            _check_session_revocation(sid)
            user_id, roles = sessions._identity_from_session_payload(session_payload)
        else:
            sid = uuid.uuid4().hex
        if job_id:
            if user_id is None:
                raise AuthError("Session required", status_code=401, code="unauthorized")
            actual = _run_sync_config(job_id, runid, requested, roles)
        else:
            restoring = _restore_identity(runid)
            restored_public = False
            if restoring is not None:
                actual, restored_public = restoring
                if requested not in {'cfg', actual}:
                    raise AuthError('Run not found', status_code=404, code='not_found')
            else:
                actual = _resolve_config(runid, requested)
            if not restored_public and not sessions._session_user_authorized_for_run(runid, user_id, roles):
                raise AuthError("Run not authorized", status_code=403, code="forbidden")
            from wepppy.weppcloud.utils.feature_access import VerifiedPrincipal
            from wepppy.weppcloud.utils.feature_access_identity import principal_claim
            principal = VerifiedPrincipal('human', user_id) if user_id is not None else VerifiedPrincipal()
            origin_claims = {'token_class': 'session', 'feature_access_principal': principal_claim(principal)}
            if restored_public:
                # Same canonical public Batch inspection exception, using the
                # bound restore input while the live PUBLIC marker is absent.
                from .feature_access import require_feature_access
                from wepppy.weppcloud.utils.feature_access_runtime import workflow_features
                for feature_id in workflow_features(runid):
                    if feature_id != 'batch_runner':
                        require_feature_access(origin_claims, feature_id, runid=runid,
                                               operation='inspect', protected_read=True)
            else:
                require_workflow_access(origin_claims, runid, operation='inspect')
        if not (os.getenv('WEPP_AUTH_JWT_SECRETS_FILE') or os.getenv('WEPP_AUTH_JWT_SECRET_FILE')):
            raise auth_tokens.JWTConfigurationError('Stream signing requires a secret file')
        try:
            signing = auth_tokens.get_jwt_config()
        except ValueError as exc:
            raise auth_tokens.JWTConfigurationError('Invalid signing configuration') from exc
        now = int(time.time())
        claims = dict(iss='weppcloud-stream', aud='wepp-' + service, token_class='session',
                      stream=service, scope=service + ':read', runid=runid, config=actual,
                      sub=sid, session_id=sid, jti=uuid.uuid4().hex, iat=now, nbf=now, exp=now + TTL_SECONDS)
        if job_id:
            claims.update(job_id=job_id, operation='run-sync', channel='run_sync')
        token = auth_tokens.encode_jwt(claims, signing.secret, algorithm='HS256')
        _store_marker(runid, sid)
        return JSONResponse(dict(token=token, expires_at=claims['exp'], expires_in=TTL_SECONDS,
                                 service=service, config=actual), headers={'Cache-Control': 'no-store'})
    except AuthError as exc:
        return error_response(exc.message, status_code=exc.status_code, code=exc.code)
    except (redis.RedisError, OSError, zipfile.BadZipFile):
        logger.warning('Stream authorization dependency unavailable')
        return error_response('Stream authorization unavailable', status_code=503, code='service_unavailable', log_exception=False)
    except (auth_tokens.JWTConfigurationError, SecretConfigurationError):
        logger.warning('Stream signing configuration unavailable')
        return error_response('Stream signing unavailable', status_code=503, code='service_unavailable', log_exception=False)
    except ValueError:
        return error_response('Invalid run or configuration', status_code=400, code='validation_error')
