from __future__ import annotations

from dataclasses import dataclass
from datetime import UTC, datetime
import hashlib
import json
from pathlib import Path
import re
from typing import Any, Dict, List, TypedDict

from .docs_contracts import NavNode, UsersumContracts, UsersumDoc

_MARKDOWN_HEADING_RE = re.compile(r"^\s{0,3}#{1,6}\s+(.*)$", re.MULTILINE)
_MARKDOWN_CODE_BLOCK_RE = re.compile(r"```.*?```", re.DOTALL)
_MARKDOWN_INLINE_CODE_RE = re.compile(r"`([^`]*)`")
_MARKDOWN_IMAGE_LINK_RE = re.compile(r"!\[([^\]]*)\]\([^)]+\)")
_MARKDOWN_INLINE_LINK_RE = re.compile(r"\[([^\]]+)\]\([^)]+\)")
_MARKDOWN_AUTOLINK_RE = re.compile(r"<(https?://[^>]+)>")
_MARKDOWN_LIST_PREFIX_RE = re.compile(r"^\s*[-*+]\s+", re.MULTILINE)
_MARKDOWN_BLOCKQUOTE_PREFIX_RE = re.compile(r"^\s*>\s?", re.MULTILINE)
_MARKDOWN_HEADING_PREFIX_RE = re.compile(r"^\s{0,3}#{1,6}\s*", re.MULTILINE)
_MARKDOWN_HTML_TAG_RE = re.compile(r"<[^>]+>")
_WHITESPACE_RE = re.compile(r"\s+")


class BreadcrumbItem(TypedDict):
    key: str
    title: str


class IndexDocument(TypedDict):
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
    breadcrumbs: List[BreadcrumbItem]
    headings: List[str]
    body_text: str
    content_hash: str
    updated_at: str | None


class IndexNavSection(TypedDict):
    key: str
    title: str
    collapsible: bool
    children: List["IndexNavNode"]


class IndexNavLeaf(TypedDict):
    key: str
    doc_id: str
    title: str


IndexNavNode = IndexNavSection | IndexNavLeaf


@dataclass(frozen=True)
class UsersumGeneratedIndex:
    version: int
    generated_at: str
    documents: List[IndexDocument]
    nav_tree: List[IndexNavNode]

    def to_jsonable(self) -> Dict[str, Any]:
        return {
            "version": self.version,
            "generated_at": self.generated_at,
            "documents": self.documents,
            "nav_tree": self.nav_tree,
        }


def _normalise_spaces(value: str) -> str:
    return _WHITESPACE_RE.sub(" ", value.strip())


def _extract_markdown_headings(markdown_source: str) -> List[str]:
    headings: List[str] = []
    for match in _MARKDOWN_HEADING_RE.finditer(markdown_source):
        heading = _normalise_spaces(match.group(1))
        if heading:
            headings.append(heading)
    return headings


def _markdown_to_search_text(markdown_source: str) -> str:
    text = _MARKDOWN_CODE_BLOCK_RE.sub(" ", markdown_source)
    text = _MARKDOWN_IMAGE_LINK_RE.sub(r"\1", text)
    text = _MARKDOWN_INLINE_LINK_RE.sub(r"\1", text)
    text = _MARKDOWN_AUTOLINK_RE.sub(r"\1", text)
    text = _MARKDOWN_INLINE_CODE_RE.sub(r"\1", text)
    text = _MARKDOWN_HEADING_PREFIX_RE.sub("", text)
    text = _MARKDOWN_LIST_PREFIX_RE.sub("", text)
    text = _MARKDOWN_BLOCKQUOTE_PREFIX_RE.sub("", text)
    text = _MARKDOWN_HTML_TAG_RE.sub(" ", text)
    text = text.replace("|", " ")
    return _normalise_spaces(text)


def _isoformat_mtime(path: Path) -> str | None:
    if not path.is_file():
        return None
    return datetime.fromtimestamp(path.stat().st_mtime, tz=UTC).isoformat()


def _content_hash(markdown_source: str) -> str:
    return hashlib.sha256(markdown_source.encode("utf-8")).hexdigest()


def _canonical_route_path(doc_id: str) -> str:
    return f"/usersum/doc/{doc_id}"


