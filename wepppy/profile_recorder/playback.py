from __future__ import annotations

import argparse
import json
import logging
import os
import shutil
import time
from collections import deque
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.parse import parse_qsl, urljoin, urlparse

import requests

Event = Dict[str, object]


class PlaybackSession:
    """
    Minimal playback runner that replays recorder events against a WEPPcloud instance.

    Only GET requests and JSON POST bodies are currently supported. Other payload
    types (form-data uploads) are surfaced in the report for manual follow-up.
    """

    def __init__(
        self,
        profile_root: Path,
        *,
        base_url: str,
        execute: bool = False,
        run_dir: Optional[Path] = None,
        session: Optional[requests.Session] = None,
        verbose: bool = False,
        logger: Optional[logging.Logger] = None,
    ) -> None:
        self.profile_root = profile_root
        self.execute = execute
        self.base_url = base_url.rstrip("/")
        self.capture_dir = profile_root / "capture"
        self.session = session or requests.Session()
        self.verbose = verbose
        self._logger = logger
        self._pending_jobs: deque[Tuple[str, str]] = deque()

        if self.verbose:
            self._log(f"PlaybackSession created (execute={self.execute}, verbose={self.verbose})")

        if not self.capture_dir.exists():
            raise FileNotFoundError(f"Capture directory not found: {self.capture_dir}")

        self.events = self._load_events(self.capture_dir / "events.jsonl")
        self.run_id = self._detect_run_id(self.events) or profile_root.name
        self.original_run_id = self.run_id
        self.playback_run_id = f"profile;;tmp;;{self.original_run_id}"
        self._log(f"Loaded {len(self.events)} events from {self.capture_dir}")
        self._log(f"Resolved run id: {self.original_run_id}")
        self._log(f"Using playback run id: {self.playback_run_id}")

        if run_dir is not None:
            self.run_dir = run_dir
            self._log(f"Using existing run directory: {self.run_dir}")
        else:
            self.run_dir = self._clone_run(profile_root, self.run_id)
            self._log(f"Cloned run snapshot to: {self.run_dir}")

        self.requests = self._index_requests(self.events)
        self.results: List[Tuple[str, str]] = []

    def _clone_run(self, profile_root: Path, run_id: str) -> Path:
        source = profile_root / "run"
        if not source.exists():
            raise FileNotFoundError(f"Run snapshot not found at {source}")
        playback_root = Path(os.environ.get("PROFILE_PLAYBACK_RUN_ROOT", "/workdir/wepppy-test-engine-data/playback_runs"))
        playback_root.mkdir(parents=True, exist_ok=True)
        target = playback_root / run_id
        if target.exists():
            shutil.rmtree(target)
        shutil.copytree(source, target)
        return target

    @staticmethod
    def _detect_run_id(events: Iterable[Event]) -> Optional[str]:
        for event in events:
            if event.get("stage") != "request":
                continue
            endpoint = str(event.get("endpoint", ""))
            path = PlaybackSession._normalise_path(endpoint)
            parts = [part for part in path.split("/") if part]
            if "runs" in parts:
                try:
                    idx = parts.index("runs")
                    return parts[idx + 1]
                except (ValueError, IndexError):
                    continue
        return None

    @staticmethod
    def _load_events(path: Path) -> List[Event]:
        events: List[Event] = []
        with path.open("r", encoding="utf-8") as handle:
            for line in handle:
                line = line.strip()
                if not line:
                    continue
                events.append(json.loads(line))
        return events

    @staticmethod
    def _index_requests(events: Iterable[Event]) -> Dict[str, Event]:
        requests: Dict[str, Event] = {}
        for event in events:
            if event.get("stage") == "request" and "id" in event:
                requests[str(event["id"])] = event
        return requests

    def run(self) -> None:
        self._log("Beginning playback")
        for event in self.events:
            if event.get("stage") != "response":
                continue
            if event.get("ok") is False:
                continue
            request_id = str(event.get("id"))
            req = self.requests.get(request_id)
            if req is None:
                self.results.append((request_id, "skipped (missing request metadata)"))
                continue

            method = str(req.get("method", "GET")).upper()
            endpoint = str(req.get("endpoint", ""))
            path = self._normalise_path(endpoint)
            effective_path = self._remap_run_path(path)
            summary = req.get("requestMeta") or {}
            json_payload: Optional[dict] = None
            if isinstance(summary, dict) and summary.get("jsonPayload"):
                try:
                    json_payload = json.loads(summary["jsonPayload"])
                except json.JSONDecodeError:
                    self.results.append((request_id, f"{effective_path}: invalid JSON payload"))
                    continue

            if method not in ("GET", "POST"):
                self.results.append((request_id, f"{effective_path}: unsupported method {method}"))
                self._log(f"Skipping {request_id}: unsupported method {method}")
                continue

            if method == "POST" and json_payload is None:
                self.results.append((request_id, f"{effective_path}: unsupported payload type"))
                self._log(f"Skipping {request_id}: unsupported payload type")
                continue

            expected_status = self._expected_status(event)
            params = self._extract_query_params(event)
            url = self._build_url(effective_path)

            if self.verbose:
                display_path = effective_path
                if effective_path != path:
                    display_path = f"{effective_path} (source {path})"
                msg = f"{request_id} {method} {url}"
                if display_path != effective_path:
                    msg += f" [{display_path}]"
                if params:
                    msg += f" params={dict(params)}"
                if json_payload is not None:
                    msg += " body=json"
                self._log(msg)

            if self.execute:
                if method == "GET":
                    self._await_pending_jobs()
                try:
                    response = self._execute_request(
                        method,
                        url,
                        params,
                        json_payload,
                        expected_status,
                        effective_path,
                    )
                    self.results.append((request_id, f"{effective_path}: HTTP {response.status_code}"))
                    if self.verbose:
                        self._log(f"{request_id} → HTTP {response.status_code}")
                except requests.RequestException as exc:
                    self.results.append((request_id, f"{effective_path}: error {exc}"))
                    if self.verbose:
                        self._log(f"{request_id} → error {exc}")
            else:
                action = f"{method} {effective_path}"
                if json_payload is not None:
                    action += f" payload={json_payload}"
                self.results.append((request_id, f"dry-run {action}"))
        if self.execute:
            self._await_pending_jobs()

    @staticmethod
    def _normalise_path(endpoint: str) -> str:
        if not endpoint:
            return ""
        parsed = urlparse(endpoint)
        path = parsed.path or endpoint
        # Ensure path starts with single slash
        if not path.startswith("/"):
            path = "/" + path
        return path

    def report(self) -> str:
        lines = ["Playback results:"]
        for request_id, status in self.results:
            lines.append(f"  - {request_id}: {status}")
        lines.append(f"Playback run directory: {self.run_dir}")
        self._log("Playback complete")
        return "\n".join(lines)

    def _execute_request(
        self,
        method: str,
        url: str,
        params: List[Tuple[str, str]],
        json_payload: Optional[dict],
        expected_status: int,
        path: str,
    ) -> requests.Response:
        kwargs: Dict[str, object] = {"timeout": 60}
        if params:
            kwargs["params"] = params
        if method == "POST" and json_payload is not None:
            kwargs["json"] = json_payload

        response = self.session.request(method, url, **kwargs)

        if method == "POST" and self.execute:
            if self.verbose:
                self._log(f"{path} response content-type {response.headers.get('Content-Type', '')}")
                try:
                    preview = response.text[:200]
                except Exception:
                    preview = "<unavailable>"
                self._log(f"{path} response preview {preview}")
            job_id = self._extract_job_id(response)
            if job_id:
                if self.verbose:
                    self._log(f"job {job_id} enqueued by {path}")
                self._pending_jobs.append((job_id, path))
            elif self.verbose:
                self._log(f"no job id detected in {path} response")

        if self._should_wait_for_completion(method, path, expected_status):
            if self.verbose:
                self._log("waiting for task completion")
            return self._poll_for_completion(url, params, expected_status)

        return response

    def _poll_for_completion(
        self,
        url: str,
        params: List[Tuple[str, str]],
        expected_status: int,
        *,
        timeout: int = 300,
        interval: float = 2.0,
    ) -> requests.Response:
        end_time = time.time() + timeout
        last_response: Optional[requests.Response] = None
        last_status: Optional[int] = None
        attempt = 0
        while True:
            try:
                response = self.session.get(url, params=params or None, timeout=60)
            except requests.RequestException as exc:
                if last_response is not None:
                    return last_response
                raise exc

            last_response = response
            if response.status_code == expected_status:
                if self.verbose:
                    self._log("wait complete")
                return response
            if response.status_code not in (401, 403, 404):
                if self.verbose:
                    self._log(f"wait aborted on status {response.status_code}")
                return response
            if time.time() >= end_time:
                if self.verbose:
                    self._log(f"wait timed out after {attempt + 1} attempts (last status {response.status_code})")
                return response
            if self.verbose and (attempt == 0 or response.status_code != last_status):
                msg = f"waiting... status {response.status_code}"
                content_type = response.headers.get("Content-Type", "")
                if content_type.startswith("application/json"):
                    try:
                        msg += f" body={response.json()}"
                    except ValueError:
                        msg += " body=<invalid json>"
                else:
                    snippet = response.text[:300] if response.text else ""
                    if snippet:
                        msg += f" body={snippet}"
                self._log(msg)
            last_status = response.status_code
            attempt += 1
            time.sleep(interval)

    def _expected_status(self, event: Event) -> int:
        status = event.get("status")
        if isinstance(status, int):
            return status
        if event.get("ok") is True:
            return 200
        return 400

    def _extract_query_params(self, event: Event) -> List[Tuple[str, str]]:
        endpoint = str(event.get("endpoint") or "")
        parsed = urlparse(endpoint)
        if parsed.query:
            return parse_qsl(parsed.query, keep_blank_values=True)
        return []

    def _build_url(self, path: str) -> str:
        base = self.base_url.rstrip("/")
        return urljoin(f"{base}/", path.lstrip("/"))

    def _should_wait_for_completion(self, method: str, path: str, expected_status: int) -> bool:
        if method != "GET" or expected_status != 200:
            return False
        return any(path.endswith(suffix) for suffix in _WAIT_SUFFIXES)

    def _log(self, message: str) -> None:
        if self._logger is not None:
            self._logger.info(message)
        else:
            print(f"[playback] {message}")

    def _await_pending_jobs(self) -> None:
        while self._pending_jobs:
            job_id, task_path = self._pending_jobs.popleft()
            if self.verbose:
                self._log(f"waiting for job {job_id} ({task_path}) to finish")
            self._wait_for_job(job_id, task=task_path)

    def _remap_run_path(self, path: str) -> str:
        prefix = f"/runs/{self.original_run_id}/"
        if path.startswith(prefix):
            return path.replace(prefix, f"/runs/{self.playback_run_id}/", 1)
        if path == f"/runs/{self.original_run_id}":
            return f"/runs/{self.playback_run_id}"
        return path

    def _extract_job_id(self, response: requests.Response) -> Optional[str]:
        content_type = response.headers.get("content-type", "")
        if "application/json" not in content_type.lower():
            return None
        try:
            payload = response.json()
        except ValueError:
            if self.verbose:
                self._log("response JSON decode failed when extracting job id")
            return None
        if isinstance(payload, dict):
            job_id = payload.get("job_id") or payload.get("jobId")
            if isinstance(job_id, str) and job_id.strip():
                return job_id.strip()
            if self.verbose:
                self._log("response JSON did not include job_id")
        return None

    def _wait_for_job(
        self,
        job_id: str,
        *,
        timeout: int = 900,
        interval: float = 2.0,
        task: Optional[str] = None,
    ) -> None:
        status_url = self._build_url(f"/rq/api/jobstatus/{job_id}")
        end_time = time.time() + timeout
        last_status: Optional[str] = None

        while True:
            try:
                response = self.session.get(status_url, params={"_": int(time.time() * 1000)}, timeout=60)
            except requests.RequestException as exc:
                if self.verbose:
                    self._log(f"job {job_id} status request failed: {exc}")
                time.sleep(interval)
                if time.time() >= end_time:
                    raise RuntimeError(f"Timeout waiting for job {job_id}") from exc
                continue

            if response.status_code == 200:
                try:
                    payload = response.json()
                except ValueError:
                    payload = {}
                status = str(payload.get("status") or "").lower()
                if self.verbose and status and status != last_status:
                    msg = f"job {job_id} status {status}"
                    if task:
                        msg += f" ({task})"
                    self._log(msg)
                last_status = status or last_status
                if status in {"finished"}:
                    return
                if status in {"failed", "stopped", "canceled"}:
                    raise RuntimeError(f"Job {job_id} ended with status {status}")
            elif response.status_code == 404:
                if self.verbose:
                    self._log(f"job {job_id} status endpoint returned 404; assuming complete")
                return
            else:
                if self.verbose:
                    self._log(f"job {job_id} status HTTP {response.status_code}")

            if time.time() >= end_time:
                raise RuntimeError(f"Timeout waiting for job {job_id}")

            time.sleep(interval)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Replay recorder events against WEPPcloud.")
    parser.add_argument("profile", type=Path, help="Path to promoted profile root.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="WEPPcloud base URL.")
    parser.add_argument("--run-dir", type=Path, help="Optional run directory to use instead of cloning the profile snapshot.")
    parser.add_argument("--execute", action="store_true", help="Execute HTTP requests (default is dry-run).")
    parser.add_argument("--cookie", help="Raw Cookie header to send with each request (for authenticated playback).")
    parser.add_argument("--cookie-file", type=Path, help="Read Cookie header from file (overrides --cookie).")
    parser.add_argument("--verbose", action="store_true", help="Print progress information while replaying.")

    args = parser.parse_args(argv)

    cookie_value: Optional[str] = args.cookie
    if args.cookie_file:
        cookie_value = args.cookie_file.read_text(encoding="utf-8").strip()

    session = requests.Session()
    if cookie_value:
        session.headers.update({"Cookie": cookie_value})

    session = PlaybackSession(
        profile_root=args.profile,
        base_url=args.base_url,
        execute=args.execute,
        run_dir=args.run_dir,
        session=session,
        verbose=args.verbose,
    )
    session.run()
    print(session.report())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())


_WAIT_SUFFIXES: Tuple[str, ...] = (
    "/query/delineation_pass/",
    "/resources/subcatchments.json",
    "/report/subcatchments/",
    "/report/channel",
)
