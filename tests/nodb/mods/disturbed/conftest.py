from __future__ import annotations

from contextlib import contextmanager
from pathlib import Path
from typing import Iterator, Tuple

import pytest

from wepppy.nodb.mods.disturbed.disturbed import Disturbed


class NoopLogger:
    def info(self, *_args: object, **_kwargs: object) -> None:
        return

    def warning(self, *_args: object, **_kwargs: object) -> None:
        return

    def debug(self, *_args: object, **_kwargs: object) -> None:
        return

    def log(self, *_args: object, **_kwargs: object) -> None:
        return


@contextmanager
def null_context() -> Iterator[None]:
    yield


@pytest.fixture
def disturbed_factory(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
):
    """Create detached Disturbed instances for focused unit tests."""

    monkeypatch.setattr(
        Disturbed,
        "locked",
        lambda self, validate_on_success=True: null_context(),
    )
    monkeypatch.setattr(
        Disturbed,
        "timed",
        lambda self, _task_name, level=20: null_context(),
    )

    def _factory(run_name: str = "run") -> Tuple[Disturbed, Path]:
        run_dir = tmp_path / run_name
        (run_dir / "disturbed").mkdir(parents=True, exist_ok=True)
        (run_dir / "wepp" / "runs").mkdir(parents=True, exist_ok=True)
        (run_dir / "soils").mkdir(parents=True, exist_ok=True)

        disturbed = Disturbed.__new__(Disturbed)
        disturbed.wd = str(run_dir)
        disturbed.logger = NoopLogger()
        disturbed._h0_max_om = 0.15
        disturbed._sol_ver = 9005.0
        disturbed._burn_shrubs = True
        disturbed._burn_grass = False
        disturbed._sbs_mode = 0
        disturbed._uniform_severity = None
        return disturbed, run_dir

    return _factory
