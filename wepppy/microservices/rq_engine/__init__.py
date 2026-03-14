from __future__ import annotations

from fastapi import FastAPI, Request

from wepppy.observability.correlation import (
    CORRELATION_ID_HEADER,
    bind_correlation_id,
    install_correlation_log_record_factory,
    reset_correlation_id,
)
from wepppy.rq.auth_actor import install_rq_auth_actor_hook

from .batch_routes import router as batch_router
from .bootstrap_routes import router as bootstrap_router
from .climate_routes import router as climate_router
from .culvert_routes import router as culvert_router
from .debris_flow_routes import router as debris_flow_router
from .dss_export_routes import router as dss_export_router
from .debug_routes import router as debug_router
from .export_routes import router as export_router
from .fork_archive_routes import router as fork_archive_router
from .job_routes import router as job_router
from .admin_job_routes import router as admin_job_router
from .landuse_routes import router as landuse_router
from .landuse_soils_routes import router as landuse_soils_router
from .migration_routes import router as migration_router
from .omni_routes import router as omni_router
from .openet_ts_routes import router as openet_ts_router
from .polaris_routes import router as polaris_router
from .project_routes import router as project_router
from .run_sync_routes import router as run_sync_router
from .rap_ts_routes import router as rap_ts_router
from .rhem_routes import router as rhem_router
from .session_routes import router as session_router
from .soils_routes import router as soils_router
from .swat_routes import router as swat_router
from .treatments_routes import router as treatments_router
from .upload_batch_runner_routes import router as upload_batch_runner_router
from .upload_climate_routes import router as upload_climate_router
from .upload_disturbed_routes import router as upload_disturbed_router
from .upload_huc_fire_routes import router as upload_huc_fire_router
from .watershed_routes import router as watershed_router
from .wepp_routes import router as wepp_router
from .ash_routes import router as ash_router

app = FastAPI(title="WEPPcloud RQ Engine", version="0.1.0")
install_correlation_log_record_factory()
install_rq_auth_actor_hook()


@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    correlation_id, token = bind_correlation_id(request.headers.get(CORRELATION_ID_HEADER))
    request.state.correlation_id = correlation_id
    try:
        response = await call_next(request)
        response.headers[CORRELATION_ID_HEADER] = correlation_id
        return response
    finally:
        reset_correlation_id(token)


@app.middleware("http")
async def forwarded_prefix_middleware(request: Request, call_next):
    prefix = request.headers.get("X-Forwarded-Prefix")
    if prefix:
        normalized = prefix.rstrip("/")
        request.scope["root_path"] = normalized if normalized else ""
    return await call_next(request)


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "scope": "rq-engine",
    }


app.include_router(job_router, prefix="/api")
app.include_router(admin_job_router, prefix="/api")
app.include_router(batch_router, prefix="/api")
app.include_router(bootstrap_router, prefix="/api")
app.include_router(culvert_router, prefix="/api")
app.include_router(session_router, prefix="/api")
app.include_router(debug_router, prefix="/api")
app.include_router(landuse_soils_router, prefix="/api")
app.include_router(landuse_router, prefix="/api")
app.include_router(migration_router, prefix="/api")
app.include_router(soils_router, prefix="/api")
app.include_router(climate_router, prefix="/api")
app.include_router(watershed_router, prefix="/api")
app.include_router(treatments_router, prefix="/api")
app.include_router(dss_export_router, prefix="/api")
app.include_router(wepp_router, prefix="/api")
app.include_router(swat_router, prefix="/api")
app.include_router(debris_flow_router, prefix="/api")
app.include_router(rhem_router, prefix="/api")
app.include_router(rap_ts_router, prefix="/api")
app.include_router(openet_ts_router, prefix="/api")
app.include_router(polaris_router, prefix="/api")
app.include_router(omni_router, prefix="/api")
app.include_router(ash_router, prefix="/api")
app.include_router(export_router, prefix="/api")
app.include_router(fork_archive_router, prefix="/api")
app.include_router(run_sync_router, prefix="/api")
app.include_router(upload_climate_router, prefix="/api")
app.include_router(upload_disturbed_router, prefix="/api")
app.include_router(upload_huc_fire_router, prefix="/api")
app.include_router(upload_batch_runner_router, prefix="/api")
app.include_router(project_router)


__all__ = ["app"]
