#!/usr/bin/env python3
from __future__ import annotations

import argparse
from pathlib import Path

from wepppy.weppcloud.usersum_docs.docs_contracts import (
    load_and_validate_contracts,
)
from wepppy.weppcloud.usersum_docs.docs_index import build_generated_index, write_generated_index
from wepppy.weppcloud.usersum_docs.vendor_sync import sync_vendor_docs


REPO_ROOT = Path(__file__).resolve().parents[1]
USERSUM_DIR = REPO_ROOT / "wepppy" / "weppcloud" / "routes" / "usersum"
GENERATED_INDEX_PATH = USERSUM_DIR / "generated" / "docs_index.json"


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
    actions = sync_vendor_docs(
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
    contracts_for_sync = load_and_validate_contracts(
        base_dir=USERSUM_DIR,
        repo_root=REPO_ROOT,
        require_local_files=True,
        require_vendor_files=False,
    )
    if not args.skip_vendor_sync:
        sync_actions = sync_vendor_docs(
            contracts_for_sync,
            repo_root=REPO_ROOT,
            write=args.write,
            clean=False,
            allow_missing_source_repos=True,
        )
        for action, detail in sync_actions:
            prefix = "[WRITE]" if args.write else "[DRYRUN]"
            print(f"{prefix} {action}: {detail}")

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
    build_parser_cmd.add_argument(
        "--skip-vendor-sync",
        action="store_true",
        help="Skip automatic vendor sync that runs before index generation.",
    )
    build_parser_cmd.set_defaults(func=cmd_build_index)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()
    return int(args.func(args))


if __name__ == "__main__":
    raise SystemExit(main())
