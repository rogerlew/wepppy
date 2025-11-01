from __future__ import annotations

import json
import logging
from pathlib import Path
from typing import Any, Dict, Optional

from .utils import sanitise_component

LOGGER = logging.getLogger(__name__)


class ProfileAssembler:
    """
    Streaming assembler stub.

    Observes recorder events and mirrors them into the profile data repository.
    The initial implementation simply appends events to a draft log so that no
    information is lost before full assembly logic lands.
    """

    def __init__(self, data_repo_root: Path) -> None:
        self.data_repo_root = Path(data_repo_root)

    def handle_event(
        self,
        run_id: str,
        capture_id: Optional[str],
        event: Dict[str, Any],
        run_dir: Optional[Path],
    ) -> None:
        try:
            run_key = sanitise_component(run_id or "global")
            capture_key = sanitise_component(capture_id or "stream")
            draft_root = self.data_repo_root / "profiles" / "_drafts" / run_key / capture_key
            draft_root.mkdir(parents=True, exist_ok=True)
            events_path = draft_root / "events.jsonl"
            with events_path.open("a", encoding="utf-8") as handle:
                handle.write(json.dumps(event, separators=(",", ":")) + "\n")

            if run_dir:
                pointer_path = draft_root / "run_dir.txt"
                if not pointer_path.exists():
                    pointer_path.write_text(str(run_dir), encoding="utf-8")
        except Exception as exc:
            LOGGER.debug("ProfileAssembler handle_event encountered an error: %s", exc)
