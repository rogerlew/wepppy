#!/usr/bin/env python3
"""Install/check the accidental-loss guard without replacing existing hooks."""
from __future__ import annotations

import argparse
import os
from pathlib import Path
import shlex
import sys

from check_integration_history import IntegrationError, git


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
        hook = common.resolve() / "hooks" / "reference-transaction"
        checker = Path(__file__).resolve().with_name("check_integration_history.py")
        content = ("#!/bin/sh\n# wepppy integration history guard v1\nexec "
                   + shlex.quote(sys.executable) + " " + shlex.quote(str(checker))
                   + ' reference-transaction "$@"\n')
        if hook.exists() or hook.is_symlink():
            if hook.is_symlink() or hook.read_text() != content or not os.access(hook, os.X_OK):
                raise IntegrationError("HOOK_CONFLICT: existing hook left unchanged")
        elif args.check:
            raise IntegrationError("HOOK_MISSING: integration guard is not installed")
        else:
            hook.parent.mkdir(parents=True, exist_ok=True)
            with hook.open("x") as stream:
                stream.write(content)
            hook.chmod(0o755)
        print(f"integration history guard {'verified' if args.check else 'installed'}: {hook}")
        return 0
    except (IntegrationError, OSError) as exc:
        print(f"hook setup refused: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
