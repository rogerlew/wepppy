"""Inline serving for generated PATH-CE HTML reports.

Serves files from the ``<wd>/path/report/`` subtree ONLY, inline (unlike
``/download/`` which forces attachment). Generated report HTML is run-derived
content, so responses ship a strict Content-Security-Policy with ``sandbox``
(no ``allow-same-origin``): the document executes in an opaque origin and
cannot read cookies or reach authenticated APIs with ambient credentials —
the stored-XSS blast radius is the report itself.

CSP allowances beyond 'self': the report's folium map iframe (upstream
behavior, recorded in the Phase 3 review) loads leaflet/jquery/bootstrap from
pinned CDN hosts and Google terrain tiles; deck.gl spawns blob: workers.
Everything else in the report is local to the report tree.
"""

from __future__ import annotations

import asyncio
import os
import stat as stat_module
from pathlib import Path
from typing import Callable, Tuple

from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import Response
from starlette.routing import Route

from wepppy.microservices.browse.auth import (
    RUN_ALLOWED_TOKEN_CLASSES,
    BrowseAuthError,
    authorize_run_request,
    handle_auth_error,
)
from wepppy.microservices.browse.security import (
    path_security_detail,
    validate_raw_subpath,
)
from wepppy.weppcloud.utils.helpers import get_wd

__all__ = ["create_routes", "REPORT_CSP"]

REPORT_SUBTREE = ("path", "report")
DEFAULT_DOCUMENT = "PATH_CE_Report.html"

# folium-iframe CDN hosts observed in the rendered artifact (Phase 3 review);
# tighten by vendoring folium assets if upstream drops them.
_FOLIUM_SCRIPT_HOSTS = (
    "https://cdn.jsdelivr.net "
    "https://cdnjs.cloudflare.com "
    "https://code.jquery.com "
    "https://netdna.bootstrapcdn.com"
)
_FOLIUM_STYLE_HOSTS = (
    "https://cdn.jsdelivr.net "
    "https://cdnjs.cloudflare.com "
    "https://netdna.bootstrapcdn.com "
    "https://fonts.googleapis.com"
)

# data: in script/style-src accommodates Quarto's embed-resources output
# (tabsets + inlined stylesheets are emitted as data: URIs); the sandbox's
# opaque origin plus 'unsafe-inline' (required by the embedded report) means
# data: grants nothing further here. No allow-popups: the report needs none,
# and window.open would be an outbound channel connect-src cannot govern.
REPORT_CSP = (
    "sandbox allow-scripts allow-downloads; "
    "default-src 'none'; "
    "base-uri 'none'; "
    "form-action 'none'; "
    f"script-src 'self' 'unsafe-inline' data: {_FOLIUM_SCRIPT_HOSTS}; "
    f"style-src 'self' 'unsafe-inline' data: {_FOLIUM_STYLE_HOSTS}; "
    "img-src 'self' data: blob: https://*.google.com https://*.googleapis.com https://cdn.jsdelivr.net; "
    "font-src 'self' data: https://fonts.gstatic.com https://cdnjs.cloudflare.com "
    "https://cdn.jsdelivr.net https://netdna.bootstrapcdn.com; "
    "connect-src 'self'; "
    "worker-src blob:; "
    "child-src 'self' blob: data:; "
    "frame-src 'self' blob: data:"
)

# Inline-safe media types the report tree legitimately contains. HTML is
# sandboxed via CSP; the rest are inert under nosniff. Anything else —
# notably scripted-document types like SVG/XHTML that would execute in the
# service origin — is forced to a download instead of rendered inline.
_INLINE_MEDIA_TYPES = {
    ".html": "text/html; charset=utf-8",
    ".htm": "text/html; charset=utf-8",
    ".js": "text/javascript; charset=utf-8",
    ".css": "text/css; charset=utf-8",
    ".json": "application/json",
    ".geojson": "application/geo+json",
    ".csv": "text/csv; charset=utf-8",
    ".png": "image/png",
}


def _media_type_for(path: Path) -> Tuple[str, bool]:
    """Return (media_type, inline). Unknown/active types download as octets."""
    suffix = path.suffix.lower()
    if suffix in _INLINE_MEDIA_TYPES:
        return _INLINE_MEDIA_TYPES[suffix], True
    return "application/octet-stream", False


