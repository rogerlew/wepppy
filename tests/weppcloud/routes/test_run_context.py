from __future__ import annotations

from pathlib import Path

import pytest

pytest.importorskip("flask")
from flask import Flask
from werkzeug.exceptions import NotFound

from wepppy.weppcloud.routes._run_context import load_run_context


pytestmark = pytest.mark.routes


def test_load_run_context_aborts_404_on_invalid_grouped_runid() -> None:
    app = Flask(__name__)

    def bad_get_wd(*_args, **_kwargs) -> str:
        raise ValueError("Invalid grouped run identifier: batch;;bad")

    with app.test_request_context("/dummy"):
        with pytest.raises(NotFound) as excinfo:
            load_run_context("batch;;bad", "0", get_wd_fn=bad_get_wd)

    assert excinfo.value.code == 404
    assert "Invalid grouped run identifier" in excinfo.value.description


def test_load_run_context_ignores_pup_query_for_grouped_runids(tmp_path: Path) -> None:
    app = Flask(__name__)
    run_root = tmp_path / "run"
    run_root.mkdir()

    def good_get_wd(*_args, **_kwargs) -> str:
        return str(run_root)

    with app.test_request_context("/dummy?pup=omni/scenarios/test"):
        ctx = load_run_context("batch;;spring-2025;;run-001", "0", get_wd_fn=good_get_wd)

    assert ctx.pup_relpath is None
    assert ctx.pup_root is None
    assert ctx.active_root == ctx.run_root


def test_load_run_context_honors_pup_query_for_simple_runids(tmp_path: Path) -> None:
    app = Flask(__name__)
    run_root = tmp_path / "run"
    pup_root = run_root / "_pups" / "omni" / "scenarios" / "test"
    pup_root.mkdir(parents=True)

    def good_get_wd(*_args, **_kwargs) -> str:
        return str(run_root)

    with app.test_request_context("/dummy?pup=omni/scenarios/test"):
        ctx = load_run_context("ab-newrun", "0", get_wd_fn=good_get_wd)

    assert ctx.pup_relpath == "omni/scenarios/test"
    assert ctx.pup_root == pup_root.resolve()
    assert ctx.active_root == pup_root.resolve()

