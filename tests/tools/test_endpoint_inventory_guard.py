from __future__ import annotations

from pathlib import Path
import runpy

import pytest

pytestmark = pytest.mark.unit


def test_endpoint_inventory_guard_reports_no_drift() -> None:
    repo_root = Path(__file__).resolve().parents[2]
    module = runpy.run_path(str(repo_root / "tools/check_endpoint_inventory.py"))
    collect_inventory_issues = module["collect_inventory_issues"]
    issues = collect_inventory_issues(repo_root)

    assert issues == []
