from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from flask import current_app
from wepppy.weppcloud.utils.helpers import get_wd

from .assembler import ProfileAssembler
from .utils import sanitise_component

LOGGER = logging.getLogger(__name__)


class ProfileRecorder:
    """Persist recorder events to per-run audit logs and forward them to the assembler."""

    def __init__(self, *, data_repo_root: Path, fallback_root: Path) -> None:
        self.data_repo_root = Path(data_repo_root)
        self.fallback_root = Path(fallback_root)
        self.assembler = ProfileAssembler(self.data_repo_root)

    def append_event(self, event: Dict[str, Any], *, user: Any = None) -> None:
        record = dict(event)
        record.setdefault("received_at", datetime.now(timezone.utc).isoformat())

        if user and getattr(user, "is_authenticated", False):
            record["user"] = {
                "id": getattr(user, "id", None),
                "email": getattr(user, "email", None),
            }

        run_id = record.get("runId") or record.get("run_id")
        capture_id = record.get("captureId") or record.get("capture_id")
        run_dir = self._resolve_run_directory(run_id)
        audit_path = self._audit_log_path(run_dir, run_id)
        self._append_jsonl(audit_path, record)

        try:
            self.assembler.handle_event(run_id or "global", capture_id, record, run_dir)
        except Exception as exc:
            LOGGER.debug("Profile assembler failed for event %s: %s", run_id, exc)

    def _resolve_run_directory(self, run_id: Optional[str]) -> Optional[Path]:
        if not run_id:
            return None
        try:
            candidate = Path(get_wd(run_id))
        except Exception as exc:
            LOGGER.debug("Failed to resolve working directory for %s: %s", run_id, exc)
            return None
        if candidate.exists():
            return candidate
        return None

    def _audit_log_path(self, run_dir: Optional[Path], run_id: Optional[str]) -> Path:
        if run_dir:
            audit_dir = run_dir / "_logs"
        else:
            safe = sanitise_component(run_id or "global")
            audit_dir = self.fallback_root / safe
        audit_dir.mkdir(parents=True, exist_ok=True)
        return audit_dir / "profile.events.jsonl"

    @staticmethod
    def _append_jsonl(path: Path, record: Dict[str, Any]) -> None:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, separators=(",", ":")) + "\n")


def _default_data_root(app) -> Path:
    raw = app.config.get("PROFILE_DATA_ROOT")
    if not raw:
        raw = "/workdir/wepppy-test-engine-data"
    return Path(raw)


def _default_fallback_root(app) -> Path:
    raw = app.config.get("PROFILE_RECORDER_GLOBAL_ROOT")
    if raw:
        return Path(raw)
    return _default_data_root(app) / "audit"


def get_profile_recorder(app) -> ProfileRecorder:
    """Return (creating if needed) the ProfileRecorder bound to the Flask app."""

    extensions = getattr(app, "extensions", None)
    if extensions is None:
        extensions = {}
        app.extensions = extensions  # type: ignore[attr-defined]

    recorder = extensions.get("profile_recorder")
    if recorder is None:
        data_root = _default_data_root(app)
        fallback_root = _default_fallback_root(app)
        recorder = ProfileRecorder(data_repo_root=data_root, fallback_root=fallback_root)
        extensions["profile_recorder"] = recorder

    return recorder
