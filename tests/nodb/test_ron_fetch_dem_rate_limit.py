from __future__ import annotations

import logging
import math
import threading
import time as _time
from pathlib import Path
from types import SimpleNamespace

import pytest

import wepppy.nodb.core.ron as ron_module
from wepppy.nodb.core.ron import Ron

pytestmark = [pytest.mark.unit, pytest.mark.nodb]


class _FakeRedis:
    def __init__(
        self,
        *,
        eval_delay_threshold: float | None = None,
        eval_delay_seconds: float = 0.0,
    ) -> None:
        self.values: dict[str, str] = {}
        self.expiry: dict[str, int] = {}
        self.eval_calls: int = 0
        self._lock = threading.Lock()
        self._eval_delay_threshold = eval_delay_threshold
        self._eval_delay_seconds = float(eval_delay_seconds)

    def get(self, key: str) -> str | None:
        with self._lock:
            return self.values.get(key)

    def set(self, key: str, value: str) -> bool:
        with self._lock:
            self.values[key] = str(value)
        return True

    def incr(self, key: str) -> int:
        with self._lock:
            try:
                current = int(self.values.get(key, "0"))
            except (TypeError, ValueError):
                current = 0
            current += 1
            self.values[key] = str(current)
            return current

    def expire(self, key: str, seconds: int) -> bool:
        with self._lock:
            self.expiry[key] = int(seconds)
        return True

    def eval(self, _script: str, numkeys: int, *args: str) -> str:
        assert numkeys == 1
        key = str(args[0])
        requested = float(args[1])

        if self._eval_delay_threshold is not None and requested < self._eval_delay_threshold:
            _time.sleep(self._eval_delay_seconds)

        with self._lock:
            self.eval_calls += 1
            raw_current = self.values.get(key, "0")
            try:
                current = float(raw_current)
            except (TypeError, ValueError):
                current = 0.0
            if not math.isfinite(current) or current <= 0.0:
                current = 0.0

            blocked_until = max(current, requested)
            blocked_str = f"{blocked_until:.3f}"
            self.values[key] = blocked_str
            return blocked_str

    def close(self) -> None:
        return None


class _FakeClock:
    def __init__(self, now: float) -> None:
        self.now = float(now)
        self.sleeps: list[float] = []

    def time(self) -> float:
        return self.now

    def sleep(self, seconds: float) -> None:
        wait = float(seconds)
        self.sleeps.append(wait)
        self.now += wait


class _DummyPrep:
    def timestamp(self, _task: object) -> None:
        return None


class _DummyRedisPrep:
    @staticmethod
    def getInstance(_wd: str) -> _DummyPrep:
        return _DummyPrep()


def _make_detached_ron(tmp_path: Path) -> Ron:
    dem_dir = tmp_path / "dem"
    dem_dir.mkdir(parents=True, exist_ok=True)

    ron = object.__new__(Ron)
    ron.wd = str(tmp_path)
    ron._dem_db = "opentopo://COP30"
    ron._dem_is_vrt = False
    ron.config_get_str = lambda *_args, **_kwargs: "opentopo://COP30"
    ron._map = SimpleNamespace(
        extent=[-120.5, 38.5, -120.4, 38.6],
        cellsize=30.0,
    )

    logger = logging.getLogger(f"tests.ron.fetch_dem.{tmp_path.name}")
    logger.handlers = []
    logger.addHandler(logging.NullHandler())
    ron.logger = logger
    return ron


def _patch_fetch_dem_dependencies(
    monkeypatch: pytest.MonkeyPatch,
    fake_redis: _FakeRedis,
    clock: _FakeClock,
) -> None:
    monkeypatch.setattr(ron_module, "redis_connection_kwargs", lambda *_args, **_kwargs: {})
    monkeypatch.setattr(ron_module.redis, "Redis", lambda **_kwargs: fake_redis)
    monkeypatch.setattr(ron_module.time, "time", clock.time)
    monkeypatch.setattr(ron_module.time, "sleep", clock.sleep)
    monkeypatch.setattr(ron_module, "RedisPrep", _DummyRedisPrep)
    monkeypatch.setattr(ron_module, "update_catalog_entry", lambda *_args, **_kwargs: None)


