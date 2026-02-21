from __future__ import annotations

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
