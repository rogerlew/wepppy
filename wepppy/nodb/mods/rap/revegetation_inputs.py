"""Publish RAP activation records without losing prior executable evidence."""
from __future__ import annotations

from contextlib import contextmanager
import os
import re
from pathlib import Path
import stat
from uuid import uuid4


def publish_revegetation_input(runs_dir: str, name: str, content: str | None) -> None:
    """Retire changed regular files visibly; never truncate linked source files."""
    if (name not in {"cancov.txt", "simfire.txt", "firedate.txt"}
            and re.fullmatch(r"p[0-9]+\.cov", name) is None):
        raise ValueError(f"Unsupported revegetation input: {name!r}")
    root = Path(runs_dir)
    target = root / name
    try:
        mode = target.lstat().st_mode
    except FileNotFoundError:
        prior = None
        file_mode = 0o666
    else:
        if not stat.S_ISREG(mode):
            raise ValueError(f"Revegetation input must be a regular file: {target}")
        file_mode = stat.S_IMODE(mode)
        prior = target.read_bytes()
    desired = None if content is None else content.encode("utf-8")
    if prior == desired:
        return
    if prior is not None:
        history = root / f"revegetation-input-{uuid4().hex}"
        history.mkdir()  # exclusive fresh directory, never follows an existing link
        os.replace(target, history / name)
    if desired is not None:
        attempt = root / f"{name}.revegetation-{uuid4().hex}.tmp"
        fd = os.open(attempt, os.O_WRONLY | os.O_CREAT | os.O_EXCL, file_mode)
        with os.fdopen(fd, "wb") as stream:
            if prior is not None:
                os.fchmod(stream.fileno(), file_mode)
            stream.write(desired)
        os.replace(attempt, target)


@contextmanager
def cover_output(runs_dir: str, name: str):
    """Keep interrupted cover writes visible and publish only a completed record."""
    if re.fullmatch(r"p[0-9]+\.cov", name) is None:
        raise ValueError(f"Unsupported cover input: {name!r}")
    target = Path(runs_dir) / name
    try:
        mode = target.lstat().st_mode
    except FileNotFoundError:
        file_mode = 0o666
    else:
        if not stat.S_ISREG(mode):
            raise ValueError(f"Cover input must be a regular file: {target}")
        file_mode = stat.S_IMODE(mode)
    attempt = Path(runs_dir) / f"{name}.revegetation-{uuid4().hex}.tmp"
    fd = os.open(attempt, os.O_WRONLY | os.O_CREAT | os.O_EXCL, file_mode)
    with os.fdopen(fd, "w", encoding="utf-8") as stream:
        yield stream
    publish_revegetation_input(runs_dir, name, attempt.read_text(encoding="utf-8"))
    attempt.unlink()  # redundant successful copy only; failures retain their attempt
