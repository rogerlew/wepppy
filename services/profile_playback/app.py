
import os
from pathlib import Path
from typing import List, Optional

import requests
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, Field
from starlette.concurrency import run_in_threadpool

from wepppy.profile_recorder.playback import PlaybackSession


PROFILE_ROOT = Path(os.environ.get("PROFILE_PLAYBACK_ROOT", "/workdir/wepppy-test-engine-data/profiles"))
DEFAULT_BASE_URL = os.environ.get("PROFILE_PLAYBACK_BASE_URL", "http://weppcloud:8000/weppcloud")
ADMIN_EMAIL = os.environ.get("ADMIN_EMAIL")
ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD")


class ProfileRunRequest(BaseModel):
    """Incoming payload for a profile replay request."""

    dry_run: bool = Field(False, description="Preview requests without executing them.")
    base_url: Optional[str] = Field(
        default=None,
        description="Override the target WEPPcloud base URL. Defaults to PROFILE_PLAYBACK_BASE_URL or http://weppcloud:8000/weppcloud.",
    )
    cookie: Optional[str] = Field(
        default=None,
        description="Optional Cookie header forwarded with every request to WEPPcloud.",
    )


class ProfileRunResult(BaseModel):
    """Replay outcome returned to the caller."""

    profile: str
    run_id: str
    dry_run: bool
    base_url: str
    run_dir: str
    report: str
    requests: List[dict]


app = FastAPI(title="WEPPcloud Profile Playback", version="0.1.0")


@app.get("/health")
async def healthcheck() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/run/{profile}", response_model=ProfileRunResult)
async def run_profile(profile: str, payload: ProfileRunRequest) -> ProfileRunResult:
    profile_root = PROFILE_ROOT / profile
    if not profile_root.exists():
        raise HTTPException(status_code=404, detail=f"Profile not found: {profile_root}")

    base_url = (payload.base_url or DEFAULT_BASE_URL).rstrip("/")

    session = requests.Session()
    if payload.cookie:
        session.headers.update({"Cookie": payload.cookie})
    elif not payload.dry_run:
        if not ADMIN_EMAIL or not ADMIN_PASSWORD:
            raise HTTPException(status_code=500, detail="ADMIN_EMAIL/ADMIN_PASSWORD must be configured for playback authentication")
        try:
            _perform_login(session, base_url, ADMIN_EMAIL, ADMIN_PASSWORD)
        except Exception as exc:
            raise HTTPException(status_code=502, detail=f"Login failed: {exc}") from exc

    playback = PlaybackSession(
        profile_root=profile_root,
        base_url=base_url,
        execute=not payload.dry_run,
        session=session,
    )

    await run_in_threadpool(playback.run)

    request_log = [{"id": request_id, "status": status} for request_id, status in playback.results]

    return ProfileRunResult(
        profile=profile,
        run_id=getattr(playback, "run_id", profile),
        dry_run=payload.dry_run,
        base_url=base_url,
        run_dir=str(playback.run_dir),
        report=playback.report(),
        requests=request_log,
    )


def _perform_login(session: requests.Session, base_url: str, email: str, password: str) -> None:
    login_url = f"{base_url.rstrip('/')}/login"
    response = session.get(login_url, timeout=30)
    response.raise_for_status()
    token = _extract_csrf_token(response.text)
    payload = {
        "email": email,
        "password": password,
        "remember": "y",
        "csrf_token": token or "",
        "next": "",
    }
    post = session.post(login_url, data=payload, timeout=30, allow_redirects=False)
    if post.status_code not in (200, 302, 303):
        raise RuntimeError(f"HTTP {post.status_code}")


def _extract_csrf_token(html: str) -> Optional[str]:
    import re

    match = re.search(r'name="csrf_token"\s+value="([^"]+)"', html)
    if match:
        return match.group(1)
    return None


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("services.profile_playback.app:app", host="0.0.0.0", port=8070, reload=False)