def _legacy_route_path(doc: UsersumDoc) -> str | None:
    rel_path = doc["rel_path"]
    category_root = "wepppy/weppcloud/routes/usersum/"
    if rel_path.startswith(category_root):
        rel_token = rel_path[len(category_root):]
        category, _, filename = rel_token.partition("/")
        if category in {"db", "input-file-specifications", "weppcloud", "path"} and filename:
            return f"/usersum/view/{category}/{filename}"
    return f"/usersum/src/{rel_path}"


def _vendor_route_path(doc: UsersumDoc, contracts: UsersumContracts) -> str | None:
    if doc["source"] != "vendor":
        return None
    vendor_id = doc["vendor_id"]
    assert vendor_id is not None
    vendor = contracts.vendors[vendor_id]
    target_root = vendor["target_root"]
    if not doc["rel_path"].startswith(f"{target_root}/"):
        return None
    rel_vendor_path = doc["rel_path"][len(target_root) + 1 :]
    return f"/usersum/vendor/{vendor_id}/{rel_vendor_path}"


def _build_doc_breadcrumb_map(contracts: UsersumContracts) -> Dict[str, List[BreadcrumbItem]]:
    key_to_title: Dict[str, str] = {}
    for doc in contracts.docs:
        key_to_title[doc["nav_key"]] = doc["title"]

    breadcrumb_map: Dict[str, List[BreadcrumbItem]] = {}

    def walk(node: NavNode, sections: List[BreadcrumbItem]) -> None:
        if "doc_id" in node:
            leaf_key = node["key"]
            breadcrumb_map[node["doc_id"]] = [*sections, {"key": leaf_key, "title": key_to_title[leaf_key]}]
            return

        section_item: BreadcrumbItem = {"key": node["key"], "title": node["title"]}
        next_sections = [*sections, section_item]
        for child in node["children"]:
            walk(child, next_sections)

    for root in contracts.nav_roots:
        walk(root, [])

    return breadcrumb_map


def _build_index_nav_tree(contracts: UsersumContracts) -> List[IndexNavNode]:
    doc_by_id = {doc["doc_id"]: doc for doc in contracts.docs}

    def convert(node: NavNode) -> IndexNavNode:
        if "doc_id" in node:
            doc = doc_by_id[node["doc_id"]]
            return IndexNavLeaf(key=node["key"], doc_id=node["doc_id"], title=doc["title"])
        children = [convert(child) for child in node["children"]]
        return IndexNavSection(
            key=node["key"],
            title=node["title"],
            collapsible=node["collapsible"],
            children=children,
        )

    return [convert(root) for root in contracts.nav_roots]


def build_generated_index(contracts: UsersumContracts, *, repo_root: Path) -> UsersumGeneratedIndex:
    breadcrumb_map = _build_doc_breadcrumb_map(contracts)
    documents: List[IndexDocument] = []
    repo_root_resolved = repo_root.resolve()

    for doc in contracts.docs:
        abs_path = (repo_root_resolved / doc["rel_path"]).resolve()
        markdown_source = abs_path.read_text(encoding="utf-8") if abs_path.is_file() else ""
        headings = _extract_markdown_headings(markdown_source)
        title = doc["title"]
        if not title and headings:
            title = headings[0]
        body_text = _markdown_to_search_text(markdown_source)

        documents.append(
            IndexDocument(
                doc_id=doc["doc_id"],
                source=doc["source"],
                rel_path=doc["rel_path"],
                title=title,
                min_role=doc["min_role"],
                category=doc["category"],
                audience_tags=doc["audience_tags"],
                status=doc["status"],
                nav_key=doc["nav_key"],
                vendor_id=doc["vendor_id"],
                route_path=_canonical_route_path(doc["doc_id"]),
                vendor_route_path=_vendor_route_path(doc, contracts),
                legacy_route_path=_legacy_route_path(doc),
                breadcrumbs=breadcrumb_map.get(doc["doc_id"], []),
                headings=headings,
                body_text=body_text,
                content_hash=_content_hash(markdown_source),
                updated_at=_isoformat_mtime(abs_path),
            )
        )

    documents.sort(key=lambda item: item["doc_id"])
    nav_tree = _build_index_nav_tree(contracts)
    return UsersumGeneratedIndex(
        version=1,
        generated_at=datetime.now(tz=UTC).isoformat(),
        documents=documents,
        nav_tree=nav_tree,
    )


def write_generated_index(index: UsersumGeneratedIndex, path: Path) -> None:
    payload = index.to_jsonable()
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def load_generated_index(path: Path) -> Dict[str, Any]:
    loaded = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(loaded, dict):
        raise ValueError(f"Generated index must be a mapping: {path}")
    return loaded
