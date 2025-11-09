from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Any, Mapping, Protocol


class _ConfiguredApp(Protocol):
    config: Mapping[str, Any]


@dataclass(frozen=True)
class RecorderConfig:
    data_repo_root: Path
    assembler_enabled: bool


def resolve_recorder_config(app: _ConfiguredApp) -> RecorderConfig: ...
