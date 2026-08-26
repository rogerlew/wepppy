from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Mapping
from wepppy.project_config_serialization import CanonicalValue

__all__ = ["PRESET_WRITER_FLAG", "PresetPolicy", "PresetPolicyError", "PresetSnapshotCandidate", "PresetSnapshotError", "load_preset_policies", "materialize_preset_snapshot", "preset_writer_enabled", "resolve_preset_snapshot"]
PRESET_WRITER_FLAG: str

class PresetPolicyError(ValueError): ...
class PresetSnapshotError(ValueError): ...

@dataclass(frozen=True, slots=True)
class PresetPolicy:
    preset_id: str
    overrides: tuple[str, ...]

@dataclass(frozen=True, slots=True)
class PresetSnapshotCandidate:
    preset_id: str
    config_filename: str
    config_bytes: bytes
    manifest_bytes: bytes
    normalized_overrides: Mapping[str, CanonicalValue]
    source_revision: str

def preset_writer_enabled(environ: Mapping[str, str] | None = ...) -> bool: ...
def load_preset_policies(policies_path: str | Path = ..., *, configs_root: str | Path = ...) -> Mapping[str, PresetPolicy]: ...
def resolve_preset_snapshot(preset_id: str, overrides: Mapping[str, object], *, source_revision: str, resolved_at: datetime | None = ..., configs_root: str | Path = ..., policies: Mapping[str, PresetPolicy] | None = ...) -> PresetSnapshotCandidate: ...
def materialize_preset_snapshot(working_directory: str | Path, candidate: PresetSnapshotCandidate) -> tuple[Path, Path]: ...
