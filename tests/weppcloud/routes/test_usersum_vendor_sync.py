from pathlib import Path
import subprocess

import pytest

from wepppy.weppcloud.usersum_docs.docs_contracts import (
    UsersumContracts,
    UsersumContractsValidationError,
)
from wepppy.weppcloud.usersum_docs.link_lint import lint_links
from wepppy.weppcloud.usersum_docs.vendor_sync import sync_vendor_docs


def _git(root: Path, *args: str) -> None:
    subprocess.run(["git", "-C", str(root), *args], check=True, capture_output=True)


@pytest.fixture
def vendor_fixture(tmp_path):
    source = tmp_path / "source"
    repo = tmp_path / "repo"
    for root in (source, repo):
        root.mkdir()
        _git(root, "init", "-q", "-b", "main")
    base = repo / "usersum"
    target = base / "vendor" / "example"
    contracts = UsersumContracts(
        docs_manifest_path=base / "docs_manifest.yaml",
        nav_tree_path=base / "nav_tree.yaml",
        vendors_path=base / "vendors.yaml",
        docs=[],
        nav_roots=[],
        nav_key_to_doc_id={},
        vendors={"example": {
            "vendor_id": "example",
            "source_repo_path": str(source),
            "source_ref": "main",
            "source_is_usersum_repo": False,
            "include_globs": ["guides/start.md"],
            "exclude_globs": ["private/*"],
            "target_root": "usersum/vendor/example",
            "route_prefix": "/usersum/vendor/example",
        }},
    )
    return source, repo, target, contracts


def _commit(root):
    _git(root, "add", ".")
    _git(root, "-c", "user.name=Test", "-c", "user.email=test@example.com", "commit", "-qm", "snapshot")


def test_vendor_walk_uses_committed_blobs_and_lints_published_anchors(vendor_fixture):
    source, repo, target, contracts = vendor_fixture
    (source / "guides").mkdir()
    start = source / "guides/start.md"
    start.write_text(
        "# Start\n\n[Next][next] [Bad](../topic.md#topic--name) [Absent](../absent.md) "
        "[Escapes](../../outside.md) [Symlink](../alias.md) [Excluded](../private/secret.md)\n\n"
        "[next]: /topic.md?mode=reading#topic%2Dname-1\n\n"
        "`[Example](../example.md)`\n",
        encoding="utf-8",
    )
    topic = "# Topic — Name\n\n# Topic — Name\n\n[Cycle](guides/start.md) [Third](leaf.md)\n"
    (source / "topic.md").write_text(topic, encoding="utf-8")
    (source / "leaf.md").write_text("# Leaf\n", encoding="utf-8")
    (source / "private").mkdir()
    (source / "private/secret.md").write_text("# Excluded\n", encoding="utf-8")
    (source / "alias.md").symlink_to("topic.md")
    _commit(source)
    (source / "absent.md").write_text("# Uncommitted\n", encoding="utf-8")
    (source / "topic.md").write_text("# Modified\n", encoding="utf-8")
    target.mkdir(parents=True)
    (target / "stale.md").write_text("# Stale\n", encoding="utf-8")

    dry_run = sync_vendor_docs(contracts, repo_root=repo, write=False, clean=True)
    assert (target / "stale.md").is_file()
    assert not (target / "topic.md").exists()
    assert sync_vendor_docs(contracts, repo_root=repo, write=True, clean=True) == dry_run
    assert {p.relative_to(target).as_posix() for p in target.rglob("*.md")} == {
        "guides/start.md", "topic.md", "leaf.md",
    }
    assert (target / "topic.md").read_text(encoding="utf-8") == topic
    reasons = [detail for action, detail in dry_run if action == "warning"]
    assert len(reasons) == 4
    assert any("../absent.md (file missing at source commit)" in warning for warning in reasons)
    assert any("../alias.md (target is not a regular committed file)" in warning for warning in reasons)
    assert any("../private/secret.md (excluded by vendor configuration)" in warning for warning in reasons)
    lint = lint_links(contracts, repo)
    assert any("topic--name" in warning for warning in lint)
    assert not any("topic%2Dname-1" in warning for warning in lint)


def test_vendor_destination_symlink_is_rejected_before_cleanup(vendor_fixture, tmp_path):
    _, repo, target, contracts = vendor_fixture
    outside = tmp_path / "outside"
    outside.mkdir()
    (outside / "sentinel.md").write_text("untouched", encoding="utf-8")
    target.parent.mkdir(parents=True)
    target.symlink_to(outside, target_is_directory=True)

    with pytest.raises(UsersumContractsValidationError, match="destination contains a symlink"):
        sync_vendor_docs(contracts, repo_root=repo, write=True, clean=True)

    assert (outside / "sentinel.md").read_text(encoding="utf-8") == "untouched"


def test_self_vendor_retains_registered_original_without_copy(vendor_fixture):
    _, repo, target, contracts = vendor_fixture
    vendor = contracts.vendors["example"]
    vendor["source_repo_path"] = str(repo)
    vendor["source_is_usersum_repo"] = True
    (repo / "guides").mkdir()
    (repo / "guides/start.md").write_text("[Restricted](/internal.md)\n", encoding="utf-8")
    (repo / "internal.md").write_text("# Internal\n", encoding="utf-8")
    _commit(repo)
    contracts.docs.append({
        "doc_id": "example.internal", "source": "local", "rel_path": "internal.md",
        "title": "Internal", "min_role": "internal", "category": "weppcloud",
        "audience_tags": [], "status": "active", "nav_key": "internal", "vendor_id": None,
    })

    actions = sync_vendor_docs(contracts, repo_root=repo, write=True, clean=True)

    assert not (target / "internal.md").exists()
    assert (target / "guides/start.md").is_file()
    assert not [action for action, _ in actions if action == "warning"]


def test_vendor_build_ref_error_keeps_previous_snapshot(vendor_fixture):
    source, repo, target, contracts = vendor_fixture
    (source / "guides").mkdir()
    (source / "guides/start.md").write_text("# Start\n", encoding="utf-8")
    _commit(source)
    target.mkdir(parents=True)
    (target / "previous.md").write_text("# Previous\n", encoding="utf-8")
    contracts.vendors["example"]["source_ref"] = "missing-ref"

    with pytest.raises(UsersumContractsValidationError, match="Vendor source"):
        sync_vendor_docs(contracts, repo_root=repo, write=True, clean=True)

    assert (target / "previous.md").is_file()


def test_vendor_archive_follows_links_and_prefers_active_blob(vendor_fixture):
    source, repo, target, contracts = vendor_fixture
    guides = source / "guides"
    guides.mkdir()
    (guides / "start.md").write_text("# Start\n", encoding="utf-8")
    history = source / "history.md"
    history.write_text("[Previous](previous.md) [Shared](shared.md)\n", encoding="utf-8")
    (source / "previous.md").write_text("# Archived\n", encoding="utf-8")
    shared = source / "shared.md"
    shared.write_text("# Superseded\n", encoding="utf-8")
    _commit(source)
    _git(source, "tag", "archive")
    history.unlink()
    (source / "previous.md").unlink()
    shared.write_text("# Authoritative\n", encoding="utf-8")
    _commit(source)
    contracts.vendors["example"].update(archive_ref="archive", archive_paths=["history.md"])

    sync_vendor_docs(contracts, repo_root=repo, write=True, clean=True)

    assert (target / "history.md").is_file()
    assert (target / "previous.md").is_file()
    assert (target / "shared.md").read_text(encoding="utf-8") == "# Authoritative\n"
