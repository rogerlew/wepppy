"""Shape-converter Starlette application scaffold."""

from __future__ import annotations

import os
import tempfile
from contextlib import asynccontextmanager
from pathlib import Path

from starlette.applications import Starlette
from starlette.requests import Request
from starlette.responses import JSONResponse
from starlette.routing import Route

SERVICE_SCOPE = "shape-converter"
DEFAULT_SCRATCH_ROOT = Path("/tmp/shape-converter")


def _resolve_scratch_root() -> Path:
    scratch_override = os.getenv("SHAPE_CONVERTER_SCRATCH_ROOT")
    if scratch_override:
        return Path(scratch_override)
    return DEFAULT_SCRATCH_ROOT


def _is_scratch_root_writable(scratch_root: Path) -> tuple[bool, str | None]:
    try:
        scratch_root.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        return False, f"scratch_root_create_failed: {exc}"

    try:
        with tempfile.NamedTemporaryFile(mode="w", dir=scratch_root, delete=True, encoding="utf-8") as handle:
            handle.write("shape-converter readiness check")
            handle.flush()
    except OSError as exc:
        return False, f"scratch_root_not_writable: {exc}"

    return True, None


async def homepage(_: Request) -> JSONResponse:
    return JSONResponse(
        {
            "service": SERVICE_SCOPE,
            "status": "ok",
            "message": "shape-converter service scaffold",
        }
    )


async def health_live(_: Request) -> JSONResponse:
    return JSONResponse(
        {
            "status": "ok",
            "scope": SERVICE_SCOPE,
            "check": "live",
        }
    )


async def health_ready(request: Request) -> JSONResponse:
    bootstrapped = bool(getattr(request.app.state, "bootstrapped", False))
    scratch_root = getattr(request.app.state, "scratch_root", _resolve_scratch_root())
    writable, failure_reason = _is_scratch_root_writable(scratch_root)

    if not bootstrapped:
        return JSONResponse(
            {
                "status": "not_ready",
                "scope": SERVICE_SCOPE,
                "check": "ready",
                "reason": "service_not_bootstrapped",
            },
            status_code=503,
        )

    if not writable:
        return JSONResponse(
            {
                "status": "not_ready",
                "scope": SERVICE_SCOPE,
                "check": "ready",
                "reason": failure_reason,
                "scratch_root": str(scratch_root),
            },
            status_code=503,
        )

    return JSONResponse(
        {
            "status": "ok",
            "scope": SERVICE_SCOPE,
            "check": "ready",
            "scratch_root": str(scratch_root),
        }
    )


@asynccontextmanager
async def app_lifespan(app: Starlette):
    app.state.scratch_root = _resolve_scratch_root()
    app.state.bootstrapped = True
    try:
        yield
    finally:
        app.state.bootstrapped = False


def create_app() -> Starlette:
    routes = [
        Route("/", homepage),
        Route("/health/live", health_live),
        Route("/health/ready", health_ready),
    ]

    app = Starlette(debug=False, routes=routes, lifespan=app_lifespan)

    @app.middleware("http")
    async def forwarded_prefix_middleware(request: Request, call_next):
        prefix = request.headers.get("X-Forwarded-Prefix")
        if prefix:
            normalized = prefix.rstrip("/")
            request.scope["root_path"] = normalized if normalized else ""
        return await call_next(request)

    return app


app = create_app()


__all__ = ["app", "create_app"]
