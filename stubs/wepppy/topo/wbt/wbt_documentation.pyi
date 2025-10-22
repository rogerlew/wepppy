from __future__ import annotations

from pathlib import Path
from typing import Mapping, Optional, Tuple

class ResourceDefinition:
    filename: str
    summary: str
    description: str
    units: str
    tool: str
    notes: Optional[str]
    inputs: Tuple[str, ...]

def generate_wbt_documentation(
    workspace: Path | str,
    *,
    context: Optional[Mapping[str, object]] = ...,
    to_readme_md: bool = ...,
    readme_name: str = ...,
) -> str: ...
