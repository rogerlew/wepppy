"""Run-scoped browser readiness and background refresh registration."""
from __future__ import annotations

import json
import logging

from redis.exceptions import RedisError
from starlette.concurrency import run_in_threadpool
from starlette.exceptions import HTTPException
from starlette.responses import JSONResponse

from wepppy.query_engine.access_scope import access_scope
from wepppy.query_engine.catalog_refresh import (
    CatalogRefreshConflict, browser_catalog_parent, catalog_readiness,
    catalog_refresh_status, is_catalog_readonly, prepare_catalog_intent, resolve_scope,
)
from wepppy.rq.query_catalog_rq import catalog_recovery_registered
from .access import authorize_request, query_data_root

LOGGER = logging.getLogger(__name__)


def _response(state: str, code: str | None = None, status: int = 200, *, retry: bool = False) -> JSONResponse:
    headers = {'Cache-Control': 'no-store'}
    if status == 202 or retry:
        headers['Retry-After'] = '2'
    body = {'state': state}
    if code is not None:
        body['code'] = code
    return JSONResponse(body, status_code=status, headers=headers)


def _catalog_ready(query_pending: bool) -> JSONResponse:
    if query_pending:
        return _response('preparing', 'catalog_preparing', 202)
    return _response('ready')


def require_prepare_origin(request) -> None:
    if request.state.query_source == 'bearer':
        return
    from .server import _is_same_origin_request
    if not _is_same_origin_request(request):
        raise HTTPException(403, 'Same-origin request required')


def readiness_response(request, scenario, *, prepare=False, paths=(), query_pending=False):
    target, base = query_data_root(request, scenario)
    try:
        relative = base.relative_to(target.path).parts
        if relative and (len(relative) != 4 or relative[:3] not in {
            ('_pups', 'omni', 'scenarios'), ('_pups', 'omni', 'contrasts')
        }):
            raise HTTPException(404, 'Run not found')
        def checkpoint():
            current_target, current_base = query_data_root(request, scenario)
            if current_target != target or current_base != base:
                raise HTTPException(404, 'Run not found')

        with access_scope(base, target.parent_path, checkpoint):
            parent = browser_catalog_parent(base)
            if parent is not None and parent != target.parent_path:
                raise HTTPException(404, 'Run not found')
            observed_scope = resolve_scope(base)
            state = catalog_readiness(base)
            if prepare and (state != 'ready' or paths):
                if parent is not None:
                    state = prepare_catalog_intent(base, paths, observed_scope=observed_scope)
                elif is_catalog_readonly(base):
                    state = 'readonly'
                else:
                    state = 'unavailable'
            if state == 'ready':
                return _catalog_ready(query_pending)
            if state == 'busy':
                return _response('unavailable', 'catalog_refresh_unavailable', 503, retry=True)
            if state == 'readonly':
                return _response('unavailable', 'catalog_readonly', 409)
            if state == 'pending' and parent is not None:
                checkpoint()
                scope = resolve_scope(base)
                if (scope.directory_identity != observed_scope.directory_identity or
                        (observed_scope.incarnation and scope.incarnation != observed_scope.incarnation)):
                    return _response('unavailable', 'catalog_refresh_unavailable', 503, retry=prepare)
                if catalog_recovery_registered(scope, register=prepare):
                    return _response('preparing', 'catalog_preparing', 202)
                # The worker can publish and the scheduler can remove the
                # dirty index entry between the readiness and Redis reads.
                if catalog_readiness(base) == 'ready':
                    return _catalog_ready(query_pending)
                status = catalog_refresh_status(base)
                if status.get('state') == 'failed' and status.get('incarnation') == scope.incarnation:
                    return _response('unavailable', 'catalog_refresh_failed', 503)
    except FileNotFoundError as exc:
        raise HTTPException(404, 'Run not found') from exc
    except PermissionError as exc:
        raise HTTPException(403, 'Catalog source outside authorized resource') from exc
    except (CatalogRefreshConflict, RedisError, OSError, ValueError):
        LOGGER.warning('Catalog readiness check unavailable', exc_info=True)
    return _response('unavailable', 'catalog_refresh_unavailable', 503)


async def catalog_prepare(request):
    await run_in_threadpool(authorize_request, request, 'query')
    require_prepare_origin(request)
    try:
        body = await request.json()
    except (json.JSONDecodeError, UnicodeDecodeError) as exc:
        raise HTTPException(400, 'Invalid catalog preparation payload') from exc
    if not isinstance(body, dict) or body.keys() - {'scenario'}:
        raise HTTPException(400, 'Invalid catalog preparation payload')
    scenario = body.get('scenario')
    if scenario is not None and not isinstance(scenario, str):
        raise HTTPException(400, 'Invalid scenario')
    return await run_in_threadpool(readiness_response, request, scenario, prepare=True)


async def catalog_status(request):
    await run_in_threadpool(authorize_request, request, 'query')
    if any(key != 'scenario' for key in request.query_params) or len(request.query_params.getlist('scenario')) > 1:
        raise HTTPException(400, 'Invalid catalog status parameters')
    return await run_in_threadpool(readiness_response, request, request.query_params.get('scenario'))
