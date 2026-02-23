#!/usr/bin/env python3
"""Report broad exception handlers in the codebase.

This tool detects:
  - bare ``except:``
  - ``except Exception`` / ``except BaseException``
  - tuples containing ``Exception`` / ``BaseException`` (for example ``except (ValueError, Exception):``)

Inline suppressions (on the ``except`` line) are honored:
  - ``# noqa: BLE001``
  - ``# broad-except: <reason>``
"""

from __future__ import annotations

import argparse
import ast
from collections import Counter
from dataclasses import asdict, dataclass, field
import json
from pathlib import Path
import re
import subprocess
import sys
from typing import Iterable, Sequence
import warnings

REPO_ROOT = Path(__file__).resolve().parents[1]
DEFAULT_SCAN_PREFIXES = ("wepppy", "services")
DEFAULT_ALLOWLIST_FILE = "docs/standards/broad-exception-boundary-allowlist.md"

_BROAD_BASES = ("Exception", "BaseException")
_ALL_BROAD_KINDS = ("bare-except", "except-Exception", "except-BaseException")
_TRY_NODE_TYPES: tuple[type[ast.AST], ...]
if hasattr(ast, "TryStar"):
    _TRY_NODE_TYPES = (ast.Try, ast.TryStar)
else:
    _TRY_NODE_TYPES = (ast.Try,)


@dataclass(frozen=True)
class ParseError:
    path: str
    error: str


@dataclass(frozen=True)
class AllowlistEntry:
    allowlist_id: str
    path: str
    line: int
    handler: str


@dataclass(frozen=True)
class AllowlistData:
    source_file: str
    entries: list[AllowlistEntry]


@dataclass(frozen=True)
class Finding:
    path: str
    lineno: int
    col: int
    kind: str
    line: str | None = None


@dataclass(frozen=True)
class Report:
    scanned_files: int
    scan_prefixes: list[str]
    allowlist_source: str | None = None
    findings: list[Finding] = field(default_factory=list)
    suppressed: int = 0
    allowlisted: int = 0
    parse_errors: list[ParseError] = field(default_factory=list)

    def counts(self) -> Counter[str]:
        return Counter(f.kind for f in self.findings)

    def by_file(self) -> Counter[str]:
        return Counter(f.path for f in self.findings)

    def to_json_dict(self) -> dict[str, object]:
        kind_counts = self.counts()
        return {
            "scanned_files": self.scanned_files,
            "scan_prefixes": list(self.scan_prefixes),
            "allowlist_source": self.allowlist_source,
            "findings_count": len(self.findings),
            "suppressed_count": self.suppressed,
            "allowlisted_count": self.allowlisted,
            "parse_errors_count": len(self.parse_errors),
            "kinds": {key: kind_counts.get(key, 0) for key in ("bare-except", "except-Exception", "except-BaseException")},
            "top_files": [{"path": path, "count": count} for path, count in self.by_file().most_common(20)],
            "findings": [asdict(finding) for finding in self.findings],
            "parse_errors": [asdict(error) for error in self.parse_errors],
        }


def _display_path(path: Path, *, repo_root: Path) -> str:
    try:
        return str(path.resolve().relative_to(repo_root))
    except ValueError:
        return str(path)


@dataclass(frozen=True)
class ChangedFile:
    status: str
    base_path: str | None
    current_path: str | None

    @property
    def status_code(self) -> str:
        return self.status[:1]


@dataclass(frozen=True)
class EnforcementFileReport:
    status: str
    base_path: str | None
    current_path: str
    base_findings: list[Finding] = field(default_factory=list)
    current_findings: list[Finding] = field(default_factory=list)
    new_findings: list[Finding] = field(default_factory=list)
    base_parse_error: ParseError | None = None
    current_parse_error: ParseError | None = None

    @property
    def base_count(self) -> int:
        return len(self.base_findings)

    @property
    def current_count(self) -> int:
        return len(self.current_findings)

    @property
    def delta(self) -> int:
        return self.current_count - self.base_count


