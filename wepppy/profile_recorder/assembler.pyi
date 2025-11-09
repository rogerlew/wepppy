from __future__ import annotations

import logging
from pathlib import Path
from typing import Any, Dict, Optional

LOGGER: logging.Logger
TASK_RULES: Dict[str, Dict[str, Any]]


class ProfileAssembler:
    data_repo_root: Path

    def __init__(self, data_repo_root: Path) -> None: ...
    def handle_event(
        self,
        run_id: str,
        capture_id: Optional[str],
        event: Dict[str, Any],
        run_dir: Optional[Path],
        *,
        file_hints: Optional[Dict[str, Path]] = ...,
    ) -> None: ...
    def promote_draft(
        self,
        run_id: str,
        capture_id: str = ...,
        *,
        slug: Optional[str] = ...,
    ) -> Dict[str, str]: ...
