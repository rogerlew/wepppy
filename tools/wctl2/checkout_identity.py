"""Require test execution to see the caller's live checkout mount.

A random, short-lived file proves shared source visibility without hashing large
repositories. This includes dirty and untracked source; copied checkouts are not
accepted. It does not freeze files against concurrent edits during a test run.
"""
from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
import os
import secrets
import shlex
import subprocess
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
          'wctl from the checkout already mounted. For an isolated worktree use '
          'wctl run-pytest-worktree --checkout PATH. No tests were started.', file=sys.stderr)
    raise SystemExit(2)
"""


_CHECKOUT_MARKERS = {"tools/wctl2/__main__.py", "docker/defaults.env"}


def _tracked_checkout_markers(candidate: Path) -> bool:
    # Caller selection is local/read-only. Ambient Git settings from a different
    # checkout must not redirect this lookup, and no optional index write is needed.
    env = {key: value for key, value in os.environ.items() if not key.startswith("GIT_")}
    env.update(GIT_OPTIONAL_LOCKS="0", GIT_NO_REPLACE_OBJECTS="1")

    def inspect(*args: str, allowed: tuple[int, ...] = (0,)) -> str:
        try:
            result = subprocess.run(
                ["git", "-C", str(candidate), *args], env=env,
                capture_output=True, text=True, timeout=10,
            )
        except subprocess.TimeoutExpired:
            raise OSError(f"Caller checkout inspection timed out at {candidate}") from None
        if result.returncode not in allowed:
            raise OSError(f"Cannot inspect caller Git checkout at {candidate}; verify its Git metadata")
        return result.stdout

    paths = sorted(_CHECKOUT_MARKERS)
    indexed = set(inspect("ls-files", "--cached", "-z", "--", *paths).split("\0"))
    if _CHECKOUT_MARKERS <= indexed:
        return True
    # A staged deletion must not disguise the caller as an unrelated repository.
    # An unborn unrelated repository has no HEAD and remains a valid fallback.
    head = inspect("rev-parse", "--verify", "--quiet", "HEAD", allowed=(0, 1)).strip()
    if not head:
        return False
    committed = set(inspect("ls-tree", "-r", "--name-only", "-z", head, "--", *paths).split("\0"))
    return _CHECKOUT_MARKERS <= committed


def requested_checkout(project_dir: Path, caller_cwd: str | None, *, explicit: bool) -> Path:
    """Use explicit project selection, then caller's WEPPpy tree, then preset."""
    if explicit:
        return project_dir.resolve()
    caller = Path(caller_cwd).resolve() if caller_cwd else Path.cwd().resolve()
    for candidate in (caller, *caller.parents):
        if all((candidate / marker).is_file() for marker in _CHECKOUT_MARKERS):
            return candidate
        if (candidate / ".git").exists():
            if _tracked_checkout_markers(candidate):
                return candidate
            # Do not walk through a different repository into an enclosing tree.
            break
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
