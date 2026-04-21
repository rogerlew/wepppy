from __future__ import annotations

import importlib
import sys

import pytest


pytestmark = pytest.mark.unit


def test_rq_package_does_not_import_worker_eagerly(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.delitem(sys.modules, "wepppy.rq", raising=False)
    monkeypatch.delitem(sys.modules, "wepppy.rq.rq_worker", raising=False)

    module = importlib.import_module("wepppy.rq")

    assert "wepppy.rq.rq_worker" not in sys.modules
    assert "WepppyRqWorker" in getattr(module, "__all__", [])

    rq_worker_module = module.rq_worker
    assert rq_worker_module.__name__ == "wepppy.rq.rq_worker"
    assert "wepppy.rq.rq_worker" in sys.modules

    worker_cls = module.WepppyRqWorker
    assert worker_cls.__name__ == "WepppyRqWorker"
