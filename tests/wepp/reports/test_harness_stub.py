from pathlib import Path

import pytest

from wepppy.wepp.reports.harness import ReportHarness


def test_harness_registry_smoke(tmp_path: Path):
    harness = ReportHarness()

    called = []

    def ok_factory(run_dir: Path):
        called.append(run_dir)
        return object()

    def failing_factory(run_dir: Path):
        raise RuntimeError("boom")

    harness.register("ok", ok_factory)
    harness.register("fail", failing_factory)

    results = harness.smoke(tmp_path)

    assert results["ok"] is True
    assert isinstance(results["fail"], RuntimeError)
    assert called == [tmp_path]

    with pytest.raises(RuntimeError):
        harness.smoke(tmp_path, raise_on_error=True)
