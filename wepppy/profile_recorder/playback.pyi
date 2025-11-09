from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import requests

Event = Dict[str, object]


class SandboxViolationError(RuntimeError): ...


class PlaybackSession:
    profile_root: Path
    execute: bool
    base_url: str

    def __init__(
        self,
        profile_root: Path,
        *,
        base_url: str,
        execute: bool = ...,
        run_dir: Optional[Path] = ...,
        session: Optional[requests.Session] = ...,
        verbose: bool = ...,
        logger: Optional[logging.Logger] = ...,
        playback_run_id: Optional[str] = ...,
    ) -> None: ...
    def run(self) -> None: ...
    def report(self) -> str: ...


def main(argv: Optional[List[str]] = ...) -> int: ...
