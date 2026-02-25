"""Async gdalinfo endpoints used by the browse microservice."""

from __future__ import annotations

import asyncio
import json
import os
import shlex
from pathlib import Path
from typing import Callable, Optional

from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

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
from wepppy.nodir.errors import NoDirError
from wepppy.nodir.fs import resolve as nodir_resolve
from wepppy.nodir.fs import stat as nodir_stat
from wepppy.nodir.materialize import materialize_file
from wepppy.nodir.paths import parse_external_subpath
from wepppy.weppcloud.routes._run_context import RunContext
from wepppy.weppcloud.utils.helpers import get_wd


def _nodir_error_payload(err: NoDirError) -> dict:
    return {
        "error": {
            "message": err.message,
            "code": err.code,
            "details": err.message,
        }
    }


def _raise_nodir_http_exception(err: NoDirError) -> None:
    raise HTTPException(status_code=err.http_status, detail=_nodir_error_payload(err))


def _resolve_gdalinfo_target_path(
    *,
    wd: str,
    subpath: str,
    allow_recorder: bool,
) -> str:
    try:
        logical_rel_path, nodir_view = parse_external_subpath(
            subpath,
            allow_admin_alias=False,
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid path.")

    # Enforce mixed/invalid/locked precedence before boundary-specific handling.
    try:
        nodir_resolve(wd, logical_rel_path, view="effective")
    except NoDirError as err:
        _raise_nodir_http_exception(err)

    requested_target = os.path.abspath(os.path.join(wd, logical_rel_path))
    _assert_within_root(wd, requested_target)
    _assert_target_within_allowed_roots(wd, requested_target, allow_recorder=allow_recorder)

    try:
        nodir_target = nodir_resolve(wd, logical_rel_path, view=nodir_view)
    except NoDirError as err:
        _raise_nodir_http_exception(err)

    if nodir_target is None:
        if not os.path.exists(requested_target) or os.path.isdir(requested_target):
            raise HTTPException(status_code=404)
        return requested_target

    try:
        entry = nodir_stat(nodir_target)
    except NoDirError as err:
        _raise_nodir_http_exception(err)
    except (FileNotFoundError, NotADirectoryError):
        raise HTTPException(status_code=404)

    if entry.is_dir:
        raise HTTPException(status_code=404)

    if nodir_target.form == "archive":
        try:
            return materialize_file(wd, logical_rel_path, purpose="gdalinfo")
        except NoDirError as err:
            _raise_nodir_http_exception(err)
        except (FileNotFoundError, IsADirectoryError):
            raise HTTPException(status_code=404)

    if not os.path.exists(requested_target) or os.path.isdir(requested_target):
        raise HTTPException(status_code=404)
    return requested_target


async def gdalinfo_with_subpath(request: Request) -> JSONResponse:
    runid = request.path_params['runid']
    config = request.path_params['config']
    subpath = request.path_params['subpath']
    try:
        auth_context = authorize_run_request(
            request,
            runid=runid,
            config=config,
            subpath=subpath,
            allow_public_without_token=True,
            require_authenticated=False,
            allowed_token_classes=RUN_ALLOWED_TOKEN_CLASSES,
        )
    except BrowseAuthError as exc:
        handle_auth_error(
            request,
            runid=runid,
            error=exc,
            redirect_on_401=False,
        )
        raise

    allow_recorder = auth_context.is_root
    raw_violation = validate_raw_subpath(subpath)
    if raw_violation is not None:
        if allow_recorder and raw_violation == PATH_SECURITY_FORBIDDEN_RECORDER:
            raw_violation = None
    if raw_violation is not None:
        raise HTTPException(status_code=403, detail=path_security_detail(raw_violation))

    ctx = await asyncio.to_thread(_resolve_run_context, runid, config)
    wd = str(ctx.active_root.resolve())
    target_path = _resolve_gdalinfo_target_path(
        wd=wd,
        subpath=subpath,
        allow_recorder=allow_recorder,
    )

    command = f"gdalinfo -json {shlex.quote(target_path)}"
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
    try:
        auth_context = authorize_group_request(
            request,
            identifier=batch_uuid,
            subpath=subpath,
            allowed_token_classes=USER_SERVICE_TOKEN_CLASSES,
        )
    except BrowseAuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)

    allow_recorder = auth_context.is_root
    raw_violation = validate_raw_subpath(subpath)
    if raw_violation is not None:
        if allow_recorder and raw_violation == PATH_SECURITY_FORBIDDEN_RECORDER:
            raw_violation = None
    if raw_violation is not None:
        raise HTTPException(status_code=403, detail=path_security_detail(raw_violation))

    wd = str(_resolve_culvert_root(batch_uuid))
    if not os.path.isdir(wd):
        raise HTTPException(status_code=404, detail=f"Culvert batch '{batch_uuid}' not found")

    target_path = _resolve_gdalinfo_target_path(
        wd=wd,
        subpath=subpath,
        allow_recorder=allow_recorder,
    )

    command = f"gdalinfo -json {shlex.quote(target_path)}"
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
    base_runid = f"batch;;{batch_name};;_base"
    try:
        auth_context = authorize_group_request(
            request,
            identifier=batch_name,
            subpath=subpath,
            allowed_token_classes=RUN_ALLOWED_TOKEN_CLASSES,
            identifier_claim_aliases=(base_runid,),
            allow_public_without_token=True,
            public_runid=base_runid,
        )
    except BrowseAuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)

    allow_recorder = auth_context.is_root
    raw_violation = validate_raw_subpath(subpath)
    if raw_violation is not None:
        if allow_recorder and raw_violation == PATH_SECURITY_FORBIDDEN_RECORDER:
            raw_violation = None
    if raw_violation is not None:
        raise HTTPException(status_code=403, detail=path_security_detail(raw_violation))

    wd = str(_resolve_batch_root(batch_name))
    if not os.path.isdir(wd):
        raise HTTPException(status_code=404, detail=f"Batch '{batch_name}' not found")

    target_path = _resolve_gdalinfo_target_path(
        wd=wd,
        subpath=subpath,
        allow_recorder=allow_recorder,
    )

    command = f"gdalinfo -json {shlex.quote(target_path)}"
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


def _assert_target_within_allowed_roots(
    root: str | Path,
    target: str | Path,
    *,
    allow_recorder: bool = False,
) -> None:
    violation = validate_resolved_target(root, target)
    if allow_recorder and violation == PATH_SECURITY_FORBIDDEN_RECORDER:
        return
    if violation is not None:
        raise HTTPException(status_code=403, detail=path_security_detail(violation))


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
