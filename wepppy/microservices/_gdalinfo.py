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

async def gdalinfo_with_subpath(request: Request) -> JSONResponse:
    runid = request.path_params['runid']
    config = request.path_params['config']
    subpath = request.path_params['subpath']

    ctx = await asyncio.to_thread(_resolve_run_context, runid, config)
    wd = str(ctx.active_root.resolve())
    target_path = os.path.abspath(os.path.join(wd, subpath))

    if not target_path.startswith(wd):
        raise HTTPException(status_code=403)
    if not os.path.exists(target_path) or os.path.isdir(target_path):
        raise HTTPException(status_code=404)

    command = f'gdalinfo -json {target_path}'
    returncode, stdout, stderr = await _run_shell_command(command, os.path.dirname(target_path) or None)
    if returncode != 0:
        raise HTTPException(status_code=500, detail=f'gdalinfo failed: {stderr.strip()}')

    try:
        return JSONResponse(json.loads(stdout))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f'gdalinfo returned invalid JSON: {exc}')

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


def _resolve_run_context(runid: str, config: str) -> RunContext:
    run_root = Path(get_wd(runid, prefer_active=False)).resolve()
    if not run_root.is_dir():
        raise HTTPException(status_code=404, detail=f"Run '{runid}' not found")

    return RunContext(
        runid=runid,
        config=config,
        run_root=run_root,
        active_root=run_root,
        pup_root=None,
        pup_relpath=None,
    )


def create_routes(prefix_path: Callable[[str], str]) -> list[Route]:
    return [
        Route(
            prefix_path('/runs/{runid}/{config}/gdalinfo/{subpath:path}'),
            gdalinfo_with_subpath,
            methods=['GET']
        )
    ]
