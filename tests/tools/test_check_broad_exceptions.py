from __future__ import annotations

import ast
from pathlib import Path

import pytest

from tools import check_broad_exceptions as cbe

pytestmark = pytest.mark.unit


def _scan(tmp_path: Path, sources: dict[str, str]) -> cbe.Report:
    paths: list[Path] = []
    for relpath, source in sources.items():
        path = tmp_path / relpath
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(source, encoding="utf-8")
        paths.append(path)
    return cbe.scan_files(paths, repo_root=tmp_path, scan_prefixes=["fixture"])


def test_detects_bare_except_and_exception_and_tuple(tmp_path: Path) -> None:
    report = _scan(
        tmp_path,
        {
            "a.py": """
def one():
    try:
        1 / 0
    except:
        return 1
""",
            "b.py": """
def two():
    try:
        1 / 0
    except Exception:
        return 2
""",
            "c.py": """
def three():
    try:
        1 / 0
    except (ValueError, Exception):
        return 3
""",
        },
    )

    kinds = report.counts()
    assert kinds["bare-except"] == 1
    assert kinds["except-Exception"] == 2
    assert kinds["except-BaseException"] == 0


def test_detects_try_star_exception_handler(tmp_path: Path) -> None:
    if not hasattr(ast, "TryStar"):
        pytest.skip("Python runtime does not support TryStar")
    report = _scan(
        tmp_path,
        {
            "star.py": """
def one():
    try:
        1 / 0
    except* Exception:
        return 1
""",
        },
    )
    assert report.counts()["except-Exception"] == 1


def test_honors_inline_suppressions(tmp_path: Path) -> None:
    report = _scan(
        tmp_path,
        {
            "a.py": """
def one():
    try:
        1 / 0
    except Exception:  # noqa: BLE001
        return 1
""",
            "b.py": """
def two():
    try:
        1 / 0
    except:  # broad-except: boundary wrapper (legacy contract)
        return 2
""",
            "c.py": """
def three():
    try:
        1 / 0
    except BaseException:
        return 3
""",
        },
    )

    assert report.suppressed == 2
    assert report.counts()["except-BaseException"] == 1


def test_report_and_json_output_are_sane(tmp_path: Path) -> None:
    report = _scan(
        tmp_path,
        {
            "pkg/mod.py": """
def one():
    try:
        1 / 0
    except Exception:
        return 1
""",
            "pkg/bad_syntax.py": "def nope(:\n  pass\n",
        },
    )

    text = cbe.format_text_report(report, repo_root=tmp_path, top_n=5, max_findings=0)
    assert "Broad exception handler report" in text
    assert "Findings:" in text
    assert "Top files" in text
    assert "pkg/mod.py" in text
    assert "Parse errors:" in text

    payload = report.to_json_dict()
    assert payload["scanned_files"] == 2
    assert payload["findings_count"] == 1
    assert payload["parse_errors_count"] == 1
    assert payload["allowlisted_count"] == 0
    assert payload["kinds"]["except-Exception"] == 1


def test_load_allowlist_parses_markdown_table(tmp_path: Path) -> None:
    allowlist_path = tmp_path / "allowlist.md"
    allowlist_path.write_text(
        """# Allowlist

| Allowlist ID | File | Line | Handler | Owner | Rationale | Expires on |
|-------------|------|-----:|---------|-------|-----------|------------|
| `AL-1` | `wepppy/a.py` | 12 | `except Exception` | owner | reason | 2026-05-31 |
| `AL-2` | `wepppy/b.py` | 15 | `except:` | owner | reason | 2026-05-31 |
""",
        encoding="utf-8",
    )
    data = cbe.load_allowlist(allowlist_path)
    assert data is not None
    assert data.source_file == str(allowlist_path)
    assert [(e.allowlist_id, e.path, e.line, e.handler) for e in data.entries] == [
        ("AL-1", "wepppy/a.py", 12, "except Exception"),
        ("AL-2", "wepppy/b.py", 15, "except:"),
    ]


def test_build_allowlist_index_rejects_unsupported_handler() -> None:
    with pytest.raises(ValueError, match="Unsupported allowlist handler"):
        cbe.build_allowlist_index(
            [
                cbe.AllowlistEntry(
                    allowlist_id="AL-3",
                    path="wepppy/a.py",
                    line=10,
                    handler="except (ValueError, RuntimeError)",
                )
            ]
        )


def test_allowlist_suppresses_matching_findings(tmp_path: Path) -> None:
    path = tmp_path / "wepppy/a.py"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        """
def one():
    try:
        1 / 0
    except Exception:
        return 1

def two():
    try:
        1 / 0
    except:
        return 2
""",
        encoding="utf-8",
    )
    allowlist = {
        ("wepppy/a.py", 5): frozenset({"except-Exception"}),
        ("wepppy/a.py", 11): frozenset({"bare-except"}),
    }
    report = cbe.scan_files(
        [path],
        repo_root=tmp_path,
        scan_prefixes=["wepppy"],
        allowlist_index=allowlist,
        allowlist_source="inline-test",
    )
    assert report.findings == []
    assert report.allowlisted == 2
    assert report.allowlist_source == "inline-test"


