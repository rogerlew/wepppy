from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class RecorderConfig:
    data_repo_root: Path
    assembler_enabled: bool


def resolve_recorder_config(app) -> RecorderConfig:
    data_root = app.config.get("PROFILE_DATA_ROOT")
    if not data_root:
        data_root = "/workdir/wepppy-test-engine-data"
    assembler_enabled = app.config.get("PROFILE_RECORDER_ASSEMBLER_ENABLED", True)
    return RecorderConfig(Path(data_root), assembler_enabled)
