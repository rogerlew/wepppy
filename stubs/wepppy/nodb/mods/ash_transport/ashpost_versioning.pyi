from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

import logging

from wepppy.wepp.interchange.versioning import Version

LOGGER: logging.Logger
MANIFEST_FILENAME: str
ASHPOST_VERSION: Version

def manifest_path(ash_post_dir: Path) -> Path: ...

def schema_with_version(schema: Any, *, version: Version = ...) -> Any: ...

def write_version_manifest(ash_post_dir: Path, *, version: Version = ...) -> Path: ...

def read_version_manifest(ash_post_dir: Path) -> Optional[Version]: ...

def needs_major_refresh(ash_post_dir: Path, *, version: Version = ...) -> bool: ...

def remove_incompatible_outputs(ash_post_dir: Path, *, version: Version = ...) -> bool: ...
