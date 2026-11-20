from __future__ import annotations

from collections import deque
from fnmatch import fnmatchcase
from pathlib import Path, PurePosixPath
import shutil
import subprocess
from tempfile import TemporaryDirectory

from .docs_contracts import UsersumContracts, UsersumContractsValidationError, VendorSpec
from .markdown_links import markdown_link_path, parse_markdown_links, source_target


def _git(source_root: Path, *args: str) -> bytes:
    try:
        return subprocess.check_output(["git", "--no-replace-objects", "-C", str(source_root), *args], stderr=subprocess.PIPE)
    except subprocess.CalledProcessError as error:
        detail = error.stderr.decode(errors="replace").strip()
        raise UsersumContractsValidationError(f"Vendor source {source_root}: {detail}") from error


def _excluded(vendor: VendorSpec, path: str) -> bool:
    return any(fnmatchcase(path, glob) for glob in vendor["exclude_globs"])


def _matches_glob(path: tuple[str, ...], pattern: tuple[str, ...]) -> bool:
    if not pattern:
        return not path
    segment, *remaining = pattern
    tail = tuple(remaining)
    if segment == "**":
        return any(_matches_glob(path[offset:], tail) for offset in range(len(path) + 1))
    return bool(path) and fnmatchcase(path[0], segment) and _matches_glob(path[1:], tail)


def _committed_entries(source_root: Path, ref: str) -> tuple[str, dict[str, tuple[str, str]]]:
    revision = _git(source_root, "rev-parse", "--verify", "--end-of-options", f"{ref}^{{commit}}").decode("ascii").strip()
    tree = _git(source_root, "ls-tree", "-r", "-z", revision)
    entries = {}
    for record in tree.split(b"\0"):
        if record:
            meta, raw_path = record.split(b"\t", 1)
            mode, _, blob = meta.decode("ascii").split()
            path = raw_path.decode("utf-8")
            if any(part in {"", ".", ".."} or part.startswith(".vendor-sync-") for part in path.split("/")):
                raise UsersumContractsValidationError(f"Vendor tree contains a noncanonical path: {path!r}")
            entries[path] = (mode, blob)
    return revision, entries


def _source_graph(
    vendor: VendorSpec, source_root: Path, originals: set[str]
) -> tuple[str, dict[str, bytes], list[str]]:
    revision, active = _committed_entries(source_root, vendor["source_ref"])
    archive_paths = set(vendor.get("archive_paths", ()))
    archive_ref = vendor.get("archive_ref")
    archived = {}
    if archive_ref:
        archive_revision, archived = _committed_entries(source_root, archive_ref)
        absent = sorted(archive_paths - archived.keys())
        if absent:
            raise UsersumContractsValidationError(f"Vendor archive is missing configured seeds: {', '.join(absent)}")
        revision += f" (archive {archive_revision})"
    entries = archived | active
    patterns = [PurePosixPath(glob).parts for glob in vendor["include_globs"]]
    seeds = []
    for path in sorted(active.keys() | archive_paths):
        mode, _ = entries[path]
        if _excluded(vendor, path) or (path not in archive_paths and not any(
            _matches_glob(PurePosixPath(path).parts, pattern) for pattern in patterns
        )):
            continue
        if not path.lower().endswith(".md") or mode not in {"100644", "100755"}:
            raise UsersumContractsValidationError(f"Vendor seed must be regular committed Markdown: {path}")
        if path in originals:
            raise UsersumContractsValidationError(f"Vendor seed duplicates a registered Usersum document: {path}")
        seeds.append(path)
    if not seeds:
        raise UsersumContractsValidationError(
            f"Vendor {vendor['vendor_id']!r} include_globs selected no committed Markdown files"
        )

    pending = deque(seeds)
    visited = set(seeds)
    documents = {}
    warnings = []
    while pending:
        origin = pending.popleft()
        blob = _git(source_root, "cat-file", "blob", entries[origin][1])
        documents[origin] = blob
        for href in dict.fromkeys(parse_markdown_links(blob.decode("utf-8")).links):
            path = markdown_link_path(href)
            if path is None:
                continue
            target = source_target(origin, path, vendor["source_repo_path"])
            if target is None:
                reason = "outside source tree or invalid path"
            elif target in originals:
                continue
            elif _excluded(vendor, target):
                reason = "excluded by vendor configuration"
            elif target not in entries:
                reason = "file missing at source commit"
            elif entries[target][0] not in {"100644", "100755"}:
                reason = "target is not a regular committed file"
            else:
                if target not in visited:
                    pending.append(target)
                    visited.add(target)
                continue
            warnings.append(f"{vendor['vendor_id']}: {origin} -> {href} ({reason})")
    return revision, documents, warnings


