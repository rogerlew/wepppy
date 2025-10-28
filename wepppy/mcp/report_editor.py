from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Mapping, Optional

from wepppy.mcp.base import mcp_tool, validate_run_scope
from wepppy.weppcloud.utils.helpers import get_wd

try:
    import markdown_edit_py as edit
    import markdown_extract_py as mde
except ImportError as exc:  # pragma: no cover - bindings installed in production
    edit = None  # type: ignore[assignment]
    mde = None  # type: ignore[assignment]
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None


def _ensure_bindings() -> None:
    if mde is None or edit is None or _IMPORT_ERROR is not None:
        raise RuntimeError(
            "markdown_extract_py / markdown_edit_py bindings are not available. "
            "Run maturin develop in the CAO virtualenv."
        )


def _run_root(runid: str) -> Path:
    root = Path(get_wd(runid))
    if not root.exists():
        raise FileNotFoundError(f"Run directory not found for {runid}")
    return root


def _report_path(runid: str, report_id: str) -> Path:
    if "/" in report_id or "\\" in report_id or ".." in report_id:
        raise ValueError("report_id must be a simple filename without path separators")
    path = _run_root(runid) / "reports" / f"{report_id}.md"
    if not path.exists():
        raise FileNotFoundError(f"Report {report_id} not found in run {runid}")
    return path


@mcp_tool()
def list_report_sections(
    runid: str, report_id: str, _jwt_claims: Mapping[str, Any] | None = None
) -> List[Dict[str, Any]]:
    """
    Return high-level metadata for each markdown section.
    """

    if _jwt_claims is None:
        raise PermissionError("Missing JWT claims for run validation")
    validate_run_scope(runid, _jwt_claims)
    _ensure_bindings()

    draft_path = _report_path(runid, report_id)
    sections = mde.extract_sections_from_file(".*", str(draft_path), all_matches=True)  # type: ignore[union-attr]

    return [
        {
            "heading": section.heading,
            "level": section.level,
            "title": section.title,
            "has_content": bool(section.body.strip()),
        }
        for section in sections
    ]


@mcp_tool()
def read_report_section(
    runid: str,
    report_id: str,
    heading_pattern: str,
    _jwt_claims: Mapping[str, Any] | None = None,
) -> str:
    """
    Extract the first matching section body from a markdown report.
    """

    if _jwt_claims is None:
        raise PermissionError("Missing JWT claims for run validation")
    validate_run_scope(runid, _jwt_claims)
    _ensure_bindings()

    draft_path = _report_path(runid, report_id)
    matches = mde.extract_from_file(  # type: ignore[union-attr]
        heading_pattern, str(draft_path), all_matches=True
    )
    if not matches:
        raise ValueError(f"No section matching '{heading_pattern}' found")
    return matches[0]


@mcp_tool()
def replace_report_section(
    runid: str,
    report_id: str,
    heading_pattern: str,
    new_content: str,
    *,
    keep_heading: bool = True,
    _jwt_claims: Mapping[str, Any] | None = None,
) -> Dict[str, Any]:
    """
    Replace the content of a markdown section using the PyO3 edit bindings.
    """

    if _jwt_claims is None:
        raise PermissionError("Missing JWT claims for run validation")
    validate_run_scope(runid, _jwt_claims)
    _ensure_bindings()

    draft_path = _report_path(runid, report_id)
    result = edit.replace(  # type: ignore[union-attr]
        str(draft_path),
        heading_pattern,
        new_content,
        keep_heading=keep_heading,
        backup=True,
    )

    payload: Dict[str, Any] = {
        "applied": getattr(result, "applied", False),
        "messages": list(getattr(result, "messages", []) or []),
        "written_path": getattr(result, "written_path", None),
    }

    if not payload["applied"]:
        raise ValueError(
            f"Replace operation did not apply any changes for pattern '{heading_pattern}'"
        )

    return payload
