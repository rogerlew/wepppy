"""D-Tale route helpers for the browse microservice."""

from __future__ import annotations

import logging
import os
from http import HTTPStatus
from pathlib import Path
from typing import Callable

import httpx
from starlette.exceptions import HTTPException
from starlette.requests import Request as StarletteRequest
from starlette.responses import RedirectResponse

_DTALE_SERVICE_URL = os.getenv('DTALE_SERVICE_URL', 'http://dtale:9010').rstrip('/')
_DTALE_INTERNAL_TOKEN = os.getenv('DTALE_INTERNAL_TOKEN', '').strip()
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
        wd_override: str | Path | None = None,
    ):
        if not _DTALE_SERVICE_URL:
            raise HTTPException(
                status_code=HTTPStatus.SERVICE_UNAVAILABLE,
                detail='D-Tale integration is not configured.',
            )

        subpath = request.path_params.get('subpath') or ''
        rel_path = subpath.lstrip('/')

        wd = os.path.abspath(str(wd_override)) if wd_override is not None else os.path.abspath(get_wd(runid))
        target = os.path.abspath(os.path.join(wd, rel_path))
        assert_within_root(wd, target)

        if not os.path.isfile(target):
            raise HTTPException(status_code=HTTPStatus.NOT_FOUND, detail='File not found.')

        rel_lower = rel_path.lower()
        if not any(rel_lower.endswith(ext) for ext in DTALE_SUPPORTED_SUFFIXES):
            raise HTTPException(
                status_code=HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
                detail='D-Tale currently supports parquet, csv/tsv, feather, and pickle files.',
            )

        payload = {
            'runid': runid,
            'config': config,
            'path': rel_path.replace('\\', '/'),
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

        logger.info('Forwarding %s to D-Tale at %s', rel_path, target_url)
        return RedirectResponse(url=target_url, status_code=HTTPStatus.SEE_OTHER)

    async def dtale_open(request: StarletteRequest):
        runid = request.path_params['runid']
        config = request.path_params['config']
        return await _dtale_open_for_root(request, runid=runid, config=config)

    async def dtale_culvert_open(request: StarletteRequest):
        batch_uuid = request.path_params['uuid']
        batch_root = resolve_culvert_batch_root(batch_uuid)
        return await _dtale_open_for_root(
            request,
            runid=batch_uuid,
            config='culvert-batch',
            wd_override=batch_root,
        )

    async def dtale_batch_open(request: StarletteRequest):
        batch_name = request.path_params['batch_name']
        batch_root = resolve_batch_root(batch_name)
        return await _dtale_open_for_root(
            request,
            runid=batch_name,
            config='batch',
            wd_override=batch_root,
        )

    return dtale_open, dtale_culvert_open, dtale_batch_open


__all__ = ['DTALE_SUPPORTED_SUFFIXES', 'build_handlers', 'resolve_dtale_base']
