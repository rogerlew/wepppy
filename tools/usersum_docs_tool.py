#!/usr/bin/env python3
from __future__ import annotations

import argparse
from fnmatch import fnmatch
import shutil
from pathlib import Path
from typing import Dict, List, Tuple

from wepppy.weppcloud.usersum_docs.docs_contracts import (
    UsersumContracts,
    UsersumContractsValidationError,
    VendorSpec,
    load_and_validate_contracts,
)
from wepppy.weppcloud.usersum_docs.docs_index import build_generated_index, write_generated_index


REPO_ROOT = Path(__file__).resolve().parents[1]
USERSUM_DIR = REPO_ROOT / "wepppy" / "weppcloud" / "routes" / "usersum"
GENERATED_INDEX_PATH = USERSUM_DIR / "generated" / "docs_index.json"


def _iter_vendor_source_files(vendor: VendorSpec) -> List[Path]:
    source_root = Path(vendor["source_repo_path"]).resolve()
    if not source_root.is_dir():
        raise UsersumContractsValidationError(
            f"Vendor source path does not exist or is not a directory: {source_root}"
        )

    selected: Dict[str, Path] = {}
    for include_glob in vendor["include_globs"]:
        for candidate in source_root.glob(include_glob):
            if not candidate.is_file():
                continue
            rel = candidate.relative_to(source_root).as_posix()
            if candidate.suffix.lower() != ".md":
                raise UsersumContractsValidationError(
                    f"Vendor include matched non-markdown file: {source_root / rel}"
                )
            excluded = any(fnmatch(rel, pattern) for pattern in vendor["exclude_globs"])
            if excluded:
                continue
            selected[rel] = candidate

    if not selected:
        raise UsersumContractsValidationError(
            f"Vendor {vendor['vendor_id']!r} include_globs selected no markdown files"
        )
    return [selected[key] for key in sorted(selected)]


def _sync_vendor_docs(
    contracts: UsersumContracts,
    *,
    repo_root: Path,
    write: bool,
    clean: bool,
) -> List[Tuple[str, str]]:
    actions: List[Tuple[str, str]] = []

    for vendor_id, vendor in contracts.vendors.items():
        target_root = (repo_root / vendor["target_root"]).resolve()
        source_root = Path(vendor["source_repo_path"]).resolve()
        source_files = _iter_vendor_source_files(vendor)

        if write and clean and target_root.exists():
            shutil.rmtree(target_root)
            actions.append(("clean", str(target_root)))

        for source_file in source_files:
            rel_path = source_file.relative_to(source_root)
            target_path = target_root / rel_path
            actions.append(("copy", f"{source_file} -> {target_path}"))
            if write:
                target_path.parent.mkdir(parents=True, exist_ok=True)
                shutil.copy2(source_file, target_path)

        actions.append(("vendor", f"{vendor_id}: {len(source_files)} file(s)"))

    return actions


def cmd_validate(args: argparse.Namespace) -> int:
    contracts = load_and_validate_contracts(
        base_dir=USERSUM_DIR,
        repo_root=REPO_ROOT,
        require_local_files=True,
        require_vendor_files=args.require_vendor_files,
    )
    print(
        f"OK: manifest/nav/vendors validated. "
        f"docs={len(contracts.docs)}, nav_leaves={len(contracts.nav_key_to_doc_id)}, vendors={len(contracts.vendors)}"
    )
    return 0


def cmd_sync_vendors(args: argparse.Namespace) -> int:
    contracts = load_and_validate_contracts(
        base_dir=USERSUM_DIR,
        repo_root=REPO_ROOT,
        require_local_files=True,
        require_vendor_files=False,
    )
    actions = _sync_vendor_docs(
        contracts,
        repo_root=REPO_ROOT,
        write=args.write,
        clean=not args.no_clean,
    )
    for action, detail in actions:
        prefix = "[WRITE]" if args.write else "[DRYRUN]"
        print(f"{prefix} {action}: {detail}")
    return 0


def cmd_build_index(args: argparse.Namespace) -> int:
    contracts = load_and_validate_contracts(
        base_dir=USERSUM_DIR,
        repo_root=REPO_ROOT,
        require_local_files=True,
        require_vendor_files=args.require_vendor_files,
    )
    index = build_generated_index(contracts, repo_root=REPO_ROOT)

    if args.write:
        write_generated_index(index, GENERATED_INDEX_PATH)
        print(f"Wrote generated index: {GENERATED_INDEX_PATH}")
    else:
        print(
            f"[DRYRUN] Would write generated index: {GENERATED_INDEX_PATH} "
            f"(documents={len(index.documents)})"
        )
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Usersum docs contracts and index tooling.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    validate_parser = subparsers.add_parser(
        "validate", help="Validate docs_manifest/nav_tree/vendors contracts."
    )
    validate_parser.add_argument(
        "--require-vendor-files",
        action="store_true",
        help="Require vendored markdown files referenced in manifest to exist on disk.",
    )
    validate_parser.set_defaults(func=cmd_validate)

    sync_parser = subparsers.add_parser(
        "sync-vendors",
        help="Sync vendor markdown from configured source repos into usersum/vendor.",
    )
    sync_parser.add_argument(
        "--write",
        action="store_true",
        help="Apply filesystem changes. Without this flag, run in dry-run mode.",
    )
    sync_parser.add_argument(
        "--no-clean",
        action="store_true",
        help="Do not delete existing vendor target root before syncing.",
    )
    sync_parser.set_defaults(func=cmd_sync_vendors)

    build_parser_cmd = subparsers.add_parser(
        "build-index",
        help="Build generated usersum docs index from contracts and markdown content.",
    )
    build_parser_cmd.add_argument(
        "--write",
        action="store_true",
        help="Write generated index file. Without this flag, run in dry-run mode.",
    )
    build_parser_cmd.add_argument(
        "--require-vendor-files",
        action="store_true",
        help="Require vendored markdown files to exist when building index.",
    )
    build_parser_cmd.set_defaults(func=cmd_build_index)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
