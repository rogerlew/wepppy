from __future__ import annotations

import json
from typing import Optional

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
    return "http://weppcloud:8000/weppcloud"


def _raise_for_status(response: requests.Response) -> None:
    try:
        response.raise_for_status()
    except requests.HTTPError as exc:
        typer.echo(f"[wctl] HTTP error {response.status_code}: {response.text}", err=True)
        raise typer.Exit(1) from exc


def _stream_post(url: str, payload: dict, headers: dict) -> None:
    with requests.post(url, json=payload, headers=headers, stream=True, timeout=None) as response:
        _raise_for_status(response)
        for chunk in response.iter_lines():
            if chunk:
                typer.echo(chunk.decode("utf-8"))


def _post_json(url: str, payload: dict, headers: dict) -> None:
    response = requests.post(url, json=payload, headers=headers, timeout=None)
    _raise_for_status(response)
    try:
        data = response.json()
    except ValueError:
        typer.echo(response.text)
    else:
        typer.echo(json.dumps(data, indent=2))


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
    ) -> None:
        context = _context(ctx)
        resolved_service_url = _default_service_url(context, service_url)
        resolved_base_url = _default_base_url(context, base_url)
        resolved_cookie = load_cookie(cookie, cookie_file)

        payload = {"dry_run": dry_run, "verbose": True}
        if resolved_base_url:
            payload["base_url"] = resolved_base_url
        if resolved_cookie:
            payload["cookie"] = resolved_cookie

        headers = {"Content-Type": "application/json"}
        if resolved_cookie:
            headers["Cookie"] = resolved_cookie

        url = f"{resolved_service_url.rstrip('/')}/run/{profile}"
        typer.echo(f"[wctl] POST {url}", err=True)
        typer.echo(f"[wctl] payload: {json.dumps(payload)}", err=True)
        _stream_post(url, payload, headers)
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
