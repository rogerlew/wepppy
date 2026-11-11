"""Primary HTTP authorization, bound to a checked canonical query target.

MCP retains its independent authentication. Shared JWT, session and feature
adapters are reused without invoking their mutable working-directory lookups.
"""
from __future__ import annotations

import os
from pathlib import Path
from urllib.parse import urlsplit

from starlette.exceptions import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from redis.exceptions import RedisError

from wepppy.microservices.browse import auth as browse_auth
from wepppy.microservices.rq_engine import auth as rq_auth
from wepppy.microservices.rq_engine.feature_access import require_feature_access, verified_principal
from wepppy.nodb.base import NoDbBase
from wepppy.weppcloud.utils import auth_tokens, helpers as run_helpers
from wepppy.weppcloud.utils.browse_cookie import query_cookie_name
from .helpers import QueryTarget, resolve_http_target, checked_path


def configured_origins() -> list[str]:
    origins = []
    for raw in os.getenv('QUERY_ENGINE_ALLOWED_ORIGINS', '').split(','):
        raw = raw.strip()
        if not raw:
            continue
        parsed = urlsplit(raw)
        if (parsed.scheme not in {'http', 'https'} or not parsed.hostname
                or parsed.username or parsed.password or parsed.path not in {'', '/'}
                or parsed.query or parsed.fragment or '*' in raw):
            raise ValueError('QUERY_ENGINE_ALLOWED_ORIGINS must contain exact HTTP(S) origins')
        parsed.port  # Validate malformed ports at startup.
        origins.append(raw.rstrip('/'))
    return origins


def _origin_tuple(value):
    p = urlsplit(value)
    if p.scheme not in {'http', 'https'} or not p.hostname or p.username or p.password:
        return None
    if p.path not in {'', '/'} or p.query or p.fragment:
        return None
    return p.scheme.lower(), p.hostname.lower(), p.port or (443 if p.scheme == 'https' else 80)


def check_origin(request):
    origin = request.headers.get('origin')
    if origin is not None:
        try:
            candidate = _origin_tuple(origin)
        except ValueError:
            candidate = None
        if candidate is None or candidate not in {_origin_tuple(o) for o in configured_origins()}:
            raise HTTPException(403, 'Origin not allowed')


def _decode(token):
    try:
        claims = auth_tokens.decode_token(token, audience='query-engine')
    except auth_tokens.JWTDecodeError as exc:
        raise HTTPException(401, 'Invalid credentials') from exc
    try:
        rq_auth.require_current_claims(claims)
    except rq_auth.AuthError as exc:
        if exc.status_code >= 500:
            raise
        raise HTTPException(401, 'Invalid credentials') from exc
    return claims


def _resource_ids(target):
    ids = set(target.credential_ids)
    if target.parent_id.startswith(('batch;;', 'culvert;;')):
        ids.add(target.parent_id.split(';;')[1])
    return ids


def _verify_claims(claims, target, operation, source):
    token_class = claims.get('token_class')
    if (token_class not in {'user', 'service', 'session'}
            or (source == 'cookie' and token_class != 'session')):
        raise HTTPException(403, 'Credential class not allowed')
    scopes = rq_auth._normalize_scopes(claims.get('scope'), auth_tokens.get_jwt_config().scope_separator)
    required = {'runs:read'}
    if operation == 'query' or (operation == 'activate' and source == 'cookie'):
        required.add('queries:execute')
    if operation == 'activate' and source == 'bearer':
        required.add('runs:activate')
    if not required.issubset(scopes):
        raise HTTPException(403, 'Insufficient scope')
    runs = browse_auth._normalize_list(claims.get('runs') or claims.get('runid'))
    if (runs and _resource_ids(target).isdisjoint(runs)) or (not runs and token_class != 'user'):
        raise HTTPException(403, 'Credential not authorized for run')
    if token_class == 'session':
        if claims.get('config') != target.config:
            raise HTTPException(403, 'Credential configuration mismatch')
        rq_auth.require_session_marker(claims, str(claims.get('runid') or ''))


