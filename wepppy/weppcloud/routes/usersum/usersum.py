from __future__ import annotations

import re
from functools import lru_cache
from html import escape as html_escape, unescape as html_unescape
from pathlib import Path
from typing import Dict, List, Tuple, TypedDict, Set
from urllib.parse import unquote, urlsplit, urlunsplit

from flask import Blueprint, abort, jsonify, redirect, render_template, request, url_for  # type: ignore[import-not-found]
from cmarkgfm import github_flavored_markdown_to_html as markdown_to_html  # type: ignore[import-not-found]
from wepppy.weppcloud.usersum_anchors import usersum_anchor_slug

usersum_bp = Blueprint('usersum', __name__, template_folder='templates')

_BASE_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _BASE_DIR.parents[3]
_DB_DIR = _BASE_DIR / 'db'
_SPEC_DIR = _BASE_DIR / 'input-file-specifications'
_WEPPCLOUD_DIR = _BASE_DIR / 'weppcloud'
_PATH_DIR = _BASE_DIR / 'path'
_CATEGORY_ROOTS: Dict[str, Path] = {
    'db': _DB_DIR,
    'input-file-specifications': _SPEC_DIR,
    'weppcloud': _WEPPCLOUD_DIR,
    'path': _PATH_DIR,
}

_PARAM_HEADER_RE = re.compile(r'^#### `([^`]+)` —\s*(.+)$')
_DETAIL_RE = re.compile(r'^- \*\*([^*]+)\*\*: ?(.*)$')
_WHITESPACE_RE = re.compile(r'\s+')
_ANCHOR_HREF_RE = re.compile(
    r'(<a\b[^>]*?\bhref\s*=\s*)(["\'])(.*?)(\2)',
    re.IGNORECASE | re.DOTALL,
)
_HEADING_RE = re.compile(
    r"<h(?P<level>[1-6])(?P<attrs>[^>]*)>(?P<body>.*?)</h\1>",
    re.IGNORECASE | re.DOTALL,
)
_HEADING_ID_ATTR_RE = re.compile(r'\bid\s*=\s*(["\'])(?P<id>.*?)\1', re.IGNORECASE | re.DOTALL)


class ParameterDetail(TypedDict):
    label: str
    text: str


class ParameterEntry(TypedDict):
    parameter: str
    summary: str
    details: List[ParameterDetail]
    section: str | None
    group: str | None
    file: str
    search_blob: str


def _friendly_display_name(filename: str) -> str:
    stem = filename[:-3] if filename.lower().endswith('.md') else filename
    title_source = re.sub(r'[._-]+', ' ', stem)
    return title_source.strip().title() or filename


def _list_markdown(directory: Path, category: str) -> List[Dict[str, str]]:
    if not directory.exists():
        return []

    items: List[Dict[str, str]] = []
    for path in sorted(directory.glob('*.md')):
        filename = path.name
        items.append({
            'filename': filename,
            'display_name': _friendly_display_name(filename),
            'url': url_for('usersum.view_markdown', category=category, filename=filename)
        })
    return items


@usersum_bp.route('/usersum/', strict_slashes=False)
def usersum_index():
    sections = []

    db_items = _list_markdown(_DB_DIR, 'db')
    if db_items:
        sections.append({'title': 'Parameter Databases', 'entries': db_items})

    spec_items = _list_markdown(_SPEC_DIR, 'input-file-specifications')
    if spec_items:
        sections.append({'title': 'Input File Specifications', 'entries': spec_items})

    wc_items = _list_markdown(_WEPPCLOUD_DIR, 'weppcloud')
    if wc_items:
        sections.append({'title': 'WEPPcloud Guides', 'entries': wc_items})

    path_items = _list_markdown(_PATH_DIR, 'path')
    if path_items:
        sections.append({'title': 'PATH Cost-Effective', 'entries': path_items})

    return render_template('usersum/index.htm', title='WEPPcloud UserSummary Documentation', sections=sections)


def _resolve_markdown_path(category: str, filename: str) -> Path:
    root = _CATEGORY_ROOTS.get(category)
    if root is None:
        abort(404)
        raise RuntimeError('unreachable')

    candidate = (root / filename).resolve()
    if not candidate.is_file() or root.resolve() not in candidate.parents:
        abort(404)
    return candidate


def _resolve_src_markdown_path(rel_path: str) -> Path:
    candidate = (_REPO_ROOT / rel_path).resolve()
    if not candidate.is_file():
        abort(404)
        raise RuntimeError('unreachable')
    if candidate.suffix.lower() != '.md' or _REPO_ROOT not in candidate.parents:
        abort(404)
    return candidate


