"""Markdown link extraction and source-relative path resolution for Usersum."""

from collections.abc import Collection, Mapping
from html.parser import HTMLParser
from pathlib import Path, PurePosixPath
import posixpath
from urllib.parse import unquote, urlsplit

from cmarkgfm import github_flavored_markdown_to_html

from wepppy.weppcloud.usersum_anchors import add_heading_anchors

from .docs_contracts import VendorSpec


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__()
        self.links: list[str] = []
        self.anchors: set[str] = set()

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag == "a":
            self.links.extend(value for key, value in attrs if key == "href" and value)
        if tag in {"h1", "h2", "h3", "h4", "h5", "h6"}:
            self.anchors.update(value for key, value in attrs if key == "id" and value)


def parse_markdown_links(source: str, *, include_heading_ids: bool = False) -> _LinkParser:
    rendered = github_flavored_markdown_to_html(source)
    if include_heading_ids:
        rendered = add_heading_anchors(rendered)
    parser = _LinkParser()
    parser.feed(rendered)
    parser.close()
    return parser


def markdown_link_path(href: str) -> str | None:
    """Return the decoded path of a local Markdown link, if any."""
    try:
        parsed = urlsplit(href)
    except ValueError:
        return None
    if parsed.scheme or parsed.netloc:
        return None
    path = unquote(parsed.path)
    if path.lower().endswith(".md"):
        return path
    return None


def source_target(origin: str, path: str, source_checkout: str) -> str | None:
    """Resolve a decoded link path inside the source tree."""
    checkout_prefix = source_checkout.rstrip("/") + "/"
    if path.startswith(checkout_prefix):
        path = "/" + path.removeprefix(checkout_prefix)
    if path.startswith("/"):
        target = posixpath.normpath(path.lstrip("/"))
    else:
        target = posixpath.normpath(posixpath.join(PurePosixPath(origin).parent.as_posix(), path))
    if target in {".", ".."} or target.startswith("../") or "\x00" in target:
        return None
    return target


def vendor_location(
    repo_root: Path, source_path: Path, vendors: Mapping[str, VendorSpec]
) -> tuple[VendorSpec, str] | None:
    """Identify the configured vendor and source-relative path of a copied page."""
    for vendor in vendors.values():
        target_root = repo_root / vendor["target_root"]
        if source_path.is_relative_to(target_root):
            return vendor, source_path.relative_to(target_root).as_posix()
    return None


def resolve_markdown_path(
    repo_root: Path,
    source_path: Path,
    decoded_path: str,
    vendors: Mapping[str, VendorSpec],
    registered_paths: Collection[str],
) -> Path | None:
    """Find a local Markdown target with vendor-relative and manifest precedence."""
    if "\x00" in decoded_path:
        return None
    location = vendor_location(repo_root, source_path, vendors)
    if location is not None:
        vendor, original_path = location
        target = source_target(original_path, decoded_path, vendor["source_repo_path"])
        if target is not None:
            if vendor["source_is_usersum_repo"] and target in registered_paths:
                return _repo_markdown_file(repo_root, repo_root / target)
            vendor_root = repo_root / vendor["target_root"]
            candidate = (vendor_root / target).resolve()
            if candidate.is_relative_to(vendor_root) and candidate.is_file():
                return _repo_markdown_file(repo_root, candidate)

    base = repo_root if decoded_path.startswith("/") else source_path.parent
    return _repo_markdown_file(repo_root, base / decoded_path.lstrip("/"))


def is_vendor_staging_path(repo_root: Path, path: Path) -> bool:
    return path.is_relative_to(repo_root) and any(
        part.startswith(".vendor-sync-") for part in path.relative_to(repo_root).parts
    )


def _repo_markdown_file(repo_root: Path, candidate: Path) -> Path | None:
    if is_vendor_staging_path(repo_root, candidate):
        return None
    candidate = candidate.resolve()
    if is_vendor_staging_path(repo_root, candidate):
        return None
    if candidate.is_relative_to(repo_root) and candidate.suffix.lower() == ".md" and candidate.is_file():
        return candidate
    return None
