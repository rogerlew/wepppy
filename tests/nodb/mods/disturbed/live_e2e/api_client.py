from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Iterable, Mapping, Sequence
from urllib.parse import quote

import requests


class LiveApiError(RuntimeError):
    """Raised when a live API contract call fails."""


@dataclass(frozen=True)
class JobWaitResult:
    job_id: str
    status_payload: dict[str, Any]
    elapsed_seconds: float


def _utcnow_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _truncate(value: Any, max_chars: int = 900) -> str:
    text = value if isinstance(value, str) else json.dumps(value, sort_keys=True, default=str)
    return text if len(text) <= max_chars else f"{text[:max_chars]}...(truncated)"


def _extract_csrf_token(html: str) -> str:
    match = re.search(r'<meta[^>]+name="csrf-token"[^>]+content="([^"]+)"', html, re.I)
    if not match:
        raise LiveApiError("Could not locate csrf-token meta tag in HTML response")
    token = match.group(1).strip()
    if not token:
        raise LiveApiError("csrf-token meta tag was present but empty")
    return token


class LiveAPIClient:
    """Small live API client for disturbed runbook flows."""

    def __init__(
        self,
        *,
        base_url: str,
        request_timeout_seconds: int,
        endpoint_log: list[dict[str, Any]],
    ) -> None:
        self.base_url = base_url.rstrip("/")
        self.timeout = float(request_timeout_seconds)
        self.endpoint_log = endpoint_log
        self.session = requests.Session()

    @staticmethod
    def _encode_runid(runid: str) -> str:
        return quote(runid, safe="")

    @staticmethod
    def _encode_config(config: str) -> str:
        return quote(config, safe="")

    @staticmethod
    def _encode_subpath(subpath: str) -> str:
        return quote(subpath, safe="/")

    @staticmethod
    def _auth_headers(bearer_token: str | None) -> dict[str, str]:
        if not bearer_token:
            return {}
        return {"Authorization": f"Bearer {bearer_token}"}

    def _request(
        self,
        method: str,
        path: str,
        *,
        headers: Mapping[str, str] | None = None,
        params: Mapping[str, Any] | None = None,
        json_body: Any | None = None,
        data: Any | None = None,
        expected_statuses: Sequence[int] = (200,),
        allow_redirects: bool = False,
        request_preview_override: Mapping[str, Any] | None = None,
        redact_response_body: bool = False,
    ) -> requests.Response:
        url = f"{self.base_url}{path}"
        request_headers = dict(headers or {})
        if request_preview_override is not None:
            request_preview = dict(request_preview_override)
        else:
            request_preview = {}
            if params:
                request_preview["params"] = dict(params)
            if json_body is not None:
                request_preview["json"] = json_body
            if data is not None:
                request_preview["data"] = str(data)

        try:
            response = self.session.request(
                method=method,
                url=url,
                headers=request_headers,
                params=params,
                json=json_body,
                data=data,
                timeout=self.timeout,
                allow_redirects=allow_redirects,
            )
        except requests.RequestException as exc:
            self.endpoint_log.append(
                {
                    "timestamp_utc": _utcnow_iso(),
                    "method": method.upper(),
                    "path": path,
                    "request": request_preview,
                    "error": str(exc),
                }
            )
            raise LiveApiError(f"{method} {path} failed: {exc}") from exc

        response_preview = {
            "status_code": response.status_code,
            "headers": {
                "content-type": response.headers.get("content-type"),
                "x-lookup-sha256": response.headers.get("x-lookup-sha256"),
                "x-lookup-variant": response.headers.get("x-lookup-variant"),
            },
            "body_excerpt": "<redacted>" if redact_response_body else _truncate(response.text),
        }

        self.endpoint_log.append(
            {
                "timestamp_utc": _utcnow_iso(),
                "method": method.upper(),
                "path": path,
                "request": request_preview,
                "response": response_preview,
            }
        )

        if response.status_code not in expected_statuses:
            raise LiveApiError(
                f"Unexpected status {response.status_code} for {method} {path}; expected {sorted(expected_statuses)}; "
                f"response={_truncate(response.text)}"
            )

        return response

    def discover_cap_endpoint(self, *, runid: str, config: str) -> str:
        path = f"/weppcloud/runs/{self._encode_runid(runid)}/{self._encode_config(config)}/"
        response = self._request("GET", path, expected_statuses=(200,))
        match = re.search(r'apiEndpoint\s*=\s*"([^"]+)"', response.text)
        if not match:
            raise LiveApiError(f"Could not discover CAP endpoint from {path}")
        endpoint = match.group(1).strip()
        if not endpoint:
            raise LiveApiError(f"Discovered empty CAP endpoint from {path}")
        if endpoint.endswith("/"):
            return endpoint
        return f"{endpoint}/"

    def fetch_login_csrf(self) -> str:
        response = self._request("GET", "/weppcloud/login", expected_statuses=(200,))
        return _extract_csrf_token(response.text)

    def login_dev_agent(self, *, email: str, password: str, csrf_token: str) -> None:
        response = self._request(
            "POST",
            "/weppcloud/login",
            data={
                "email": email,
                "password": password,
                "remember": "y",
                "csrf_token": csrf_token,
            },
            expected_statuses=(200, 302),
            allow_redirects=False,
            request_preview_override={
                "data": {
                    "email": "<redacted>",
                    "password": "<redacted>",
                    "remember": "y",
                    "csrf_token": "<redacted>",
                }
            },
        )
        # Flask-Security redirects on success in most environments.
        if response.status_code == 302:
            return
        # Some deployments may return 200 with an authenticated page; validate via profile fetch.
        if response.status_code == 200:
            return
        raise LiveApiError(f"Login response returned unexpected status {response.status_code}")

    def fetch_profile_csrf(self) -> str:
        response = self._request(
            "GET",
            "/weppcloud/profile",
            expected_statuses=(200,),
            allow_redirects=True,
        )
        if "/weppcloud/profile" not in response.url:
            raise LiveApiError(
                "Expected authenticated profile response, but request did not resolve to /weppcloud/profile"
            )
        return _extract_csrf_token(response.text)

    def mint_profile_token(self, *, profile_csrf: str) -> dict[str, Any]:
        response = self._request(
            "POST",
            "/weppcloud/profile/mint-token",
            headers={"X-CSRFToken": profile_csrf},
            expected_statuses=(200,),
            request_preview_override={"headers": {"X-CSRFToken": "<redacted>"}},
            redact_response_body=True,
        )
        return response.json()

    def login_and_mint_dev_agent_bearer(self, *, email: str, password: str) -> dict[str, Any]:
        login_csrf = self.fetch_login_csrf()
        self.login_dev_agent(email=email, password=password, csrf_token=login_csrf)
        profile_csrf = self.fetch_profile_csrf()
        payload = self.mint_profile_token(profile_csrf=profile_csrf)
        token_payload = payload.get("Content") or payload.get("content") or payload.get("success") or {}
        token = str(token_payload.get("token") or "").strip()
        if not token:
            raise LiveApiError(f"mint-token response did not include bearer token: {_truncate(payload)}")
        return dict(token_payload)

    def issue_session_token(
        self,
        *,
        runid: str,
        config: str,
        session_origin: str,
        bearer_token: str | None,
    ) -> dict[str, Any]:
        path = (
            f"/rq-engine/api/runs/{self._encode_runid(runid)}/{self._encode_config(config)}/session-token"
        )
        headers = {"Origin": session_origin, **self._auth_headers(bearer_token)}
        response = self._request(
            "POST",
            path,
            headers=headers,
            expected_statuses=(200,),
            redact_response_body=True,
        )
        return response.json()

    def cap_challenge(self, cap_endpoint: str) -> dict[str, Any]:
        endpoint = cap_endpoint.rstrip("/")
        url_path = endpoint.removeprefix(self.base_url)
        response = self._request("POST", f"{url_path}/challenge", expected_statuses=(200,))
        return response.json()

    def cap_redeem(
        self,
        cap_endpoint: str,
        *,
        token: str,
        solutions: Iterable[int],
    ) -> dict[str, Any]:
        endpoint = cap_endpoint.rstrip("/")
        url_path = endpoint.removeprefix(self.base_url)
        response = self._request(
            "POST",
            f"{url_path}/redeem",
            json_body={"token": token, "solutions": list(solutions)},
            expected_statuses=(200,),
        )
        return response.json()

    def fork_run(
        self,
        *,
        source_runid: str,
        config: str,
        bearer_token: str,
        target_runid: str,
        cap_token: str,
    ) -> dict[str, Any]:
        path = f"/rq-engine/api/runs/{self._encode_runid(source_runid)}/{self._encode_config(config)}/fork"
        payload = {
            "target_runid": target_runid,
            "undisturbify": False,
            "cap_token": cap_token,
        }
        response = self._request(
            "POST",
            path,
            headers=self._auth_headers(bearer_token),
            json_body=payload,
            expected_statuses=(200,),
        )
        return response.json()

    def get_job_status(self, *, job_id: str, bearer_token: str | None = None) -> dict[str, Any]:
        path = f"/rq-engine/api/jobstatus/{quote(job_id, safe='')}"
        response = self._request(
            "GET",
            path,
            headers=self._auth_headers(bearer_token),
            expected_statuses=(200,),
        )
        return response.json()

    def wait_for_job(
        self,
        *,
        job_id: str,
        timeout_seconds: float,
        poll_interval_seconds: float,
        bearer_token: str | None = None,
    ) -> JobWaitResult:
        started = time.monotonic()
        terminal_failure_statuses = {"failed", "stopped", "canceled"}
        in_progress_statuses = {"queued", "started", "deferred", "scheduled"}

        while True:
            payload = self.get_job_status(job_id=job_id, bearer_token=bearer_token)
            status = str(payload.get("status") or "").strip().lower()
            elapsed = time.monotonic() - started

            if status == "finished":
                return JobWaitResult(job_id=job_id, status_payload=payload, elapsed_seconds=elapsed)
            if status in terminal_failure_statuses:
                raise LiveApiError(
                    f"Job {job_id} ended in terminal failure state '{status}': {_truncate(payload)}"
                )
            if status not in in_progress_statuses:
                raise LiveApiError(
                    f"Job {job_id} returned unexpected state '{status}': {_truncate(payload)}"
                )
            if elapsed > timeout_seconds:
                raise LiveApiError(
                    f"Timed out waiting for job {job_id} after {elapsed:.1f}s; last_status='{status}'"
                )

            time.sleep(poll_interval_seconds)

    def disturbed_lookup_meta(
        self,
        *,
        runid: str,
        config: str,
        bearer_token: str,
        lookup: str,
    ) -> dict[str, Any]:
        path = f"/weppcloud/runs/{self._encode_runid(runid)}/{self._encode_config(config)}/api/disturbed/lookup_meta"
        response = self._request(
            "GET",
            path,
            params={"lookup": lookup},
            headers=self._auth_headers(bearer_token),
            expected_statuses=(200,),
        )
        payload = response.json()
        return dict(payload.get("Content") or {})

    def disturbed_lookup_snapshot(
        self,
        *,
        runid: str,
        config: str,
        bearer_token: str,
        lookup: str,
    ) -> dict[str, Any]:
        path = f"/weppcloud/runs/{self._encode_runid(runid)}/{self._encode_config(config)}/api/disturbed/lookup_snapshot"
        response = self._request(
            "GET",
            path,
            params={"lookup": lookup},
            headers=self._auth_headers(bearer_token),
            expected_statuses=(200,),
        )
        payload = response.json()
        return dict(payload.get("Content") or {})

    def disturbed_modify(
        self,
        *,
        runid: str,
        config: str,
        bearer_token: str,
        lookup: str,
        rows: list[dict[str, Any]] | list[list[Any]],
        if_match_sha256: str,
        expected_statuses: Sequence[int] = (200,),
    ) -> requests.Response:
        path = f"/weppcloud/runs/{self._encode_runid(runid)}/{self._encode_config(config)}/tasks/modify_disturbed"
        return self._request(
            "POST",
            path,
            params={"lookup": lookup},
            headers=self._auth_headers(bearer_token),
            json_body={"rows": rows, "if_match_sha256": if_match_sha256},
            expected_statuses=expected_statuses,
        )

    def load_extended_lookup(
        self,
        *,
        runid: str,
        config: str,
        bearer_token: str,
    ) -> None:
        path = (
            f"/weppcloud/runs/{self._encode_runid(runid)}/{self._encode_config(config)}/"
            "tasks/load_extended_land_soil_lookup"
        )
        self._request(
            "POST",
            path,
            headers=self._auth_headers(bearer_token),
            expected_statuses=(200,),
        )

    def sync_base_to_extended_lookup(
        self,
        *,
        runid: str,
        config: str,
        bearer_token: str,
    ) -> None:
        path = (
            f"/weppcloud/runs/{self._encode_runid(runid)}/{self._encode_config(config)}/"
            "tasks/sync_base_to_extended_land_soil_lookup"
        )
        self._request(
            "POST",
            path,
            headers=self._auth_headers(bearer_token),
            expected_statuses=(200,),
        )

    def build_soils(
        self,
        *,
        runid: str,
        config: str,
        bearer_token: str,
        initial_sat: float = 0.75,
        sol_ver: float = 9002.0,
    ) -> str:
        path = f"/rq-engine/api/runs/{self._encode_runid(runid)}/{self._encode_config(config)}/build-soils"
        response = self._request(
            "POST",
            path,
            headers=self._auth_headers(bearer_token),
            json_body={"initial_sat": initial_sat, "sol_ver": sol_ver},
            expected_statuses=(200,),
        )
        payload = response.json()
        job_id = str(payload.get("job_id") or "")
        if not job_id:
            raise LiveApiError(f"build-soils did not return job_id: {_truncate(payload)}")
        return job_id

    def prep_wepp_watershed(
        self,
        *,
        runid: str,
        config: str,
        bearer_token: str,
    ) -> str:
        path = f"/rq-engine/api/runs/{self._encode_runid(runid)}/{self._encode_config(config)}/prep-wepp-watershed"
        response = self._request(
            "POST",
            path,
            headers=self._auth_headers(bearer_token),
            json_body={},
            expected_statuses=(200,),
        )
        payload = response.json()
        job_id = str(payload.get("job_id") or "")
        if not job_id:
            raise LiveApiError(f"prep-wepp-watershed did not return job_id: {_truncate(payload)}")
        return job_id

    def download_bytes(
        self,
        *,
        runid: str,
        config: str,
        subpath: str,
        bearer_token: str | None = None,
    ) -> bytes:
        path = (
            f"/weppcloud/runs/{self._encode_runid(runid)}/{self._encode_config(config)}/download/"
            f"{self._encode_subpath(subpath)}"
        )
        response = self._request(
            "GET",
            path,
            headers=self._auth_headers(bearer_token),
            expected_statuses=(200,),
            allow_redirects=True,
        )
        return response.content

    def download_text(
        self,
        *,
        runid: str,
        config: str,
        subpath: str,
        bearer_token: str | None = None,
    ) -> str:
        return self.download_bytes(
            runid=runid,
            config=config,
            subpath=subpath,
            bearer_token=bearer_token,
        ).decode("utf-8", errors="replace")