def _route_for_repo_markdown(path: Path) -> str | None:
    resolved = path.resolve()

    for category, root in _CATEGORY_ROOTS.items():
        root_resolved = root.resolve()
        if root_resolved in resolved.parents:
            rel_filename = resolved.relative_to(root_resolved).as_posix()
            return url_for('usersum.view_markdown', category=category, filename=rel_filename)

    if _REPO_ROOT in resolved.parents:
        rel_path = resolved.relative_to(_REPO_ROOT).as_posix()
        return url_for('usersum.view_src_markdown', rel_path=rel_path)

    return None


def _resolve_linked_markdown_path(source_path: Path, href_path: str) -> Path | None:
    rel_token = href_path.strip()
    if not rel_token:
        return None

    candidate: Path
    if rel_token.startswith('/'):
        candidate = (_REPO_ROOT / rel_token.lstrip('/')).resolve()
    else:
        candidate = (source_path.parent / rel_token).resolve()

    if not candidate.is_file():
        return None
    if candidate.suffix.lower() != '.md':
        return None
    if _REPO_ROOT not in candidate.parents:
        return None
    return candidate


def _rewrite_markdown_href(source_path: Path, href: str) -> str:
    parsed = urlsplit(href)
    if parsed.scheme or parsed.netloc:
        return href

    path_part = parsed.path
    if not path_part or not path_part.lower().endswith('.md'):
        return href

    linked_path = _resolve_linked_markdown_path(source_path, unquote(path_part))
    if linked_path is None:
        return href

    routed_path = _route_for_repo_markdown(linked_path)
    if routed_path is None:
        return href

    return urlunsplit(('', '', routed_path, parsed.query, parsed.fragment))


def _rewrite_markdown_links(source_path: Path, content_html: str) -> str:
    def _replace(match: re.Match[str]) -> str:
        href_value = html_unescape(match.group(3))
        rewritten_href = _rewrite_markdown_href(source_path, href_value)
        if rewritten_href == href_value:
            return match.group(0)

        return (
            f"{match.group(1)}{match.group(2)}"
            f"{html_escape(rewritten_href, quote=True)}"
            f"{match.group(4)}"
        )

    return _ANCHOR_HREF_RE.sub(_replace, content_html)


def _add_heading_anchors(content_html: str) -> str:
    slug_counts: Dict[str, int] = {}

    def _reserve_slug(slug: str) -> str:
        count = slug_counts.get(slug, 0)
        if count == 0:
            slug_counts[slug] = 1
            return slug

        while True:
            candidate = f"{slug}-{count}"
            count += 1
            if candidate not in slug_counts:
                slug_counts[slug] = count
                slug_counts[candidate] = 1
                return candidate

    def _replace(match: re.Match[str]) -> str:
        level = match.group("level")
        attrs = match.group("attrs") or ""
        body = match.group("body")

        existing_id_match = _HEADING_ID_ATTR_RE.search(attrs)
        if existing_id_match is not None:
            existing_id = existing_id_match.group("id").strip()
            if existing_id:
                slug_counts.setdefault(existing_id, 1)
            return match.group(0)

        base_slug = usersum_anchor_slug(body) or "section"
        anchor_id = _reserve_slug(base_slug)
        escaped_anchor_id = html_escape(anchor_id, quote=True)
        return f'<h{level}{attrs} id="{escaped_anchor_id}">{body}</h{level}>'

    return _HEADING_RE.sub(_replace, content_html)


def _render_markdown_document(path: Path, *, title: str):
    markdown_source = path.read_text(encoding='utf-8')
    content_html = markdown_to_html(markdown_source)
    content_html = _add_heading_anchors(content_html)
    content_html = _rewrite_markdown_links(path, content_html)
    return render_template(
        'usersum/view.htm',
        title=title,
        content_html=content_html,
    )


@usersum_bp.route('/usersum/view/<category>/<path:filename>')
def view_markdown(category: str, filename: str):
    path = _resolve_markdown_path(category, filename)
    display_name = _friendly_display_name(path.name)
    return _render_markdown_document(path, title=display_name)


@usersum_bp.route('/usersum/src/<path:rel_path>')
def view_src_markdown(rel_path: str):
    path = _resolve_src_markdown_path(rel_path)
    display_name = str(path.relative_to(_REPO_ROOT))
    return _render_markdown_document(path, title=display_name)


@usersum_bp.route('/usersum/src//<path:rel_path>')
def view_src_markdown_legacy(rel_path: str):
    return redirect(url_for('usersum.view_src_markdown', rel_path=rel_path), code=308)


def _normalise_spaces(value: str) -> str:
    return _WHITESPACE_RE.sub(' ', value.strip())


def _coerce_bool(value: str | None) -> bool:
    if value is None:
        return False
    lowered = value.strip().lower()
    return lowered in {'1', 'true', 'yes', 'on', 'extended', '-e', '--extended'}


