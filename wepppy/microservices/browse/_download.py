"""Starlette-compatible download routes extracted from the legacy Flask blueprint."""

from __future__ import annotations

import asyncio
import os
from io import BytesIO
from pathlib import Path
from typing import Callable

from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import FileResponse, PlainTextResponse, Response
from starlette.routing import Route

import pandas as pd
import pyarrow.parquet as pq

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
from wepppy.weppcloud.routes._run_context import RunContext
from wepppy.weppcloud.utils.helpers import get_wd


async def aria2c_spec(request: Request) -> PlainTextResponse:
    runid = request.path_params['runid']
    config = request.path_params['config']
    try:
        auth_context = authorize_run_request(
            request,
            runid=runid,
            subpath='',
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

    ctx = await asyncio.to_thread(_resolve_run_context, runid, config)
    wd = str(ctx.active_root.resolve())
    base_url = f"https://wepp.cloud/weppcloud/runs/{runid}/{config}/download"

    file_specs = await asyncio.to_thread(
        _collect_file_specs,
        wd,
        base_url,
        auth_context.is_root,
    )
    spec_content = "\n".join(file_specs)
    return PlainTextResponse(spec_content)


async def download_with_subpath(request: Request) -> Response:
    subpath = request.path_params.get('subpath', '')
    runid = request.path_params['runid']
    config = request.path_params['config']
    try:
        auth_context = authorize_run_request(
            request,
            runid=runid,
            subpath=subpath,
            allow_public_without_token=True,
            require_authenticated=False,
            allowed_token_classes=RUN_ALLOWED_TOKEN_CLASSES,
        )
    except BrowseAuthError as exc:
        return handle_auth_error(
            request,
            runid=runid,
            error=exc,
            redirect_on_401=True,
            redirect_html_only=True,
        )

    allow_recorder = auth_context.is_root
    violation = validate_raw_subpath(subpath)
    if violation is not None:
        if allow_recorder and violation == PATH_SECURITY_FORBIDDEN_RECORDER:
            violation = None
    if violation is not None:
        raise HTTPException(status_code=403, detail=path_security_detail(violation))

    ctx = await asyncio.to_thread(_resolve_run_context, runid, config)
    wd = str(ctx.active_root.resolve())
    dir_path = os.path.abspath(os.path.join(wd, subpath))

    _assert_within_root(wd, dir_path)
    _assert_target_within_allowed_roots(wd, dir_path, allow_recorder=allow_recorder)

    if not os.path.exists(dir_path):
        raise HTTPException(status_code=404)

    return await download_response_file(dir_path, query_params=request.query_params)


async def download_culvert_with_subpath(request: Request) -> Response:
    subpath = request.path_params.get('subpath', '')
    batch_uuid = request.path_params['uuid']
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
    violation = validate_raw_subpath(subpath)
    if violation is not None:
        if allow_recorder and violation == PATH_SECURITY_FORBIDDEN_RECORDER:
            violation = None
    if violation is not None:
        raise HTTPException(status_code=403, detail=path_security_detail(violation))

    wd = str(_resolve_culvert_root(batch_uuid))
    if not os.path.isdir(wd):
        raise HTTPException(status_code=404, detail=f"Culvert batch '{batch_uuid}' not found")

    dir_path = os.path.abspath(os.path.join(wd, subpath))
    _assert_within_root(wd, dir_path)
    _assert_target_within_allowed_roots(wd, dir_path, allow_recorder=allow_recorder)
    if not os.path.exists(dir_path):
        raise HTTPException(status_code=404)

    return await download_response_file(dir_path, query_params=request.query_params)


async def download_batch_with_subpath(request: Request) -> Response:
    subpath = request.path_params.get('subpath', '')
    batch_name = request.path_params['batch_name']
    try:
        auth_context = authorize_group_request(
            request,
            identifier=batch_name,
            subpath=subpath,
            allowed_token_classes=USER_SERVICE_TOKEN_CLASSES,
        )
    except BrowseAuthError as exc:
        raise HTTPException(status_code=exc.status_code, detail=exc.message)

    allow_recorder = auth_context.is_root
    violation = validate_raw_subpath(subpath)
    if violation is not None:
        if allow_recorder and violation == PATH_SECURITY_FORBIDDEN_RECORDER:
            violation = None
    if violation is not None:
        raise HTTPException(status_code=403, detail=path_security_detail(violation))

    wd = str(_resolve_batch_root(batch_name))
    if not os.path.isdir(wd):
        raise HTTPException(status_code=404, detail=f"Batch '{batch_name}' not found")

    dir_path = os.path.abspath(os.path.join(wd, subpath))
    _assert_within_root(wd, dir_path)
    _assert_target_within_allowed_roots(wd, dir_path, allow_recorder=allow_recorder)
    if not os.path.exists(dir_path):
        raise HTTPException(status_code=404)

    return await download_response_file(dir_path, query_params=request.query_params)


async def download_response_file(path: str, query_params) -> Response:
    filename = os.path.basename(path)
    ext = os.path.splitext(filename)[1].lower()
    as_csv = query_params.get('as_csv') if query_params else False

    if as_csv and ext == '.parquet':
        df = await asyncio.to_thread(_parquet_to_dataframe_with_units, path)
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


def _parquet_to_dataframe_with_units(path: str) -> pd.DataFrame:
    table = pq.read_table(path)
    df = table.to_pandas()
    schema = table.schema
    # Only generate column names for actual DataFrame columns (not index columns)
    column_names = [_field_label_with_units(field) for field in schema 
                    if field.name not in df.index.names and field.name != '__index_level_0__']
    df.columns = column_names
    return df


def _field_label_with_units(field) -> str:
    label = field.name
    metadata = getattr(field, "metadata", None)
    if metadata is None:
        return label
    units_bytes = metadata.get(b"units")
    if units_bytes:
        try:
            units = units_bytes.decode().strip()
        except UnicodeDecodeError:
            units = units_bytes.decode("utf-8", "ignore").strip()
        if units:
            suffix = f"({units})"
            if suffix not in label:
                return f"{label} {suffix}"
    return label


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


def _collect_file_specs(wd: str, base_url: str, allow_recorder: bool) -> list[str]:
    specs: list[str] = []
    for root, _dirs, files in os.walk(wd):
        for file in files:
            file_path = os.path.join(root, file)
            relative_path = os.path.relpath(file_path, wd)
            violation = validate_raw_subpath(relative_path)
            if (
                violation is not None
                and not (allow_recorder and violation == PATH_SECURITY_FORBIDDEN_RECORDER)
            ):
                continue
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
        Route(
            prefix_path('/culverts/{uuid}/download/{subpath:path}'),
            download_culvert_with_subpath,
            methods=['GET']
        ),
        Route(
            prefix_path('/batch/{batch_name}/download/{subpath:path}'),
            download_batch_with_subpath,
            methods=['GET']
        ),
    ]
