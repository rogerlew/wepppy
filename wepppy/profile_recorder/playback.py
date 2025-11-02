from __future__ import annotations

import argparse
import json
import os
import shutil
import tempfile
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Tuple
from urllib.parse import urlparse

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
    ) -> None:
        self.profile_root = profile_root
        self.execute = execute
        self.base_url = base_url.rstrip("/")
        self.capture_dir = profile_root / "capture"
        if not self.capture_dir.exists():
            raise FileNotFoundError(f"Capture directory not found: {self.capture_dir}")

        self.events = self._load_events(self.capture_dir / "events.jsonl")
        self.run_id = self._detect_run_id(self.events) or profile_root.name

        if run_dir is not None:
            self.run_dir = run_dir
        else:
            self.run_dir = self._clone_run(profile_root, self.run_id)

        self.session = session or requests.Session()

        self.requests = self._index_requests(self.events)
        self.results: List[Tuple[str, str]] = []

    def _clone_run(self, profile_root: Path, run_id: str) -> Path:
        source = profile_root / "run"
        if not source.exists():
            raise FileNotFoundError(f"Run snapshot not found at {source}")
        playback_root = Path(os.environ.get("PROFILE_PLAYBACK_RUN_ROOT", tempfile.gettempdir()))
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
            summary = req.get("requestMeta") or {}
            json_payload: Optional[dict] = None
            if isinstance(summary, dict) and summary.get("jsonPayload"):
                try:
                    json_payload = json.loads(summary["jsonPayload"])
                except json.JSONDecodeError:
                    self.results.append((request_id, f"{path}: invalid JSON payload"))
                    continue

            if method not in ("GET", "POST"):
                self.results.append((request_id, f"{path}: unsupported method {method}"))
                continue

            if method == "POST" and json_payload is None:
                self.results.append((request_id, f"{path}: unsupported payload type"))
                continue

            if self.execute:
                url = f"{self.base_url}{path}"
                try:
                    response = self.session.request(method, url, json=json_payload, timeout=60)
                    self.results.append((request_id, f"{path}: HTTP {response.status_code}"))
                except requests.RequestException as exc:
                    self.results.append((request_id, f"{path}: error {exc}"))
            else:
                action = f"{method} {path}"
                if json_payload is not None:
                    action += f" payload={json_payload}"
                self.results.append((request_id, f"dry-run {action}"))

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
        return "\n".join(lines)


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description="Replay recorder events against WEPPcloud.")
    parser.add_argument("profile", type=Path, help="Path to promoted profile root.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="WEPPcloud base URL.")
    parser.add_argument("--run-dir", type=Path, help="Optional run directory to use instead of cloning the profile snapshot.")
    parser.add_argument("--execute", action="store_true", help="Execute HTTP requests (default is dry-run).")
    parser.add_argument("--cookie", help="Raw Cookie header to send with each request (for authenticated playback).")
    parser.add_argument("--cookie-file", type=Path, help="Read Cookie header from file (overrides --cookie).")

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
    )
    session.run()
    print(session.report())
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
