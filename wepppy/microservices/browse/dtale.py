"""D-Tale route helpers for the browse microservice."""

from __future__ import annotations

import logging
import os
from http import HTTPStatus
from pathlib import Path
from typing import Callable, Sequence

import httpx
from starlette.exceptions import HTTPException
from starlette.requests import Request as StarletteRequest
from starlette.responses import RedirectResponse

from wepppy.config.secrets import get_secret
from wepppy.microservices.browse.auth import (
    RUN_ALLOWED_TOKEN_CLASSES,
    USER_SERVICE_TOKEN_CLASSES,
    BrowseAuthError,
    authorize_group_request,
    authorize_run_request,
    handle_auth_error,
)
from wepppy.microservices.browse.security import (
    PATH_SECURITY_FORBIDDEN_RECORDER,
    path_security_detail,
    validate_raw_subpath,
    validate_resolved_target,
)
from wepppy.runtime_paths.errors import NoDirError
from wepppy.runtime_paths.fs import resolve as nodir_resolve
from wepppy.runtime_paths.fs import stat as nodir_stat
from wepppy.runtime_paths.materialize import materialize_file
from wepppy.runtime_paths.paths import parse_external_subpath

_DTALE_SERVICE_URL = os.getenv('DTALE_SERVICE_URL', 'http://dtale:9010').rstrip('/')
_DTALE_INTERNAL_TOKEN = (get_secret('DTALE_INTERNAL_TOKEN') or '').strip()
DTALE_SUPPORTED_SUFFIXES = (
    '.parquet',
    '.pq',
    '.feather',
    '.arrow',
    '.csv',
    '.csv.gz',
    '.tsv',
    '.tsv.gz',
    '.pkl',
    '.pickle',
)
_DTALE_HTTP_TIMEOUT = httpx.Timeout(60.0, connect=5.0)


def _nodir_error_payload(err: NoDirError) -> dict:
    return {
        'error': {
            'message': err.message,
            'code': err.code,
            'details': err.message,
        }
    }


def _raise_nodir_http_exception(err: NoDirError) -> None:
    raise HTTPException(status_code=err.http_status, detail=_nodir_error_payload(err))


def resolve_dtale_base(
    request_path: str,
    runid: str,
    config: str,
    prefix_path: Callable[[str], str],
) -> str:
    browse_marker = '/browse'
    if browse_marker in request_path:
        base = request_path.split(browse_marker, 1)[0]
        browse_base = f'{base}/browse/'
    else:
        browse_base = prefix_path(f'/runs/{runid}/{config}/browse/')

    if '/browse/' in browse_base:
        return browse_base.replace('/browse/', '/dtale/', 1)
    if browse_base.endswith('/browse'):
        return browse_base[: -len('/browse')] + '/dtale/'
    return prefix_path(f'/runs/{runid}/{config}/dtale/')


