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

    _assert_within_root(wd, target_path)
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


async def gdalinfo_culvert_with_subpath(request: Request) -> JSONResponse:
    batch_uuid = request.path_params['uuid']
    subpath = request.path_params['subpath']

    wd = str(_resolve_culvert_root(batch_uuid))
    if not os.path.isdir(wd):
        raise HTTPException(status_code=404, detail=f"Culvert batch '{batch_uuid}' not found")

    target_path = os.path.abspath(os.path.join(wd, subpath))
    _assert_within_root(wd, target_path)
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


async def gdalinfo_batch_with_subpath(request: Request) -> JSONResponse:
    batch_name = request.path_params['batch_name']
    subpath = request.path_params['subpath']

    wd = str(_resolve_batch_root(batch_name))
    if not os.path.isdir(wd):
        raise HTTPException(status_code=404, detail=f"Batch '{batch_name}' not found")

    target_path = os.path.abspath(os.path.join(wd, subpath))
    _assert_within_root(wd, target_path)
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


def _resolve_culvert_root(batch_uuid: str) -> Path:
    culverts_root = Path(os.getenv("CULVERTS_ROOT", "/wc1/culverts")).resolve()
    return _resolve_root_child(culverts_root, batch_uuid, "culvert batch")


def _resolve_batch_root(batch_name: str) -> Path:
    batch_root = Path(os.getenv("BATCH_RUNNER_ROOT", "/wc1/batch")).resolve()
    return _resolve_root_child(batch_root, batch_name, "batch")


def _resolve_root_child(root: Path, value: str, label: str) -> Path:
    if not value or value in (".", ".."):
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {label} identifier.",
        )
    value_path = Path(value)
    if len(value_path.parts) != 1 or value_path.name != value:
        raise HTTPException(
            status_code=400,
            detail=f"Invalid {label} identifier.",
        )
    root_path = Path(os.path.abspath(str(root)))
    candidate = Path(os.path.abspath(str(root_path / value)))
    try:
        common = os.path.commonpath([str(root_path), str(candidate)])
    except ValueError as exc:
        raise HTTPException(status_code=403, detail="Path traversal detected.") from exc
    if common != str(root_path):
        raise HTTPException(status_code=403, detail="Path traversal detected.")
    return candidate


def _assert_within_root(root: str | Path, target: str | Path) -> None:
    try:
        common = os.path.commonpath(
            [os.path.abspath(str(root)), os.path.abspath(str(target))]
        )
    except ValueError as exc:
        raise HTTPException(status_code=403, detail="Invalid path.") from exc
    if common != os.path.abspath(str(root)):
        raise HTTPException(status_code=403, detail="Invalid path.")


def create_routes(prefix_path: Callable[[str], str]) -> list[Route]:
    return [
        Route(
            prefix_path('/runs/{runid}/{config}/gdalinfo/{subpath:path}'),
            gdalinfo_with_subpath,
            methods=['GET']
        ),
        Route(
            prefix_path('/culverts/{uuid}/gdalinfo/{subpath:path}'),
            gdalinfo_culvert_with_subpath,
            methods=['GET']
        ),
        Route(
            prefix_path('/batch/{batch_name}/gdalinfo/{subpath:path}'),
            gdalinfo_batch_with_subpath,
            methods=['GET']
        ),
    ]
