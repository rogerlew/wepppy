from __future__ import annotations

from pathlib import Path

import pytest

from wepppy.weppcloud.usersum_docs.docs_contracts import (
    UsersumContractsValidationError,
    load_and_validate_contracts,
)


pytestmark = pytest.mark.routes


def _write_contracts(
    base_dir: Path,
    *,
    manifest_doc_id: str = "docs.sample",
    manifest_nav_key: str = "docs.sample",
    nav_doc_id: str = "docs.sample",
    extra_manifest_doc: str = "",
    vendors_yaml: str | None = None,
) -> None:
    base_dir.mkdir(parents=True, exist_ok=True)

    (base_dir / "docs_manifest.yaml").write_text(
        (
            "version: 1\n"
            "docs:\n"
            f"  - doc_id: {manifest_doc_id}\n"
            "    source: local\n"
            "    rel_path: docs/sample.md\n"
            "    title: Sample Doc\n"
            "    min_role: user\n"
            "    category: sample\n"
            "    audience_tags: [user]\n"
            "    status: active\n"
            f"    nav_key: {manifest_nav_key}\n"
            f"{extra_manifest_doc}"
        ),
        encoding="utf-8",
    )
    (base_dir / "nav_tree.yaml").write_text(
        (
            "version: 1\n"
            "roots:\n"
            "  - key: docs\n"
            "    title: Docs\n"
            "    collapsible: false\n"
            "    children:\n"
            f"      - key: {manifest_nav_key}\n"
            f"        doc_id: {nav_doc_id}\n"
        ),
        encoding="utf-8",
    )
    if vendors_yaml is None:
        vendors_yaml = (
            "version: 1\n"
            "vendors:\n"
            "  - vendor_id: sample-vendor\n"
            "    source_repo_path: /tmp\n"
            "    source_ref: main\n"
            "    include_globs: [\"docs/**/*.md\"]\n"
            "    exclude_globs: []\n"
            "    target_root: docs/vendor/sample-vendor\n"
            "    route_prefix: /usersum/vendor/sample-vendor\n"
        )
    (base_dir / "vendors.yaml").write_text(vendors_yaml, encoding="utf-8")


def test_usersum_contracts_validate_repo_contracts() -> None:
    repo_root = Path(__file__).resolve().parents[3]
    usersum_dir = repo_root / "wepppy" / "weppcloud" / "routes" / "usersum"

    contracts = load_and_validate_contracts(
        base_dir=usersum_dir,
        repo_root=repo_root,
        require_local_files=True,
        require_vendor_files=False,
    )

    assert contracts.docs
    assert contracts.nav_roots
    assert contracts.vendors


def test_usersum_contracts_reject_manifest_nav_doc_mismatch(tmp_path: Path) -> None:
    repo_root = tmp_path
    (repo_root / "docs").mkdir(parents=True, exist_ok=True)
    (repo_root / "docs" / "sample.md").write_text("# Sample\n", encoding="utf-8")
    base_dir = tmp_path / "usersum"
    _write_contracts(base_dir, nav_doc_id="docs.other")

    with pytest.raises(UsersumContractsValidationError):
        load_and_validate_contracts(
            base_dir=base_dir,
            repo_root=repo_root,
            require_local_files=True,
            require_vendor_files=False,
        )


def test_usersum_contracts_reject_duplicate_manifest_nav_key(tmp_path: Path) -> None:
    repo_root = tmp_path
    (repo_root / "docs").mkdir(parents=True, exist_ok=True)
    (repo_root / "docs" / "sample.md").write_text("# Sample\n", encoding="utf-8")
    (repo_root / "docs" / "sample2.md").write_text("# Sample 2\n", encoding="utf-8")

    extra_doc = (
        "  - doc_id: docs.sample2\n"
        "    source: local\n"
        "    rel_path: docs/sample2.md\n"
        "    title: Sample Doc 2\n"
        "    min_role: user\n"
        "    category: sample\n"
        "    audience_tags: [user]\n"
        "    status: active\n"
        "    nav_key: docs.sample\n"
    )
    base_dir = tmp_path / "usersum"
    _write_contracts(base_dir, extra_manifest_doc=extra_doc)

    with pytest.raises(UsersumContractsValidationError):
        load_and_validate_contracts(
            base_dir=base_dir,
            repo_root=repo_root,
            require_local_files=True,
            require_vendor_files=False,
        )


def test_usersum_contracts_reject_vendor_doc_with_unknown_vendor(tmp_path: Path) -> None:
    repo_root = tmp_path
    (repo_root / "docs").mkdir(parents=True, exist_ok=True)
    (repo_root / "docs" / "sample.md").write_text("# Sample\n", encoding="utf-8")
    base_dir = tmp_path / "usersum"
    _write_contracts(
        base_dir,
        extra_manifest_doc=(
            "  - doc_id: vendor.sample.doc\n"
            "    source: vendor\n"
            "    vendor_id: unknown-vendor\n"
            "    rel_path: docs/vendor/unknown-vendor/doc.md\n"
            "    title: Vendor Doc\n"
            "    min_role: operator\n"
            "    category: vendor\n"
            "    audience_tags: [operator]\n"
            "    status: active\n"
            "    nav_key: vendor.sample.doc\n"
        ),
    )
    (base_dir / "nav_tree.yaml").write_text(
        (
            "version: 1\n"
            "roots:\n"
            "  - key: docs\n"
            "    title: Docs\n"
            "    collapsible: false\n"
            "    children:\n"
            "      - key: docs.sample\n"
            "        doc_id: docs.sample\n"
            "      - key: vendor.sample.doc\n"
            "        doc_id: vendor.sample.doc\n"
        ),
        encoding="utf-8",
    )

    with pytest.raises(UsersumContractsValidationError):
        load_and_validate_contracts(
            base_dir=base_dir,
            repo_root=repo_root,
            require_local_files=True,
            require_vendor_files=False,
        )
