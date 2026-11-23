"""Check Usersum links using the same destinations and IDs as the live renderer."""

from functools import lru_cache
from pathlib import Path
from urllib.parse import unquote, urlsplit

from wepppy.weppcloud.usersum_anchors import usersum_anchor_from_section

from .docs_contracts import UsersumContracts
from .markdown_links import markdown_link_path, parse_markdown_links, resolve_markdown_path


def lint_links(contracts: UsersumContracts, repo_root: Path) -> list[str]:
    repo_root = repo_root.resolve()
    base_dir = contracts.docs_manifest_path.parent.resolve()
    registered = {doc["rel_path"] for doc in contracts.docs}
    warnings = []

    @lru_cache(maxsize=None)
    def parse(path: Path):
        return parse_markdown_links(path.read_text(encoding="utf-8"), include_heading_ids=True)

    scoped = set(base_dir.rglob("*.md")) | {repo_root / path for path in registered}
    paths = {
        path for path in scoped
        if not path.is_symlink() and path.is_file() and path.resolve().is_relative_to(repo_root)
    }
    for origin in sorted(paths):
        for href in dict.fromkeys(parse(origin).links):
            try:
                parsed = urlsplit(href)
            except ValueError:
                continue
            if parsed.scheme or parsed.netloc:
                continue
            fragment = unquote(parsed.fragment)
            decoded_path = markdown_link_path(href)
            if decoded_path is not None:
                target = resolve_markdown_path(repo_root, origin, decoded_path, contracts.vendors, registered)
            elif fragment and not parsed.path:
                target = origin
            else:
                continue

            reason = None
            if target is None:
                reason = "missing Markdown target"
            elif fragment and fragment not in parse(target).anchors:
                reason = f"fragment {fragment!r} is absent in {target.relative_to(repo_root)}"
                normalized = usersum_anchor_from_section(fragment)
                if normalized in parse(target).anchors:
                    reason += f"; use #{normalized}"
            if reason:
                warnings.append(f"{origin.relative_to(repo_root)} -> {href} ({reason})")

    return warnings