def _credentials(request, target, operation):
    bearer = browse_auth._extract_bearer_token(request)
    if bearer:
        claims = _decode(bearer)
        _verify_claims(claims, target, operation, 'bearer')
        return claims, 'bearer'
    for resource in target.credential_ids:
        token = request.cookies.get(query_cookie_name(resource, target.config))
        if not token:
            continue
        try:
            claims = _decode(token)
            # A prefix-scoped cookie must bind to the exact selected key.
            if claims.get('runid') != resource or claims.get('config') != target.config:
                continue
            _verify_claims(claims, target, operation, 'cookie')
            return claims, 'cookie'
        except (rq_auth.AuthError, HTTPException) as exc:
            if exc.status_code >= 500:
                raise
            if exc.status_code == 403:
                raise
            # Expired/revoked cookies are anonymous; explicit bearer never falls back.
    return None, 'none'


def _ownerless_metadata(path):
    from wepppy.nodb.core import Ron
    metadata = path / 'ron.nodb'
    if not metadata.is_file() or metadata.is_symlink():
        raise HTTPException(404, 'Run not found')
    # getInstance/load_detached initialize logs or ensure VERSION. Admission must
    # use the canonical decoder directly, without those write-capable adapters.
    text = Ron._preprocess_json_for_decode(metadata.read_text())
    Ron._ensure_legacy_module_imports(text)
    if not isinstance(Ron._decode_jsonpickle(text), Ron):
        raise HTTPException(404, 'Run not found')


def _authorize_resource(target, claims, *, operation='read', source='bearer'):
    """Authorize using only checked paths and current account/resource state."""
    rq_auth._reject_fork_preparing_run(target.parent_id)
    parts = target.parent_id.split(';;')
    grouped = parts[0] in {'batch', 'culvert'} and len(parts) == 3
    public = NoDbBase.ispublic(str(target.group_base or target.parent_path))
    if parts[0] in {'profile', 'culvert'} and len(parts) == 3:
        public = False
    if grouped:
        if not public or operation == 'activate':
            if claims is None:
                raise HTTPException(401, 'Authentication required')
            if parts[0] == 'culvert' and claims.get('token_class') == 'session':
                raise HTTPException(403, 'Credential class not allowed')
            principal = require_feature_access(claims, parts[0] + '_runner',
                                               operation='inspect', protected_read=True)
            if source == 'cookie' and operation == 'activate' and principal.kind != 'human':
                raise HTTPException(403, 'Authenticated human required')
        return
    owners = None
    if not public:
        owners = run_helpers.get_run_owners_lazy(target.parent_id)
        if not owners and len(parts) == 1:
            _ownerless_metadata(target.parent_path)
            public = True
    if public and operation != 'activate':
        return
    if claims is None:
        raise HTTPException(401, 'Authentication required')
    if claims.get('token_class') == 'service':
        return  # Already checked signed resource and operation scopes.
    principal = verified_principal(claims)
    if principal.kind != 'human':
        raise HTTPException(403, 'Run access denied')
    if principal.roles & {'Admin', 'Root'}:
        return
    if owners is None:
        owners = run_helpers.get_run_owners_lazy(target.parent_id)
    if any(owner.id == principal.user_id for owner in owners):
        return
    if operation != 'activate' and 'PortlandGroup' in principal.roles:
        from wepppy.weppcloud.utils.portland_collections import portland_runids
        if target.parent_id in portland_runids():
            return
    raise HTTPException(403, 'Run access denied')


def authorize_resource(target, claims, *, operation='read', source='bearer'):
    """Translate account/store failures at every admission and recheck boundary."""
    try:
        return _authorize_resource(target, claims, operation=operation, source=source)
    except (SQLAlchemyError, RedisError, RuntimeError, OSError) as exc:
        raise HTTPException(503, 'Authorization service unavailable') from exc


def authorize_request(request, operation='read') -> QueryTarget:
    check_origin(request)
    try:
        target = resolve_http_target(request.path_params['runid'])
    except ValueError as exc:
        raise HTTPException(400, 'Invalid run/config target') from exc
    except FileNotFoundError as exc:
        raise HTTPException(404, 'Run not found') from exc
    try:
        claims, source = _credentials(request, target, operation)
        if source == 'cookie' and request.method == 'POST':
            from .server import _is_same_origin_request
            if not _is_same_origin_request(request):
                raise HTTPException(403, 'Same-origin request required')
        authorize_resource(target, claims, operation=operation, source=source)
    except (rq_auth.AuthError, browse_auth.BrowseAuthError) as exc:
        raise HTTPException(exc.status_code, 'Authentication required' if exc.status_code == 401 else 'Run access denied') from exc
    request.state.query_target = target
    request.state.query_claims = claims
    request.state.query_operation = operation
    request.state.query_source = source
    return target