@dataclass(frozen=True)
class EnforcementReport:
    base_ref: str
    merge_base: str
    scan_prefixes: list[str]
    allowlist_source: str | None = None
    files: list[EnforcementFileReport] = field(default_factory=list)

    @property
    def net_delta(self) -> int:
        return sum(f.delta for f in self.files)

    @property
    def has_new_findings(self) -> bool:
        return any(f.delta > 0 for f in self.files)

    @property
    def parse_errors(self) -> list[ParseError]:
        errors: list[ParseError] = []
        for f in self.files:
            if f.base_parse_error is not None:
                errors.append(f.base_parse_error)
            if f.current_parse_error is not None:
                errors.append(f.current_parse_error)
        return errors

    @property
    def current_parse_errors(self) -> list[ParseError]:
        errors: list[ParseError] = []
        for f in self.files:
            if f.current_parse_error is not None:
                errors.append(f.current_parse_error)
        return errors


def _git_ls_files(repo_root: Path, paths: Sequence[str]) -> list[Path]:
    proc = subprocess.run(
        ["git", "ls-files", "-z", "--", *paths],
        cwd=str(repo_root),
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git ls-files failed: {proc.stderr.strip()}")
    entries = [entry for entry in proc.stdout.split("\0") if entry]
    return [repo_root / entry for entry in entries]


def _git_merge_base(repo_root: Path, *, base_ref: str) -> str:
    proc = subprocess.run(
        ["git", "merge-base", "HEAD", base_ref],
        cwd=str(repo_root),
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git merge-base failed: {proc.stderr.strip()}")
    return proc.stdout.strip()


def _git_diff_name_status_z(repo_root: Path, *, base_commit: str, pathspecs: Sequence[str]) -> str:
    cmd = ["git", "diff", "--name-status", "-z", "--find-renames", base_commit]
    if pathspecs:
        cmd.extend(["--", *pathspecs])
    proc = subprocess.run(
        cmd,
        cwd=str(repo_root),
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        raise RuntimeError(f"git diff --name-status failed: {proc.stderr.strip()}")
    return proc.stdout


def parse_git_name_status_z(output: str) -> list[ChangedFile]:
    """Parse `git diff --name-status -z` output into ChangedFile records.

    Rename (`R*`) and copy (`C*`) records include both old and new paths.
    """
    if not output:
        return []

    parts = [part for part in output.split("\0") if part]
    changes: list[ChangedFile] = []
    idx = 0
    while idx < len(parts):
        status = parts[idx]
        idx += 1
        if not status:
            continue

        status_code = status[:1]
        if status_code in {"R", "C"}:
            if idx + 1 >= len(parts):
                raise ValueError(f"Malformed git name-status output near status={status!r}")
            old_path = parts[idx]
            new_path = parts[idx + 1]
            idx += 2
            changes.append(ChangedFile(status=status, base_path=old_path, current_path=new_path))
            continue

        if idx >= len(parts):
            raise ValueError(f"Malformed git name-status output near status={status!r}")
        path = parts[idx]
        idx += 1

        if status_code == "A":
            changes.append(ChangedFile(status=status, base_path=None, current_path=path))
        elif status_code == "D":
            changes.append(ChangedFile(status=status, base_path=path, current_path=None))
        else:
            changes.append(ChangedFile(status=status, base_path=path, current_path=path))

    return changes


def _path_is_under_prefixes(path: str, *, prefixes: Sequence[str]) -> bool:
    if not prefixes:
        return True
    for prefix in prefixes:
        if path == prefix or path.startswith(f"{prefix}/"):
            return True
    return False


def _is_suppressed_except_line(line: str) -> bool:
    if "# broad-except:" in line:
        return True
    lowered = line.lower()
    return "noqa" in lowered and "ble001" in lowered


def _is_markdown_table_delimiter(cells: Sequence[str]) -> bool:
    for cell in cells:
        token = cell.strip()
        if not token:
            continue
        if any(ch not in "-: " for ch in token):
            return False
    return True


def _allowlist_kinds_for_handler(handler: str) -> frozenset[str]:
    normalized = handler.strip().strip("`").lower()
    if normalized in {"except:", "bare except", "bare-except"}:
        return frozenset({"bare-except"})
    if "except baseexception" in normalized:
        return frozenset({"except-BaseException"})
    if "except exception" in normalized:
        return frozenset({"except-Exception"})
    if normalized in {"*", "any", "all"}:
        return frozenset(_ALL_BROAD_KINDS)
    raise ValueError(f"Unsupported allowlist handler: {handler!r}")


def load_allowlist(path: Path) -> AllowlistData | None:
    if not path.exists():
        return None

    try:
        raw_lines = path.read_text(encoding="utf-8").splitlines()
    except (OSError, UnicodeDecodeError) as exc:
        raise ValueError(f"Failed to read allowlist file {path}: {exc}") from exc

    entries: list[AllowlistEntry] = []
    in_table = False
    for raw_line in raw_lines:
        line = raw_line.strip()
        if not line.startswith("|"):
            continue

        cells = [cell.strip() for cell in line.strip("|").split("|")]
        if len(cells) < 4:
            continue

        header = [cell.lower() for cell in cells[:4]]
        if header == ["allowlist id", "file", "line", "handler"]:
            in_table = True
            continue
        if not in_table:
            continue
        if _is_markdown_table_delimiter(cells):
            continue

        allowlist_id, file_path, line_token, handler = cells[:4]
        if not allowlist_id or not file_path or not line_token or not handler:
            raise ValueError(f"Malformed allowlist row in {path}: {raw_line}")

        line_token_normalized = re.sub(r"[^0-9]", "", line_token)
        if not line_token_normalized:
            raise ValueError(f"Allowlist line number is not numeric in {path}: {raw_line}")

        entries.append(
            AllowlistEntry(
                allowlist_id=allowlist_id.strip("`"),
                path=file_path.strip("`"),
                line=int(line_token_normalized),
                handler=handler.strip("`"),
            )
        )

    return AllowlistData(source_file=str(path), entries=entries)


def build_allowlist_index(entries: Sequence[AllowlistEntry]) -> dict[tuple[str, int], frozenset[str]]:
    index: dict[tuple[str, int], frozenset[str]] = {}
    for entry in entries:
        key = (entry.path, entry.line)
        entry_kinds = _allowlist_kinds_for_handler(entry.handler)
        existing = index.get(key, frozenset())
        index[key] = frozenset(set(existing) | set(entry_kinds))
    return index


def _is_allowlisted_finding(
    *,
    path: str,
    lineno: int,
    kind: str,
    allowlist_index: dict[tuple[str, int], frozenset[str]] | None,
) -> bool:
    if not allowlist_index:
        return False
    key = (path, lineno)
    if key not in allowlist_index:
        return False
    return kind in allowlist_index[key]


def _flatten_exception_types(node: ast.expr) -> Iterable[ast.expr]:
    if isinstance(node, ast.Tuple):
        return node.elts
    return (node,)


def _broad_kinds_for_handler(handler: ast.ExceptHandler) -> set[str]:
    if handler.type is None:
        return {"bare-except"}

    kinds: set[str] = set()
    for exc_type in _flatten_exception_types(handler.type):
        name: str | None = None
        if isinstance(exc_type, ast.Name):
            name = exc_type.id
        elif isinstance(exc_type, ast.Attribute):
            name = exc_type.attr
        if name in _BROAD_BASES:
            kinds.add(f"except-{name}")
    return kinds


def scan_python_source(*, source: str, filename: str) -> tuple[list[tuple[int, int, str]], ParseError | None]:
    """Return (lineno, col, kind) records for broad handlers in a single file."""
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("ignore", SyntaxWarning)
            tree = ast.parse(source, filename=filename)
    except (SyntaxError, ValueError) as exc:
        return [], ParseError(path=filename, error=str(exc))

    findings: list[tuple[int, int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, _TRY_NODE_TYPES):
            continue
        for handler in node.handlers:
            for kind in sorted(_broad_kinds_for_handler(handler)):
                findings.append((handler.lineno, handler.col_offset, kind))
    return findings, None


def scan_python_source_for_findings(
    *,
    source: str,
    filename: str,
    allowlist_index: dict[tuple[str, int], frozenset[str]] | None = None,
) -> tuple[list[Finding], ParseError | None]:
    """Scan a single file's source and return unsuppressed Finding objects."""
    raw_findings, parse_error = scan_python_source(source=source, filename=filename)
    if parse_error is not None:
        return [], parse_error

    lines = source.splitlines()
    findings: list[Finding] = []
    for lineno, col, kind in raw_findings:
        line = lines[lineno - 1] if 1 <= lineno <= len(lines) else ""
        if _is_suppressed_except_line(line):
            continue
        if _is_allowlisted_finding(path=filename, lineno=lineno, kind=kind, allowlist_index=allowlist_index):
            continue
        findings.append(Finding(path=filename, lineno=lineno, col=col, kind=kind, line=line.rstrip("\n") or None))
    return findings, None


def scan_files(
    file_paths: Sequence[Path],
    *,
    repo_root: Path = REPO_ROOT,
    scan_prefixes: Sequence[str] = DEFAULT_SCAN_PREFIXES,
    allowlist_index: dict[tuple[str, int], frozenset[str]] | None = None,
    allowlist_source: str | None = None,
) -> Report:
    findings: list[Finding] = []
    parse_errors: list[ParseError] = []
    suppressed = 0
    allowlisted = 0

    for file_path in file_paths:
        if file_path.suffix != ".py":
            continue
        try:
            raw = file_path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            parse_errors.append(ParseError(path=_display_path(file_path, repo_root=repo_root), error=str(exc)))
            continue

        display_path = _display_path(file_path, repo_root=repo_root)
        lines = raw.splitlines()
        raw_findings, parse_error = scan_python_source(source=raw, filename=display_path)
        if parse_error is not None:
            parse_errors.append(parse_error)
            continue

        for lineno, col, kind in raw_findings:
            line = lines[lineno - 1] if 1 <= lineno <= len(lines) else ""
            if _is_suppressed_except_line(line):
                suppressed += 1
                continue
            if _is_allowlisted_finding(path=display_path, lineno=lineno, kind=kind, allowlist_index=allowlist_index):
                allowlisted += 1
                continue
            findings.append(
                Finding(
                    path=display_path,
                    lineno=lineno,
                    col=col,
                    kind=kind,
                    line=line.rstrip("\n") or None,
                )
            )

    scanned_files = sum(1 for path in file_paths if path.suffix == ".py")
    return Report(
        scanned_files=scanned_files,
        scan_prefixes=list(scan_prefixes),
        allowlist_source=allowlist_source,
        findings=sorted(findings, key=lambda f: (f.path, f.lineno, f.col, f.kind)),
        suppressed=suppressed,
        allowlisted=allowlisted,
        parse_errors=parse_errors,
    )


def build_report(
    *,
    repo_root: Path = REPO_ROOT,
    scan_prefixes: Sequence[str] = DEFAULT_SCAN_PREFIXES,
    allowlist_index: dict[tuple[str, int], frozenset[str]] | None = None,
    allowlist_source: str | None = None,
) -> Report:
    file_paths = _git_ls_files(repo_root, scan_prefixes)
    return scan_files(
        file_paths,
        repo_root=repo_root,
        scan_prefixes=scan_prefixes,
        allowlist_index=allowlist_index,
        allowlist_source=allowlist_source,
    )


def _git_show_text(repo_root: Path, *, rev: str, path: str) -> str | None:
    proc = subprocess.run(
        ["git", "show", f"{rev}:{path}"],
        cwd=str(repo_root),
        text=True,
        capture_output=True,
        check=False,
    )
    if proc.returncode != 0:
        return None
    return proc.stdout


def _compute_new_findings_by_kind(
    *,
    base_findings: Sequence[Finding],
    current_findings: Sequence[Finding],
) -> list[Finding]:
    """Return a deterministic slice of current findings representing net-new broad catches.

    Enforcement mode is net-new: decreases in one kind offset increases in another
    only at the total count level, but for output we attribute the net increase
    in a given file to a deterministic slice of current findings.
    """
    net_new = len(current_findings) - len(base_findings)
    if net_new <= 0:
        return []

    base_counts = Counter(f.kind for f in base_findings)
    current_by_kind: dict[str, list[Finding]] = {}
    for finding in sorted(current_findings, key=lambda f: (f.kind, f.lineno, f.col, f.path)):
        current_by_kind.setdefault(finding.kind, []).append(finding)

    new_findings: list[Finding] = []
    for kind, findings in sorted(current_by_kind.items()):
        base_count = base_counts.get(kind, 0)
        if len(findings) > base_count:
            new_findings.extend(findings[base_count:])
    if len(new_findings) > net_new:
        return new_findings[:net_new]
    return new_findings


def build_enforcement_file_report_from_sources(
    *,
    status: str,
    base_path: str | None,
    current_path: str,
    base_source: str,
    current_source: str,
    allowlist_index: dict[tuple[str, int], frozenset[str]] | None = None,
) -> EnforcementFileReport:
    base_display = base_path if base_path is not None else current_path
    base_findings, base_parse_error = scan_python_source_for_findings(
        source=base_source,
        filename=base_display,
        allowlist_index=allowlist_index,
    )
    current_findings, current_parse_error = scan_python_source_for_findings(
        source=current_source,
        filename=current_path,
        allowlist_index=allowlist_index,
    )
    return EnforcementFileReport(
        status=status,
        base_path=base_path,
        current_path=current_path,
        base_findings=base_findings,
        current_findings=current_findings,
        new_findings=_compute_new_findings_by_kind(base_findings=base_findings, current_findings=current_findings),
        base_parse_error=base_parse_error,
        current_parse_error=current_parse_error,
    )


def build_enforcement_report(
    *,
    repo_root: Path = REPO_ROOT,
    base_ref: str = "origin/master",
    scan_prefixes: Sequence[str] = DEFAULT_SCAN_PREFIXES,
    allowlist_index: dict[tuple[str, int], frozenset[str]] | None = None,
    allowlist_source: str | None = None,
) -> EnforcementReport:
    merge_base = _git_merge_base(repo_root, base_ref=base_ref)
    diff_output = _git_diff_name_status_z(repo_root, base_commit=merge_base, pathspecs=scan_prefixes)
    changes = parse_git_name_status_z(diff_output)

    changed_python_files: list[ChangedFile] = []
    for change in changes:
        if change.current_path is None:
            continue
        if not change.current_path.endswith(".py"):
            continue
        if not _path_is_under_prefixes(change.current_path, prefixes=scan_prefixes):
            continue
        changed_python_files.append(change)

    files: list[EnforcementFileReport] = []
    for change in changed_python_files:
        current_path = change.current_path
        assert current_path is not None

        current_file = repo_root / current_path
        try:
            current_source = current_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError) as exc:
            files.append(
                EnforcementFileReport(
                    status=change.status,
                    base_path=change.base_path,
                    current_path=current_path,
                    current_parse_error=ParseError(path=current_path, error=str(exc)),
                )
            )
            continue

        base_source = ""
        if change.base_path is not None:
            shown = _git_show_text(repo_root, rev=merge_base, path=change.base_path)
            if shown is not None:
                base_source = shown

        files.append(
            build_enforcement_file_report_from_sources(
                status=change.status,
                base_path=change.base_path,
                current_path=current_path,
                base_source=base_source,
                current_source=current_source,
                allowlist_index=allowlist_index,
            )
        )

    return EnforcementReport(
        base_ref=base_ref,
        merge_base=merge_base,
        scan_prefixes=list(scan_prefixes),
        allowlist_source=allowlist_source,
        files=sorted(files, key=lambda f: (f.current_path, f.status)),
    )


def format_enforcement_text_report(
    report: EnforcementReport,
    *,
    repo_root: Path = REPO_ROOT,
    max_violations: int = 50,
) -> str:
    lines: list[str] = []
    lines.append("Broad exception handler changed-file enforcement")
    lines.append("")
    lines.append(f"Repo root: {repo_root}")
    lines.append(f"Base ref: {report.base_ref}")
    lines.append(f"Merge base: {report.merge_base}")
    lines.append(f"Path filter: {', '.join(report.scan_prefixes)}")
    lines.append(f"Allowlist source: {report.allowlist_source or '(disabled)'}")
    lines.append(f"Changed Python files scanned: {len(report.files)}")

    if report.files:
        lines.append("")
        lines.append("Files:")
        for f in report.files:
            if f.base_path is not None and f.base_path != f.current_path:
                lines.append(f"  {f.status} {f.base_path} -> {f.current_path}")
            else:
                lines.append(f"  {f.status} {f.current_path}")

    parse_errors = report.parse_errors
    current_parse_errors = report.current_parse_errors
    if parse_errors:
        lines.append("")
        lines.append("Parse errors:")
        for err in parse_errors[: min(20, len(parse_errors))]:
            lines.append(f"  {err.path}: {err.error}")
        if len(parse_errors) > 20:
            lines.append(f"  ... ({len(parse_errors) - 20} more)")

    if report.files:
        lines.append("")
        lines.append("Per-file delta (unsuppressed broad catches):")
        for f in report.files:
            delta = f.delta
            delta_str = f"{delta:+d}"
            if f.base_path is not None and f.base_path != f.current_path:
                header = f"{f.status} {f.base_path} -> {f.current_path}"
            else:
                header = f"{f.status} {f.current_path}"
            lines.append(f"  {header} (base={f.base_count} current={f.current_count} delta={delta_str})")
            for finding in f.new_findings[: max_violations if max_violations > 0 else len(f.new_findings)]:
                suffix = f"  # {finding.line.strip()}" if finding.line else ""
                lines.append(f"    + {finding.path}:{finding.lineno}:{finding.col} {finding.kind}{suffix}")

    lines.append("")
    lines.append(f"Net delta (all changed files): {report.net_delta:+d}")
    if current_parse_errors:
        lines.append("Result: FAIL (parse errors in changed files)")
    elif report.has_new_findings:
        lines.append("Result: FAIL (per-file broad-catch increase detected in changed files)")
    else:
        lines.append("Result: PASS")

    return "\n".join(lines) + "\n"


def format_text_report(
    report: Report,
    *,
    repo_root: Path = REPO_ROOT,
    top_n: int = 10,
    max_findings: int = 50,
) -> str:
    kind_counts = report.counts()
    file_counts = report.by_file()

    lines: list[str] = []
    lines.append("Broad exception handler report")
    lines.append("")
    lines.append(f"Repo root: {repo_root}")
    lines.append(f"Scanned files: {report.scanned_files}")
    lines.append(f"Allowlist source: {report.allowlist_source or '(disabled)'}")
    lines.append(
        f"Findings: {len(report.findings)} "
        f"(suppressed: {report.suppressed}, allowlisted: {report.allowlisted}, parse errors: {len(report.parse_errors)})"
    )
    lines.append(
        "Kinds: "
        + ", ".join(
            f"{kind}={kind_counts.get(kind, 0)}"
            for kind in ("bare-except", "except-Exception", "except-BaseException")
        )
    )
    lines.append("")
    lines.append(f"Top files (by findings, n={top_n}):")
    for path, count in file_counts.most_common(top_n):
        lines.append(f"  {path}: {count}")

    if report.parse_errors:
        lines.append("")
        lines.append("Parse errors:")
        for err in report.parse_errors[: min(20, len(report.parse_errors))]:
            lines.append(f"  {err.path}: {err.error}")
        if len(report.parse_errors) > 20:
            lines.append(f"  ... ({len(report.parse_errors) - 20} more)")

    if report.findings:
        lines.append("")
        total = len(report.findings)
        shown = total if max_findings == 0 else min(total, max_findings)
        lines.append(f"Findings (showing {shown} of {total}):")
        for finding in report.findings[:shown]:
            suffix = f"  # {finding.line.strip()}" if finding.line else ""
            lines.append(f"  {finding.path}:{finding.lineno}:{finding.col} {finding.kind}{suffix}")
        if shown < total:
            lines.append(f"  ... ({total - shown} more; use --max-findings 0 to show all)")

    return "\n".join(lines) + "\n"


def parse_args(argv: Sequence[str]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "paths",
        nargs="*",
        help="Paths to scan (defaults to wepppy services). Passed to git ls-files.",
    )
    parser.add_argument(
        "--enforce-changed",
        action="store_true",
        help="Enforce a 'no per-file broad-catch increases' rule on changed Python files only (diff vs merge-base).",
    )
    parser.add_argument(
        "--base-ref",
        default="origin/master",
        help="Base git ref for --enforce-changed merge-base (default: origin/master).",
    )
    parser.add_argument(
        "--allowlist-file",
        default=DEFAULT_ALLOWLIST_FILE,
        help=f"Markdown allowlist file (default: {DEFAULT_ALLOWLIST_FILE}).",
    )
    parser.add_argument(
        "--no-allowlist",
        action="store_true",
        help="Disable allowlist suppression.",
    )
    parser.add_argument("--json", action="store_true", help="Emit JSON report to stdout.")
    parser.add_argument("--top", type=int, default=10, help="Number of top files to show in text report.")
    parser.add_argument(
        "--max-findings",
        type=int,
        default=50,
        help="Max findings to show in text report (0 shows all).",
    )
    return parser.parse_args(list(argv))


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(sys.argv[1:] if argv is None else argv)
    scan_prefixes = tuple(args.paths) if args.paths else DEFAULT_SCAN_PREFIXES
    allowlist_index: dict[tuple[str, int], frozenset[str]] | None = None
    allowlist_source: str | None = None
    if not args.no_allowlist:
        allowlist_path = REPO_ROOT / args.allowlist_file
        try:
            allowlist_data = load_allowlist(allowlist_path)
        except ValueError as exc:
            raise SystemExit(str(exc))
        if allowlist_data is not None:
            try:
                allowlist_index = build_allowlist_index(allowlist_data.entries)
            except ValueError as exc:
                raise SystemExit(f"Invalid allowlist entry in {allowlist_path}: {exc}")
            allowlist_source = allowlist_data.source_file

    if args.enforce_changed:
        if args.json:
            raise SystemExit("--json is not supported with --enforce-changed (enforcement mode emits text)")
        enforcement = build_enforcement_report(
            repo_root=REPO_ROOT,
            base_ref=args.base_ref,
            scan_prefixes=scan_prefixes,
            allowlist_index=allowlist_index,
            allowlist_source=allowlist_source,
        )
        sys.stdout.write(format_enforcement_text_report(enforcement, repo_root=REPO_ROOT))
        if enforcement.current_parse_errors:
            return 1
        return 1 if enforcement.has_new_findings else 0

    report = build_report(
        repo_root=REPO_ROOT,
        scan_prefixes=scan_prefixes,
        allowlist_index=allowlist_index,
        allowlist_source=allowlist_source,
    )
    if args.json:
        payload = report.to_json_dict()
        sys.stdout.write(json.dumps(payload, indent=2, sort_keys=True))
        sys.stdout.write("\n")
    else:
        sys.stdout.write(format_text_report(report, repo_root=REPO_ROOT, top_n=args.top, max_findings=args.max_findings))

    return 1 if report.findings else 0


if __name__ == "__main__":
    raise SystemExit(main())
