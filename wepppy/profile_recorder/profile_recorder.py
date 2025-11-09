from __future__ import annotations

"""Profile recorder entry points used by WEPPcloud Flask routes."""

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import TYPE_CHECKING, Any, Dict, Iterable, Optional

from wepppy.weppcloud.utils.helpers import get_wd

from .assembler import ProfileAssembler
from .config import RecorderConfig, resolve_recorder_config
from .utils import sanitise_component

if TYPE_CHECKING:
    from flask import Flask

EventPayload = Dict[str, Any]
FileHintMap = Dict[str, Path]

LOGGER = logging.getLogger(__name__)

KNOWN_FILE_KEYS: Iterable[str] = (
    "files_created",
    "files_removed",
    "output_files",
    "output_path",
    "input_files",
    "upload_files",
)


class ProfileRecorder:
    """Persist recorder events to per-run audit logs and forward them to the assembler."""

    def __init__(self, *, config: RecorderConfig) -> None:
        """Initialize the recorder and its assembler helper.

        Args:
            config: Runtime configuration that points to the data repository root.
        """
        self.config = config
        self.assembler = ProfileAssembler(self.config.data_repo_root)

    def append_event(
        self,
        event: EventPayload,
        *,
        user: Any = None,
        assembler_override: Optional[bool] = None,
    ) -> None:
        """Write a recorder event and optionally dispatch it to the assembler.

        Args:
            event: Arbitrary JSON-like payload emitted by the recorder routes.
            user: Optional Flask user object; metadata is copied when authenticated.
            assembler_override: Force-enable/disable assembler handling when set.
        """
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

        assembler_enabled = (
            self.config.assembler_enabled
            if assembler_override is None
            else assembler_override
        )

        if assembler_enabled:
            file_hints = self._extract_file_candidates(record, run_dir)
            try:
                self.assembler.handle_event(
                    run_id or "global",
                    capture_id,
                    record,
                    run_dir,
                    file_hints=file_hints,
                )
            except Exception as exc:
                LOGGER.debug("Profile assembler failed for event %s: %s", run_id, exc)

    def _resolve_run_directory(self, run_id: Optional[str]) -> Optional[Path]:
        """Return (and create if needed) the working directory for the given run."""
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
        """Return the JSONL audit log path for the run or a global fallback."""
        if run_dir is not None:
            audit_dir = run_dir / "_logs"
        else:
            safe = sanitise_component(run_id or "global")
            audit_dir = self.config.data_repo_root / "audit" / safe
        audit_dir.mkdir(parents=True, exist_ok=True)
        return audit_dir / "profile.events.jsonl"

    def _extract_file_candidates(
        self,
        event: EventPayload,
        run_dir: Optional[Path],
    ) -> FileHintMap:
        """Inspect an event for run-relative file references."""
        if not run_dir:
            return {}

        candidates: FileHintMap = {}
        for key in KNOWN_FILE_KEYS:
            if key not in event:
                continue
            raw = event[key]
            if raw is None:
                continue

            if isinstance(raw, str):
                self._maybe_add_candidate(candidates, key, run_dir, raw)
            elif isinstance(raw, (list, tuple, set)):
                for idx, entry in enumerate(raw):
                    self._maybe_add_candidate(candidates, f"{key}[{idx}]", run_dir, entry)
            elif isinstance(raw, dict):
                for subkey, entry in raw.items():
                    self._maybe_add_candidate(candidates, f"{key}.{subkey}", run_dir, entry)
        return candidates

    @staticmethod
    def _maybe_add_candidate(
        bucket: Dict[str, Path],
        label: str,
        run_dir: Path,
        entry: Any,
    ) -> None:
        """Record a file candidate when the payload looks like a path."""
        if not entry or not isinstance(entry, str):
            return
        candidate = Path(entry)
        if not candidate.is_absolute():
            candidate = run_dir / candidate
        bucket[label] = candidate

    @staticmethod
    def _append_jsonl(path: Path, record: EventPayload) -> None:
        """Append a serialized event to the JSONL audit log."""
        with path.open("a", encoding="utf-8") as handle:
            handle.write(json.dumps(record, separators=(",", ":")) + "\n")


def get_profile_recorder(app: Flask) -> ProfileRecorder:
    """Return (creating if needed) the :class:`ProfileRecorder` bound to the Flask app."""

    extensions = getattr(app, "extensions", None)
    if extensions is None:
        extensions = {}
        app.extensions = extensions  # type: ignore[attr-defined]

    recorder = extensions.get("profile_recorder")
    if recorder is None:
        recorder = ProfileRecorder(config=resolve_recorder_config(app))
        extensions["profile_recorder"] = recorder

    return recorder
