"""Async gdalinfo endpoints used by the browse microservice."""

from __future__ import annotations

import asyncio
import json
import os
from pathlib import Path
from typing import Callable, Optional

from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

from wepppy.weppcloud.routes._run_context import RunContext
from wepppy.weppcloud.utils.helpers import get_wd


async def gdalinfo_report(request: Request) -> JSONResponse:
    runid = request.path_params['runid']
    config = request.path_params['config']
    wepp = request.path_params.get('wepp')  # unused, preserved for compatibility
    subpath = request.path_params['subpath']
    return await _gdalinfo_tree(runid, config, subpath, request)


async def gdalinfo_tree(request: Request) -> JSONResponse:
    runid = request.path_params['runid']
    config = request.path_params['config']
    subpath = request.path_params['subpath']
    return await _gdalinfo_tree(runid, config, subpath, request)


async def _gdalinfo_tree(runid: str, config: str, subpath: str, request: Request) -> JSONResponse:
    pup_relpath = request.query_params.get('pup')
    ctx = await asyncio.to_thread(_resolve_run_context, runid, config, pup_relpath)
    wd = str(ctx.active_root.resolve())
    target_path = os.path.abspath(os.path.join(wd, subpath))

    if not target_path.startswith(wd):
        raise HTTPException(status_code=403)

    if not os.path.exists(target_path) or os.path.isdir(target_path):
        raise HTTPException(status_code=404)

    return await _gdalinfo_response(target_path)


async def _gdalinfo_response(path: str) -> JSONResponse:
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail='path does not exist')

    command = f'gdalinfo -json {path}'
    returncode, stdout, stderr = await _run_shell_command(command, os.path.dirname(path) or None)
    if returncode != 0:
        raise HTTPException(status_code=500, detail=f'gdalinfo failed: {stderr.strip()}')

    try:
        jsobj = json.loads(stdout)
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f'gdalinfo returned invalid JSON: {exc}')

    return JSONResponse(jsobj)


async def _run_shell_command(command: str, cwd: Optional[str]) -> tuple[int, str, str]:
    process = await asyncio.create_subprocess_shell(
        command,
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.PIPE,
        cwd=cwd,
    )
    stdout, stderr = await process.communicate()
    return (
        process.returncode,
        stdout.decode('utf-8', errors='replace'),
        stderr.decode('utf-8', errors='replace'),
    )


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


def create_routes(prefix_path: Callable[[str], str]) -> list[Route]:
    return [
        Route(
            prefix_path('/runs/{runid}/{config}/gdalinfo/{subpath:path}'),
            gdalinfo_tree,
            methods=['GET']
        ),
        Route(
            prefix_path('/runs/{runid}/{config}/report/{wepp}/gdalinfo/{subpath:path}'),
            gdalinfo_report,
            methods=['GET']
        ),
    ]
