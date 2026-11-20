import comrak
import pytest

from wepppy.markdown_render import MarkdownExtension, markdown_link_destinations, render_markdown


def test_default_profile_renders_gfm_and_existing_code_fence_markup() -> None:
    source = (
        "| A | B |\n|---|---|\n| 1 | 2 |\n\n"
        "- [x] Done\n\n~~Old~~\n\nwww.example.org\n\n"
        "```python\nprint('hello')\n```\n"
    )

    html = render_markdown(source)

    assert "<table>" in html and "<td>2</td>" in html
    assert '<input type="checkbox" checked="" disabled="" />' in html
    assert "<del>Old</del>" in html
    assert '<a href="http://www.example.org">www.example.org</a>' in html
    assert '<pre lang="python"><code>' in html


@pytest.mark.parametrize("rewrite", [None, lambda href: href])
def test_direct_and_ast_renderers_keep_source_html_and_unsafe_urls_inert(rewrite) -> None:
    source = '<b>raw</b> [link](javascript:example) ![image](javascript:example)'

    html = render_markdown(source, rewrite_link=rewrite)

    assert "<b>" not in html
    assert "raw" in html
    assert '<a href="">link</a>' in html
    assert '<img src="" alt="image"' in html


def test_link_rewrite_preserves_title_label_and_literal_content() -> None:
    source = (
        '[**Reference**][guide]\n\n'
        '[guide]: ./guide.md?mode=reading#section "Guide title"\n\n'
        '![Image [description](./description.md)](./image.png)\n\n'
        '`[In code](./inline.md)`\n\n'
        '```markdown\n[In fenced code](./fenced.md)\n```\n'
    )
    seen = []

    def rewrite(href: str) -> str:
        seen.append(href)
        return "/usersum/doc/guide?mode=reading#section"

    assert markdown_link_destinations(source) == ["./guide.md?mode=reading#section"]
    html = render_markdown(source, rewrite_link=rewrite)

    assert seen == ["./guide.md?mode=reading#section"]
    assert 'href="/usersum/doc/guide?mode=reading#section" title="Guide title"><strong>Reference</strong>' in html
    assert 'src="./image.png"' in html
    assert "[In code](./inline.md)" in html
    assert "[In fenced code](./fenced.md)" in html


def test_link_rewrite_cannot_bypass_comrak_url_policy() -> None:
    html = render_markdown("[link](./guide.md)", rewrite_link=lambda href: "javascript:example")

    assert '<a href="">link</a>' in html


def test_python_extensions_are_opt_in_for_each_render() -> None:
    source = "> [!NOTE]\n> Example\n"

    assert "<blockquote>" in render_markdown(source)
    assert 'class="markdown-alert markdown-alert-note"' in render_markdown(
        source, extensions=(MarkdownExtension.ALERTS,),
    )
    assert "<blockquote>" in render_markdown(source)


@pytest.mark.parametrize("inspect_only", [False, True])
def test_parsed_nodes_do_not_retain_native_parent_cycles(monkeypatch, inspect_only) -> None:
    original = comrak.parse_document
    documents = []

    def record(*args, **kwargs):
        document = original(*args, **kwargs)
        documents.append(document)
        return document

    monkeypatch.setattr(comrak, "parse_document", record)
    source = '[Link](./guide.md) ![Image [description](./description.md)](./image.png)'
    if inspect_only:
        assert markdown_link_destinations(source) == ["./guide.md"]
    else:
        def failing_callback(href: str) -> str:
            raise ValueError("callback failed")

        with pytest.raises(ValueError, match="callback failed"):
            render_markdown(source, rewrite_link=failing_callback)

    pending = documents[:]
    assert pending and pending[0].children
    while pending:
        node = pending.pop()
        assert node.parent is None
        pending.extend(node.children)
