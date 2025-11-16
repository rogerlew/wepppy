import traceback

import pytest

from wepppy.rq.exception_logging import with_exception_logging


@pytest.mark.unit
def test_with_exception_logging_appends_trace(tmp_path, monkeypatch):
    # Redirect get_wd to a temp run directory
    monkeypatch.setattr("wepppy.rq.exception_logging.get_wd", lambda runid: str(tmp_path))

    @with_exception_logging
    def boom(runid: str) -> None:
        raise ValueError("boom")

    with pytest.raises(ValueError):
        boom("sample-run")

    log_path = tmp_path / "exceptions.log"
    assert log_path.exists(), "exceptions.log should be created on failure"
    contents = log_path.read_text()
    assert "boom" in contents
    assert "ValueError" in contents
    assert "boom failed" in contents


@pytest.mark.unit
def test_with_exception_logging_handles_kwargs_runid(tmp_path, monkeypatch):
    monkeypatch.setattr("wepppy.rq.exception_logging.get_wd", lambda runid: str(tmp_path))

    @with_exception_logging
    def boom(*, runid: str) -> None:
        raise RuntimeError("kaboom")

    with pytest.raises(RuntimeError):
        boom(runid="kw-run")

    contents = (tmp_path / "exceptions.log").read_text()
    assert "kaboom" in contents
