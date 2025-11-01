from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, Optional

from wepppy.weppcloud.utils.helpers import get_wd

from .assembler import ProfileAssembler
from .config import RecorderConfig, resolve_recorder_config
from .utils import sanitise_component

LOGGER = logging.getLogger(__name__)


class ProfileRecorder:
    """Persist recorder events to per-run audit logs and forward them to the assembler."""

    def __init__(self, *, config: RecorderConfig) -> None:
        self.config = config
        self.assembler = ProfileAssembler(self.config.data_repo_root)

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

        if self.config.assembler_enabled:
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
        try:
            candidate.mkdir(parents=True, exist_ok=True)
        except Exception as exc:
            LOGGER.debug("Failed to ensure working directory exists for %s: %s", run_id, exc)
        return candidate

    def _audit_log_path(self, run_dir: Optional[Path], run_id: Optional[str]) -> Path:
        if run_dir is not None:
            audit_dir = run_dir / "_logs"
        else:
            safe = sanitise_component(run_id or "global")
            audit_dir = self.config.data_repo_root / "audit" / safe
        audit_dir.mkdir(parents=True, exist_ok=True)
        return audit_dir / "profile.events.jsonl"

    @staticmethod
    def _append_jsonl(path: Path, record: Dict[str, Any]) -> None:
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, separators=(",", ":")) + "\n")


def get_profile_recorder(app) -> ProfileRecorder:
    """Return (creating if needed) the ProfileRecorder bound to the Flask app."""

    extensions = getattr(app, "extensions", None)
    if extensions is None:
        extensions = {}
        app.extensions = extensions  # type: ignore[attr-defined]

    recorder = extensions.get("profile_recorder")
    if recorder is None:
        recorder = ProfileRecorder(config=resolve_recorder_config(app))
        extensions["profile_recorder"] = recorder

    return recorder