def _parse_parameter_file(path: Path) -> List[ParameterEntry]:
    section: str | None = None
    group: str | None = None
    entries: List[ParameterEntry] = []

    lines = path.read_text(encoding='utf-8').splitlines()
    index = 0
    while index < len(lines):
        line = lines[index]
        if line.startswith('## '):
            section = line[3:].strip()
            index += 1
            continue
        if line.startswith('### '):
            group = line[4:].strip()
            index += 1
            continue

        header_match = _PARAM_HEADER_RE.match(line)
        if header_match:
            parameter = header_match.group(1).strip()
            summary = header_match.group(2).strip()
            details: List[ParameterDetail] = []

            next_index = index + 1
            while next_index < len(lines):
                candidate = lines[next_index]
                if candidate.startswith('#### ') or candidate.startswith('### ') or candidate.startswith('## '):
                    break
                detail_match = _DETAIL_RE.match(candidate)
                if detail_match:
                    label = detail_match.group(1).strip()
                    text = detail_match.group(2).strip()
                    details.append({'label': label, 'text': text})
                next_index += 1

            detail_text = ' '.join(
                f"{detail['label']} {detail['text']}" for detail in details
            )

            entries.append({
                'parameter': parameter,
                'summary': summary,
                'details': details,
                'section': section,
                'group': group,
                'file': path.name,
                'search_blob': _normalise_spaces(' '.join([
                    parameter,
                    summary,
                    section or '',
                    group or '',
                    path.name,
                    detail_text,
                ])).lower(),
            })
            index = next_index
            continue

        index += 1

    return entries


@lru_cache(maxsize=1)
def _load_parameter_catalog() -> Tuple[Dict[str, List[ParameterEntry]], List[ParameterEntry]]:
    by_name: Dict[str, List[ParameterEntry]] = {}
    all_entries: List[ParameterEntry] = []

    if not _DB_DIR.exists():
        return by_name, all_entries

    for path in sorted(_DB_DIR.glob('*.md')):
        file_entries = _parse_parameter_file(path)
        for entry in file_entries:
            parameter_lower = entry['parameter'].lower()
            all_entries.append(entry)
            by_name.setdefault(parameter_lower, []).append(entry)

    return by_name, all_entries


def _format_parameter_entry(entry: ParameterEntry, include_extended: bool) -> List[str]:
    lines: List[str] = []
    lines.append(f"{entry['parameter']} — {entry['summary']}")

    context_parts: List[str] = []
    if entry['section']:
        context_parts.append(entry['section'])
    if entry['group']:
        context_parts.append(entry['group'])
    context_label = ' › '.join(context_parts)
    if context_label:
        lines.append(f"Context: {context_label} [{entry['file']}]")
    else:
        lines.append(f"Source: {entry['file']}")

    for detail in entry['details']:
        label = detail['label']
        if not include_extended and label.lower() == 'extended':
            continue
        lines.append(f"{label}: {detail['text']}")

    return lines


@usersum_bp.route('/usersum/api/parameter')
def usersum_api_parameter():
    name = request.args.get('name', '').strip()
    if not name:
        return jsonify({'error': {'message': 'Parameter name is required.'}}), 400

    include_extended = _coerce_bool(request.args.get('extended'))
    by_name, _ = _load_parameter_catalog()
    entries = by_name.get(name.lower())

    if not entries:
        return jsonify({'error': {'message': f'No entries found for "{name}".'}}), 404

    lines: List[str] = []
    for entry in entries:
        lines.extend(_format_parameter_entry(entry, include_extended))
        lines.append('')

    if lines:
        lines.pop()

    return jsonify({'lines': lines})


@usersum_bp.route('/usersum/api/keyword')
def usersum_api_keyword():
    keyword = request.args.get('q') or request.args.get('keyword')
    if not keyword:
        return jsonify({'error': {'message': 'Keyword is required.'}}), 400

    term = keyword.strip().lower()
    if not term:
        return jsonify({'error': {'message': 'Keyword is required.'}}), 400

    _, entries = _load_parameter_catalog()
    matches: List[ParameterEntry] = []
    seen: Set[Tuple[str, str, str | None, str | None, str]] = set()

    for entry in entries:
        if term in entry['search_blob']:
            identity = (entry['parameter'], entry['summary'], entry['section'], entry['group'], entry['file'])
            if identity in seen:
                continue
            seen.add(identity)
            matches.append(entry)
        if len(matches) >= 25:
            break

    if not matches:
        return jsonify({'lines': [f'No matches found for "{keyword}".']}), 200

    lines: List[str] = []
    for entry in matches:
        context_parts: List[str] = []
        if entry['section']:
            context_parts.append(entry['section'])
        if entry['group']:
            context_parts.append(entry['group'])
        context_label = ' › '.join(context_parts)
        if context_label:
            lines.append(f"{entry['parameter']} — {entry['summary']} [{context_label}] ({entry['file']})")
        else:
            lines.append(f"{entry['parameter']} — {entry['summary']} ({entry['file']})")

    return jsonify({'lines': lines})


__all__ = ['usersum_bp']
