#!/usr/bin/env python3
"""Install/check a stable accidental-loss guard without replacing existing hooks."""
from __future__ import annotations

import argparse
import hashlib
import os
from pathlib import Path
import shlex
import sys
import tempfile

from check_integration_history import IntegrationError, git


INSTALLED_CHECKER = "wepppy-integration-history-v1.py"


def verify_existing(path: Path, content: bytes, *, executable: bool) -> bool:
    if not path.exists() and not path.is_symlink():
        return False
    if (path.is_symlink() or not path.is_file() or path.read_bytes() != content
            or (executable and not os.access(path, os.X_OK))):
        raise IntegrationError(
            f"HOOK_CONFLICT: {path.name} left unchanged; review and back up the "
            "installed guard before an operator removes its owned files and reinstalls"
        )
    return True


def install_file(path: Path, content: bytes, mode: int) -> None:
    """Publish complete content without replacing even a concurrent installer."""
    descriptor, temporary = tempfile.mkstemp(prefix=".integration-hook-", dir=path.parent)
    try:
        with os.fdopen(descriptor, "wb") as stream:
            stream.write(content)
            stream.flush()
            os.fsync(stream.fileno())
        os.chmod(temporary, mode)
        os.link(temporary, path)
        directory = os.open(path.parent, os.O_RDONLY | os.O_DIRECTORY)
        try:
            os.fsync(directory)
        finally:
            os.close(directory)
    finally:
        os.unlink(temporary)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--repo", type=Path, default=Path.cwd())
    parser.add_argument("--check", action="store_true")
    args = parser.parse_args()
    try:
        repo = args.repo.resolve()
        configured = git(repo, "config", "--get", "core.hooksPath", allowed=(0, 1))
        if configured:
            raise IntegrationError("CUSTOM_HOOKS_PATH: preserve existing manager; integrate guard explicitly")
        common = Path(git(repo, "rev-parse", "--git-common-dir"))
        if not common.is_absolute():
            common = repo / common
        hooks = common.resolve() / "hooks"
        hook = hooks / "reference-transaction"
        installed_checker = hooks / INSTALLED_CHECKER
        source = Path(__file__).resolve().with_name("check_integration_history.py").read_bytes()
        digest = hashlib.sha256(source).hexdigest()
        content = ("#!/bin/sh\n# wepppy integration history guard v2\n"
                   + f"# installed checker sha256: {digest}\nexec "
                   + shlex.quote(sys.executable) + " " + shlex.quote(str(installed_checker))
                   + ' reference-transaction "$@"\n').encode()
        # Inspect both destinations before mutating either. Never overwrite LFS,
        # another hook manager, or a previously installed different revision.
        has_hook = verify_existing(hook, content, executable=True)
        has_checker = verify_existing(installed_checker, source, executable=False)
        if args.check and not (has_hook and has_checker):
            raise IntegrationError("HOOK_MISSING: stable integration guard is not fully installed")
        if not args.check:
            hooks.mkdir(parents=True, exist_ok=True)
            if not has_checker:
                install_file(installed_checker, source, 0o644)
            if not has_hook:
                install_file(hook, content, 0o755)
        print(f"integration history guard {'verified' if args.check else 'installed'}: "
              f"{hook}; checker sha256={digest}")
        return 0
    except (IntegrationError, OSError) as exc:
        print(f"hook setup refused: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
