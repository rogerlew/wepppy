"""Copy lint contracts for source templates and published HTML."""

import subprocess
import sys
import unittest
from pathlib import Path

from tools.lint_html_content import lint


class TestHtmlContentLint(unittest.TestCase):
    def test_inline_nodes_entities_and_line_numbers(self):
        source = "<p>First paragraph</p>\n<p>Open <mark>WEPP</mark>&nbsp;<em>Cloud</em>.</p>"
        self.assertEqual(lint(source, ".html"), [(2, "WEPP\xa0Cloud", "product-name", "WEPPcloud")])
        self.assertEqual(lint("<p>WEPP</p><p>Cloud</p>", ".html"), [])

    def test_accessible_and_display_attributes(self):
        source = """
<img alt="WEPP Cloud" src="/weppcloud/image.png">
<optgroup label="WEPPCloud"></optgroup>
<input type="submit" value="WEPPCLOUD">
<div aria-valuetext="weppcloud" title="WEPP cloud"></div>
<input type value="internal">
"""
        self.assertEqual([line for line, *_ in lint(source, ".html")], [2, 3, 4, 5, 5])

    def test_visible_copy_inside_template_element(self):
        self.assertEqual(len(lint("<template><p>WEPP Cloud</p></template>", ".htm")), 1)

    def test_jinja_static_copy_and_technical_identifiers(self):
        source = """
{% set title = 'WEPP Cloud Sign In' %}
{{ usersum_doc_link('weppcloud', 'doc.md', 'Help using WEPPCloud') }}
{# WEPP Cloud #}
{{ control(label="weppcloud", value="weppcloud") }}
{% set repo = 'weppcloud-wbt' %}
"""
        self.assertEqual([line for line, *_ in lint(source, ".htm")], [2, 3, 5])

    def test_markdown_code_urls_and_text_in_links(self):
        source = "`weppcloud` and [WEPP Cloud home](https://wepp.cloud/weppcloud/)\n\n```\nWEPP Cloud\n```"
        self.assertEqual([word for _, word, *_ in lint(source, ".md")], ["WEPP Cloud"])

    def test_scientific_prose_and_journal_title(self):
        source = """<p>One metre, ten millimetres and two meters.</p>
<p>Cited in <i>Environmental Modelling &amp; Software</i>.</p>"""
        self.assertEqual(lint(source, ".html"), [
            (1, "metre", "us-spelling", "meter"),
            (1, "millimetres", "us-spelling", "millimeters"),
        ])

    def test_si_prefixes_and_symbols(self):
        source = "<p>1 metre, 5-metre grid, kilometres, micrometres, hectolitre, millilitres, quectolitres. Use L, l, mL, µm. Report tonnes, a tonne, tons, or a ton.</p>"
        actual = [(found, expected) for _, found, _, expected in lint(source, ".html")]
        self.assertCountEqual(actual, [
            ("metre", "meter"), ("metre", "meter"), ("kilometres", "kilometers"),
            ("micrometres", "micrometers"), ("hectolitre", "hectoliter"),
            ("millilitres", "milliliters"), ("quectolitres", "quectoliters"),
        ])

    def test_python_exception_and_docstring(self):
        source = '"""The weppcloud database key."""\nKEY = "weppcloud"\nraise ValueError("WEPP Cloud failed")'
        self.assertEqual(lint(source, ".py"), [(3, "WEPP Cloud", "product-name", "WEPPcloud")])

    def test_cli_accepts_rendered_html_on_stdin(self):
        root = Path(__file__).resolve().parents[2]
        for source, status in [("<p>Use WEPPcloud.</p>", 0), ("<p>Use WeppCloud.</p>", 1)]:
            with self.subTest(source=source):
                result = subprocess.run([sys.executable, "-m", "tools.lint_html_content", "-"],
                                        input=source, cwd=root, capture_output=True, text=True)
                self.assertEqual(result.returncode, status, result.stderr)
                if status:
                    self.assertIn("-:1: product-name:", result.stdout)
