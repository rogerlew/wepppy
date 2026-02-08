from __future__ import annotations

from pathlib import Path
import runpy

import pytest

pytestmark = pytest.mark.unit


def test_route_contract_checklist_guard_reports_no_drift() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    module = runpy.run_path(str(repo_root / "tools/check_route_contract_checklist.py"))
    collect_checklist_issues = module["collect_checklist_issues"]
    issues = collect_checklist_issues(repo_root)

    assert issues == []