def _security_headers(media_type: str, inline: bool, filename: str) -> dict:
    headers = {
        "X-Content-Type-Options": "nosniff",
        "Referrer-Policy": "no-referrer",
        "Cache-Control": "private, no-store",
    }
    if media_type.startswith("text/html"):
        headers["Content-Security-Policy"] = REPORT_CSP
    if not inline:
        headers["Content-Disposition"] = f'attachment; filename="{filename}"'
    return headers


def _read_report_file(runid: str, subpath: str) -> Tuple[bytes, Path]:
    """Resolve and read a regular file inside <wd>/path/report/.

    The render service never writes symlinks anywhere in this tree, so every
    component from the run root down — including ``path`` and ``report``
    themselves — must be a real directory/file; any symlink is hostile or
    corrupt. The leaf is opened with O_NOFOLLOW and validated via fstat so a
    last-instant leaf swap cannot serve outside content. (Directory-component
    swaps between the walk and the open remain a narrow race, accepted and
    recorded in the security review: run trees are wepppy-managed.)
    """
    wd = Path(get_wd(runid, prefer_active=False)).resolve()
    if not wd.is_dir():
        raise HTTPException(status_code=404, detail=f"Run '{runid}' not found")

    # walk the fixed subtree components first — a symlinked path/ or report/
    # would otherwise be blessed as the containment root by resolve()
    report_root = wd
    for component in REPORT_SUBTREE:
        report_root = report_root / component
        if report_root.is_symlink():
            raise HTTPException(status_code=403, detail="Symlinked report content is forbidden.")
    if not report_root.is_dir():
        raise HTTPException(
            status_code=404,
            detail="No PATH-CE report has been generated for this run.",
        )
    report_root = report_root.resolve()

    parts = [p for p in Path(subpath or DEFAULT_DOCUMENT).parts if p not in ("", ".")]
    if ".." in parts or any(p.startswith("/") for p in parts):
        raise HTTPException(status_code=403, detail="Path escapes the report subtree.")

    probe = report_root
    for part in parts:
        probe = probe / part
        if probe.is_symlink():
            raise HTTPException(status_code=403, detail="Symlinked report content is forbidden.")

    target = probe.resolve()
    if not target.is_relative_to(report_root):
        raise HTTPException(status_code=403, detail="Path escapes the report subtree.")

    try:
        fd = os.open(target, os.O_RDONLY | os.O_NOFOLLOW | os.O_CLOEXEC)
    except FileNotFoundError:
        raise HTTPException(status_code=404)
    except OSError as exc:
        # ELOOP: the leaf became a symlink after the walk
        raise HTTPException(status_code=403, detail="Symlinked report content is forbidden.") from exc
    try:
        info = os.fstat(fd)
        if not stat_module.S_ISREG(info.st_mode):
            raise HTTPException(status_code=404)
        with os.fdopen(fd, "rb") as handle:
            fd = -1
            content = handle.read()
    finally:
        if fd != -1:
            os.close(fd)
    return content, target


async def report_document(request: Request) -> Response:
    return await _serve(request, "")


async def report_asset(request: Request) -> Response:
    return await _serve(request, request.path_params.get("subpath", ""))


async def _serve(request: Request, subpath: str) -> Response:
    runid = request.path_params["runid"]
    config = request.path_params["config"]

    try:
        authorize_run_request(
            request,
            runid=runid,
            config=config,
            subpath=f"path/report/{subpath}",
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

    violation = validate_raw_subpath(subpath)
    if violation is not None:
        raise HTTPException(status_code=403, detail=path_security_detail(violation))

    content, target = await asyncio.to_thread(_read_report_file, runid, subpath)
    media_type, inline = _media_type_for(target)
    return Response(
        content,
        media_type=media_type,
        headers=_security_headers(media_type, inline, target.name),
    )


def create_routes(prefix_path: Callable[[str], str]) -> list[Route]:
    return [
        Route(
            prefix_path("/runs/{runid}/{config}/report/path_ce/"),
            report_document,
            methods=["GET"],
        ),
        Route(
            prefix_path("/runs/{runid}/{config}/report/path_ce"),
            report_document,
            methods=["GET"],
        ),
        Route(
            prefix_path("/runs/{runid}/{config}/report/path_ce/{subpath:path}"),
            report_asset,
            methods=["GET"],
        ),
    ]
