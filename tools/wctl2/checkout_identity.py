"""Require test execution to see the caller's live checkout mount.

A random, short-lived file proves shared source visibility without hashing large
repositories. This includes dirty and untracked source; copied checkouts are not
accepted. It does not freeze files against concurrent edits during a test run.
"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import secrets
import shlex
import tempfile
from typing import Iterator


_CONTAINER_CHECK = """import pathlib, sys
probe = pathlib.Path('/workdir/wepppy') / sys.argv[1]
try:
    matches = probe.read_text(encoding='ascii') == sys.argv[2]
except OSError:
    matches = False
if not matches:
    print('WCTL_CHECKOUT_MISMATCH: container /workdir/wepppy is not the requested '
          'live checkout. Mount the requested checkout before testing, or invoke '
          'wctl from the checkout already mounted. No tests were started.', file=sys.stderr)
    raise SystemExit(2)
"""


def requested_checkout(project_dir: Path, caller_cwd: str | None, *, explicit: bool) -> Path:
    """Use explicit project selection, then caller's WEPPpy tree, then preset."""
    if explicit:
        return project_dir.resolve()
    caller = Path(caller_cwd).resolve() if caller_cwd else Path.cwd().resolve()
    for candidate in (caller, *caller.parents):
        if (candidate / "tools/wctl2/__main__.py").is_file() and (candidate / "docker/defaults.env").is_file():
            return candidate
    return project_dir.resolve()


@contextmanager
def checked_test_command(project_dir: Path, command: str) -> Iterator[str]:
    """Keep a readable mount probe alive until the container command returns."""
    token = secrets.token_hex(32)
    probe: Path | None = None
    try:
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="ascii", prefix=".wctl-checkout-", dir=project_dir, delete=False,
        ) as handle:
            probe = Path(handle.name)
            handle.write(token)
        # The nonce grants no authority and contains no user data. Test containers
        # may use a different UID or a read-only mount; they only need read access.
        probe.chmod(0o644)
        check = shlex.join([
            "/opt/venv/bin/python", "-c", _CONTAINER_CHECK, probe.name, token,
        ])
        yield f"{check} && {command}"
    finally:
        if probe is not None:
            probe.unlink(missing_ok=True)
