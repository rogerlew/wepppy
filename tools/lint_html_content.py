"""Lint WEPPcloud copy in HTML, help pages and selected user-facing messages."""

from __future__ import annotations

import argparse
import ast
from bisect import bisect_right
from html import unescape
from html.parser import HTMLParser
from pathlib import Path
import subprocess
import sys

from jinja2 import Environment, TemplateSyntaxError

from tools.ui_spelling_rules import spelling_findings
from wepppy.markdown_render import render_markdown


ROOT = Path(__file__).resolve().parents[1]
SOURCES = (
    ":(glob)wepppy/**/*.htm", ":(glob)wepppy/**/*.html",
    ":(glob)wepppy/weppcloud/routes/usersum/weppcloud/**/*.md",
    ":(glob)wepppy/weppcloud/routes/usersum/input-file-specifications/**/*.md",
    ":(glob)wepppy/weppcloud/routes/usersum/db/**/*.md",
    ":(glob)wepppy/nodb/**/ENDUSER.md", ":(glob)wepppy/nodb/mods/*/README.md",
    ":(glob)docs/user-guide/**/*.md",
    "wepppy/export/ermit_input.py", "wepppy/nodb/mods/ag_fields/ag_fields.py",
    "wepppy/weppcloud/routes/nodb_api/project_bp.py",
    ":(exclude,glob)**/vendor/**", ":(exclude,glob)**/node_modules/**",
)
JINJA = Environment(keep_trailing_newline=True)
HIDDEN = {"code", "pre", "script", "style"}
INLINE = {"a", "abbr", "b", "bdi", "bdo", "cite", "data", "del", "em", "i",
          "ins", "label", "mark", "q", "s", "small", "span", "strong", "sub", "sup", "u"}
LABELS = {"alt", "aria-label", "aria-description", "aria-valuetext", "placeholder", "title"}


def located_findings(text, line):
    """Attach text-relative positions to rule diagnostics."""
    for match, rule, expected in spelling_findings(text):
        yield line + text.count("\n", 0, match.start()), match[0], rule, expected


class ContentLint(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.hidden = []
        self.parts = []
        self.findings = []

    def check_parts(self):
        offsets, lines, chunks = [], [], []
        length = 0
        for line, chunk in self.parts:
            offsets.append(length)
            lines.append(line)
            chunks.append(chunk)
            length += len(chunk)
        for match, rule, expected in spelling_findings("".join(chunks)):
            index = bisect_right(offsets, match.start()) - 1
            line = lines[index] + chunks[index].count("\n", 0, match.start() - offsets[index])
            self.findings.append((line, match[0], rule, expected))
        self.parts.clear()

    def handle_starttag(self, tag, attrs):
        if tag not in INLINE:
            self.check_parts()
        if tag in HIDDEN:
            self.hidden.append(tag)
        if self.hidden:
            return
        labels = LABELS
        if tag in {"option", "optgroup", "track"}:
            labels = labels | {"label"}
        if tag == "input" and (dict(attrs).get("type") or "").lower() in {"submit", "button", "reset"}:
            labels = labels | {"value"}
        for name, value in attrs:
            if name in labels and value:
                self.findings.extend(located_findings(value, self.getpos()[0]))

    def handle_endtag(self, tag):
        if tag not in INLINE:
            self.check_parts()
        if self.hidden and tag == self.hidden[-1]:
            self.hidden.pop()

    def handle_data(self, data):
        if data and not self.hidden:
            self.parts.append((self.getpos()[0], data))

    def close(self):
        super().close()
        self.check_parts()


def lint_python(source):
    tree = ast.parse(source)
    docstrings = set()
    for scope in ast.walk(tree):
        if isinstance(scope, (ast.Module, ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)):
            if ast.get_docstring(scope, clean=False) is not None:
                docstrings.add(scope.body[0].value)
    findings = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Constant) or not isinstance(node.value, str) or node in docstrings:
            continue
        if node.value == "weppcloud":  # AgFields database key
            continue
        findings.extend(located_findings(node.value, node.lineno))
    return findings


def lint_template(source, parser):
    """Keep HTML source lines and check literal copy passed through Jinja macros."""
    markup = []
    previous = []
    for line, kind, value in JINJA.lex(source):
        if kind == "data":
            markup.append(value)
            continue
        if kind.endswith("_begin"):
            previous.clear()
            markup.append(" ")
        if kind == "string":
            literal = unescape(value[1:-1])
            # Lowercase is also a positional category/key in helpers such as usersum_doc_link.
            display_param = len(previous) >= 2 and previous[-2] in LABELS | {"label"} and previous[-1] == "="
            if literal not in {"weppcloud", "weppcloud-wbt"} or not previous or display_param:
                parser.findings.extend(located_findings(literal, line))
        if kind not in {"whitespace", "data"} and not kind.endswith("_begin"):
            previous.append(value)
        markup.append("\n" * value.count("\n"))
    parser.feed("".join(markup))


def lint(source, suffix):
    if suffix == ".py":
        return lint_python(source)
    parser = ContentLint()
    if suffix == ".md":
        parser.feed(render_markdown(source))
    elif suffix.lower() in {".html", ".htm"} and any(marker in source for marker in ("{{", "{%", "{#")):
        lint_template(source, parser)
    else:
        parser.feed(source)
    parser.close()
    return sorted(parser.findings)


def main():
    cli = argparse.ArgumentParser(description=__doc__)
    cli.add_argument("files", nargs="*", help="HTML, Markdown, Python, or - for rendered HTML on stdin")
    files = cli.parse_args().files
    if not files:
        tracked = subprocess.check_output(["git", "ls-files", "-z", "--", *SOURCES], cwd=ROOT)
        files = [str(ROOT / name.decode()) for name in tracked.split(b"\0") if name]
    errors = 0
    for name in files:
        path = Path(name)
        try:
            source = sys.stdin.read() if name == "-" else path.read_text(encoding="utf-8")
            findings = lint(source, path.suffix)
        except (OSError, UnicodeError, SyntaxError, TemplateSyntaxError) as exc:
            print(f"{name}: {exc}", file=sys.stderr)
            errors += 1
            continue
        for line, spelling, rule, expected in findings:
            location = "rendered line " if path.suffix == ".md" else ""
            label = path.relative_to(ROOT) if path.is_relative_to(ROOT) else path
            print(f"{label}:{location}{line}: {rule}: {spelling!r} should be {expected!r}")
            errors += 1
    print(f"HTML content lint checked {len(files)} inputs with {errors} findings.", file=sys.stderr)
    return int(bool(errors))


if __name__ == "__main__":
    raise SystemExit(main())