def _safe_destination(target: Path, repo_root: Path) -> None:
    for path in (target, *target.parents):
        if path == repo_root:
            break
        if path.is_symlink():
            raise UsersumContractsValidationError(f"Vendor destination contains a symlink: {path}")
    if target.exists() and not target.is_dir():
        raise UsersumContractsValidationError(f"Vendor destination is not a directory: {target}")
    for child in target.rglob("*"):
        if child.is_symlink() or not (child.is_file() or child.is_dir()):
            raise UsersumContractsValidationError(f"Vendor destination contains an unsupported entry: {child}")


def _write_snapshot(target: Path, documents: dict[str, bytes], *, clean: bool) -> None:
    target.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".vendor-sync-", dir=target.parent) as temporary:
        staged = Path(temporary) / "new"
        previous = Path(temporary) / "old"
        if target.exists() and not clean:
            shutil.copytree(target, staged)
        else:
            staged.mkdir()
        for path, blob in documents.items():
            destination = staged / path
            destination.parent.mkdir(parents=True, exist_ok=True)
            destination.write_bytes(blob)
        if target.exists():
            target.rename(previous)
        try:
            staged.rename(target)
        except OSError:
            if previous.exists():
                previous.rename(target)
            raise


def sync_vendor_docs(
    contracts: UsersumContracts,
    *,
    repo_root: Path,
    write: bool,
    clean: bool,
    allow_missing_source_repos: bool = False,
) -> list[tuple[str, str]]:
    actions: list[tuple[str, str]] = []
    repo_root = repo_root.resolve()
    vendor_root = contracts.vendors_path.parent / "vendor"
    targets = [repo_root / vendor["target_root"] for vendor in contracts.vendors.values()]
    for index, target in enumerate(targets):
        if target == vendor_root or not target.is_relative_to(vendor_root):
            raise UsersumContractsValidationError(f"Vendor destination is outside {vendor_root}: {target}")
        if any(target.is_relative_to(other) or other.is_relative_to(target) for other in targets[:index]):
            raise UsersumContractsValidationError(f"Vendor destination overlaps another vendor: {target}")
        _safe_destination(target, repo_root)

    plans = []
    for (vendor_id, vendor), target_root in zip(contracts.vendors.items(), targets):
        source_root = Path(vendor["source_repo_path"]).resolve()
        if allow_missing_source_repos and not source_root.is_dir():
            actions.append(("skip", f"{vendor_id}: source repo path missing ({source_root})"))
            continue
        git_root = Path(_git(source_root, "rev-parse", "--show-toplevel").decode().strip())
        if git_root.resolve() != source_root:
            raise UsersumContractsValidationError(f"Vendor source must name the Git worktree root: {source_root}")
        same_repo = _git(source_root, "rev-parse", "--path-format=absolute", "--git-common-dir") == _git(
            repo_root, "rev-parse", "--path-format=absolute", "--git-common-dir"
        )
        if same_repo != vendor.get("source_is_usersum_repo", False):
            raise UsersumContractsValidationError(f"Vendor {vendor_id}: source_is_usersum_repo disagrees with Git")
        originals = {doc["rel_path"] for doc in contracts.docs} if same_repo else set()
        revision, documents, warnings = _source_graph(vendor, source_root, originals)
        actions.extend(("warning", warning) for warning in warnings)
        actions.extend(("copy", f"{source_root}/{path} -> {target_root / path}") for path in sorted(documents))
        actions.append(("vendor", f"{vendor_id}: {len(documents)} file(s) at {revision}"))
        plans.append((target_root, documents))
    for target_root, documents in plans:
        required = {
            (repo_root / doc["rel_path"]).relative_to(target_root).as_posix()
            for doc in contracts.docs
            if doc["source"] == "vendor" and (repo_root / doc["rel_path"]).is_relative_to(target_root)
        }
        missing = sorted(required - documents.keys())
        if missing:
            raise UsersumContractsValidationError(
                f"Vendor snapshot {target_root} is missing registered Markdown: {', '.join(missing)}"
            )
    if write:
        for target_root, documents in plans:
            _write_snapshot(target_root, documents, clean=clean)

    return actions