def recheck(request):
    target = request.state.query_target
    # Revalidate physical identity without consulting the WD cache.
    if (target.path.resolve() != target.path or target.parent_path.resolve() != target.parent_path
            or (target.group_base is not None and target.group_base.resolve() != target.group_base)):
        raise HTTPException(404, 'Run not found')
    claims = request.state.query_claims
    try:
        if claims is not None:
            rq_auth.require_current_claims(claims)
            if claims.get('token_class') == 'session':
                rq_auth.require_session_marker(claims, str(claims['runid']))
        authorize_resource(target, claims, operation=request.state.query_operation,
                           source=request.state.query_source)
    except rq_auth.AuthError as exc:
        raise HTTPException(exc.status_code, 'Run access denied') from exc
    except (SQLAlchemyError, RedisError, RuntimeError, OSError) as exc:
        raise HTTPException(503, 'Authorization service unavailable') from exc
    return target


def require_data_path(request, path):
    target = request.state.query_target
    from wepppy.query_engine.access_scope import AccessScope
    base = getattr(request.state, 'query_data_root', target.path)
    try:
        AccessScope(base, target.parent_path, lambda: None).require_path(Path(path))
    except PermissionError as exc:
        raise HTTPException(403, 'Dataset outside authorized resource') from exc


def prepare_context(request, run_path, *, scenario=None, **kwargs):
    """Validate scenario/cache paths before any context activation or repair."""
    from wepppy.query_engine.context import _resolve_scenario_dir, resolve_run_context
    target = recheck(request)
    base = _resolve_scenario_dir(target.path, scenario)
    try:
        checked_path(base, target.path)
        checked_path(base / '_query_engine', target.path)
        checked_path(base / '_query_engine' / 'catalog.json', target.path)
    except (ValueError, FileNotFoundError) as exc:
        raise HTTPException(404, 'Run not found') from exc
    request.state.query_data_root = base
    from wepppy.query_engine.access_scope import access_scope
    try:
        with access_scope(base, target.parent_path, lambda: recheck(request)):
            from wepppy.query_engine.access_scope import current_scope
            from wepppy.query_engine.catalog_refresh import _load_catalog, pending_catalog_requests
            retained = _load_catalog(base, rebuild_malformed=True)
            if retained is None or pending_catalog_requests(base):
                # Only new/repairing catalogs need a tree preflight. Cached reads
                # validate selected sources, preserving targeted freshness costs.
                current_scope().before_scan(base)
            if retained is not None:
                for entry in retained['files']:
                    selected = entry.get('fs_path') or entry['path']
                    current_scope().source_path(Path(selected), retained.get('root'))
            context = resolve_run_context(str(base), **kwargs)
            if context.catalog.root != base:
                from dataclasses import replace
                from wepppy.query_engine.catalog import DatasetCatalog
                entries = [replace(entry, fs_path=str(current_scope().source_path(
                    Path(entry.fs_path or entry.path), str(context.catalog.root))))
                    for entry in context.catalog.entries()]
                context.catalog = DatasetCatalog(base, entries)
            return context
    except PermissionError as exc:
        if (base / 'READONLY').exists():
            raise HTTPException(409, 'Project is read-only') from exc
        raise HTTPException(403, 'Dataset outside authorized resource') from exc


def execute_scoped(request, callback, *args, **kwargs):
    from wepppy.query_engine.access_scope import access_scope
    target = recheck(request)
    base = getattr(request.state, 'query_data_root', target.path)
    try:
        with access_scope(base, target.parent_path, lambda: recheck(request)):
            from wepppy.query_engine.access_scope import current_scope
            if kwargs.get('force_refresh'):
                current_scope().before_scan(base)
            return callback(*args, **kwargs)
    except PermissionError as exc:
        if (base / 'READONLY').exists():
            raise HTTPException(409, 'Project is read-only') from exc
        raise HTTPException(403, 'Dataset outside authorized resource') from exc
