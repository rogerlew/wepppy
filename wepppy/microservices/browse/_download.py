"""Starlette-compatible download routes extracted from the legacy Flask blueprint."""

from __future__ import annotations

import asyncio
import os
from io import BytesIO
from pathlib import Path
from typing import BinaryIO, Callable
from urllib.parse import urlsplit

from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import FileResponse, PlainTextResponse, Response, StreamingResponse
from starlette.routing import Route

import pandas as pd
import pyarrow.parquet as pq

from wepppy.config.secrets import get_secret
from wepppy.microservices.browse.auth import (
    RUN_ALLOWED_TOKEN_CLASSES,
    USER_SERVICE_TOKEN_CLASSES,
    BrowseAuthError,
    authorize_group_request,
    authorize_run_request,
    handle_auth_error,
    is_root_only_path,
)
from wepppy.microservices.browse.security import (
    PATH_SECURITY_FORBIDDEN_RECORDER,
    path_security_detail,
    validate_raw_subpath,
    validate_resolved_target,
)
from wepppy.nodir import (
    NoDirError,
    open_read as nodir_open_read,
    parse_external_subpath,
    resolve as nodir_resolve,
    stat as nodir_stat,
)
from wepppy.nodir.paths import NODIR_ROOTS, split_nodir_root
from wepppy.weppcloud.routes._run_context import RunContext
from wepppy.weppcloud.utils.helpers import get_wd

_NODIR_SUFFIX = ".nodir"
_NODIR_ROOTS = frozenset(NODIR_ROOTS)


def _normalize_prefix(prefix: str | None) -> str:
    if not prefix:
        return ""
    trimmed = prefix.strip()
    if not trimmed or trimmed == "/":
        return ""
    return "/" + trimmed.strip("/")


def _resolve_external_origin(request: Request) -> str:
    """Return the externally reachable origin (scheme://host[:port])."""

    scheme = (os.getenv("OAUTH_REDIRECT_SCHEME") or request.url.scheme or "https").strip().lower()
    if not scheme:
        scheme = "https"

    raw_host = (get_secret("EXTERNAL_HOST") or os.getenv("OAUTH_REDIRECT_HOST") or "").strip()
    if raw_host:
        # Accept either "host[:port]" or a full URL like "https://host[:port]/...".
        if "://" in raw_host:
            parsed = urlsplit(raw_host)
            if parsed.scheme and parsed.netloc:
                return f"{parsed.scheme}://{parsed.netloc}"
        lowered = raw_host.lower()
        if lowered.startswith("http://"):
            scheme = "http"
            raw_host = raw_host[7:]
        elif lowered.startswith("https://"):
            scheme = "https"
            raw_host = raw_host[8:]
        host_only = raw_host.split("/")[0].strip()
        if host_only:
            return f"{scheme}://{host_only}"

    forwarded_host = (request.headers.get("X-Forwarded-Host") or "").split(",")[0].strip()
    if forwarded_host:
        forwarded_proto = (request.headers.get("X-Forwarded-Proto") or "").split(",")[0].strip().lower()
        proto = forwarded_proto or scheme
        return f"{proto}://{forwarded_host}"

    return f"{request.url.scheme}://{request.url.netloc}"


def _resolve_aria2c_base_url(request: Request, runid: str, config: str) -> str:
    origin = _resolve_external_origin(request)
    site_prefix = _normalize_prefix(os.getenv("SITE_PREFIX", "/weppcloud"))
    return f"{origin}{site_prefix}/runs/{runid}/{config}/download"


def _nodir_error_payload(err: NoDirError) -> dict:
    return {
        "error": {
            "message": err.message,
            "code": err.code,
            "details": err.message,
        }
    }


def _raise_nodir_error(err: NoDirError) -> None:
    raise HTTPException(status_code=err.http_status, detail=_nodir_error_payload(err))


def _is_admin_context(auth_context) -> bool:
    roles = set(getattr(auth_context, "roles", frozenset()))
    return "admin" in roles or "root" in roles


def _is_mixed_nodir_root(wd: str, root: str) -> bool:
    return os.path.isdir(os.path.join(wd, root)) and os.path.lexists(
        os.path.join(wd, f"{root}{_NODIR_SUFFIX}")
    )


