from __future__ import annotations

import json
import re
from pathlib import Path
from typing import NamedTuple, Optional

import requests
import typer

from ..context import CLIContext
from ..util import load_cookie


def _context(ctx: typer.Context) -> CLIContext:
    context = ctx.obj
    if not isinstance(context, CLIContext):
        raise RuntimeError("CLIContext is not initialised.")
    return context


def _default_service_url(context: CLIContext, override: Optional[str]) -> str:
    if override:
        return override
    candidate = context.env_value("PROFILE_PLAYBACK_URL") or context.environment.get("PROFILE_PLAYBACK_URL")
    if candidate:
        return candidate
    return "http://127.0.0.1:8070"


def _default_base_url(context: CLIContext, override: Optional[str]) -> str:
    if override:
        return override
    candidate = context.env_value("PROFILE_PLAYBACK_BASE_URL") or context.environment.get("PROFILE_PLAYBACK_BASE_URL")
    if candidate:
        return candidate
    # Local HTTP base URL works only when callers supply their own cookie; playback's automated
    # login requires the public HTTPS host because WEPPcloud marks auth cookies as Secure.
    return "http://weppcloud:8000/weppcloud"

def _resolve_coverage_config(context: CLIContext, override: Optional[str]) -> Optional[str]:
    if override:
        candidate = Path(override)
        if not candidate.is_absolute():
            candidate = (context.project_dir / candidate).resolve()
        return str(candidate)
    default = context.project_dir / "wepppy" / "weppcloud" / "coverage.profile-playback.ini"
    if default.exists():
        return str(default.resolve())
    return None


def _raise_for_status(response: requests.Response) -> None:
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        typer.echo(f"[wctl] HTTP error {response.status_code}: {response.text}", err=True)
        raise typer.Exit(1) from exc


class PlaybackStreamOutcome(NamedTuple):
    token: Optional[str]
    saw_error: bool


_TOKEN_RE = re.compile(r"token=([0-9a-fA-F]{32})")
_ERROR_PATTERNS = ("playback error", "runtimeerror", "traceback", "status failed")


def _update_outcome(outcome: PlaybackStreamOutcome, line: str) -> PlaybackStreamOutcome:
    token_match = _TOKEN_RE.search(line)
    token = outcome.token or (token_match.group(1) if token_match else None)
    lowered = line.lower()
    saw_error = outcome.saw_error or any(pattern in lowered for pattern in _ERROR_PATTERNS)
    return PlaybackStreamOutcome(token=token, saw_error=saw_error)


def _parse_lines(lines, outcome: PlaybackStreamOutcome) -> PlaybackStreamOutcome:
    for line in lines:
        outcome = _update_outcome(outcome, line)
        typer.echo(line)
    return outcome


def _stream_post(url: str, payload: dict, headers: dict) -> PlaybackStreamOutcome:
    outcome = PlaybackStreamOutcome(token=None, saw_error=False)
    try:
        with requests.post(url, json=payload, headers=headers, stream=True, timeout=None) as response:
            _raise_for_status(response)
            received_any = False
            try:
                for chunk in response.iter_lines():
                    if chunk:
                        line = chunk.decode("utf-8")
                        outcome = _update_outcome(outcome, line)
                        typer.echo(line)
                        received_any = True
            except requests.exceptions.ChunkedEncodingError as exc:
                if not received_any:
                    raise
                typer.echo(
                    f"[wctl] Streaming finished with chunked-encoding warning ({exc}); continuing without fallback.",
                    err=True,
                )
                return outcome
    except Exception as exc:
        # Handle chunked transfer encoding issues by falling back to non-streaming
        typer.echo(f"[wctl] Streaming failed ({exc.__class__.__name__}: {exc}), falling back to non-streaming...", err=True)
        try:
            response = requests.post(url, json=payload, headers=headers, stream=False, timeout=None)
            _raise_for_status(response)
            # Output the response text line by line to simulate streaming
            outcome = _parse_lines(response.text.splitlines(), outcome)
        except Exception as fallback_exc:
            typer.echo(f"[wctl] Fallback also failed: {fallback_exc}", err=True)
            raise typer.Exit(1) from fallback_exc
    return outcome


