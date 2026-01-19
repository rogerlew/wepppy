from __future__ import annotations

from pathlib import Path
from typing import List, Tuple


ASH_POST_DOC_ORDER: List[Tuple[str, str]]
MAX_SAMPLE_ROWS: int

def generate_ashpost_documentation(ash_post_dir: Path | str, to_readme_md: bool = ...) -> str: ...
