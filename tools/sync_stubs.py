#!/usr/bin/env python3
"""Synchronize .pyi files into the local stubs/ tree for stubtest."""

from __future__ import annotations

import shutil
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[1]
PACKAGE_ROOT = REPO_ROOT / "wepppy"
STUB_ROOT = REPO_ROOT / "stubs" / "wepppy"


def clean_stub_root() -> None:
    if STUB_ROOT.exists():
        shutil.rmtree(STUB_ROOT)
    STUB_ROOT.mkdir(parents=True, exist_ok=True)


def copy_pyi_files() -> None:
    for source in PACKAGE_ROOT.rglob("*.pyi"):
        target = STUB_ROOT / source.relative_to(PACKAGE_ROOT)
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copy2(source, target)


def ensure_markers() -> None:
    # Ensure the runtime package advertises type information.
    (PACKAGE_ROOT / "py.typed").write_text("")
    # Mark the stub tree with a py.typed (useful when packaging separately).
    (STUB_ROOT / "py.typed").write_text("")


def main() -> None:
    clean_stub_root()
    copy_pyi_files()
    ensure_markers()
    print(f"Stub files copied to {STUB_ROOT}")


if __name__ == "__main__":
    main()