def build_handlers(
    *,
    get_wd: Callable[[str], str],
    assert_within_root: Callable[[str | Path, str | Path], None],
    resolve_culvert_batch_root: Callable[[str], Path],
    resolve_batch_root: Callable[[str], Path],
    logger: logging.Logger,
):
    async def _dtale_open_for_root(
        request: StarletteRequest,
        *,
        runid: str,
        config: str,
        auth_mode: str,
        wd_override: str | Path | None = None,
        group_allowed_token_classes: Sequence[str] = USER_SERVICE_TOKEN_CLASSES,
        group_identifier_claim_aliases: Sequence[str] | None = None,
        group_allow_public_without_token: bool = False,
        group_public_runid: str | None = None,
    ):
        if not _DTALE_SERVICE_URL:
            raise HTTPException(
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                detail='D-Tale integration is not configured.',
            )

        subpath = request.path_params.get('subpath') or ''
        rel_path = subpath.lstrip('/')
        if auth_mode == 'run':
            try:
                auth_context = authorize_run_request(
                    request,
                    runid=runid,
                    config=config,
                    subpath=rel_path,
                    allow_public_without_token=False,
                    require_authenticated=True,
                    allowed_token_classes=RUN_ALLOWED_TOKEN_CLASSES,
                )
            except BrowseAuthError as exc:
                return handle_auth_error(
                    request,
                    runid=runid,
                    error=exc,
                    redirect_on_401=True,
                )
        else:
            try:
                auth_context = authorize_group_request(
                    request,
                    identifier=runid,
                    subpath=rel_path,
                    allowed_token_classes=group_allowed_token_classes,
                    identifier_claim_aliases=group_identifier_claim_aliases,
                    allow_public_without_token=group_allow_public_without_token,
                    public_runid=group_public_runid,
                )
            except BrowseAuthError as exc:
                raise HTTPException(status_code=exc.status_code, detail=exc.message)

        allow_recorder = auth_context.is_root
        raw_violation = validate_raw_subpath(rel_path)
        if raw_violation is not None:
            if allow_recorder and raw_violation == PATH_SECURITY_FORBIDDEN_RECORDER:
                raw_violation = None
        if raw_violation is not None:
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN,
                detail=path_security_detail(raw_violation),
            )

        try:
            logical_rel_path, nodir_view = parse_external_subpath(
                rel_path,
                allow_admin_alias=False,
            )
        except ValueError:
            raise HTTPException(status_code=HTTPStatus.BAD_REQUEST, detail='Invalid path.')

        wd = os.path.abspath(str(wd_override)) if wd_override is not None else os.path.abspath(get_wd(runid))

        # Enforce mixed/invalid/locked precedence before boundary-specific handling.
        try:
            nodir_resolve(wd, logical_rel_path, view='effective')
        except NoDirError as err:
            _raise_nodir_http_exception(err)

        requested_target = os.path.abspath(os.path.join(wd, logical_rel_path))
        assert_within_root(wd, requested_target)
        resolved_violation = validate_resolved_target(wd, requested_target)
        if resolved_violation is not None:
            if allow_recorder and resolved_violation == PATH_SECURITY_FORBIDDEN_RECORDER:
                resolved_violation = None
        if resolved_violation is not None:
            raise HTTPException(
                status_code=HTTPStatus.FORBIDDEN,
                detail=path_security_detail(resolved_violation),
            )

        try:
            nodir_target = nodir_resolve(wd, logical_rel_path, view=nodir_view)
        except NoDirError as err:
            _raise_nodir_http_exception(err)

        if nodir_target is None:
            if not os.path.isfile(requested_target):
                raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail='File not found.')
            dtale_rel_path = logical_rel_path.replace('\\', '/')
        else:
            try:
                nodir_entry = nodir_stat(nodir_target)
            except NoDirError as err:
                _raise_nodir_http_exception(err)
            except (FileNotFoundError, NotADirectoryError):
                raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail='File not found.')

            if nodir_entry.is_dir:
                raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail='File not found.')

            if nodir_target.form == 'archive':
                try:
                    materialized_path = Path(materialize_file(wd, logical_rel_path, purpose='dtale'))
                except NoDirError as err:
                    _raise_nodir_http_exception(err)
                except (FileNotFoundError, IsADirectoryError):
                    raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail='File not found.')

                try:
                    dtale_rel_path = materialized_path.relative_to(Path(wd)).as_posix()
                except ValueError as exc:
                    raise HTTPException(
                        status_code=HTTPStatus.INTERNAL_SERVER_ERROR,
                        detail='Failed to prepare materialized file path.',
                    ) from exc
            else:
                if not os.path.isfile(requested_target):
                    raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail='File not found.')
                dtale_rel_path = logical_rel_path.replace('\\', '/')

        rel_lower = dtale_rel_path.lower()
        if not any(rel_lower.endswith(ext) for ext in DTALE_SUPPORTED_SUFFIXES):
            raise HTTPException(
                status_code=HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
                detail='D-Tale currently supports parquet, csv/tsv, feather, and pickle files.',
            )

        payload = {
            'runid': runid,
            'config': config,
            'path': dtale_rel_path,
        }
        headers = {}
        if _DTALE_INTERNAL_TOKEN:
            headers['X-DTALE-TOKEN'] = _DTALE_INTERNAL_TOKEN

        endpoint = f'{_DTALE_SERVICE_URL}/internal/load'
        try:
            async with httpx.AsyncClient(timeout=_DTALE_HTTP_TIMEOUT) as client:
                response = await client.post(endpoint, json=payload, headers=headers)
        except httpx.HTTPError as exc:
            logger.error('Unable to reach D-Tale loader at %s', endpoint, exc_info=True)
            raise HTTPException(
                status_code=HTTPStatus.BAD_GATEWAY,
                detail='Unable to contact the D-Tale service.',
            ) from exc

        if response.status_code >= 400:
            detail = None
            try:
                error_payload = response.json()
                detail = error_payload.get('description') or error_payload.get('error')
            except ValueError:
                detail = response.text.strip()
            detail = detail or 'D-Tale rejected the load request.'
            raise HTTPException(status_code=response.status_code, detail=detail)

        try:
            data = response.json()
        except ValueError as exc:
            logger.error('Invalid response from D-Tale: %s', response.text)
            raise HTTPException(
                status_code=HTTPStatus.BAD_GATEWAY,
                detail='Received malformed response from D-Tale.',
            ) from exc

        target_url = data.get('url')
        if not target_url:
            raise HTTPException(
                status_code=HTTPStatus.BAD_GATEWAY,
                detail='D-Tale response missing redirect URL.',
            )

        logger.info('Forwarding %s to D-Tale at %s', logical_rel_path, target_url)
        return RedirectResponse(url=target_url, status_code=HTTPStatus.SEE_OTHER)

    async def dtale_open(request: StarletteRequest):
        runid = request.path_params['runid']
        config = request.path_params['config']
        return await _dtale_open_for_root(
            request,
            runid=runid,
            config=config,
            auth_mode='run',
        )

    async def dtale_culvert_open(request: StarletteRequest):
        batch_uuid = request.path_params['uuid']
        batch_root = resolve_culvert_batch_root(batch_uuid)
        return await _dtale_open_for_root(
            request,
            runid=batch_uuid,
            config='culvert-batch',
            auth_mode='group',
            wd_override=batch_root,
        )

    async def dtale_batch_open(request: StarletteRequest):
        batch_name = request.path_params['batch_name']
        batch_root = resolve_batch_root(batch_name)
        base_runid = f"batch;;{batch_name};;_base"
        return await _dtale_open_for_root(
            request,
            runid=batch_name,
            config='batch',
            auth_mode='group',
            wd_override=batch_root,
            group_allowed_token_classes=RUN_ALLOWED_TOKEN_CLASSES,
            group_identifier_claim_aliases=(base_runid,),
            group_allow_public_without_token=True,
            group_public_runid=base_runid,
        )

    return dtale_open, dtale_culvert_open, dtale_batch_open


__all__ = ['DTALE_SUPPORTED_SUFFIXES', 'build_handlers', 'resolve_dtale_base']
