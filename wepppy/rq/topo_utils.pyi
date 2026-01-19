from __future__ import annotations

from pathlib import Path


def _prune_stream_order(
    flovec_path: Path,
    netful_path: Path,
    passes: int,
    *,
    overwrite_netful: bool = ...,
) -> None: ...


__all__ = ["_prune_stream_order"]
