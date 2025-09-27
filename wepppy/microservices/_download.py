"""Starlette-compatible download routes extracted from the legacy Flask blueprint."""

from __future__ import annotations

import asyncio
import os
from io import BytesIO
from pathlib import Path
from typing import Callable
from urllib.parse import urlencode

from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import FileResponse, PlainTextResponse, Response
from starlette.routing import Route

import pandas as pd

from wepppy.weppcloud.routes._run_context import RunContext
from wepppy.weppcloud.utils.helpers import get_wd


async def aria2c_spec(request: Request) -> PlainTextResponse:
    runid = request.path_params['runid']
    config = request.path_params['config']

    pup_relpath = request.query_params.get('pup')
    ctx = await asyncio.to_thread(_resolve_run_context, runid, config, pup_relpath)
    wd = str(ctx.active_root.resolve())
    base_url = f"https://wepp.cloud/weppcloud/runs/{runid}/{config}/download"
    if ctx.pup_relpath:
        base_url = f"{base_url}?{urlencode({'pup': ctx.pup_relpath})}"

    file_specs = await asyncio.to_thread(_collect_file_specs, wd, base_url)
    spec_content = "\n".join(file_specs)
    return PlainTextResponse(spec_content)


async def download_with_subpath(request: Request) -> Response:
    subpath = request.path_params.get('subpath', '')
    return await _download_tree(request, subpath)


async def _download_tree(request: Request, subpath: str) -> Response:
    runid = request.path_params['runid']
    config = request.path_params['config']

    pup_relpath = request.query_params.get('pup')
    ctx = await asyncio.to_thread(_resolve_run_context, runid, config, pup_relpath)
    wd = str(ctx.active_root.resolve())
    dir_path = os.path.abspath(os.path.join(wd, subpath))

    if not dir_path.startswith(wd):
        raise HTTPException(status_code=403)

    if not os.path.exists(dir_path):
        raise HTTPException(status_code=404)

    return await download_response_file(dir_path, query_params=request.query_params)


async def download_response_file(path: str, query_params) -> Response:
    filename = os.path.basename(path)
    ext = os.path.splitext(filename)[1].lower()
    as_csv = query_params.get('as_csv') if query_params else False

    if as_csv and ext == '.parquet':
        df = await asyncio.to_thread(pd.read_parquet, path)
        csv_bytes = await asyncio.to_thread(_df_to_csv_bytes, df)
        csv_name = os.path.splitext(filename)[0] + '.csv'
        headers = {
            'Content-Disposition': f'attachment; filename="{csv_name}"'
        }
        return Response(csv_bytes, media_type='text/csv', headers=headers)

    return FileResponse(path, filename=filename)


def _df_to_csv_bytes(df: pd.DataFrame) -> bytes:
    buf = BytesIO()
    df.to_csv(buf, index=False)
    return buf.getvalue()


def _resolve_run_context(runid: str, config: str, pup_relpath: str | None) -> RunContext:
    run_root = Path(get_wd(runid, prefer_active=False)).resolve()
    if not run_root.is_dir():
        raise HTTPException(status_code=404, detail=f"Run '{runid}' not found")

    sanitized = (pup_relpath or '').strip()
    pup_root: Path | None = None
    active_root = run_root

    if sanitized:
        pups_root = (run_root / '_pups').resolve()
        if not pups_root.is_dir():
            raise HTTPException(status_code=404, detail='Unknown pup project')

        candidate = (pups_root / sanitized).resolve()
        try:
            candidate.relative_to(pups_root)
        except ValueError:
            raise HTTPException(status_code=404, detail='Unknown pup project')

        if not candidate.is_dir():
            raise HTTPException(status_code=404, detail='Unknown pup project')

        pup_root = candidate
        active_root = candidate

    return RunContext(
        runid=runid,
        config=config,
        run_root=run_root,
        active_root=active_root,
        pup_root=pup_root,
        pup_relpath=sanitized or None,
    )


def _collect_file_specs(wd: str, base_url: str) -> list[str]:
    specs: list[str] = []
    for root, _dirs, files in os.walk(wd):
        for file in files:
            file_path = os.path.join(root, file)
            relative_path = os.path.relpath(file_path, wd)
            url = f"{base_url}/{relative_path}"
            specs.append(f"{url}\n out={relative_path}")
    return specs


def create_routes(prefix_path: Callable[[str], str]) -> list[Route]:
    return [
        Route(
            prefix_path('/runs/{runid}/{config}/aria2c.spec'),
            aria2c_spec,
            methods=['GET']
        ),
        Route(
            prefix_path('/runs/{runid}/{config}/download/{subpath:path}'),
            download_with_subpath,
            methods=['GET']
        ),
    ]
