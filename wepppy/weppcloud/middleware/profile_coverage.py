from __future__ import annotations

import uuid
from pathlib import Path
from typing import Optional

import coverage
from flask import Flask, g, request

from wepppy.rq.utils import (
    clear_profile_trace_slug,
    install_profile_trace_queue_hook,
    set_profile_trace_slug,
)

PROFILE_TRACE_HEADER = "X-Profile-Trace"


class ProfileCoverageManager:
    """Request-scoped controller that toggles coverage collection per profile."""

    def __init__(self, app: Flask) -> None:
        self.app = app
        self.enabled: bool = bool(app.config.get("PROFILE_COVERAGE_ENABLED", False))
        self.data_root = Path(
            app.config.get(
                "PROFILE_COVERAGE_DIR", "/workdir/wepppy-test-engine-data/coverage"
            )
        )
        self.context_prefix: str = app.config.get(
            "PROFILE_COVERAGE_CONTEXT_PREFIX", "profile"
        )
        self._config_path = self._resolve_config_path(
            app.config.get("PROFILE_COVERAGE_CONFIG")
        )
        self._ensure_data_root()

    def _ensure_data_root(self) -> None:
        if not self.enabled:
            self.app.logger.info("Profile coverage disabled")
            return
        try:
            self.data_root.mkdir(parents=True, exist_ok=True)
            self.app.logger.info(
                "Profile coverage enabled; writing data to %s", self.data_root
            )
        except OSError as exc:
            self.enabled = False
            self.app.logger.error(
                "Profile coverage disabled: unable to create %s (%s)",
                self.data_root,
                exc,
            )

    def _resolve_config_path(self, raw_path: Optional[str]) -> Optional[Path]:
        if raw_path:
            candidate = Path(raw_path)
        else:
            candidate = Path(self.app.root_path) / "coverage.profile-playback.ini"
        if candidate.exists():
            return candidate
        self.app.logger.warning(
            "Profile coverage config %s not found; falling back to coverage defaults",
            candidate,
        )
        return None

    def before_request(self) -> None:
        if not self.enabled:
            return

        slug = request.headers.get(PROFILE_TRACE_HEADER)
        if not slug:
            return

        slug = slug.strip()
        if not slug:
            return

        request_token = uuid.uuid4().hex
        g.profile_trace_slug = slug
        g.profile_trace_request_id = request_token
        set_profile_trace_slug(slug)

        coverage_obj = self._start_coverage(slug, request_token)
        if coverage_obj is None:
            return

        g.profile_coverage = coverage_obj

    def after_request(self, response):
        if getattr(g, "profile_coverage", None) is not None:
            self._stop_coverage()
        else:
            self._clear_trace_state()
        return response

    def teardown_request(self, _exc: Optional[BaseException]) -> None:
        if getattr(g, "profile_coverage", None) is not None:
            self._stop_coverage()
        else:
            self._clear_trace_state()

    def _coverage_kwargs(self, slug: str, request_token: str) -> dict[str, object]:
        data_file = self.data_root / f"{slug}.coverage"
        kwargs: dict[str, object] = {
            "data_file": str(data_file),
            "data_suffix": True,
            "parallel": True,
            "context": f"{self.context_prefix}:{slug}:{request_token}",
        }
        if self._config_path:
            kwargs["config_file"] = str(self._config_path)
        return kwargs

    def _start_coverage(
        self, slug: str, request_token: str
    ) -> Optional[coverage.Coverage]:
        try:
            cov = coverage.Coverage(**self._coverage_kwargs(slug, request_token))
            cov.load()
            cov.start()
            return cov
        except Exception as exc:  # pragma: no cover - defensive logging
            self.app.logger.exception(
                "Failed to start profile coverage for %s: %s", slug, exc
            )
            return None

    def _stop_coverage(self) -> None:
        coverage_obj: Optional[coverage.Coverage] = getattr(
            g, "profile_coverage", None
        )
        slug = getattr(g, "profile_trace_slug", None)
        if coverage_obj is None:
            self._clear_trace_state()
            return
        try:
            coverage_obj.stop()
            coverage_obj.save()
        except Exception as exc:  # pragma: no cover - defensive logging
            self.app.logger.exception(
                "Failed to save profile coverage for %s: %s", slug or "<unknown>", exc
            )
        finally:
            g.pop("profile_coverage", None)
            self._clear_trace_state()

    def _clear_trace_state(self) -> None:
        g.pop("profile_trace_slug", None)
        g.pop("profile_trace_request_id", None)
        clear_profile_trace_slug()


def init_profile_coverage(app: Flask) -> ProfileCoverageManager:
    """Register the profile coverage middleware if enabled."""
    manager = ProfileCoverageManager(app)
    app.extensions["profile_coverage"] = manager
    if manager.enabled:
        install_profile_trace_queue_hook()
        app.before_request(manager.before_request)
        app.after_request(manager.after_request)
        app.teardown_request(manager.teardown_request)
    return manager
