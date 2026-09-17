from pathlib import Path

__all__ = ["sha256_file"]

def sha256_file(path: str | Path, *, use_cache: bool = True) -> str: ...
