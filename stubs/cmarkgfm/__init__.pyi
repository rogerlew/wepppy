from typing import Sequence

__all__ = [
    "github_flavored_markdown_to_html",
    "markdown_to_html",
    "markdown_to_html_with_extensions",
    "Options",
]

class Options:
    CMARK_OPT_DEFAULT: int
    CMARK_OPT_FOOTNOTES: int
    CMARK_OPT_GITHUB_PRE_LANG: int
    CMARK_OPT_HARDBREAKS: int
    CMARK_OPT_LIBERAL_HTML_TAG: int
    CMARK_OPT_NOBREAKS: int
    CMARK_OPT_NORMALIZE: int
    CMARK_OPT_SMART: int
    CMARK_OPT_SOURCEPOS: int
    CMARK_OPT_STRIKETHROUGH_DOUBLE_TILDE: int
    CMARK_OPT_TABLE_PREFER_STYLE_ATTRIBUTES: int
    CMARK_OPT_UNSAFE: int
    CMARK_OPT_VALIDATE_UTF8: int

    def __init__(self) -> None: ...


def github_flavored_markdown_to_html(text: str, options: int = ...) -> str: ...


def markdown_to_html(text: str, options: int = ...) -> str: ...


def markdown_to_html_with_extensions(
    text: str,
    options: int = ...,
    extensions: Sequence[str] | None = ...,
) -> str: ...
