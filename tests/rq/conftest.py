"""Explicit boundary fixtures for RQ orchestration unit tests."""
from pathlib import Path

import pytest


@pytest.fixture
def record_nodb_cache_clear(monkeypatch: pytest.MonkeyPatch):
    """Install an explicit recorder at an orchestration module's cache boundary."""
    def install(module):
        calls: list[tuple[str, str]] = []

        def clear(runid: str, *, pup_relpath: str) -> list[Path]:
            calls.append((runid, pup_relpath))
            return []

        monkeypatch.setattr(module, "clear_nodb_file_cache", clear)
        return calls

    return install


@pytest.fixture
def wepp_cache_clear_calls(record_nodb_cache_clear) -> list[tuple[str, str]]:
    import wepppy.rq.wepp_rq as wepp_rq

    return record_nodb_cache_clear(wepp_rq)
