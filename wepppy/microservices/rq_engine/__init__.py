from __future__ import annotations

from fastapi import FastAPI

from .culvert_routes import router as culvert_router
from .job_routes import router as job_router

app = FastAPI(title="WEPPcloud RQ Engine", version="0.1.0")


@app.get("/health")
def health() -> dict[str, str]:
    return {
        "status": "ok",
        "scope": "rq-engine",
    }


app.include_router(job_router, prefix="/api")
app.include_router(culvert_router, prefix="/api")


__all__ = ["app"]