def test_parse_git_name_status_z_supports_rename_add_delete() -> None:
    output = "\0".join(
        [
            "M",
            "wepppy/a.py",
            "R100",
            "wepppy/old.py",
            "wepppy/new.py",
            "A",
            "services/new_service.py",
            "D",
            "wepppy/dead.py",
            "",
        ]
    )
    changes = cbe.parse_git_name_status_z(output)
    assert [(c.status, c.base_path, c.current_path) for c in changes] == [
        ("M", "wepppy/a.py", "wepppy/a.py"),
        ("R100", "wepppy/old.py", "wepppy/new.py"),
        ("A", None, "services/new_service.py"),
        ("D", "wepppy/dead.py", None),
    ]


def test_build_enforcement_file_report_counts_only_net_new_unsuppressed() -> None:
    base_source = """
def one():
    try:
        1 / 0
    except Exception:
        return 1
"""
    current_source = """
def one():
    try:
        1 / 0
    except Exception:
        return 1

def two():
    try:
        1 / 0
    except Exception:
        return 2
"""
    file_report = cbe.build_enforcement_file_report_from_sources(
        status="M",
        base_path="wepppy/a.py",
        current_path="wepppy/a.py",
        base_source=base_source,
        current_source=current_source,
    )
    assert file_report.base_count == 1
    assert file_report.current_count == 2
    assert file_report.delta == 1
    assert len(file_report.new_findings) == 1
    assert file_report.new_findings[0].kind == "except-Exception"


def test_build_enforcement_file_report_respects_allowlist() -> None:
    base_source = "def one():\n    return 1\n"
    current_source = """
def one():
    try:
        1 / 0
    except Exception:
        return 1
"""
    file_report = cbe.build_enforcement_file_report_from_sources(
        status="M",
        base_path="wepppy/a.py",
        current_path="wepppy/a.py",
        base_source=base_source,
        current_source=current_source,
        allowlist_index={("wepppy/a.py", 5): frozenset({"except-Exception"})},
    )
    assert file_report.base_count == 0
    assert file_report.current_count == 0
    assert file_report.delta == 0
    assert file_report.new_findings == []


def test_build_enforcement_file_report_does_not_list_kind_swap_when_net_delta_is_zero() -> None:
    base_source = """
def one():
    try:
        1 / 0
    except:
        return 1
"""
    current_source = """
def one():
    try:
        1 / 0
    except Exception:
        return 1
"""
    file_report = cbe.build_enforcement_file_report_from_sources(
        status="M",
        base_path="wepppy/a.py",
        current_path="wepppy/a.py",
        base_source=base_source,
        current_source=current_source,
    )
    assert file_report.base_count == 1
    assert file_report.current_count == 1
    assert file_report.delta == 0
    assert file_report.new_findings == []


def test_enforcement_report_flags_per_file_net_new_findings_even_when_global_delta_is_zero() -> None:
    base_source_two = """
def one():
    try:
        1 / 0
    except Exception:
        return 1

def two():
    try:
        1 / 0
    except Exception:
        return 2
"""
    current_source_one = """
def one():
    try:
        1 / 0
    except Exception:
        return 1
"""
    file_a = cbe.build_enforcement_file_report_from_sources(
        status="M",
        base_path="wepppy/a.py",
        current_path="wepppy/a.py",
        base_source=base_source_two,
        current_source=current_source_one,
    )
    file_b = cbe.build_enforcement_file_report_from_sources(
        status="A",
        base_path=None,
        current_path="wepppy/b.py",
        base_source="",
        current_source=current_source_one,
    )
    enforcement = cbe.EnforcementReport(
        base_ref="origin/master",
        merge_base="deadbeef",
        scan_prefixes=["wepppy"],
        files=[file_a, file_b],
    )
    assert file_a.delta == -1
    assert file_b.delta == 1
    assert enforcement.net_delta == 0
    assert enforcement.has_new_findings


def test_enforcement_current_parse_error_is_recorded() -> None:
    file_report = cbe.build_enforcement_file_report_from_sources(
        status="M",
        base_path="wepppy/a.py",
        current_path="wepppy/a.py",
        base_source="def ok():\n    return 1\n",
        current_source="def nope(:\n  pass\n",
    )
    assert file_report.current_parse_error is not None
    enforcement = cbe.EnforcementReport(
        base_ref="origin/master",
        merge_base="deadbeef",
        scan_prefixes=["wepppy"],
        files=[file_report],
    )
    assert len(enforcement.current_parse_errors) == 1
