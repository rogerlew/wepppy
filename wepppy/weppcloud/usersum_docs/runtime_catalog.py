from __future__ import annotations

from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Tuple, TypedDict

from .docs_contracts import load_and_validate_contracts
from .docs_index import build_generated_index, load_generated_index

_ROLE_RANK: Dict[str, int] = {
    "user": 0,
    "operator": 1,
    "developer": 2,
    "internal": 3,
}


class RuntimeDoc(TypedDict):
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
    route_path: str
    vendor_route_path: str | None
    legacy_route_path: str | None
    breadcrumbs: List[Dict[str, str]]
    headings: List[str]
    body_text: str
    content_hash: str
    updated_at: str | None


class RuntimeNavLeaf(TypedDict):
    key: str
    doc_id: str
    title: str


class RuntimeNavSection(TypedDict):
    key: str
    title: str
    collapsible: bool
    children: List["RuntimeNavNode"]


RuntimeNavNode = RuntimeNavLeaf | RuntimeNavSection


@dataclass(frozen=True)
class RuntimeCatalog:
    docs: List[RuntimeDoc]
    nav_tree: List[RuntimeNavNode]
    docs_by_id: Dict[str, RuntimeDoc]
    docs_by_rel_path: Dict[str, RuntimeDoc]
    docs_by_legacy_route_path: Dict[str, RuntimeDoc]
    docs_by_vendor_route_path: Dict[str, RuntimeDoc]
    docs_by_nav_key: Dict[str, RuntimeDoc]

    def visible_doc(self, doc: RuntimeDoc, caller_max_role: str) -> bool:
        return _ROLE_RANK[doc["min_role"]] <= _ROLE_RANK[caller_max_role]

    def visible_docs(self, caller_max_role: str) -> List[RuntimeDoc]:
        return [doc for doc in self.docs if self.visible_doc(doc, caller_max_role)]


def _doc_index_path(usersum_base_dir: Path) -> Path:
    return usersum_base_dir / "generated" / "docs_index.json"


def _build_runtime_catalog_from_index(index_payload: Dict[str, Any]) -> RuntimeCatalog:
    docs_raw = index_payload.get("documents")
    nav_tree_raw = index_payload.get("nav_tree")
    if not isinstance(docs_raw, list) or not isinstance(nav_tree_raw, list):
        raise ValueError("Generated usersum docs index is missing required documents/nav_tree arrays")

    docs: List[RuntimeDoc] = []
    docs_by_id: Dict[str, RuntimeDoc] = {}
    docs_by_rel_path: Dict[str, RuntimeDoc] = {}
    docs_by_legacy_route_path: Dict[str, RuntimeDoc] = {}
    docs_by_vendor_route_path: Dict[str, RuntimeDoc] = {}
    docs_by_nav_key: Dict[str, RuntimeDoc] = {}

    for raw in docs_raw:
        if not isinstance(raw, dict):
            raise ValueError("Generated usersum docs index contains non-mapping document entries")
        doc = RuntimeDoc(**raw)
        docs.append(doc)
        docs_by_id[doc["doc_id"]] = doc
        docs_by_rel_path[doc["rel_path"]] = doc
        docs_by_nav_key[doc["nav_key"]] = doc
        legacy_route_path = doc["legacy_route_path"]
        if legacy_route_path:
            docs_by_legacy_route_path[legacy_route_path] = doc
        vendor_route_path = doc["vendor_route_path"]
        if vendor_route_path:
            docs_by_vendor_route_path[vendor_route_path] = doc

    return RuntimeCatalog(
        docs=docs,
        nav_tree=nav_tree_raw,
        docs_by_id=docs_by_id,
        docs_by_rel_path=docs_by_rel_path,
        docs_by_legacy_route_path=docs_by_legacy_route_path,
        docs_by_vendor_route_path=docs_by_vendor_route_path,
        docs_by_nav_key=docs_by_nav_key,
    )


@lru_cache(maxsize=1)
def load_runtime_catalog(*, usersum_base_dir: Path, repo_root: Path) -> RuntimeCatalog:
    index_path = _doc_index_path(usersum_base_dir)
    if index_path.is_file():
        return _build_runtime_catalog_from_index(load_generated_index(index_path))

    contracts = load_and_validate_contracts(
        base_dir=usersum_base_dir,
        repo_root=repo_root,
        require_local_files=True,
        require_vendor_files=False,
    )
    generated = build_generated_index(contracts, repo_root=repo_root)
    return _build_runtime_catalog_from_index(generated.to_jsonable())


def filter_nav_tree_for_visibility(
    nav_tree: List[RuntimeNavNode],
    *,
    docs_by_id: Dict[str, RuntimeDoc],
    caller_max_role: str,
    active_doc_id: str | None = None,
) -> List[Dict[str, Any]]:
    def walk(node: RuntimeNavNode) -> Tuple[Optional[Dict[str, Any]], bool]:
        if "doc_id" in node:
            doc = docs_by_id.get(node["doc_id"])
            if doc is None:
                return None, False
            if _ROLE_RANK[doc["min_role"]] > _ROLE_RANK[caller_max_role]:
                return None, False
            is_active = doc["doc_id"] == active_doc_id
            payload: Dict[str, Any] = {
                "kind": "leaf",
                "key": node["key"],
                "doc_id": doc["doc_id"],
                "title": doc["title"],
                "href": doc["route_path"],
                "is_active": is_active,
            }
            return payload, is_active

        children_payload: List[Dict[str, Any]] = []
        subtree_has_active = False
        for child in node["children"]:
            child_payload, child_active = walk(child)
            if child_payload is None:
                continue
            children_payload.append(child_payload)
            subtree_has_active = subtree_has_active or child_active

        if not children_payload:
            return None, False

        payload = {
            "kind": "section",
            "key": node["key"],
            "title": node["title"],
            "collapsible": node["collapsible"],
            "children": children_payload,
            "is_expanded": subtree_has_active,
        }
        return payload, subtree_has_active

    filtered: List[Dict[str, Any]] = []
    for root in nav_tree:
        payload, _ = walk(root)
        if payload is not None:
            filtered.append(payload)
    return filtered
