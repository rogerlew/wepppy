from __future__ import annotations

from fnmatch import fnmatch
from pathlib import Path
import shutil
from typing import Dict, List, Tuple

from .docs_contracts import UsersumContracts, UsersumContractsValidationError, VendorSpec


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
            if any(fnmatch(rel, pattern) for pattern in vendor["exclude_globs"]):
                continue
            selected[rel] = candidate

    if not selected:
        raise UsersumContractsValidationError(
            f"Vendor {vendor['vendor_id']!r} include_globs selected no markdown files"
        )
    return [selected[key] for key in sorted(selected)]


def sync_vendor_docs(
    contracts: UsersumContracts,
    *,
    repo_root: Path,
    write: bool,
    clean: bool,
    allow_missing_source_repos: bool = False,
) -> List[Tuple[str, str]]:
    actions: List[Tuple[str, str]] = []

    for vendor_id, vendor in contracts.vendors.items():
        target_root = (repo_root / vendor["target_root"]).resolve()
        source_root = Path(vendor["source_repo_path"]).resolve()
        if allow_missing_source_repos and not source_root.is_dir():
            actions.append(("skip", f"{vendor_id}: source repo path missing ({source_root})"))
            continue

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
