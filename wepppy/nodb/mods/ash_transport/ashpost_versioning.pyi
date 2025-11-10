from __future__ import annotations

from pathlib import Path
from typing import Optional

import pyarrow as pa

from wepppy.wepp.interchange.versioning import Version

MANIFEST_FILENAME: str
ASHPOST_VERSION: Version

def manifest_path(ash_post_dir: Path) -> Path: ...

def schema_with_version(schema: pa.Schema, *, version: Version = ...) -> pa.Schema: ...

def write_version_manifest(ash_post_dir: Path, *, version: Version = ...) -> Path: ...

def read_version_manifest(ash_post_dir: Path) -> Optional[Version]: ...

def needs_major_refresh(ash_post_dir: Path, *, version: Version = ...) -> bool: ...

def remove_incompatible_outputs(ash_post_dir: Path, *, version: Version = ...) -> bool: ...