def _post_json(url: str, payload: dict, headers: dict) -> None:
    response = requests.post(url, json=payload, headers=headers, timeout=None)
    _raise_for_status(response)
    try:
        data = response.json()
    except ValueError:
        typer.echo(response.text)
    else:
        typer.echo(json.dumps(data, indent=2))


def _fetch_result(service_url: str, token: str, headers: dict) -> Optional[dict]:
    # Only forward cookies for result lookup; other headers (content-type, encoding)
    # are unnecessary for GET.
    result_headers = {}
    if "Cookie" in headers:
        result_headers["Cookie"] = headers["Cookie"]
    url = f"{service_url.rstrip('/')}/run/result/{token}"
    response = requests.get(url, headers=result_headers, timeout=60)
    if response.status_code == 404:
        return None
    _raise_for_status(response)
    try:
        return response.json()
    except ValueError:
        typer.echo(f"[wctl] Unexpected non-JSON result for token {token}: {response.text}", err=True)
        raise typer.Exit(1)


def register(app: typer.Typer) -> None:
    @app.command("run-test-profile")
    def run_test_profile(
        ctx: typer.Context,
        profile: str = typer.Argument(..., help="Profile slug (for example backed-globule)."),
        dry_run: bool = typer.Option(False, "--dry-run", help="Preview without executing requests."),
        base_url: Optional[str] = typer.Option(None, "--base-url", help="Override WEPPcloud base URL."),
        service_url: Optional[str] = typer.Option(None, "--service-url", help="Override playback service URL."),
        cookie: Optional[str] = typer.Option(None, "--cookie", help="Raw Cookie header forwarded to WEPPcloud."),
        cookie_file: Optional[str] = typer.Option(
            None,
            "--cookie-file",
            help="Read Cookie header from a file.",
        ),
        trace_code: bool = typer.Option(False, "--trace-code", help="Enable profile coverage tracing."),
        coverage_dir: Optional[str] = typer.Option(
            None,
            "--coverage-dir",
            help="Directory inside the profile-playback container where combined coverage artifacts are written.",
        ),
        coverage_config: Optional[str] = typer.Option(
            None,
            "--coverage-config",
            help="Override coverage.profile-playback.ini path (relative to the project root).",
        ),
    ) -> None:
        context = _context(ctx)
        resolved_service_url = _default_service_url(context, service_url)
        resolved_base_url = _default_base_url(context, base_url)
        resolved_cookie = load_cookie(cookie, cookie_file)
        resolved_coverage_config = _resolve_coverage_config(context, coverage_config) if trace_code else None

        payload = {"dry_run": dry_run, "verbose": True}
        if resolved_base_url:
            payload["base_url"] = resolved_base_url
        if resolved_cookie:
            payload["cookie"] = resolved_cookie
        if trace_code:
            payload["trace_code"] = True
            if coverage_dir:
                payload["coverage_dir"] = coverage_dir
            if resolved_coverage_config:
                payload["coverage_config"] = resolved_coverage_config

        headers = {"Content-Type": "application/json", "Accept-Encoding": "identity"}
        if resolved_cookie:
            headers["Cookie"] = resolved_cookie

        url = f"{resolved_service_url.rstrip('/')}/run/{profile}"
        typer.echo(f"[wctl] POST {url}", err=True)
        typer.echo(f"[wctl] payload: {json.dumps(payload)}", err=True)
        outcome = _stream_post(url, payload, headers)

        if outcome.saw_error:
            typer.echo("[wctl] playback stream reported errors; failing CI early.", err=True)
            raise typer.Exit(1)

        if not outcome.token:
            typer.echo(
                "[wctl] playback stream completed without exposing result token; skipping result lookup.",
                err=True,
            )
            raise typer.Exit(0)

        result = _fetch_result(resolved_service_url, outcome.token, headers)
        if result is None:
            typer.echo(f"[wctl] no result found for token={outcome.token}; marking as failure.", err=True)
            raise typer.Exit(1)

        typer.echo(f"[wctl] playback completed successfully; token={outcome.token}", err=True)
        raise typer.Exit(0)

    @app.command("run-fork-profile")
    def run_fork_profile(
        ctx: typer.Context,
        profile: str = typer.Argument(..., help="Profile slug (for example backed-globule)."),
        undisturbify: bool = typer.Option(False, "--undisturbify", help="Request undisturbify processing."),
        target_runid: Optional[str] = typer.Option(None, "--target-runid", help="Override destination run id."),
        timeout: int = typer.Option(600, "--timeout", help="Seconds to wait for the fork job (default: 600)."),
        base_url: Optional[str] = typer.Option(None, "--base-url", help="Override WEPPcloud base URL."),
        service_url: Optional[str] = typer.Option(None, "--service-url", help="Override playback service URL."),
        cookie: Optional[str] = typer.Option(None, "--cookie", help="Raw Cookie header forwarded to WEPPcloud."),
        cookie_file: Optional[str] = typer.Option(
            None,
            "--cookie-file",
            help="Read Cookie header from a file.",
        ),
    ) -> None:
        context = _context(ctx)
        resolved_service_url = _default_service_url(context, service_url)
        resolved_base_url = _default_base_url(context, base_url)
        resolved_cookie = load_cookie(cookie, cookie_file)

        payload = {
            "undisturbify": undisturbify,
            "timeout_seconds": timeout,
        }
        if target_runid:
            payload["target_runid"] = target_runid
        if resolved_base_url:
            payload["base_url"] = resolved_base_url
        if resolved_cookie:
            payload["cookie"] = resolved_cookie

        headers = {"Content-Type": "application/json"}
        if resolved_cookie:
            headers["Cookie"] = resolved_cookie

        url = f"{resolved_service_url.rstrip('/')}/fork/{profile}"
        typer.echo(f"[wctl] POST {url}", err=True)
        typer.echo(f"[wctl] payload: {json.dumps(payload)}", err=True)
        _post_json(url, payload, headers)
        raise typer.Exit(0)

    @app.command("run-archive-profile")
    def run_archive_profile(
        ctx: typer.Context,
        profile: str = typer.Argument(..., help="Profile slug (for example backed-globule)."),
        archive_comment: Optional[str] = typer.Option(
            None,
            "--archive-comment",
            help="Optional comment stored with the archive.",
        ),
        timeout: int = typer.Option(600, "--timeout", help="Seconds to wait for the archive job (default: 600)."),
        base_url: Optional[str] = typer.Option(None, "--base-url", help="Override WEPPcloud base URL."),
        service_url: Optional[str] = typer.Option(None, "--service-url", help="Override playback service URL."),
        cookie: Optional[str] = typer.Option(None, "--cookie", help="Raw Cookie header forwarded to WEPPcloud."),
        cookie_file: Optional[str] = typer.Option(
            None,
            "--cookie-file",
            help="Read Cookie header from a file.",
        ),
    ) -> None:
        context = _context(ctx)
        resolved_service_url = _default_service_url(context, service_url)
        resolved_base_url = _default_base_url(context, base_url)
        resolved_cookie = load_cookie(cookie, cookie_file)

        payload = {
            "timeout_seconds": timeout,
        }
        if archive_comment is not None:
            payload["comment"] = archive_comment
        if resolved_base_url:
            payload["base_url"] = resolved_base_url
        if resolved_cookie:
            payload["cookie"] = resolved_cookie

        headers = {"Content-Type": "application/json"}
        if resolved_cookie:
            headers["Cookie"] = resolved_cookie

        url = f"{resolved_service_url.rstrip('/')}/archive/{profile}"
        typer.echo(f"[wctl] POST {url}", err=True)
        typer.echo(f"[wctl] payload: {json.dumps(payload)}", err=True)
        _post_json(url, payload, headers)
        raise typer.Exit(0)
