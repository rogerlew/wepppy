"""Shared CommonMark and GFM rendering for WEPPpy."""

from collections.abc import Callable, Iterable
from enum import StrEnum

import comrak


class MarkdownExtension(StrEnum):
    """Comrak options available for explicit opt-in by Python consumers."""

    ALERTS = "alerts"
    DESCRIPTION_LISTS = "description_lists"
    FOOTNOTES = "footnotes"


_SAFE_RENDER = comrak.RenderOptions(github_pre_lang=True, unsafe_=False)


def _extension_options(extensions: Iterable[MarkdownExtension]) -> comrak.ExtensionOptions:
    enabled = frozenset(MarkdownExtension(extension) for extension in extensions)
    return comrak.ExtensionOptions(
        table=True,
        tasklist=True,
        strikethrough=True,
        autolink=True,
        alerts=MarkdownExtension.ALERTS in enabled,
        description_lists=MarkdownExtension.DESCRIPTION_LISTS in enabled,
        footnotes=MarkdownExtension.FOOTNOTES in enabled,
    )


def _parse_link_tree(
    source: str, options: comrak.ExtensionOptions,
) -> tuple[comrak.AstNode, list[tuple[comrak.AstNode, comrak.NodeLink]]]:
    document = comrak.parse_document(source, options, render_options=_SAFE_RENDER)
    pending = [(document, True)]
    links = []
    while pending:
        node, inspect_links = pending.pop()
        # This binding retains strong parent and child references outside Python GC.
        # Its formatter rebuilds the tree using only children.
        node.parent = None
        if inspect_links:
            value = node.node_value
            if isinstance(value, comrak.Image):
                inspect_links = False
            elif isinstance(value, comrak.Link) and value.value.url:
                links.append((node, value.value))
        pending.extend((child, inspect_links) for child in reversed(node.children))
    return document, links


def markdown_link_destinations(source: str) -> list[str]:
    """Return destinations of parsed links in document order."""
    _, links = _parse_link_tree(source, _extension_options(()))
    return [link.url for _, link in links]


def render_markdown(
    source: str,
    *,
    extensions: Iterable[MarkdownExtension] = (),
    rewrite_link: Callable[[str], str] | None = None,
) -> str:
    """Render Markdown with safe HTML defaults and optional link rewriting."""
    options = _extension_options(extensions)
    if rewrite_link is None:
        return comrak.markdown_to_html(source, options, render_options=_SAFE_RENDER)

    document, links = _parse_link_tree(source, options)
    for node, link in links:
        rewritten = rewrite_link(link.url)
        if rewritten != link.url:
            node.node_value = comrak.Link(comrak.NodeLink(rewritten, link.title))
    return comrak.format_html(document, options, render_options=_SAFE_RENDER)
