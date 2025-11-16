#!/usr/bin/env python3
"""
Helper CLI used by wctl to exercise the profile playback microservice.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

import requests


def _default_service_url() -> str:
    return (
        os.environ.get("PROFILE_PLAYBACK_URL")
        or os.environ.get("PROFILE_PLAYBACK_DEFAULT_SERVICE_URL")
        or "http://127.0.0.1:8070"
    )


def _default_base_url() -> str:
    return (
        os.environ.get("PROFILE_PLAYBACK_BASE_URL")
        or os.environ.get("PROFILE_PLAYBACK_DEFAULT_BASE_URL")
        or "http://weppcloud:8000/weppcloud"
    )


def _load_cookie(value: Optional[str], path: Optional[str]) -> Optional[str]:
    if path:
        cookie_path = Path(path)
        if not cookie_path.exists():
            raise SystemExit(f"Cookie file not found: {cookie_path}")
        return cookie_path.read_text().strip()
    if value:
        return value.strip()
    return None


def _stream_post(url: str, payload: dict, headers: dict) -> int:
    with requests.post(url, json=payload, headers=headers, stream=True, timeout=None) as response:
        try:
            response.raise_for_status()
        except requests.HTTPError as exc:
            sys.stderr.write(f"[wctl] HTTP error {response.status_code}: {response.text}\n")
            raise SystemExit(exc) from exc

        for chunk in response.iter_lines():
            if chunk:
                print(chunk.decode("utf-8"), flush=True)
    return 0


def _post_json(url: str, payload: dict, headers: dict) -> int:
    response = requests.post(url, json=payload, headers=headers, timeout=None)
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        sys.stderr.write(f"[wctl] HTTP error {response.status_code}: {response.text}\n")
        raise SystemExit(exc) from exc
    try:
        data = response.json()
    except ValueError:
        print(response.text)
    else:
        print(json.dumps(data, indent=2))
    return 0


def run_test(args: argparse.Namespace) -> int:
    service_url = args.service_url or _default_service_url()
    base_url = args.base_url or _default_base_url()
    cookie = _load_cookie(args.cookie, args.cookie_file)

    payload = {
        "dry_run": args.dry_run,
        "verbose": True,
    }
    if base_url:
        payload["base_url"] = base_url
    if cookie:
        payload["cookie"] = cookie

    if args.trace_code:
        payload["trace_code"] = True
        if args.coverage_dir:
            payload["coverage_dir"] = args.coverage_dir
        if args.coverage_config:
            payload["coverage_config"] = args.coverage_config

    headers = {"Content-Type": "application/json"}
    if cookie:
        headers["Cookie"] = cookie

    url = f"{service_url.rstrip('/')}/run/{args.profile}"
    print(f"[wctl] POST {url}", file=sys.stderr)
    print(f"[wctl] payload: {json.dumps(payload)}", file=sys.stderr)
    return _stream_post(url, payload, headers)


def run_fork(args: argparse.Namespace) -> int:
    service_url = args.service_url or _default_service_url()
    base_url = args.base_url or _default_base_url()
    cookie = _load_cookie(args.cookie, args.cookie_file)

    payload = {
        "undisturbify": args.undisturbify,
        "timeout_seconds": args.timeout,
    }
    if args.target_runid:
        payload["target_runid"] = args.target_runid
    if base_url:
        payload["base_url"] = base_url
    if cookie:
        payload["cookie"] = cookie

    headers = {"Content-Type": "application/json"}
    if cookie:
        headers["Cookie"] = cookie

    url = f"{service_url.rstrip('/')}/fork/{args.profile}"
    print(f"[wctl] POST {url}", file=sys.stderr)
    print(f"[wctl] payload: {json.dumps(payload)}", file=sys.stderr)
    return _post_json(url, payload, headers)


def run_archive(args: argparse.Namespace) -> int:
    service_url = args.service_url or _default_service_url()
    base_url = args.base_url or _default_base_url()
    cookie = _load_cookie(args.cookie, args.cookie_file)

    payload = {
        "timeout_seconds": args.timeout,
    }
    if args.archive_comment is not None:
        payload["comment"] = args.archive_comment
    if base_url:
        payload["base_url"] = base_url
    if cookie:
        payload["cookie"] = cookie

    headers = {"Content-Type": "application/json"}
    if cookie:
        headers["Cookie"] = cookie

    url = f"{service_url.rstrip('/')}/archive/{args.profile}"
    print(f"[wctl] POST {url}", file=sys.stderr)
    print(f"[wctl] payload: {json.dumps(payload)}", file=sys.stderr)
    return _post_json(url, payload, headers)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Profile playback helper invoked by wctl.")
    sub = parser.add_subparsers(dest="command", required=True)

    test = sub.add_parser("run-test-profile", help="Replay a recorded profile via /run/<profile>.")
    test.add_argument("profile")
    test.add_argument("--dry-run", action="store_true", help="Preview without executing requests.")
    test.add_argument("--base-url", help="Override WEPPcloud base URL.")
    test.add_argument("--service-url", help="Override playback service URL.")
    test.add_argument("--cookie", help="Raw Cookie header forwarded to WEPPcloud.")
    test.add_argument("--cookie-file", help="Read Cookie header from a file.")
    test.add_argument("--trace-code", action="store_true", help="Enable profile coverage tracing.")
    test.add_argument("--coverage-dir", help="Directory for combined coverage artifacts inside the playback container.")
    test.add_argument("--coverage-config", help="Override coverage.profile-playback.ini path.")
    test.set_defaults(func=run_test)

    fork = sub.add_parser("run-fork-profile", help="Trigger a fork job against the sandbox run.")
    fork.add_argument("profile")
    fork.add_argument("--undisturbify", action="store_true", help="Request undisturbify processing.")
    fork.add_argument("--target-runid", help="Override destination run id.")
    fork.add_argument("--timeout", type=int, default=600, help="Seconds to wait for the fork job (default: 600).")
    fork.add_argument("--base-url", help="Override WEPPcloud base URL.")
    fork.add_argument("--service-url", help="Override playback service URL.")
    fork.add_argument("--cookie", help="Raw Cookie header forwarded to WEPPcloud.")
    fork.add_argument("--cookie-file", help="Read Cookie header from a file.")
    fork.set_defaults(func=run_fork)

    archive = sub.add_parser("run-archive-profile", help="Trigger an archive job against the sandbox run.")
    archive.add_argument("profile")
    archive.add_argument("--archive-comment", help="Optional comment stored with the archive.")
    archive.add_argument("--timeout", type=int, default=600, help="Seconds to wait for the archive job (default: 600).")
    archive.add_argument("--base-url", help="Override WEPPcloud base URL.")
    archive.add_argument("--service-url", help="Override playback service URL.")
    archive.add_argument("--cookie", help="Raw Cookie header forwarded to WEPPcloud.")
    archive.add_argument("--cookie-file", help="Read Cookie header from a file.")
    archive.set_defaults(func=run_archive)

    return parser


def main(argv: Optional[list[str]] = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())
