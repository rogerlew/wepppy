from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path, PurePosixPath
from typing import Any, Dict, List, Tuple, TypedDict

import yaml

_VALID_ROLES = {"user", "operator", "developer", "internal"}
_VALID_STATUSES = {"active", "deprecated", "draft"}
_VALID_SOURCES = {"local", "vendor"}


class UsersumDoc(TypedDict):
    doc_id: str
    source: str
    rel_path: str
    title: str
    min_role: str
    category: str
    audience_tags: List[str]
    status: str
    nav_key: str
    vendor_id: str | None


class VendorSpec(TypedDict):
    vendor_id: str
    source_repo_path: str
    source_ref: str
    include_globs: List[str]
    exclude_globs: List[str]
    target_root: str
    route_prefix: str


class NavLeaf(TypedDict):
    key: str
    doc_id: str


class NavSection(TypedDict):
    key: str
    title: str
    collapsible: bool
    children: List["NavNode"]


NavNode = NavLeaf | NavSection


@dataclass(frozen=True)
class UsersumContracts:
    docs_manifest_path: Path
    nav_tree_path: Path
    vendors_path: Path
    docs: List[UsersumDoc]
    nav_roots: List[NavNode]
    nav_key_to_doc_id: Dict[str, str]
    vendors: Dict[str, VendorSpec]


class UsersumContractsValidationError(ValueError):
    pass


