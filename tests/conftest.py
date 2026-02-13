import importlib
import sys
from typing import Any

import pytest

from tests.factories.fixtures import rq_environment, rq_recorder  # noqa: F401


def pytest_configure(config) -> None:
    """Register custom markers used across the suite."""
    config.addinivalue_line("markers", "unit: Fast, isolated unit tests")
    config.addinivalue_line("markers", "integration: Cross-module integration tests")
    config.addinivalue_line("markers", "microservice: Exercises external microservices")
    config.addinivalue_line("markers", "routes: Flask/HTTP route tests")
    config.addinivalue_line("markers", "nodb: NoDb controller and locking tests")
    config.addinivalue_line("markers", "slow: Tests with timing dependencies (>2s)")
    config.addinivalue_line("markers", "requires_network: Tests that reach external services")


@pytest.fixture(autouse=True)
def _clear_secret_file_env(monkeypatch: pytest.MonkeyPatch) -> None:
    """Ensure host-configured `*_FILE` vars do not leak into unit tests."""

    for key in (
        "ADMIN_PASSWORD_FILE",
        "AGENT_JWT_SECRET_FILE",
        "CAP_SECRET_FILE",
        "CLIMATE_ENGINE_API_KEY_FILE",
        "DTALE_INTERNAL_TOKEN_FILE",
        "OAUTH_GITHUB_CLIENT_SECRET_FILE",
        "OAUTH_GOOGLE_CLIENT_SECRET_FILE",
        "OAUTH_ORCID_CLIENT_SECRET_FILE",
        "OPENET_API_KEY_FILE",
        "OPENTOPOGRAPHY_API_KEY_FILE",
        "POSTGRES_PASSWORD_FILE",
        "REDIS_PASSWORD_FILE",
        "SECRET_KEY_FILE",
        "SECURITY_PASSWORD_SALT_FILE",
        "WC_TOKEN_FILE",
        "WEPP_AUTH_JWT_SECRET_FILE",
        "WEPP_AUTH_JWT_SECRETS_FILE",
        "WEPP_MCP_JWT_SECRET_FILE",
        "ZOHO_NOREPLY_EMAIL_PASSWORD_FILE",
    ):
        monkeypatch.delenv(key, raising=False)


@pytest.fixture(scope="session", autouse=True)
def _ensure_all_your_base() -> None:
    module = importlib.import_module("wepppy.all_your_base")
    sys.modules["wepppy.all_your_base"] = module


@pytest.fixture(scope="session", autouse=True)
def _install_redis_stub():
    try:
        redis_module = importlib.import_module("redis")
    except Exception:  # pragma: no cover - redis may be unavailable
        redis_module = None  # type: ignore[assignment]

    if not redis_module:
        yield
        return

    original_cls: Any = getattr(redis_module, "Redis", None)

    class RecordingRedis:
        def __init__(self, *args, **kwargs):
            self.args = args
            self.kwargs = dict(kwargs)
            self.store = {}
            self.hashes = {}
            self.published = []

        def set(self, key, value, *args, **kwargs):
            self.store[key] = value
            return True

        def get(self, key):
            return self.store.get(key)

        def delete(self, key):
            self.store.pop(key, None)

        def hset(self, name, key, value):
            bucket = self.hashes.setdefault(name, {})
            bucket[key] = value
            return 1

        def hget(self, name, key):
            return self.hashes.get(name, {}).get(key)

        def hgetall(self, name):
            return dict(self.hashes.get(name, {}))

        def hdel(self, name, key):
            bucket = self.hashes.get(name)
            if bucket and key in bucket:
                del bucket[key]
                return 1
            return 0

        def publish(self, channel, message):
            self.published.append((channel, message))
            return 1

    redis_module.Redis = RecordingRedis

    try:
        redis_settings = importlib.import_module("wepppy.config.redis_settings")
        if getattr(redis_settings, "redis", None):
            redis_settings.redis.Redis = RecordingRedis  # type: ignore[attr-defined]
    except Exception:  # pragma: no cover - import safety
        pass

    yield

    if original_cls is not None:
        redis_module.Redis = original_cls
        try:
            redis_settings = importlib.import_module("wepppy.config.redis_settings")
            if getattr(redis_settings, "redis", None):
                redis_settings.redis.Redis = original_cls  # type: ignore[attr-defined]
        except Exception:  # pragma: no cover - import safety
            pass


@pytest.fixture(scope="session", autouse=True)
def _import_nodb_base() -> None:
    try:
        base_module = importlib.import_module("wepppy.nodb.base")
        nodb_pkg = importlib.import_module("wepppy.nodb")
        root_pkg = importlib.import_module("wepppy")
        setattr(root_pkg, "nodb", nodb_pkg)
        setattr(nodb_pkg, "base", base_module)
    except Exception:
        pass

    try:
        profile_pkg = importlib.import_module("wepppy.profile_recorder")
        root_pkg = importlib.import_module("wepppy")
        setattr(root_pkg, "profile_recorder", profile_pkg)
    except Exception:
        pass


@pytest.fixture(scope="session", autouse=True)
def _ensure_wepppy_namespace() -> None:
    """Ensure key subpackages are attached to the root wepppy module."""
    root_pkg = importlib.import_module("wepppy")
    for name in ("locales", "weppcloud", "rq"):
        try:
            submod = importlib.import_module(f"wepppy.{name}")
            setattr(root_pkg, name, submod)
        except Exception:
            continue
