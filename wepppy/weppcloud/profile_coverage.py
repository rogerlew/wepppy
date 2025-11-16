"""Flask integration helpers for profile playback coverage tracing."""

from __future__ import annotations

import logging
from typing import Optional, Tuple
from uuid import uuid4

from flask import Flask, g, request

try:
    from coverage import Coverage
    from coverage.exceptions import CoverageException
except ImportError as exc:  # coverage is required for profile tracing
    raise RuntimeError("coverage.py must be installed for profile coverage") from exc

from wepppy.profile_coverage import ProfileCoverageSettings, load_settings_from_env
from wepppy.profile_coverage.runtime import (
    install_rq_hooks,
    reset_profile_trace_slug,
    set_profile_trace_slug,
)

_LOGGER = logging.getLogger(__name__)
_REQUEST_STATE_KEY = "_profile_coverage_state"


def _start_coverage(settings: ProfileCoverageSettings, slug: str) -> Optional[Tuple[Coverage, object]]:
    trace_token = uuid4().hex
    ctx_token = set_profile_trace_slug(slug)

    kwargs = settings.coverage_kwargs(slug, trace_token)
    _LOGGER.info(
        "Profile coverage start slug=%s data_file=%s context=%s",
        slug,
        kwargs.get("data_file"),
        kwargs.get("context"),
    )
    try:
        cov = Coverage(**kwargs)
        try:
            cov.load()
        except CoverageException:
            # Fresh run; no prior data to load.
            pass
        cov.start()
    except Exception as exc:  # pragma: no cover - defensive logging
        reset_profile_trace_slug(ctx_token)
        _LOGGER.error("Failed to start profile coverage for %s: %s", slug, exc)
        return None

    return cov, ctx_token


def _stop_coverage(state: Tuple[Coverage, object], slug: str) -> None:
    coverage_obj, ctx_token = state
    try:
        coverage_obj.stop()
        coverage_obj.save()
    except CoverageException as exc:  # pragma: no cover - logging only
        _LOGGER.warning("Profile coverage save failed for %s: %s", slug, exc)
    except Exception as exc:  # pragma: no cover - defensive logging
        _LOGGER.exception("Unexpected error while saving profile coverage for %s: %s", slug, exc)
    finally:
        reset_profile_trace_slug(ctx_token)


def init_profile_coverage(app: Flask) -> None:
    """Attach request hooks that enable coverage tracing when requested."""

    settings = load_settings_from_env()
    if not settings.enabled:
        app.logger.info("Profile coverage disabled via configuration or environment flag.")
        return
    if not settings.ensure_data_root(app.logger):
        return

    settings.log_config_status(app.logger)
    install_rq_hooks()
    app.extensions["profile_coverage_settings"] = settings

    @app.before_request
    def _start_profile_trace() -> None:  # pragma: no cover - requires Flask request context
        slug = request.headers.get("X-Profile-Trace")
        if not slug:
            app.logger.debug("Profile coverage: missing X-Profile-Trace header for %s", request.path)
            return
        app.logger.info("Profile coverage: header detected slug=%s path=%s", slug, request.path)
        state = _start_coverage(settings, slug)
        if state is None:
            return
        g.profile_trace_slug = slug
        setattr(g, _REQUEST_STATE_KEY, (state, slug))

    @app.teardown_request
    def _stop_profile_trace(exception: BaseException | None) -> None:  # pragma: no cover - requires Flask
        state_entry = getattr(g, _REQUEST_STATE_KEY, None)
        if not state_entry:
            return
        (state, slug) = state_entry
        _stop_coverage(state, slug)
        setattr(g, _REQUEST_STATE_KEY, None)


__all__ = ["init_profile_coverage"]
