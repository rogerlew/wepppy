#!/usr/bin/env python3
"""Convert legacy watershed structure.pkl files to structure.json."""

from __future__ import annotations

import argparse
import json
import os
import pickle
import sys
from pathlib import Path
from typing import Iterable, List


def _iter_structure_pickles(root: Path) -> Iterable[Path]:
    if not root.exists():
        return
    for path in root.rglob("structure.pkl"):
        if not path.is_file():
            continue
        if path.parent.name != "watershed":
            continue
        yield path


def _normalize_structure(obj: object) -> List[List[int]]:
    if not isinstance(obj, list):
        raise ValueError("structure.pkl must contain a list of rows")
    structure: List[List[int]] = []
    for row in obj:
        if not isinstance(row, (list, tuple)):
            raise ValueError("structure.pkl rows must be lists")
        structure.append([int(value) for value in row])
    return structure


def _write_json(path: Path, payload: List[List[int]]) -> None:
    tmp_path = path.with_suffix(".json.tmp")
    with open(tmp_path, "w", encoding="utf-8") as handle:
        json.dump(payload, handle)
    os.replace(tmp_path, path)


def _update_watershed_nodb(run_root: Path, structure_json: Path, *, dry_run: bool) -> bool:
    nodb_path = run_root / "watershed.nodb"
    if not nodb_path.exists():
        return False
    try:
        with open(nodb_path, "r", encoding="utf-8") as handle:
            data = json.load(handle)
    except (OSError, json.JSONDecodeError):
        return False

    state = data.get("py/state", data)
    if not isinstance(state, dict):
        return False

    structure_ref = state.get("_structure")
    structure_json_str = str(structure_json)
    if structure_ref == structure_json_str:
        return False

    state["_structure"] = structure_json_str
    if dry_run:
        return True

    with open(nodb_path, "w", encoding="utf-8") as handle:
        json.dump(data, handle, indent=2)
    return True


def _convert_pickle(
    pickle_path: Path,
    *,
    dry_run: bool,
    force: bool,
    delete_pickle: bool,
    update_nodb: bool,
    verbose: bool,
) -> tuple[bool, bool]:
    structure_json = pickle_path.with_suffix(".json")
    if structure_json.exists() and not force:
        return False, False

    if verbose:
        print(f"Converting {pickle_path}")

    if dry_run:
        return True, update_nodb

    with open(pickle_path, "rb") as handle:
        structure_obj = pickle.load(handle)

    structure = _normalize_structure(structure_obj)
    _write_json(structure_json, structure)

    if update_nodb:
        _update_watershed_nodb(pickle_path.parent.parent, structure_json, dry_run=dry_run)

    if delete_pickle:
        pickle_path.unlink(missing_ok=True)

    return True, update_nodb


def _cleanup_legacy_pickle(
    pickle_path: Path,
    *,
    dry_run: bool,
    verbose: bool,
) -> bool:
    if verbose:
        print(f"Removing {pickle_path}")
    if dry_run:
        return True
    pickle_path.unlink(missing_ok=True)
    return True


def _default_roots() -> list[Path]:
    candidates = [
        Path("/geodata/weppcloud_runs"),
        Path("/wc1/runs"),
        Path("/geodata/wc1/runs"),
    ]
    return [path for path in candidates if path.exists()]


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Convert watershed/structure.pkl to structure.json."
    )
    parser.add_argument(
        "--roots",
        nargs="*",
        type=Path,
        default=None,
        help="Root directories to scan (defaults to known run roots).",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Report conversions without writing files.",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Overwrite existing structure.json files.",
    )
    parser.add_argument(
        "--delete-pkl",
        action="store_true",
        help="Delete structure.pkl after successful conversion.",
    )
    parser.add_argument(
        "--cleanup-pkl",
        action="store_true",
        help="Remove structure.pkl without converting (use after conversion).",
    )
    parser.add_argument(
        "--skip-nodb-update",
        action="store_true",
        help="Do not update watershed.nodb _structure pointer.",
    )
    parser.add_argument(
        "--verbose",
        action="store_true",
        help="Print each converted path.",
    )
    args = parser.parse_args()

    roots = args.roots if args.roots else _default_roots()
    if not roots:
        print("No valid roots found; supply --roots explicitly.", file=sys.stderr)
        return 1

    total = 0
    converted = 0
    skipped = 0
    errors = 0

    for root in roots:
        for pickle_path in _iter_structure_pickles(root):
            total += 1
            try:
                if args.cleanup_pkl:
                    _cleanup_legacy_pickle(
                        pickle_path,
                        dry_run=args.dry_run,
                        verbose=args.verbose,
                    )
                    converted += 1
                else:
                    did_convert, _ = _convert_pickle(
                        pickle_path,
                        dry_run=args.dry_run,
                        force=args.force,
                        delete_pickle=args.delete_pkl,
                        update_nodb=not args.skip_nodb_update,
                        verbose=args.verbose,
                    )
                    if did_convert:
                        converted += 1
                    else:
                        skipped += 1
            except Exception as exc:
                errors += 1
                print(f"Failed to convert {pickle_path}: {exc}", file=sys.stderr)

    print(
        "Conversion summary:",
        f"total={total}",
        f"converted={converted}",
        f"skipped={skipped}",
        f"errors={errors}",
        sep=" ",
    )
    return 0 if errors == 0 else 2


if __name__ == "__main__":
    raise SystemExit(main())
