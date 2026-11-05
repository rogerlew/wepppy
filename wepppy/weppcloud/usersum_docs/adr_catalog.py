"""Live discovery of public Architecture Decision Records from the repository."""

from dataclasses import dataclass
from datetime import date
from pathlib import Path
import re

_FILENAME = re.compile(r"(ADR-([0-9]+))-[^/\\]+\.md")
_DATE_LABEL = r"(?:\*\*Date:\*\*|\*\*Date\*\*:|Date:)"
_DATE_FIELD = re.compile(
    r"^\s*(?:[-*+]\s+)?(?:" + _DATE_LABEL
    + r"|(?:\*\*)?Status(?::\*\*|\*\*:|:).*?\s(?<!Review )" + _DATE_LABEL + r")\s*(.*)$"
)


@dataclass(frozen=True)
class AdrRecord:
    filename: str
    identifier: str
    number: int
    title: str
    recorded_date: date | None


def _root(repo_root: Path) -> Path | None:
    root = repo_root / "docs" / "adrs"
    if root.is_symlink() or not root.is_dir() or not root.resolve().is_relative_to(repo_root.resolve()):
        return None
    return root


def resolve_adr(repo_root: Path, filename: str) -> Path | None:
    """Apply the same direct-file boundary to listing, detail and link routing."""
    if not _FILENAME.fullmatch(filename):
        return None
    root = _root(repo_root)
    if root is None:
        return None
    path = root / filename
    if path.is_symlink() or not path.is_file():
        return None
    return path


def read_adr(path: Path) -> AdrRecord:
    source = path.read_text(encoding="utf-8")
    title = None
    recorded_date = None
    date_seen = False
    preamble = True
    fence = None
    previous = ""
    for line in source.splitlines():
        stripped = line.strip()
        marker = re.match(r"^ {0,3}(`{3,}|~{3,})", line)
        if marker:
            token = marker[1]
            if fence is None:
                fence = token
            elif token[0] == fence[0] and len(token) >= len(fence) and stripped == token:
                fence = None
            previous = ""
            continue
        if fence:
            continue
        heading = re.match(r"^ {0,3}#\s+(.+?)\s*#*\s*$", line)
        if title is None:
            if heading:
                title = heading[1]
            elif previous and re.fullmatch(r" {0,3}=+\s*", line):
                title = previous.strip()
        if re.match(r"^ {0,3}#{2,6}(?:\s|$)", line) or (previous and re.fullmatch(r" {0,3}-+\s*", line)):
            preamble = False
        field = _DATE_FIELD.match(line) if preamble and not date_seen else None
        if field:
            date_seen = True
            token = re.match(r"([0-9]{4}-[0-9]{2}-[0-9]{2})(?![0-9])", field[1])
            if token:
                try:
                    recorded_date = date.fromisoformat(token[1])
                except ValueError:
                    # Invalid recorded dates stay visible as undated records.
                    pass
        previous = line
    match = _FILENAME.fullmatch(path.name)
    if match is None:
        raise ValueError(f"Not an ADR filename: {path.name}")
    return AdrRecord(path.name, match[1], int(match[2]), title or path.name, recorded_date)


def discover_adrs(repo_root: Path) -> list[AdrRecord]:
    root = _root(repo_root)
    if root is None:
        return []
    records = [read_adr(path) for path in root.iterdir() if resolve_adr(repo_root, path.name) is not None]
    return sorted(records, key=lambda item: (item.recorded_date is not None, item.recorded_date or date.min, item.number, item.filename), reverse=True)
