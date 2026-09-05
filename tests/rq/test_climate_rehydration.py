from __future__ import annotations

import json
import os
from pathlib import Path

import pytest

from tests.nodb.lock_contention_utils import ensure_climate_stub
from wepppy.nodb import base as nodb_base
from wepppy.nodb.base import NoDbStaleWriteError
from wepppy.nodb.core.climate import Climate
from wepppy.weppcloud.utils import helpers
from wepppy.nodb import batch_runner as batch_runner_module
from wepppy.rq import culvert_rq as culvert_rq_module


pytestmark = [pytest.mark.unit, pytest.mark.nodb]


class _Cache:
    def __init__(self) -> None:
        self.store: dict[str, object] = {}

    def set(self, key: str, value: object, *args, **kwargs) -> bool:
        self.store[str(key)] = value
        return True

    def get(self, key: str):
        return self.store.get(str(key))

    def scan_iter(self, *, match: str):
        prefix = match.removesuffix("*")
        yield from (key for key in tuple(self.store) if key.startswith(prefix))

    def delete(self, key: str) -> int:
        return int(self.store.pop(str(key), None) is not None)


def _persist_generation(wd: Path, value: str) -> None:
    detached = Climate.load_detached(str(wd))
    assert detached is not None
    detached.lock()
    try:
        detached._test_generation = value
        detached.dump()
    finally:
        detached.unlock()


def _prepare_interleaved_climate(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> tuple[Path, str, Climate, _Cache, str]:
    ensure_climate_stub(str(tmp_path))
    Climate._instances.clear()
    early = Climate.getInstance(str(tmp_path))
    with early.locked():
        early._test_generation = "old"

    cache = _Cache()
    monkeypatch.setattr(nodb_base, "redis_nodb_cache_client", cache)
    monkeypatch.setattr(helpers, "get_wd", lambda _runid: str(tmp_path))

    before = os.stat(early._nodb)
    target_size = before.st_size
    candidate = "new"
    for attempt in range(12):
        _persist_generation(tmp_path, candidate)
        after = os.stat(early._nodb)
        if after.st_size == target_size:
            assert after.st_mtime != before.st_mtime
            break
        if after.st_size > target_size:
            candidate = candidate[:-1] or "n"
        else:
            candidate += "x"
    else:
        raise AssertionError("could not produce a same-size Climate NoDb rewrite")

    assert early._nodb_mtime != after.st_mtime
    assert early._nodb_size == target_size

    with pytest.raises(NoDbStaleWriteError):
        with early.locked():
            early._test_generation = "stale"

    current = Climate.load_detached(str(tmp_path))
    assert current is not None
    return tmp_path, "batch;;demo;;leaf", early, cache, current._test_generation


@pytest.mark.parametrize(
    ("builder", "runid"),
    [
        (
            batch_runner_module._build_climate_at_mutation_boundary,
            "batch;;demo;;leaf",
        ),
        (
            culvert_rq_module._build_climate_at_mutation_boundary,
            "culvert;;demo;;leaf",
        ),
    ],
)
def test_climate_boundary_rehydrates_after_same_size_generation_advance(
    builder,
    runid: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    wd, _, early, cache, generation = _prepare_interleaved_climate(tmp_path, monkeypatch)
    events: list[str] = []

    def _build(current: Climate) -> None:
        events.append(getattr(current, "_test_generation"))
        with current.locked():
            current._test_generation = "run"

    monkeypatch.setattr(Climate, "build", _build)
    current = builder(runid, str(wd))

    assert current._test_generation == "run"
    assert events == [generation]
    assert current is early
    assert str(Path(current._nodb)) in cache.store
    persisted = Climate.load_detached(str(wd))
    assert persisted is not None
    assert persisted._test_generation == "run"


@pytest.mark.parametrize(
    ("module", "builder", "runid"),
    [
        (
            batch_runner_module,
            batch_runner_module._build_climate_at_mutation_boundary,
            "batch;;demo;;leaf",
        ),
        (
            culvert_rq_module,
            culvert_rq_module._build_climate_at_mutation_boundary,
            "culvert;;demo;;leaf",
        ),
    ],
)
def test_climate_boundary_uses_exact_scoped_clear_before_hydration(
    module,
    builder,
    runid: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    events: list[object] = []
    current = object.__new__(Climate)

    def _clear(actual_runid: str, *, pup_relpath: str) -> None:
        events.append(("clear", actual_runid, pup_relpath))

    def _get_instance(wd: str):
        events.append(("hydrate", wd))
        return current

    def _build(self: object) -> None:
        events.append(("build", self))

    monkeypatch.setattr(module, "clear_nodb_file_cache", _clear)
    monkeypatch.setattr(module.Climate, "getInstance", _get_instance)
    monkeypatch.setattr(module.Climate, "build", _build)

    result = builder(runid, str(tmp_path))

    assert result is current
    assert events == [
        ("clear", runid, "climate.nodb"),
        ("hydrate", str(tmp_path)),
        ("build", current),
    ]


@pytest.mark.parametrize("state", ["absent", "empty", "malformed"])
@pytest.mark.parametrize(
    ("builder", "runid"),
    [
        (
            batch_runner_module._build_climate_at_mutation_boundary,
            "batch;;demo;;leaf",
        ),
        (
            culvert_rq_module._build_climate_at_mutation_boundary,
            "culvert;;demo;;leaf",
        ),
    ],
)
def test_climate_boundary_preserves_explicit_invalid_state_failures(
    builder,
    runid: str,
    state: str,
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    Climate._instances.clear()
    monkeypatch.setattr(nodb_base, "redis_nodb_cache_client", _Cache())
    monkeypatch.setattr(helpers, "get_wd", lambda _runid: str(tmp_path))
    climate_path = tmp_path / "climate.nodb"
    if state == "empty":
        climate_path.write_text("", encoding="utf-8")
    elif state == "malformed":
        climate_path.write_text("not-json", encoding="utf-8")

    with pytest.raises((FileNotFoundError, json.JSONDecodeError, TypeError, ValueError)):
        builder(runid, str(tmp_path))
