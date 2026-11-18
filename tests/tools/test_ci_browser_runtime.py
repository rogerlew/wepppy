"""A passing browser process must not hide skipped authenticated coverage."""
import json
from pathlib import Path
import runpy

import pytest


@pytest.fixture
def validate():
    return runpy.run_path(str(Path(__file__).parents[1] / "ci_browser_runtime.py"))["validate_reports"]


def test_all_skipped_suite_is_not_accepted(tmp_path, validate):
    report = tmp_path / "result.json"
    report.write_text(json.dumps({"stats": {"expected": 0, "skipped": 12}}))
    with pytest.raises(RuntimeError, match="no passing checks"):
        validate(report, tmp_path / "missing.json", "controllers")


def test_authenticated_pages_must_be_scanned(tmp_path, validate):
    report = tmp_path / "result.json"
    report.write_text(json.dumps({"stats": {"expected": 4}}))
    axe = tmp_path / "axe.json"
    pages = ["ui-components-theme-lab", "ui-components-report-a11y", "weppcloud-root", "weppcloud-interfaces"]
    axe.write_text(json.dumps({"scans": [{"pageId": page} for page in pages]}))
    with pytest.raises(RuntimeError, match="runs0-dashboard"):
        validate(report, axe, "accessibility")
    pages += ["weppcloud-profile", "weppcloud-config-builder", "runs0-dashboard"]
    axe.write_text(json.dumps({"scans": [{"pageId": page} for page in pages]}))
    validate(report, axe, "accessibility")


def test_missing_report_is_not_accepted(tmp_path, validate):
    with pytest.raises(FileNotFoundError):
        validate(tmp_path / "missing.json", tmp_path / "axe.json", "theme-metrics")
