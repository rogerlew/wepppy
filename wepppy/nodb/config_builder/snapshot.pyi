from dataclasses import dataclass
from datetime import datetime
from typing import Mapping
from .schema import BuilderSelections, Registry, ResolvedBuilderConfig
from wepppy.nodb.project_config_snapshot import PresetSnapshotCandidate
__all__ = ["BUILDER_WRITER_FLAG", "BuilderCandidate", "builder_writer_enabled", "parse_builder_selections", "resolve_builder_candidate"]
BUILDER_WRITER_FLAG: str
@dataclass(frozen=True)
class BuilderCandidate:
    resolved: ResolvedBuilderConfig
    artifact: PresetSnapshotCandidate
    review: Mapping[str, object]
def builder_writer_enabled(environ: Mapping[str, str] | None = ...) -> bool: ...
def parse_builder_selections(payload: object) -> BuilderSelections: ...
def resolve_builder_candidate(selections: BuilderSelections, *, registry: Registry | None = ..., resolved_at: datetime | None = ...) -> BuilderCandidate: ...