def _allowlisted_raw_nodir_root(rel_path: str) -> str | None:
    if rel_path.lower().endswith(_NODIR_SUFFIX):
        root = rel_path[: -len(_NODIR_SUFFIX)]
        if root in _NODIR_ROOTS and "/" not in root:
            return root
    return None


def _stream_binary_download(fp: BinaryIO, filename: str) -> StreamingResponse:
    def _iter_chunks():
        try:
            while True:
                chunk = fp.read(65536)
                if not chunk:
                    break
                yield chunk
        finally:
            fp.close()

    return StreamingResponse(
        _iter_chunks(),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


async def aria2c_spec(request: Request) -> PlainTextResponse:
    runid = request.path_params['runid']
    config = request.path_params['config']
    try:
        auth_context = authorize_run_request(
            request,
            runid=runid,
            config=config,
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
    base_url = _resolve_aria2c_base_url(request, runid, config)

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
            config=config,
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
    is_admin = _is_admin_context(auth_context)
    violation = validate_raw_subpath(subpath)
    if violation is not None:
        if allow_recorder and violation == PATH_SECURITY_FORBIDDEN_RECORDER:
            violation = None
    if violation is not None:
        raise HTTPException(status_code=403, detail=path_security_detail(violation))

    ctx = await asyncio.to_thread(_resolve_run_context, runid, config)
    wd = str(ctx.active_root.resolve())

    raw_candidate = (subpath or "").replace("\\", "/").lstrip("/")
    raw_root = _allowlisted_raw_nodir_root(raw_candidate)
    if raw_root is not None:
        archive_path = os.path.abspath(os.path.join(wd, f"{raw_root}{_NODIR_SUFFIX}"))
        if not os.path.exists(archive_path):
            raise HTTPException(status_code=404)
        if _is_mixed_nodir_root(wd, raw_root) and not is_admin:
            _raise_nodir_error(
                NoDirError(
                    http_status=409,
                    code="NODIR_MIXED_STATE",
                    message=f"{raw_root} is in mixed state (dir + .nodir present)",
                )
            )
        if not is_admin:
            try:
                nodir_resolve(wd, raw_root, view="archive")
            except NoDirError as err:
                _raise_nodir_error(err)
        _assert_within_root(wd, archive_path)
        _assert_target_within_allowed_roots(wd, archive_path, allow_recorder=allow_recorder)
        return await download_response_file(archive_path, query_params=request.query_params)

    rel_subpath = subpath or "."
    try:
        logical_rel_path, nodir_view = parse_external_subpath(
            rel_subpath,
            allow_admin_alias=False,
        )
    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid path.")

    nodir_root, _inner = split_nodir_root(logical_rel_path)
    if nodir_root is not None and nodir_view == "archive" and _is_mixed_nodir_root(wd, nodir_root):
        _raise_nodir_error(
            NoDirError(
                http_status=409,
                code="NODIR_MIXED_STATE",
                message=f"{nodir_root} is in mixed state (dir + .nodir present)",
            )
        )

    nodir_target = None
    try:
        nodir_target = nodir_resolve(wd, logical_rel_path, view=nodir_view)
    except NoDirError as err:
        _raise_nodir_error(err)

    if nodir_target is not None:
        try:
            entry = nodir_stat(nodir_target)
        except FileNotFoundError:
            raise HTTPException(status_code=404)
        if entry.is_dir:
            raise HTTPException(status_code=404)
        try:
            fp = nodir_open_read(nodir_target)
        except FileNotFoundError:
            raise HTTPException(status_code=404)
        except NoDirError as err:
            _raise_nodir_error(err)
        filename = entry.name
        return _stream_binary_download(fp, filename)

    if nodir_root is not None and nodir_view == "archive":
        raise HTTPException(status_code=404)

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
            required_service_groups=("culverts",),
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
    for root in _NODIR_ROOTS:
        if _is_mixed_nodir_root(wd, root):
            raise HTTPException(
                status_code=409,
                detail={
                    "error": {
                        "message": f"{root} is in mixed state (dir + .nodir present)",
                        "code": "NODIR_MIXED_STATE",
                        "details": f"{root} is in mixed state (dir + .nodir present)",
                    }
                },
            )

    specs: list[str] = []
    for root, _dirs, files in os.walk(wd):
        for file in files:
            file_path = os.path.join(root, file)
            relative_path = os.path.relpath(file_path, wd)
            if is_root_only_path(relative_path) and not allow_recorder:
                continue
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