def _load_yaml(path: Path) -> Dict[str, Any]:
    if not path.is_file():
        raise UsersumContractsValidationError(f"Missing required contract file: {path}")
    loaded = yaml.safe_load(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise UsersumContractsValidationError(f"Contract file must parse to a mapping: {path}")
    return loaded


def _expect_version(payload: Dict[str, Any], path: Path, expected: int = 1) -> None:
    version = payload.get("version")
    if version != expected:
        raise UsersumContractsValidationError(
            f"{path.name}: expected version {expected}, got {version!r}"
        )


def _require_string(value: Any, context: str) -> str:
    if not isinstance(value, str):
        raise UsersumContractsValidationError(f"{context} must be a string")
    normalized = value.strip()
    if not normalized:
        raise UsersumContractsValidationError(f"{context} must be non-empty")
    return normalized


def _require_string_list(value: Any, context: str) -> List[str]:
    if not isinstance(value, list):
        raise UsersumContractsValidationError(f"{context} must be a list of strings")
    values: List[str] = []
    for idx, item in enumerate(value):
        values.append(_require_string(item, f"{context}[{idx}]"))
    return values


def _validate_rel_markdown_path(value: str, context: str) -> str:
    pure = PurePosixPath(value)
    if pure.is_absolute():
        raise UsersumContractsValidationError(f"{context} must be repo-relative (not absolute)")
    if ".." in pure.parts:
        raise UsersumContractsValidationError(f"{context} must not contain '..' traversal segments")
    if pure.suffix.lower() != ".md":
        raise UsersumContractsValidationError(f"{context} must point to a .md file")
    normalized = pure.as_posix()
    if normalized.startswith("./"):
        normalized = normalized[2:]
    return normalized


def _validate_rel_dir_path(value: str, context: str) -> str:
    pure = PurePosixPath(value)
    if pure.is_absolute():
        raise UsersumContractsValidationError(f"{context} must be repo-relative (not absolute)")
    if ".." in pure.parts:
        raise UsersumContractsValidationError(f"{context} must not contain '..' traversal segments")
    normalized = pure.as_posix().rstrip("/")
    if normalized.startswith("./"):
        normalized = normalized[2:]
    if not normalized:
        raise UsersumContractsValidationError(f"{context} must be non-empty")
    return normalized


def _parse_docs_manifest(payload: Dict[str, Any], path: Path) -> List[UsersumDoc]:
    _expect_version(payload, path)
    raw_docs = payload.get("docs")
    if not isinstance(raw_docs, list):
        raise UsersumContractsValidationError(f"{path.name}: 'docs' must be a list")

    docs: List[UsersumDoc] = []
    doc_ids: set[str] = set()
    nav_keys: set[str] = set()
    for idx, raw_doc in enumerate(raw_docs):
        context = f"{path.name}: docs[{idx}]"
        if not isinstance(raw_doc, dict):
            raise UsersumContractsValidationError(f"{context} must be a mapping")

        doc_id = _require_string(raw_doc.get("doc_id"), f"{context}.doc_id")
        if doc_id in doc_ids:
            raise UsersumContractsValidationError(f"{context}.doc_id duplicates existing doc_id {doc_id!r}")
        doc_ids.add(doc_id)

        source = _require_string(raw_doc.get("source"), f"{context}.source")
        if source not in _VALID_SOURCES:
            raise UsersumContractsValidationError(f"{context}.source must be one of {_VALID_SOURCES}")

        rel_path = _validate_rel_markdown_path(
            _require_string(raw_doc.get("rel_path"), f"{context}.rel_path"),
            f"{context}.rel_path",
        )
        title = _require_string(raw_doc.get("title"), f"{context}.title")
        min_role = _require_string(raw_doc.get("min_role"), f"{context}.min_role")
        if min_role not in _VALID_ROLES:
            raise UsersumContractsValidationError(f"{context}.min_role must be one of {_VALID_ROLES}")
        category = _require_string(raw_doc.get("category"), f"{context}.category")
        audience_tags = _require_string_list(raw_doc.get("audience_tags", []), f"{context}.audience_tags")
        status = _require_string(raw_doc.get("status"), f"{context}.status")
        if status not in _VALID_STATUSES:
            raise UsersumContractsValidationError(f"{context}.status must be one of {_VALID_STATUSES}")
        nav_key = _require_string(raw_doc.get("nav_key"), f"{context}.nav_key")
        if nav_key in nav_keys:
            raise UsersumContractsValidationError(f"{context}.nav_key duplicates existing nav_key {nav_key!r}")
        nav_keys.add(nav_key)

        vendor_id_raw = raw_doc.get("vendor_id")
        vendor_id: str | None = None
        if vendor_id_raw is not None:
            vendor_id = _require_string(vendor_id_raw, f"{context}.vendor_id")
        if source == "vendor" and vendor_id is None:
            raise UsersumContractsValidationError(f"{context}.vendor_id is required for source='vendor'")
        if source == "local" and vendor_id is not None:
            raise UsersumContractsValidationError(f"{context}.vendor_id must be omitted for source='local'")

        docs.append(
            UsersumDoc(
                doc_id=doc_id,
                source=source,
                rel_path=rel_path,
                title=title,
                min_role=min_role,
                category=category,
                audience_tags=audience_tags,
                status=status,
                nav_key=nav_key,
                vendor_id=vendor_id,
            )
        )

    return docs


def _parse_nav_tree(payload: Dict[str, Any], path: Path) -> Tuple[List[NavNode], Dict[str, str]]:
    _expect_version(payload, path)
    roots_value = payload.get("roots")
    if not isinstance(roots_value, list):
        raise UsersumContractsValidationError(f"{path.name}: 'roots' must be a list")

    used_keys: set[str] = set()
    doc_id_to_key: Dict[str, str] = {}
    key_to_doc_id: Dict[str, str] = {}

    def parse_node(raw_node: Any, context: str) -> NavNode:
        if not isinstance(raw_node, dict):
            raise UsersumContractsValidationError(f"{context} must be a mapping")

        key = _require_string(raw_node.get("key"), f"{context}.key")
        if key in used_keys:
            raise UsersumContractsValidationError(f"{context}.key duplicates existing key {key!r}")
        used_keys.add(key)

        if "doc_id" in raw_node:
            doc_id = _require_string(raw_node.get("doc_id"), f"{context}.doc_id")
            if "children" in raw_node:
                raise UsersumContractsValidationError(f"{context} leaf node must not define children")
            if doc_id in doc_id_to_key:
                raise UsersumContractsValidationError(
                    f"{context}.doc_id duplicates existing nav doc_id {doc_id!r}"
                )
            doc_id_to_key[doc_id] = key
            key_to_doc_id[key] = doc_id
            return NavLeaf(key=key, doc_id=doc_id)

        title = _require_string(raw_node.get("title"), f"{context}.title")
        collapsible_raw = raw_node.get("collapsible", False)
        if not isinstance(collapsible_raw, bool):
            raise UsersumContractsValidationError(f"{context}.collapsible must be a boolean")
        children_raw = raw_node.get("children")
        if not isinstance(children_raw, list):
            raise UsersumContractsValidationError(f"{context}.children must be a list")
        children: List[NavNode] = []
        for idx, child in enumerate(children_raw):
            children.append(parse_node(child, f"{context}.children[{idx}]"))
        return NavSection(
            key=key,
            title=title,
            collapsible=collapsible_raw,
            children=children,
        )

    roots: List[NavNode] = []
    for idx, root in enumerate(roots_value):
        roots.append(parse_node(root, f"{path.name}: roots[{idx}]"))

    return roots, key_to_doc_id


def _parse_vendors(payload: Dict[str, Any], path: Path) -> Dict[str, VendorSpec]:
    _expect_version(payload, path)
    raw_vendors = payload.get("vendors")
    if not isinstance(raw_vendors, list):
        raise UsersumContractsValidationError(f"{path.name}: 'vendors' must be a list")

    vendors: Dict[str, VendorSpec] = {}
    route_prefixes: set[str] = set()
    for idx, raw_vendor in enumerate(raw_vendors):
        context = f"{path.name}: vendors[{idx}]"
        if not isinstance(raw_vendor, dict):
            raise UsersumContractsValidationError(f"{context} must be a mapping")

        vendor_id = _require_string(raw_vendor.get("vendor_id"), f"{context}.vendor_id")
        if vendor_id in vendors:
            raise UsersumContractsValidationError(f"{context}.vendor_id duplicates existing vendor_id {vendor_id!r}")
        source_repo_path = _require_string(raw_vendor.get("source_repo_path"), f"{context}.source_repo_path")
        source_ref = _require_string(raw_vendor.get("source_ref"), f"{context}.source_ref")
        include_globs = _require_string_list(raw_vendor.get("include_globs"), f"{context}.include_globs")
        if not include_globs:
            raise UsersumContractsValidationError(f"{context}.include_globs must not be empty")
        exclude_globs = _require_string_list(raw_vendor.get("exclude_globs", []), f"{context}.exclude_globs")
        target_root = _validate_rel_dir_path(
            _require_string(raw_vendor.get("target_root"), f"{context}.target_root"),
            f"{context}.target_root",
        )
        route_prefix = _require_string(raw_vendor.get("route_prefix"), f"{context}.route_prefix")
        if not route_prefix.startswith("/usersum/vendor/"):
            raise UsersumContractsValidationError(
                f"{context}.route_prefix must begin with '/usersum/vendor/'"
            )
        if route_prefix in route_prefixes:
            raise UsersumContractsValidationError(
                f"{context}.route_prefix duplicates existing route_prefix {route_prefix!r}"
            )
        route_prefixes.add(route_prefix)

        vendors[vendor_id] = VendorSpec(
            vendor_id=vendor_id,
            source_repo_path=source_repo_path,
            source_ref=source_ref,
            include_globs=include_globs,
            exclude_globs=exclude_globs,
            target_root=target_root,
            route_prefix=route_prefix,
        )

    return vendors


def load_and_validate_contracts(
    *,
    base_dir: Path,
    repo_root: Path,
    require_local_files: bool = True,
    require_vendor_files: bool = False,
) -> UsersumContracts:
    docs_manifest_path = base_dir / "docs_manifest.yaml"
    nav_tree_path = base_dir / "nav_tree.yaml"
    vendors_path = base_dir / "vendors.yaml"

    docs_payload = _load_yaml(docs_manifest_path)
    nav_payload = _load_yaml(nav_tree_path)
    vendors_payload = _load_yaml(vendors_path)

    docs = _parse_docs_manifest(docs_payload, docs_manifest_path)
    nav_roots, nav_key_to_doc_id = _parse_nav_tree(nav_payload, nav_tree_path)
    vendors = _parse_vendors(vendors_payload, vendors_path)

    manifest_doc_ids = {doc["doc_id"] for doc in docs}
    nav_doc_ids = set(nav_key_to_doc_id.values())
    if manifest_doc_ids != nav_doc_ids:
        missing_in_nav = sorted(manifest_doc_ids - nav_doc_ids)
        missing_in_manifest = sorted(nav_doc_ids - manifest_doc_ids)
        raise UsersumContractsValidationError(
            "Manifest/nav doc coverage mismatch: "
            f"missing_in_nav={missing_in_nav}, missing_in_manifest={missing_in_manifest}"
        )

    for doc in docs:
        expected_doc_id = nav_key_to_doc_id.get(doc["nav_key"])
        if expected_doc_id is None:
            raise UsersumContractsValidationError(
                f"Manifest nav_key {doc['nav_key']!r} not found in nav tree"
            )
        if expected_doc_id != doc["doc_id"]:
            raise UsersumContractsValidationError(
                f"Manifest doc {doc['doc_id']!r} nav_key {doc['nav_key']!r} maps to "
                f"different nav doc_id {expected_doc_id!r}"
            )
        if doc["source"] == "vendor":
            vendor_id = doc["vendor_id"]
            if vendor_id is None or vendor_id not in vendors:
                raise UsersumContractsValidationError(
                    f"Vendor doc {doc['doc_id']!r} references unknown vendor_id {vendor_id!r}"
                )

    repo_root_resolved = repo_root.resolve()
    for doc in docs:
        rel_path = doc["rel_path"]
        abs_path = (repo_root_resolved / rel_path).resolve()
        if repo_root_resolved not in abs_path.parents:
            raise UsersumContractsValidationError(
                f"Doc rel_path resolves outside repository root: {rel_path!r}"
            )
        should_require_file = require_local_files and doc["source"] == "local"
        if doc["source"] == "vendor":
            should_require_file = require_vendor_files
            vendor_id = doc["vendor_id"]
            assert vendor_id is not None
            vendor_target_root = vendors[vendor_id]["target_root"]
            if not rel_path.startswith(f"{vendor_target_root}/"):
                raise UsersumContractsValidationError(
                    f"Vendor doc {doc['doc_id']!r} rel_path must be under target_root {vendor_target_root!r}"
                )
        if should_require_file and not abs_path.is_file():
            raise UsersumContractsValidationError(f"Missing markdown file for doc rel_path {rel_path!r}")

    return UsersumContracts(
        docs_manifest_path=docs_manifest_path,
        nav_tree_path=nav_tree_path,
        vendors_path=vendors_path,
        docs=docs,
        nav_roots=nav_roots,
        nav_key_to_doc_id=nav_key_to_doc_id,
        vendors=vendors,
    )