def test_fetch_dem_uses_default_150_second_block_when_rate_cap_hit(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    ron = _make_detached_ron(tmp_path)
    fake_redis = _FakeRedis()
    clock = _FakeClock(1000.0)

    minute_key = f"{ron_module._OPENTOPO_MINUTE_KEY_PREFIX}:{int(clock.time() // 60)}"
    fake_redis.values[minute_key] = "1"

    monkeypatch.setenv("OPENTOPO_MAX_REQUESTS_PER_MINUTE", "1")
    monkeypatch.delenv("OPENTOPO_BLOCK_SECONDS", raising=False)
    monkeypatch.delenv("OPENTOPO_PENALTY_BLOCK_SECONDS", raising=False)

    _patch_fetch_dem_dependencies(monkeypatch, fake_redis, clock)

    def _fake_retrieve(
        _extent: tuple[float, float, float, float],
        dst_fn: str,
        _cellsize: float,
        dataset: str = "SRTMGL1_E",
        resample: str = "bilinear",
    ) -> None:
        assert dataset.startswith("opentopo://")
        assert resample == "bilinear"
        Path(dst_fn).write_bytes(b"dem")

    monkeypatch.setattr(ron_module, "opentopo_retrieve", _fake_retrieve)

    ron.fetch_dem()

    blocked_until = float(fake_redis.values[ron_module._OPENTOPO_BLOCK_UNTIL_KEY])
    assert blocked_until == pytest.approx(1150.0, abs=0.01)
    assert sum(clock.sleeps) == pytest.approx(150.0, abs=0.01)
    assert fake_redis.eval_calls >= 1
    assert Path(ron.dem_fn).exists()


def test_fetch_dem_sets_10_minute_penalty_block_on_429(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    ron = _make_detached_ron(tmp_path)
    fake_redis = _FakeRedis()
    clock = _FakeClock(2000.0)

    monkeypatch.delenv("OPENTOPO_PENALTY_BLOCK_SECONDS", raising=False)
    monkeypatch.setenv("OPENTOPO_MAX_REQUESTS_PER_MINUTE", "50")

    _patch_fetch_dem_dependencies(monkeypatch, fake_redis, clock)

    def _rate_limited_retrieve(*_args, **_kwargs) -> None:
        raise RuntimeError("OpenTopography DEM request failed (status=429).")

    monkeypatch.setattr(ron_module, "opentopo_retrieve", _rate_limited_retrieve)

    with pytest.raises(RuntimeError, match="status=429"):
        ron.fetch_dem()

    blocked_until = float(fake_redis.values[ron_module._OPENTOPO_BLOCK_UNTIL_KEY])
    assert blocked_until == pytest.approx(2600.0, abs=0.01)


def test_fetch_dem_sets_10_minute_penalty_block_on_401_vendor_throttle_response(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    ron = _make_detached_ron(tmp_path)
    fake_redis = _FakeRedis()
    clock = _FakeClock(2500.0)

    monkeypatch.delenv("OPENTOPO_PENALTY_BLOCK_SECONDS", raising=False)
    monkeypatch.setenv("OPENTOPO_MAX_REQUESTS_PER_MINUTE", "50")

    _patch_fetch_dem_dependencies(monkeypatch, fake_redis, clock)

    def _ot_vendor_throttle_response(*_args, **_kwargs) -> None:
        # OpenTopography can emit 401 for throttling responses.
        raise RuntimeError("OpenTopography DEM request failed (status=401).")

    monkeypatch.setattr(ron_module, "opentopo_retrieve", _ot_vendor_throttle_response)

    with pytest.raises(RuntimeError, match="status=401"):
        ron.fetch_dem()

    blocked_until = float(fake_redis.values[ron_module._OPENTOPO_BLOCK_UNTIL_KEY])
    assert blocked_until == pytest.approx(3100.0, abs=0.01)


def test_fetch_dem_ignores_non_finite_block_key_values(
    monkeypatch: pytest.MonkeyPatch,
    tmp_path: Path,
) -> None:
    ron = _make_detached_ron(tmp_path)
    fake_redis = _FakeRedis()
    clock = _FakeClock(3000.0)

    fake_redis.values[ron_module._OPENTOPO_BLOCK_UNTIL_KEY] = "inf"

    monkeypatch.setenv("OPENTOPO_MAX_REQUESTS_PER_MINUTE", "50")
    _patch_fetch_dem_dependencies(monkeypatch, fake_redis, clock)

    def _fake_retrieve(
        _extent: tuple[float, float, float, float],
        dst_fn: str,
        _cellsize: float,
        **_kwargs,
    ) -> None:
        Path(dst_fn).write_bytes(b"dem")

    monkeypatch.setattr(ron_module, "opentopo_retrieve", _fake_retrieve)

    ron.fetch_dem()

    assert clock.sleeps == []
    assert Path(ron.dem_fn).exists()


def test_set_opentopo_block_until_uses_atomic_redis_eval_under_concurrency(
    tmp_path: Path,
) -> None:
    ron = _make_detached_ron(tmp_path)
    fake_redis = _FakeRedis(eval_delay_threshold=1500.0, eval_delay_seconds=0.05)

    barrier = threading.Barrier(3)
    errors: list[Exception] = []

    def _worker(requested_until: float) -> None:
        barrier.wait(timeout=2)
        try:
            ron._set_opentopo_block_until(fake_redis, requested_until=requested_until)
        except Exception as exc:  # pragma: no cover - diagnostic path
            errors.append(exc)

    high = threading.Thread(target=_worker, args=(4000.0,))
    low = threading.Thread(target=_worker, args=(3500.0,))
    high.start()
    low.start()
    barrier.wait(timeout=2)
    high.join(timeout=2)
    low.join(timeout=2)

    assert errors == []
    assert float(fake_redis.values[ron_module._OPENTOPO_BLOCK_UNTIL_KEY]) == pytest.approx(4000.0, abs=0.01)
    assert fake_redis.eval_calls == 2


def test_extract_status_code_supports_multiple_status_shapes() -> None:
    class _RuntimeLikeError(RuntimeError):
        def __init__(self, *args: object, status_code: int | None = None) -> None:
            super().__init__(*args)
            self.status_code = status_code

    class _ResponseBackedError(RuntimeError):
        def __init__(self, *args: object) -> None:
            super().__init__(*args)
            self.response = SimpleNamespace(status_code=429)

    assert Ron._extract_status_code(_RuntimeLikeError("x", status_code=401)) == 401
    assert Ron._extract_status_code(_ResponseBackedError("x")) == 429
    assert Ron._extract_status_code(RuntimeError("OpenTopography status code: 429")) == 429
    assert Ron._extract_status_code(RuntimeError("OpenTopography DEM request failed.")) is None
