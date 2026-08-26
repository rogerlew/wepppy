#!/usr/bin/env python3
"""Check or rewrite active NoDb config sources to canonical lexical forms."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

REPO_ROOT = Path(__file__).resolve().parents[1]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from wepppy.project_config_serialization import normalize_source_text


def source_paths() -> list[Path]:
    config_root = REPO_ROOT / "wepppy" / "nodb" / "configs"
    return sorted(config_root.glob("*.cfg"))


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true", help="Rewrite noncanonical sources atomically")
    args = parser.parse_args()

    changed: list[Path] = []
    for path in source_paths():
        original = path.read_text(encoding="utf-8")
        normalized = normalize_source_text(original)
        if normalized == original:
            continue
        changed.append(path)
        if args.write:
            temporary = path.with_name(f".{path.name}.wp00b.tmp")
            temporary.write_text(normalized, encoding="utf-8", newline="\n")
            temporary.replace(path)
    if changed and not args.write:
        for path in changed:
            print(path.relative_to(REPO_ROOT))
        print(f"project-config source normalization required: {len(changed)} file(s)")
        return 1
    action = "normalized" if args.write else "validated"
    print(f"project-config sources {action}: {len(source_paths())} file(s); changed={len(changed)}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
