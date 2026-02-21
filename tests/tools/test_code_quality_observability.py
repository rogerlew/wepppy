from __future__ import annotations

import json
from pathlib import Path
import runpy

import pytest

pytestmark = pytest.mark.unit


def _module() -> dict[str, object]:
    repo_root = Path(__file__).resolve().parents[2]
    return runpy.run_path(str(repo_root / "tools/code_quality_observability.py"))


def test_classify_severity_respects_threshold_bands() -> None:
    module = _module()
    classify_severity = module["classify_severity"]

    assert classify_severity("python_cc", 10) == "green"
    assert classify_severity("python_cc", 15) == "yellow"
    assert classify_severity("python_cc", 45) == "red"
    assert classify_severity("python_cc", None) == "unknown"


def test_trend_from_values_covers_all_states() -> None:
    module = _module()
    trend_from_values = module["trend_from_values"]

    assert trend_from_values(None, None) == "n/a"
    assert trend_from_values(None, 10) == "new"
    assert trend_from_values(10, None) == "removed"
    assert trend_from_values(10, 5) == "improved"
    assert trend_from_values(10, 10) == "unchanged"
    assert trend_from_values(10, 15) == "worsened"


def test_scope_filters_include_expected_paths() -> None:
    module = _module()
    is_python_scope = module["is_python_scope"]
    is_js_scope = module["is_js_scope"]

    assert is_python_scope("wepppy/rq/wepp_rq.py")
    assert not is_python_scope("wepppy/all_your_base/geo/ogrmerge.py")
    assert not is_python_scope("stubs/wepppy/rq/wepp_rq.pyi")

    assert is_js_scope("wepppy/weppcloud/controllers_js/wepp.js")
    assert is_js_scope("wepppy/weppcloud/static-src/tests/smoke/page-load.spec.js")
    assert is_js_scope("wepppy/weppcloud/static/js/gl-dashboard/state.js")
    assert not is_js_scope("wepppy/weppcloud/static/js/d3.js")
    assert not is_js_scope("wepppy/weppcloud/static-src/node_modules/pkg/index.js")


def test_load_changed_metric_exceptions_reads_valid_file(tmp_path: Path) -> None:
    module = _module()
    load_changed_metric_exceptions = module["load_changed_metric_exceptions"]

    exceptions_path = tmp_path / "exceptions.json"
    exceptions_path.write_text(
        json.dumps(
            {
                "changed_file_metric_exceptions": [
                    {
                        "path": "wepppy/nodb/core/*.py",
                        "metric": "python_cc",
                        "reason": "extraction deferred while preserving readability",
                        "owner": "nodb",
                        "expires_on": "2026-06-01",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    rules, source_path = load_changed_metric_exceptions(str(exceptions_path))
    assert source_path is not None
    assert source_path.endswith("exceptions.json")
    assert len(rules) == 1
    assert rules[0].path == "wepppy/nodb/core/*.py"
    assert rules[0].metric == "python_cc"
    assert rules[0].reason == "extraction deferred while preserving readability"
    assert rules[0].owner == "nodb"
    assert rules[0].expires_on == "2026-06-01"


def test_load_changed_metric_exceptions_rejects_invalid_metric(tmp_path: Path) -> None:
    module = _module()
    load_changed_metric_exceptions = module["load_changed_metric_exceptions"]

    exceptions_path = tmp_path / "exceptions.json"
    exceptions_path.write_text(
        json.dumps(
            {
                "changed_file_metric_exceptions": [
                    {
                        "path": "wepppy/nodb/core/*.py",
                        "metric": "python_halstead",
                        "reason": "invalid metric name test",
                    }
                ]
            }
        ),
        encoding="utf-8",
    )

    with pytest.raises(ValueError, match="invalid 'metric'"):
        load_changed_metric_exceptions(str(exceptions_path))


def test_match_changed_metric_exception_supports_globs() -> None:
    module = _module()
    changed_metric_exception = module["ChangedMetricException"]
    match_changed_metric_exception = module["match_changed_metric_exception"]

    rules = [
        changed_metric_exception(
            path="wepppy/nodb/core/*.py",
            metric="python_cc",
            reason="tracked readability tradeoff",
            owner="nodb",
            expires_on=None,
        ),
    ]

    matched = match_changed_metric_exception("wepppy/nodb/core/watershed.py", "python_cc", rules)
    assert matched is not None
    assert matched.reason == "tracked readability tradeoff"
    assert match_changed_metric_exception("wepppy/nodb/core/watershed.py", "python_file_sloc", rules) is None
